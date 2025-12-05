from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import logging
import os
import sys
import json
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

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

# Paths to Agent Scripts
PROJECT_ROOT = os.path.dirname(BASE_DIR)
LYRICS_SCRIPT = os.path.join(PROJECT_ROOT, "lyrics_display_agent", "lyrics_server.py")
PLAYBACK_SCRIPT = os.path.join(PROJECT_ROOT, "audio_playback_agent", "playback_server.py")
EVALUATOR_SCRIPT = os.path.join(PROJECT_ROOT, "singing_evaluator_agent", "evaluator_server.py")
JUDGE_SCRIPT = os.path.join(PROJECT_ROOT, "judge_agent", "judge_server.py")

class SongRequest(BaseModel):
    query: str

class RecordingRequest(BaseModel):
    audio_data: str # Base64 encoded audio
    song_id: str = "unknown"

async def call_mcp_tool(script_path: str, tool_name: str, arguments: dict):
    """Helper to call an MCP tool via stdio."""
    env = os.environ.copy()
    server_params = StdioServerParameters(
        command=sys.executable,
        args=[script_path],
        env=env
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(tool_name, arguments=arguments)
            
            # Parse result content
            if result.content and hasattr(result.content[0], 'text'):
                try:
                    # Some tools return JSON string, others might return plain text
                    # We try to parse as JSON if possible
                    return json.loads(result.content[0].text)
                except json.JSONDecodeError:
                    return result.content[0].text
            return None

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/api/play_song")
async def play_song(request: SongRequest):
    query = request.query
    logger.info(f"Host received play request for: {query}")
    
    try:
        # 1. Fetch Lyrics (MCP)
        logger.info("Calling Lyrics Agent...")
        lyrics_data = await call_mcp_tool(LYRICS_SCRIPT, "search_lyrics", {"query": query})
        
        if not lyrics_data or "error" in lyrics_data:
            logger.warning(f"Lyrics not found or error: {lyrics_data}")
            # We continue even if lyrics fail, to try playback
        
        # 2. Start Audio Playback (MCP)
        logger.info("Calling Playback Agent...")
        audio_status = await call_mcp_tool(PLAYBACK_SCRIPT, "search_and_play", {"query": query})
        
        return {
            "status": "success",
            "audio_status": audio_status,
            "lyrics": lyrics_data
        }
        
    except Exception as e:
        logger.error(f"Error communicating with agents: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/stop_song")
async def stop_song():
    try:
        logger.info("Stopping playback...")
        status = await call_mcp_tool(PLAYBACK_SCRIPT, "stop_audio", {})
        return {"status": status}
    except Exception as e:
        logger.error(f"Error stopping audio: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/submit_recording")
async def submit_recording(request: RecordingRequest):
    try:
        logger.info("Received recording submission...")
        
        # 1. Analyze Singing (Evaluator Agent)
        logger.info("Calling Singing Evaluator...")
        eval_result = await call_mcp_tool(EVALUATOR_SCRIPT, "evaluate_singing", {
            "audio_data": request.audio_data,
            "performance_segment_id": f"seg_{request.song_id}"
        })
        
        if not eval_result or "error" in eval_result:
            logger.error(f"Evaluator failed: {eval_result}")
            raise HTTPException(status_code=500, detail="Singing evaluation failed")

        # 2. Get Judge Feedback (Judge Agent)
        logger.info("Calling Judge Agent...")
        # Judge expects "evaluation_data" as a dict
        judge_feedback = await call_mcp_tool(JUDGE_SCRIPT, "evaluate_performance", {
            "evaluation_data": eval_result,
            "personality": "strict_judge" # Default personality
        })
        
        return {
            "status": "success",
            "scores": eval_result,
            "feedback": judge_feedback
        }

    except Exception as e:
        logger.error(f"Error processing recording: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    # Run on port 8090
    uvicorn.run(app, host="0.0.0.0", port=8090)
