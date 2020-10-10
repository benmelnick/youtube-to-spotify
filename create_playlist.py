import json
from secrets import spotify_user_id
from constants import SPOTIFY_API_URL, YOUTUBE_API_URL, YOUTUBE_URL, HEADERS
import requests
import os
import youtube_dl

import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors

class CreatePlaylist:

    def __init__(self):
        self.youtube_client = self.get_youtube_client()
        self.all_liked_songs = {}

    """
    Step 1: log into youtube
    """
    def get_youtube_client(self):
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

        return youtube_client

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

            spotify_uri = None
            # only query spotify for the song name if youtube-dl could actually find it
            if song_name is not None:
                spotify_uri = self.get_spotify_uri(song_name, artist)
            else:
                print(f"youtube-dl could not find song name for video {video_title}")

            self.all_liked_songs[video_title] = {
                "youtube_url": youtube_url,
                "song_name": song_name,
                "artist": artist,
                # fetch the spotify link at the same time as the liked youtube video
                "spotify_uri": spotify_uri
            }

    """
    Step 3: create a new playlist in spotify
    calls spotify api to create playlist
    """
    def create_playlist(self):
        request_body = json.dumps({
            "name": "YouTube Likes",
            "description": "My liked YouTube videos",
            "public": True
        })

        query = SPOTIFY_API_URL + "/users/{}/playlists".format(spotify_user_id)
        response = requests.post(
            query,
            data=request_body,
            headers=HEADERS
        )
        response_json = response.json()

        return response_json["id"]

    """ 
    Step 4: search for the song in spotify
    """
    def get_spotify_uri(self, song_name, artist):
        query = SPOTIFY_API_URL + "/search?query=track%3A{}+artist%3A{}&type=track&offset=0&limit=20".format(
            song_name,
            artist
        )
        response = requests.get(
            query,
            headers=HEADERS
        )
        response_json = response.json()
        songs = response_json["tracks"]["items"]

        # use just the first song
        try:
            uri = songs[0]["uri"]
            return uri
        except IndexError:
            print(F"no Spotify results for song {song_name} by artist {artist}")

    """
    the main body of the code - calls all of the above methods in a single workflow
    """
    def add_song_to_playlist(self):
        # grab all of the information for songs
        self.get_liked_videos()

        # collect spotify uri of each song in liked videos
        uris = []
        for song, info in self.all_liked_songs.items():
            uri = info["spotify_uri"]
            if uri is not None:
                uris.append(uri)

        # create new playlist on spotify
        playlist_id = self.create_playlist()

        request_body = json.dumps({
            "uris": uris
        })
        query = SPOTIFY_API_URL + "/playlists/{}/tracks".format(playlist_id)

        response = requests.put(
            query,
            data=request_body,
            headers=HEADERS
        )
        response_json = response.json()

        return response_json


if __name__ == '__main__':
    cp = CreatePlaylist()
    cp.add_song_to_playlist()