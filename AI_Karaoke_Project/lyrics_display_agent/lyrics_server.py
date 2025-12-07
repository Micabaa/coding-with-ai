from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import logging
import lyricsgenius
import syncedlyrics
import os
import re
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Lyrics Display Agent")

# Initialize Genius Client (Fallback)
GENIUS_ACCESS_TOKEN = os.getenv("GENIUS_ACCESS_TOKEN")
genius = None
if GENIUS_ACCESS_TOKEN:
    genius = lyricsgenius.Genius(GENIUS_ACCESS_TOKEN)
else:
    logger.warning("GENIUS_ACCESS_TOKEN not found. Text-only fallback will be limited.")

# Data Models
class LyricLine(BaseModel):
    timestamp: float
    text: str

class SongLyrics(BaseModel):
    song_id: str
    title: str
    lyrics: List[LyricLine]
    synced: bool = False

class SearchRequest(BaseModel):
    query: str

class SyncRequest(BaseModel):
    timestamp: float
    song_id: str

# Mock Database & Cache
lyrics_cache = {
    "song1": SongLyrics(
        song_id="song1",
        title="Demo Song 1",
        lyrics=[
            LyricLine(timestamp=0.0, text="[Intro]"),
            LyricLine(timestamp=5.0, text="Hello world, this is a test"),
            LyricLine(timestamp=10.0, text="Singing along with the AI"),
            LyricLine(timestamp=15.0, text="Karaoke night is the best"),
        ],
        synced=True
    )
}

def parse_lrc(lrc_text: str) -> List[LyricLine]:
    """
    Parses LRC format strings: [mm:ss.xx] Lyric text
    """
    lines = lrc_text.split('\n')
    parsed = []
    # Regex for [mm:ss.xx] or [mm:ss]
    regex = re.compile(r'\[(\d+):(\d+(?:\.\d+)?)\](.*)')
    
    for line in lines:
        match = regex.match(line.strip())
        if match:
            minutes = int(match.group(1))
            seconds = float(match.group(2))
            text = match.group(3).strip()
            total_seconds = minutes * 60 + seconds
            if text: # Skip empty lines/metadata usually
                parsed.append(LyricLine(timestamp=total_seconds, text=text))
    
    return parsed

def parse_genius_lyrics(lyrics_text: str) -> List[LyricLine]:
    """
    Parses raw Genius lyrics (text only).
    Assigns dummy timestamps.
    """
    lines = lyrics_text.split('\n')
    parsed = []
    t = 0.0
    for line in lines:
        line = line.strip()
        if line:
            # Check if it's a section header like [Chorus], keep it but usually minimal time
            parsed.append(LyricLine(timestamp=t, text=line))
            t += 4.0 # Estimate 4 seconds per line
    return parsed

@app.get("/lyrics/{song_id}", response_model=SongLyrics)
def get_lyrics(song_id: str):
    if song_id in lyrics_cache:
        return lyrics_cache[song_id]
    raise HTTPException(status_code=404, detail="Lyrics not found in cache. Use /search_lyrics first.")

@app.get("/search_lyrics")
def search_lyrics(query: str):
    """
    Searches for lyrics.
    1. Try syncedlyrics (LRC) first.
    2. Fallback to Genius (Text).
    """
    try:
        logger.info(f"Searching syncedlyrics for: {query}")
        # syncedlyrics.search returns a string of LRC content or None
        lrc_content = syncedlyrics.search(query)
        
        if lrc_content:
            logger.info("Found synced lyrics!")
            parsed_lyrics = parse_lrc(lrc_content)
            # Simple song ID generation
            song_id = re.sub(r'\W+', '_', query.lower())
            
            song_obj = SongLyrics(
                song_id=song_id,
                title=query.title(), # Estimate title from query
                lyrics=parsed_lyrics,
                synced=True
            )
            lyrics_cache[song_id] = song_obj
            return song_obj
            
    except Exception as e:
        logger.error(f"Syncedlyrics search failed: {e}")
        # Continue to fallback

    # Fallback to Genius
    if not genius:
        if query.lower() == "demo":
             return lyrics_cache["song1"]
        raise HTTPException(status_code=503, detail="Genius API token not configured and no synced lyrics found.")

    try:
        logger.info(f"Searching Genius for: {query}")
        song = genius.search_song(query)
        if not song:
            raise HTTPException(status_code=404, detail="Song not found on Genius or SyncedLyrics")
        
        parsed_lyrics = parse_genius_lyrics(song.lyrics)
        song_data = song.to_dict()
        song_id = str(song_data.get('id', 'unknown'))
        
        song_obj = SongLyrics(
            song_id=song_id,
            title=song.title,
            lyrics=parsed_lyrics,
            synced=False
        )
        lyrics_cache[song_id] = song_obj
        return song_obj
        
    except Exception as e:
        logger.error(f"Genius search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/sync")
def sync_lyrics(request: SyncRequest):
    """
    Receives current timestamp to finding the active line.
    Useful if the frontend is dumb, but for this plan the frontend is smart.
    We keep this endpoint for potential server-side usage.
    """
    song = lyrics_cache.get(request.song_id)
    if not song:
        raise HTTPException(status_code=404, detail="Song not found")
    
    current_line = None
    # Simple search
    for i, line in enumerate(song.lyrics):
        if line.timestamp <= request.timestamp:
            current_line = line
        else:
            break
            
    return {"current_line": current_line}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)