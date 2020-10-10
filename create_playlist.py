import json
from secrets import spotify_user_id
from constants import SPOTIFY_API_URL, HEADERS
import requests


class CreatePlaylist:

    # Step 1: log into youtube
    def get_youtube_client(self):
        pass

    # Step 2: get liked videos
    def get_liked_videos(self):
        pass

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