import logging
import os
import yt_dlp
import json
import contextlib
import io
from mcp.server.fastmcp import FastMCP

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AudioPlaybackMCP")

# Initialize FastMCP Server
mcp = FastMCP("Audio Playback Agent")

# Robust directory handling
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SONGS_DIR = os.path.join(BASE_DIR, "songs")

if not os.path.exists(SONGS_DIR):
    os.makedirs(SONGS_DIR)

def download_video(query: str):
    """
    Searches for a video and downloads it as MP4.
    Returns filename (basename) and title.
    """
    # Updated ydl_opts based on the instruction
    # Updated ydl_opts based on the instruction
    ydl_opts = {
        'format': 'bestvideo+bestaudio/best', # Get video!
        'merge_output_format': 'mp4', # Force merge to mp4
        'outtmpl': os.path.join(SONGS_DIR, '%(id)s.%(ext)s'),
        'quiet': True,
        'no_warnings': True,
        'noprogress': True,
        'noplaylist': True,
        'default_search': 'ytsearch5:',
        'extract_flat': False,
    }

    try:
        # Redirect stdout/stderr to suppress any leaking output from yt-dlp
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
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
                     raise Exception("No video found")

                video_id = video_info['id']
                title = video_info['title']
                file_path = os.path.join(SONGS_DIR, f"{video_id}.mp4")

                # Download if not exists
                if not os.path.exists(file_path):
                    logger.info(f"Downloading video: {title}")
                    ydl_opts['default_search'] = 'ytsearch1:' # Reset
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
        raise e

@mcp.tool()
def play_song(query: str) -> str:
    """
    Searches for a karaoke video, downloads it, and returns the playback details.
    
    Args:
        query: Song title (e.g. "Bohemian Rhapsody")
        
    Returns:
        JSON string containing track title, url, file_path, and is_sing_king flag.
    """
    search_query = f"{query} karaoke"
    try:
        video_data = download_video(search_query)
        
        # Verify file exists
        file_path = video_data['file_path']
        if not os.path.exists(file_path):
             return json.dumps({"error": "Downloaded file not found"})

        title = video_data['title']
        is_sing_king = "sing king" in title.lower()
        
        # Construct URL relative to the Host
        filename = os.path.basename(file_path)
        url = f"/songs/{filename}"

        result = {
            "status": "success", 
            "track": title,
            "url": url,
            "file_path": file_path,
            "is_sing_king": is_sing_king
        }
        return json.dumps(result)
        
    except Exception as e:
        logger.error(f"Search failed: {e}")
        return json.dumps({"error": str(e)})

@mcp.tool()
def stop_song() -> str:
    """Stops the current song playback."""
    return json.dumps({"status": "stopped"})

if __name__ == "__main__":
    mcp.run()
