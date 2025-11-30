from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import subprocess
import os
import signal
import logging
import yt_dlp
import glob

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Audio Playback Agent")

# Global variable to keep track of the playback process
current_process = None
SONGS_DIR = "songs"

# Ensure songs directory exists
if not os.path.exists(SONGS_DIR):
    os.makedirs(SONGS_DIR)

class PlayRequest(BaseModel):
    track_path: str

class SearchRequest(BaseModel):
    query: str

def download_audio(query: str):
    """
    Searches for a video on YouTube and downloads the audio.
    Returns the path to the downloaded file.
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
        'default_search': 'ytsearch1:', # Search and download the first result
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        logger.info(f"Searching and downloading: {query}")
        info = ydl.extract_info(query, download=True)
        if 'entries' in info:
            info = info['entries'][0]
        
        # Find the downloaded file
        # yt-dlp might sanitize the filename, so we look for the most recently modified file in the dir
        # or try to predict the filename. 
        # A simpler way for this MVP: return the filename from info dict
        filename = ydl.prepare_filename(info)
        # The actual file will have the extension replaced by mp3
        base, _ = os.path.splitext(filename)
        final_path = f"{base}.mp3"
        
        return final_path, info.get('title', 'Unknown Title')

@app.post("/play")
def play_audio(request: PlayRequest):
    global current_process
    
    track_path = request.track_path
    
    if not os.path.exists(track_path):
        raise HTTPException(status_code=404, detail=f"Track not found at {track_path}")

    # Stop any currently playing audio
    if current_process and current_process.poll() is None:
        stop_audio()

    try:
        # Use afplay on macOS for audio playback
        logger.info(f"Starting playback for: {track_path}")
        current_process = subprocess.Popen(['afplay', track_path])
        return {"status": "playing", "track": track_path}
    except Exception as e:
        logger.error(f"Failed to play audio: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/search_and_play")
def search_and_play(request: SearchRequest):
    """
    Searches YouTube for the query (appends 'karaoke' automatically),
    downloads the audio, and plays it.
    """
    query = f"{request.query} karaoke"
    try:
        file_path, title = download_audio(query)
        
        # Verify file exists
        if not os.path.exists(file_path):
             # Fallback: sometimes extension handling is tricky, look for any file with that name
             # or just list dir and pick latest? 
             # Let's try to be robust:
             logger.warning(f"Expected file {file_path} not found. Checking directory...")
             # This part can be improved, but let's assume yt-dlp did its job.
             raise HTTPException(status_code=500, detail="Downloaded file not found")

        # Play it
        return play_audio(PlayRequest(track_path=file_path))
        
    except Exception as e:
        logger.error(f"Search and play failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/stop")
def stop_audio():
    global current_process
    if current_process and current_process.poll() is None:
        logger.info("Stopping playback...")
        current_process.terminate()
        try:
            current_process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            current_process.kill()
        current_process = None
        return {"status": "stopped"}
    return {"status": "no audio playing"}

@app.get("/status")
def get_status():
    global current_process
    if current_process and current_process.poll() is None:
        return {"status": "playing"}
    return {"status": "stopped"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)