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

import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import logging
import yt_dlp

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Video Playback Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Robust directory handling
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SONGS_DIR = os.path.join(BASE_DIR, "songs")

if not os.path.exists(SONGS_DIR):
    os.makedirs(SONGS_DIR)

app.mount("/songs", StaticFiles(directory=SONGS_DIR), name="songs")

class SearchRequest(BaseModel):
    query: str

def download_video(query: str):
    """
    Searches for a video and downloads it as MP4.
    Returns filename and title.
    """
    ydl_opts = {
        'format': 'best[ext=mp4]/best', # Prefer mp4
        'outtmpl': f'{SONGS_DIR}/%(title)s.%(ext)s',
        'noplaylist': True,
        'quiet': True,
        'default_search': 'ytsearch1:',
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        logger.info(f"Searching and downloading video: {query}")
        info = ydl.extract_info(query, download=True)
        
        if 'entries' in info:
            info = info['entries'][0]
        
        filename = ydl.prepare_filename(info)
        # Ensure we return just the filename
        final_filename = os.path.basename(filename)
        return final_filename, info.get('title', 'Unknown Title')

@app.post("/search_and_play")
def search_and_play(request: SearchRequest):
    """
    Downloads video and returns local URL.
    Checks for 'Sing King' in title.
    """
    query = f"{request.query} karaoke"
    try:
        filename, title = download_video(query)
        
        # Verify file exists
        file_path = os.path.join(SONGS_DIR, filename)
        if not os.path.exists(file_path):
             # Try checking if yt-dlp changed extension (e.g. mkv/webm)
             # But prepare_filename usually is correct.
             logger.warning(f"Expected file {file_path} not found.")
             # Fallback check dir for similar name? skipping for now
             raise HTTPException(status_code=500, detail="Downloaded file not found")

        is_sing_king = "sing king" in title.lower()

        return {
            "status": "success", 
            "track": title,
            "url": f"http://localhost:8001/songs/{filename}", # Local URL
            "is_sing_king": is_sing_king
        }
        
    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/stop")
def stop_audio():
    return {"status": "stopped"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)