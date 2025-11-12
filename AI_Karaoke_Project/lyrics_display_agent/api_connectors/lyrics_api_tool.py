import requests

class LyricsAPIConnector:
    def __init__(self, api_url):
        self.api_url = api_url

    def fetch_lyrics(self, song_title, artist_name):
        response = requests.get(self.api_url, params={'title': song_title, 'artist': artist_name})
        if response.status_code == 200:
            return response.json().get('lyrics', 'Lyrics not found')
        else:
            return 'Error fetching lyrics'

# Example usage:
# connector = LyricsAPIConnector('https://api.lyrics.ovh/v1')
# lyrics = connector.fetch_lyrics('Shape of You', 'Ed Sheeran')
# print(lyrics)