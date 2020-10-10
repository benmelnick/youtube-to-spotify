from secrets import spotify_api_token

# URLs
SPOTIFY_API_URL = "https://api/spotify.com/v1"
YOUTUBE_API_URL = "https://www.googleapis.com/auth/youtube.readonly"

# HTTP request headers
HEADERS = {
    "Content-Type": "application/json",
    "Authorization": "Bearer {}".format(spotify_api_token)
}
