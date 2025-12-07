from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import logging
import yt_dlp
import glob

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Audio Playback Agent")

# Allow CORS so the host (on a different port) or browser can fetch/play
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Robust directory handling
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Assume songs are in a directory relative to this agent or project root
# Using a local 'songs' directory in this agent's folder for simplicity and safety
SONGS_DIR = os.path.join(BASE_DIR, "songs")

if not os.path.exists(SONGS_DIR):
    os.makedirs(SONGS_DIR)

# Mount the songs directory to serve files statically
app.mount("/songs", StaticFiles(directory=SONGS_DIR), name="songs")

class PlayRequest(BaseModel):
    track_path: str

class SearchRequest(BaseModel):
    query: str

def download_audio(query: str):
    """
    Searches for a video on YouTube and downloads the audio.
    Returns the filename (relative to SONGS_DIR).
    """
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': f'{SONGS_DIR}/%(title)s.%(ext)s',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'noplaylist': True,
        'quiet': True,
        'default_search': 'ytsearch1:', 
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        logger.info(f"Searching and downloading: {query}")
        info = ydl.extract_info(query, download=True)
        if 'entries' in info:
            info = info['entries'][0]
        
        filename = ydl.prepare_filename(info)
        base, _ = os.path.splitext(filename)
        # yt-dlp with mp3 conversion results in .mp3
        final_abs_path = f"{base}.mp3"
        
        # We need the relative path or filename to serve it
        final_filename = os.path.basename(final_abs_path)
        
        return final_filename, info.get('title', 'Unknown Title')

@app.post("/play")
def play_audio(request: PlayRequest):
    """
    Returns the URL for the audio file.
    Expects 'track_path' to be the filename or relative path.
    """
    # Assuming track_path is just the filename now
    filename = os.path.basename(request.track_path)
    
    file_path = os.path.join(SONGS_DIR, filename)
    if not os.path.exists(file_path):
         raise HTTPException(status_code=404, detail=f"Track not found: {filename}")

    # Return the full URL to the file
    # Assuming localhost:8001
    return {
        "status": "playing", 
        "track": filename,
        "url": f"http://localhost:8001/songs/{filename}",
        "file_path": file_path # Absolute path for internal use
    }

@app.post("/search_and_play")
def search_and_play(request: SearchRequest):
    query = f"{request.query} karaoke"
    try:
        filename, title = download_audio(query)
        
        # Verify file exists
        file_path = os.path.join(SONGS_DIR, filename)
        if not os.path.exists(file_path):
             logger.warning(f"Expected file {file_path} not found.")
             raise HTTPException(status_code=500, detail="Downloaded file not found")

        return play_audio(PlayRequest(track_path=filename))
        
    except Exception as e:
        logger.error(f"Search and play failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/stop")
def stop_audio():
    # Helper for compatibility, but the frontend controls playback now.
    return {"status": "stopped (client-side control)"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)