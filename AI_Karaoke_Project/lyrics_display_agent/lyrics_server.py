from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import logging
import lyricsgenius
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Lyrics Display Agent")

# Initialize Genius Client
# User should provide GENIUS_ACCESS_TOKEN in .env
GENIUS_ACCESS_TOKEN = os.getenv("GENIUS_ACCESS_TOKEN")
genius = None
if GENIUS_ACCESS_TOKEN:
    genius = lyricsgenius.Genius(GENIUS_ACCESS_TOKEN)
else:
    logger.warning("GENIUS_ACCESS_TOKEN not found. Lyrics fetching will be limited or mocked.")

# Data Models
class LyricLine(BaseModel):
    timestamp: float
    text: str

class SongLyrics(BaseModel):
    song_id: str
    title: str
    lyrics: List[LyricLine]

class SearchRequest(BaseModel):
    query: str

# Mock Database (Fallback)
lyrics_db = {
    "song1": SongLyrics(
        song_id="song1",
        title="Demo Song 1",
        lyrics=[
            LyricLine(timestamp=0.0, text="[Intro]"),
            LyricLine(timestamp=5.0, text="Hello world, this is a test"),
            LyricLine(timestamp=10.0, text="Singing along with the AI"),
            LyricLine(timestamp=15.0, text="Karaoke night is the best"),
        ]
    )
}

class SyncRequest(BaseModel):
    timestamp: float
    song_id: str

def parse_genius_lyrics(lyrics_text: str) -> List[LyricLine]:
    """
    Parses raw Genius lyrics into lines.
    Since Genius doesn't provide timestamps, we'll assign dummy timestamps
    evenly distributed or just 0 for all (scrolling manually).
    For this MVP, we'll just split by lines and assign incremental timestamps
    assuming a 3-second gap, which is naive but functional for display.
    """
    lines = lyrics_text.split('\n')
    parsed = []
    t = 0.0
    for line in lines:
        line = line.strip()
        if line:
            parsed.append(LyricLine(timestamp=t, text=line))
            t += 3.0 # Arbitrary 3 seconds per line
    return parsed

@app.get("/lyrics/{song_id}", response_model=SongLyrics)
def get_lyrics(song_id: str):
    if song_id in lyrics_db:
        return lyrics_db[song_id]
    raise HTTPException(status_code=404, detail="Lyrics not found in cache. Use /search_lyrics first.")

@app.get("/search_lyrics")
def search_lyrics(query: str):
    """
    Searches for lyrics on Genius.
    """
    if not genius:
        # Fallback to mock if no token
        if query.lower() == "demo":
             return lyrics_db["song1"]
        raise HTTPException(status_code=503, detail="Genius API token not configured.")

    try:
        logger.info(f"Searching Genius for: {query}")
        song = genius.search_song(query)
        if not song:
            raise HTTPException(status_code=404, detail="Song not found on Genius")
        
        parsed_lyrics = parse_genius_lyrics(song.lyrics)
        
        # Access ID safely via to_dict()
        song_data = song.to_dict()
        song_id = str(song_data.get('id', 'unknown'))
        
        # Cache it (simple in-memory cache)
        song_obj = SongLyrics(
            song_id=song_id,
            title=song.title,
            lyrics=parsed_lyrics
        )
        lyrics_db[song_id] = song_obj
        
        return song_obj
        
    except Exception as e:
        logger.error(f"Genius search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/sync")
def sync_lyrics(request: SyncRequest):
    """
    Receives a current timestamp and 'displays' the corresponding lyric line.
    """
    song = lyrics_db.get(request.song_id)
    if not song:
        raise HTTPException(status_code=404, detail="Song not found")
    
    current_line = None
    for line in song.lyrics:
        if line.timestamp <= request.timestamp:
            current_line = line
        else:
            break
            
    if current_line:
        # logger.info(f"Displaying: {current_line.text}")
        return {"current_line": current_line}
    
    return {"current_line": None}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)