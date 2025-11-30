from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import requests
import logging
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="AI Karaoke Host Agent")

# Get the directory of the current script
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")

# Mount static files
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Templates
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# Agent URLs (Localhost for now)
AUDIO_AGENT_URL = "http://localhost:8001"
LYRICS_AGENT_URL = "http://localhost:8002"

class SongRequest(BaseModel):
    query: str

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/api/play_song")
async def play_song(request: SongRequest):
    query = request.query
    logger.info(f"Host received play request for: {query}")
    
    try:
        # 1. Start Audio Playback (Async/Background in agent)
        audio_resp = requests.post(f"{AUDIO_AGENT_URL}/search_and_play", json={"query": query}, timeout=60)
        audio_resp.raise_for_status()
        audio_data = audio_resp.json()
        
        # 2. Fetch Lyrics
        lyrics_resp = requests.get(f"{LYRICS_AGENT_URL}/search_lyrics", params={"query": query}, timeout=10)
        lyrics_resp.raise_for_status()
        lyrics_data = lyrics_resp.json()
        
        return {
            "status": "success",
            "audio": audio_data,
            "lyrics": lyrics_data
        }
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Error communicating with agents: {e}")
        # Try to return partial info or error
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/stop_song")
async def stop_song():
    try:
        requests.post(f"{AUDIO_AGENT_URL}/stop")
        return {"status": "stopped"}
    except Exception as e:
        logger.error(f"Error stopping audio: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)