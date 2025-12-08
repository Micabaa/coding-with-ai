from fastapi import FastAPI, Request, HTTPException, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import requests
import logging
import os
import json

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
# Agent URLs (Localhost for now)
AUDIO_AGENT_URL = "http://localhost:8001"
LYRICS_AGENT_URL = "http://localhost:8002"
EVALUATOR_AGENT_URL = "http://localhost:8003"
JUDGE_AGENT_URL = "http://localhost:8004"

class SongRequest(BaseModel):
    query: str

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# Global state to track current song
current_song_metadata = {}

@app.post("/api/play_song")
async def play_song(request: SongRequest):
    query = request.query
    logger.info(f"Host received play request for: {query}")
    
    try:
        # 1. Start Audio Playback (Async/Background in agent)
        audio_resp = requests.post(f"{AUDIO_AGENT_URL}/search_and_play", json={"query": query}, timeout=60)
        audio_resp.raise_for_status()
        audio_data = audio_resp.json()
        
        # Store metadata for evaluation
        # Assuming audio_data contains 'file_path' or we can derive it. 
        # The Audio Agent returns 'url' which might be a local path or served URL.
        # Let's check what Audio Agent returns. It usually returns a 'track' name.
        # Ideally Audio Agent should return the absolute path for internal use.
        # For now, let's assume the Audio Agent saves to 'songs/<track>.mp3' relative to project root.
        # We'll try to reconstruct it or pass what we have.
        
        if 'file_path' in audio_data:
             current_song_metadata['audio_path'] = audio_data['file_path']
        
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

@app.post("/api/submit_performance")
async def submit_performance(
    audio_file: UploadFile = File(...),
    personality: str = Form("strict_judge"),
    reference_lyrics: str = Form(None),
    offset: float = Form(0.0)
):
    """
    Orchestrates the evaluation process:
    1. Send audio to Singing Evaluator.
    2. Send results to Judge Agent.
    3. Return feedback.
    """
    try:
        logger.info("Received performance submission.")
        
        # 1. Send to Evaluator
        audio_content = await audio_file.read()
        
        # Prepare multipart upload for evaluator
        files = {'audio_file': ('performance.wav', audio_content, 'audio/wav')}
        data = {'offset': str(offset)}
        if reference_lyrics:
            data['reference_lyrics'] = reference_lyrics
            
        # Add reference audio path if available
        if 'audio_path' in current_song_metadata:
            data['reference_audio_path'] = current_song_metadata['audio_path']
        
        logger.info(f"Sending audio to Evaluator with metadata: {data.keys()}")
        eval_resp = requests.post(f"{EVALUATOR_AGENT_URL}/evaluate_singing", files=files, data=data, timeout=120)
        eval_resp.raise_for_status()
        evaluation_result = eval_resp.json()
        logger.info(f"Evaluator result: {evaluation_result}")
        
        # 2. Send to Judge
        judge_payload = {
            "evaluation_data": evaluation_result,
            "personality": personality
        }
        
        logger.info(f"Sending data to Judge ({personality})...")
        judge_resp = requests.post(f"{JUDGE_AGENT_URL}/evaluate_performance", json=judge_payload, timeout=30)
        judge_resp.raise_for_status()
        judge_result = judge_resp.json()
        
        return {
            "status": "success",
            "evaluation": evaluation_result,
            "feedback": judge_result["feedback"]
        }

    except Exception as e:
        logger.error(f"Error processing performance: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Leaderboard/Profile Logic

LEADERBOARD_FILE = os.path.join(BASE_DIR, "leaderboard.json")

def load_leaderboard():
    if not os.path.exists(LEADERBOARD_FILE):
        return {"casual": [], "competition": []}
    try:
        with open(LEADERBOARD_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {"casual": [], "competition": []}

def save_leaderboard(data):
    with open(LEADERBOARD_FILE, "w") as f:
        json.dump(data, f, indent=2)

@app.get("/api/leaderboard")
async def get_leaderboard():
    return load_leaderboard()

@app.post("/api/save_score")
async def save_score(request: Request):
    """
    Saves a score to the leaderboard.
    Expected JSON: { "user_name": str, "score": int, "mode": "casual"|"competition", "song": str }
    """
    data = await request.json()
    user_name = data.get("user_name", "Anonymous")
    score = data.get("score", 0)
    mode = data.get("mode", "casual")
    song_title = data.get("song", "Unknown Song")
    
    leaderboard = load_leaderboard()
    
    entry = {
        "user_name": user_name,
        "score": score,
        "song": song_title,
        "date": "Just now" # You might want to use datetime.now().isoformat()
    }
    
    if mode == "competition":
        leaderboard["competition"].append(entry)
        # Sort desc
        leaderboard["competition"].sort(key=lambda x: x["score"], reverse=True)
    else:
        leaderboard["casual"].append(entry)
        leaderboard["casual"].sort(key=lambda x: x["score"], reverse=True)
        
    save_leaderboard(leaderboard)
    return {"status": "success", "leaderboard": leaderboard}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
