import os
import logging
import yt_dlp
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

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
    Returns filename (basename) and title.
    """
    ydl_opts = {
        'format': 'best[ext=mp4]',
        'noplaylist': True,
        'quiet': True,
        'default_search': 'ytsearch5:', # Search 5 candidates
        # 'paths': ... (handled by output template)
        'outtmpl': os.path.join(SONGS_DIR, '%(id)s.%(ext)s'),
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            logger.info(f"Searching for: {query}")
            info = ydl.extract_info(query, download=False)
            
            video_info = None
            if 'entries' in info:
                # Filter for videos > 60s to avoid Shorts/Teasers
                for entry in info['entries']:
                    duration = entry.get('duration', 0)
                    if duration > 60:
                        video_info = entry
                        break
                
                # Fallback to first if no long video found
                if not video_info and info['entries']:
                    video_info = info['entries'][0]
            else:
                video_info = info

            if not video_info:
                 raise HTTPException(404, "No video found")

            video_id = video_info['id']
            title = video_info['title']
            file_path = os.path.join(SONGS_DIR, f"{video_id}.mp4")

            # Download if not exists
            if not os.path.exists(file_path):
                logger.info(f"Downloading video: {title}")
                # We need to re-run with THIS specific video ID to download
                # Or just let ydl download it now? 
                # Better to configure ydl to download THE filtered video.
                # Re-run ydl for the specific ID
                ydl_opts['default_search'] = 'ytsearch1:' # Reset
                # Actually, simply running process logic:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl_download:
                    ydl_download.download([video_info['webpage_url']])
            
            return {
                "url": f"/songs/{video_id}.mp4",
                "title": title,
                "track": title,
                "file_path": os.path.abspath(file_path)
            }
    except Exception as e:
        logger.error(f"Error in download_video: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/search_and_play")
def search_and_play(request: SearchRequest):
    """
    Downloads video and returns local URL.
    Checks for 'Sing King' in title.
    """
    query = f"{request.query} karaoke"
    try:
        video_data = download_video(query)
        
        # Verify file exists
        file_path = video_data['file_path']
        if not os.path.exists(file_path):
             logger.warning(f"Expected file {file_path} not found.")
             raise HTTPException(status_code=500, detail="Downloaded file not found")

        title = video_data['title']
        is_sing_king = "sing king" in title.lower()
        
        # Construct URL (assuming default port 8001)
        # Note: If running on a different port/host, this needs to be dynamic or configured.
        filename = os.path.basename(file_path)
        url = f"http://localhost:8001/songs/{filename}"

        return {
            "status": "success", 
            "track": title,
            "url": url,
            "file_path": file_path, # Absolute path for evaluator
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