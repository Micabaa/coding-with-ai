import subprocess
import os
import logging
import yt_dlp
from mcp.server.fastmcp import FastMCP

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("PlaybackAgent")

# Initialize FastMCP Server
mcp = FastMCP("Audio Playback Agent")

# PID file to track the running audio process
PID_FILE = "playback.pid"
SONGS_DIR = "songs"

# Ensure songs directory exists
if not os.path.exists(SONGS_DIR):
    os.makedirs(SONGS_DIR)

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
        'no_warnings': True,
        'noprogress': True,
        'default_search': 'ytsearch1:', # Search and download the first result
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        logger.info(f"Searching and downloading: {query}")
        info = ydl.extract_info(query, download=True)
        if 'entries' in info:
            info = info['entries'][0]
        
        filename = ydl.prepare_filename(info)
        base, _ = os.path.splitext(filename)
        final_path = f"{base}.mp3"
        
        return final_path, info.get('title', 'Unknown Title')

@mcp.tool()
def stop_audio() -> str:
    """Stops the currently playing audio using the PID file."""
    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE, "r") as f:
                pid = int(f.read().strip())
            
            logger.info(f"Stopping process with PID: {pid}")
            os.kill(pid, 15) # SIGTERM
            
            # Wait a bit and check if it's gone, if not SIGKILL
            try:
                os.waitpid(pid, os.WNOHANG)
            except ChildProcessError:
                pass # Already gone
                
            os.remove(PID_FILE)
            return "Playback stopped."
        except ProcessLookupError:
            os.remove(PID_FILE)
            return "Process was not running."
        except Exception as e:
            logger.error(f"Error stopping audio: {e}")
            return f"Error stopping audio: {e}"
    else:
        return "No audio playing (PID file not found)."

@mcp.tool()
def search_and_play(query: str) -> str:
    """
    Searches YouTube for the query (appends 'karaoke' automatically),
    downloads the audio, and plays it.
    """
    # Stop any existing playback first
    stop_audio()

    search_query = f"{query} karaoke"
    try:
        file_path, title = download_audio(search_query)
        
        if not os.path.exists(file_path):
             return f"Error: Downloaded file not found at {file_path}"

        # Play it
        logger.info(f"Starting playback for: {file_path}")
        # Use afplay on macOS for audio playback
        process = subprocess.Popen(['afplay', file_path])
        
        # Save PID to file
        with open(PID_FILE, "w") as f:
            f.write(str(process.pid))
        
        return f"Now playing: {title}"
        
    except Exception as e:
        logger.error(f"Search and play failed: {e}")
        return f"Error: {str(e)}"

if __name__ == "__main__":
    print("🎤 Starting Audio Playback Agent MCP Server...")
    mcp.run()