import lyricsgenius
import os
from dotenv import load_dotenv

load_dotenv()
token = os.getenv("GENIUS_ACCESS_TOKEN")
# If token is in parent dir, load_dotenv might not find it if run from here without args, 
# but let's assume it's set or we pass it manually if needed.
# Actually, the previous run failed with 500, not 503, so the token WAS found.

if not token:
    # Try to read from ../.env manually just in case
    try:
        with open("../.env") as f:
            for line in f:
                if line.startswith("GENIUS_ACCESS_TOKEN"):
                    token = line.split("=")[1].strip()
                    break
    except:
        pass

print(f"Token found: {token[:5]}..." if token else "No token")

if token:
    genius = lyricsgenius.Genius(token)
    song = genius.search_song("Happy Birthday")
    if song:
        print("Song found!")
        print(f"Dir: {dir(song)}")
        print(f"ID: {song.id if hasattr(song, 'id') else 'No id attr'}")
        print(f"Dictionary: {song.to_dict().keys()}")
