from secrets import SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET
from constants import PLAYLIST_NAME, YOUTUBE_API_URL, YOUTUBE_URL, IGNORE
import os
import youtube_dl
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import sys

import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors

class CreatePlaylist:

    def __init__(self):
        self.youtube_client = self.get_youtube_client()
        self.spotify_client = self.get_spotify_client()
        self.all_liked_songs = {}
        self.user_id = self.get_user_id()
        self.playlist_id = self.get_playlist()
        self.cache = self.init_cache()

    """
    Step 1: log into youtube
    """
    def get_youtube_client(self):
        try:
            print("Initializing YouTube client...")
            # disable OAuthlib's HTTPS verification when running locally
            # DO NOT leave this enabled in production
            os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

            api_service_name = "youtube"
            api_version = "v3"
            client_secrets_file = "client_secret.json"

            # get credentials and create an API client
            scopes = [YOUTUBE_API_URL]
            flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(client_secrets_file, scopes)
            credentials = flow.run_console()

            youtube_client = googleapiclient.discovery.build(api_service_name, api_version, credentials=credentials)

            print("YouTube client initialized")
            return youtube_client
        except:
            sys.exit("Error initializing YouTube client")

    def get_spotify_client(self):
        try:
            print("Initializing Spotify client...")
            scope = "playlist-modify-public"
            sp = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id=SPOTIFY_CLIENT_ID, client_secret=SPOTIFY_CLIENT_SECRET,
                                                           redirect_uri="http://localhost:8080/callback", scope=scope))
            print("Spotify client initialized")
            return sp
        except Exception as e:
            print(e)
            print("Error initializing Spotify client")

    """
    Step 2: get liked videos
    places all of the important info into a dictionary
    """
    def get_liked_videos(self):
        request = self.youtube_client.videos().list(
            part="snippet,contentDetails,statistics",
            myRating="like"
        )
        response = request.execute()

        # collect each video and get the important info
        for item in response["items"]:
            video_title = item["snippet"]["title"]
            print(f"Found liked video {video_title}")
            youtube_url = YOUTUBE_URL.format(item["id"])

            # use youtube_dl to collect song name and artist name
            # given the video URL, return the song name and artist - use this info to query spotify
            video = youtube_dl.YoutubeDL({}).extract_info(item["id"], download=False)
            song_name = video["track"]
            artist = video["artist"]

            # only query spotify for the song name if youtube-dl could actually find it
            if song_name is not None:
                spotify_uri = self.get_spotify_uri(song_name, artist)
            else:
                # youtube-dl seems to only be working if the video is published with only the song name in the title
                # if youtube-dl didn't work, we know that the artist name is very likely in the title
                # need to filter the title to separate the two search parameters (song name and artist)
                print(f"youtube-dl could not find song name for video {video_title}")
                filtered_title = self.filter_title(video_title)
                spotify_uri = self.get_spotify_uri(filtered_title["track"], filtered_title["artist"])

            self.all_liked_songs[video_title] = {
                "youtube_url": youtube_url,
                "song_name": song_name,
                "artist": artist,
                # fetch the spotify link at the same time as the liked youtube video
                "spotify_uri": spotify_uri["uri"],
                "existsInPlaylist": spotify_uri["existsInCache"]
            }

    def filter_title(self, video_title):
        # todo: this method assume that the format is (artist) - (song name) - need to try the other way around
        print(f"Filtering {video_title}...")
        for ch in IGNORE:
            if ch in video_title:
                video_title = video_title.replace(ch, '')
        artist = (video_title.rsplit("-")[0]).strip()
        track = (video_title[len(artist) + 2:]).strip()

        return {"artist": artist, "track": track}

    def get_user_id(self):
        return self.spotify_client.current_user()["id"]

    """
    Step 3: create a new playlist in spotify
    calls spotify api to create playlist
    """
    def get_playlist(self):
        print(f"Fetching playlists for user {self.user_id}")

        # check to make sure the playlist already exists
        playlists = self.spotify_client.current_user_playlists()
        for playlist in playlists["items"]:
            if playlist["name"] == PLAYLIST_NAME:
                print(f"Playlist {PLAYLIST_NAME} already exists")
                playlist_id = playlist["id"]
                return playlist_id

        new_playlist = self.spotify_client.user_playlist_create(self.user_id, PLAYLIST_NAME,
                                                                description="My liked YouTube videos")
        playlist_id = new_playlist["id"]
        print(f"Created new playlist {playlist_id}")

        return playlist_id

    def init_cache(self):
        print("Populating cache...")
        cache = {}
        playlist_items = self.spotify_client.playlist_items(self.playlist_id)
        count = 0
        for item in playlist_items["items"]:
            uri = item["track"]["uri"]
            song_name = item["track"]["name"]
            cache[song_name] = uri
            count += 1
        print(f"Brought {count} song uri's into cache")

        return cache

    """ 
    Step 4: search for the song in spotify
    """
    def get_spotify_uri(self, song_name, artist):
        # check the cache
        for key in self.cache:
            if key.lower() in song_name.lower():
                print(f"Found {song_name} in cache")
                return {"uri": self.cache[key], "existsInCache": True}

        print(f"Searching Spotify for {song_name} by {artist}")
        search_query = "artist:{} track:{}".format(artist, song_name)

        search_result = self.spotify_client.search(search_query, limit=1, type='track', market=None)
        if search_result["tracks"]["total"] == 0:
            print(f"No Spotify results for song {song_name} by artist {artist}")
            uri = 0
        else:
            # return the URI
            print(f"Successfully found Spotify results for {song_name} by {artist}")
            uri = search_result["tracks"]["items"][-1]["uri"]
            actual_song_name = search_result["tracks"]["items"][-1]["name"]
            self.cache[actual_song_name] = uri

        return {"uri": uri, "existsInCache": False}

    """
    checks in the playlist to see if the song has been avoided - avoids duplicates
    """
    def song_does_not_exist(self, song_uri):
        # check the cache to see if song already exists in the playlist
        if song_uri in self.cache:
            return False
        else:
            # cache miss - add to the cache
            self.cache[song_uri] = 1
            return True
    """
    the main body of the code - calls all of the above methods in a single workflow
    """
    def add_song_to_playlist(self):
        # grab all of the information for songs
        self.get_liked_videos()

        # collect spotify uri of each song in liked videos
        uris = []
        for song, info in self.all_liked_songs.items():
            song_uri = info["spotify_uri"]
            if (song_uri is not 0) and (not info["existsInPlaylist"]):
                # add the uri's for songs that did not already exist
                uris.append(song_uri)

        if len(uris) == 0:
            print("No songs to add")
            return

        # add songs to playlist
        print(f"Adding {len(uris)} songs to playlist...")
        print(uris)
        response = self.spotify_client.playlist_add_items(self.playlist_id, uris)
        print(f"Successfully added {len(uris)} songs to playlist")
        print(response)


def run(cp):
    cp.add_song_to_playlist()


# main code
if __name__ == "__main__":
    create_playlist = CreatePlaylist()
    create_playlist.add_song_to_playlist()
    # schedule.every(1).minutes.do(run, create_playlist)
    #
    # while True:
    #     schedule.run_pending()
    #     time.sleep(1)

