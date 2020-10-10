from secrets import spotify_api_token

SPOTIFY_API_URL = "https://api/spotify.com/v1"
HEADERS = {
    "Content-Type": "application/json",
    "Authorization": "Bearer {}".format(spotify_api_token)
}
