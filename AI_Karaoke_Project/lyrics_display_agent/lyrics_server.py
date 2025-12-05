import logging
import lyricsgenius
import os
import json
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("LyricsAgent")

# Initialize FastMCP Server
mcp = FastMCP("Lyrics Display Agent")

# Initialize Genius Client
# User should provide GENIUS_ACCESS_TOKEN in .env
GENIUS_ACCESS_TOKEN = os.getenv("GENIUS_ACCESS_TOKEN")
genius = None
if GENIUS_ACCESS_TOKEN:
    genius = lyricsgenius.Genius(GENIUS_ACCESS_TOKEN)
else:
    logger.warning("GENIUS_ACCESS_TOKEN not found. Lyrics fetching will be limited or mocked.")

# Mock Database (Fallback)
lyrics_db = {
    "song1": {
        "song_id": "song1",
        "title": "Demo Song 1",
        "lyrics": [
            {"timestamp": 0.0, "text": "[Intro]"},
            {"timestamp": 5.0, "text": "Hello world, this is a test"},
            {"timestamp": 10.0, "text": "Singing along with the AI"},
            {"timestamp": 15.0, "text": "Karaoke night is the best"},
        ]
    }
}

def parse_genius_lyrics(lyrics_text: str) -> list:
    """
    Parses raw Genius lyrics into lines with estimated timestamps.
    """
    lines = lyrics_text.split('\n')
    parsed = []
    t = 0.0
    for line in lines:
        line = line.strip()
        if line:
            parsed.append({"timestamp": t, "text": line})
            t += 3.0 # Arbitrary 3 seconds per line
    return parsed

@mcp.tool()
def search_lyrics(query: str) -> str:
    """
    Searches for lyrics on Genius. Returns JSON string of the song object.
    """
    if not genius:
        # Fallback to mock if no token
        logger.warning("No Genius token. Returning mock lyrics.")
        return json.dumps(lyrics_db["song1"])

    try:
        logger.info(f"Searching Genius for: {query}")
        song = genius.search_song(query)
        if not song:
            return json.dumps({"error": "Song not found on Genius"})
        
        parsed_lyrics = parse_genius_lyrics(song.lyrics)
        
        # Access ID safely via to_dict()
        song_data = song.to_dict()
        song_id = str(song_data.get('id', 'unknown'))
        
        # Cache it (simple in-memory cache)
        song_obj = {
            "song_id": song_id,
            "title": song.title,
            "lyrics": parsed_lyrics
        }
        lyrics_db[song_id] = song_obj
        
        return json.dumps(song_obj)
        
    except Exception as e:
        logger.error(f"Genius search failed: {e}")
        return json.dumps({"error": str(e)})

@mcp.tool()
def get_lyrics(song_id: str) -> str:
    """
    Retrieves cached lyrics by song_id. Returns JSON string.
    """
    if song_id in lyrics_db:
        return json.dumps(lyrics_db[song_id])
    return json.dumps({"error": "Lyrics not found in cache. Use search_lyrics first."})

if __name__ == "__main__":
    print("🎤 Starting Lyrics Display Agent MCP Server...")
    mcp.run()