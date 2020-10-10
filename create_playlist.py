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

        youtube_client = googleapiclient.build(api_service_name, api_version, credentials=credentials)

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
            youtube_url = YOUTUBE_URL.format(item["id"])

            # use youtube_dl to collect song name and artist name
            # given the video URL, return the song name and artist - use this info to query spotify
            video = youtube_dl.YoutubeDL({}).extract_info(youtube_url, download=False)
            song_name = video["track"]
            artist = video["artist"]

            self.all_liked_songs[video_title] = {
                "youtube_url": youtube_url,
                "song_name": song_name,
                "artist": artist,
                # fetch the spotify link at the same time as the liked youtube video
                "spotify_uri": self.get_spotify_uri(song_name, artist)
            }

    """
    Step 3: create a new playlist in spotify
    calls spotify api to create playlist
    """
    def create_playlist(self):
        request_body = json.dump({
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
        query = SPOTIFY_API_URL + "/search?query=track%3A{}+artists%3A{}&type=track&offset=0&limit=20".format(
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
        uri = songs[0]

        return uri

    # Step 5: add song to new playlist
    def add_song_to_playlist(self):
        pass