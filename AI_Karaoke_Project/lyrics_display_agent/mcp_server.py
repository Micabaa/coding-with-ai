import logging
import os
import re
import json
from typing import List, Optional, Dict, Any
from mcp.server.fastmcp import FastMCP
import lyricsgenius
import syncedlyrics
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("LyricsMCP")

# Initialize FastMCP Server
mcp = FastMCP("Lyrics Agent")

# Initialize Genius Client
GENIUS_ACCESS_TOKEN = os.getenv("GENIUS_ACCESS_TOKEN")
genius = None
if GENIUS_ACCESS_TOKEN:
    genius = lyricsgenius.Genius(GENIUS_ACCESS_TOKEN)
else:
    logger.warning("GENIUS_ACCESS_TOKEN not found. Text-only fallback will be limited.")

def parse_lrc(lrc_text: str) -> List[Dict[str, Any]]:
    """Parses LRC format strings: [mm:ss.xx] Lyric text"""
    lines = lrc_text.split('\n')
    parsed = []
    regex = re.compile(r'\[(\d+):(\d+(?:\.\d+)?)\](.*)')
    
    for line in lines:
        match = regex.match(line.strip())
        if match:
            minutes = int(match.group(1))
            seconds = float(match.group(2))
            text = match.group(3).strip()
            total_seconds = minutes * 60 + seconds
            if text:
                parsed.append({"timestamp": total_seconds, "text": text})
    return parsed

def parse_genius_lyrics(lyrics_text: str) -> List[Dict[str, Any]]:
    """Parses raw Genius lyrics (text only). Assigns dummy timestamps."""
    lines = lyrics_text.split('\n')
    parsed = []
    t = 0.0
    for line in lines:
        line = line.strip()
        if line:
            parsed.append({"timestamp": t, "text": line})
            t += 4.0 
    return parsed

@mcp.tool()
def search_lyrics(query: str) -> str:
    """
    Searches for lyrics for a given song query.
    First tries to find synced lyrics (LRC), then falls back to Genius (text only).
    
    Args:
        query: Song title and artist (e.g. "Bohemian Rhapsody Queen")
        
    Returns:
        JSON string containing song title, id, and list of lyric lines with timestamps.
    """
    try:
        logger.info(f"Searching syncedlyrics for: {query}")
        lrc_content = syncedlyrics.search(query)
        
        if lrc_content:
            logger.info("Found synced lyrics!")
            parsed_lyrics = parse_lrc(lrc_content)
            song_id = re.sub(r'\W+', '_', query.lower())
            
            result = {
                "song_id": song_id,
                "title": query.title(),
                "lyrics": parsed_lyrics,
                "synced": True
            }
            return json.dumps(result)
            
    except Exception as e:
        logger.error(f"Syncedlyrics search failed: {e}")

    # Fallback to Genius
    if not genius:
        return json.dumps({"error": "Genius API token not configured and no synced lyrics found."})

    try:
        logger.info(f"Searching Genius for: {query}")
        song = genius.search_song(query)
        if not song:
            return json.dumps({"error": "Song not found on Genius or SyncedLyrics"})
        
        parsed_lyrics = parse_genius_lyrics(song.lyrics)
        song_data = song.to_dict()
        song_id = str(song_data.get('id', 'unknown'))
        
        result = {
            "song_id": song_id,
            "title": song.title,
            "lyrics": parsed_lyrics,
            "synced": False
        }
        return json.dumps(result)
        
    except Exception as e:
        logger.error(f"Genius search failed: {e}")
        return json.dumps({"error": str(e)})

if __name__ == "__main__":
    mcp.run()
