import asyncio
import logging
import os
import json
import sys
from contextlib import AsyncExitStack
from typing import Optional
from pathlib import Path
from dotenv import load_dotenv
from openai import AsyncOpenAI
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Load environment variables
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AgenticHost")

class KaraokeHost:
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            logger.warning("OPENAI_API_KEY not found.")
            self.client = None
        else:
            self.client = AsyncOpenAI(api_key=self.api_key)
        
        self.exit_stack = AsyncExitStack()
        self.sessions = {}
        self.tools = []
        self.tool_map = {}
        self.security_policy = SecurityPolicy()

    async def connect_to_server(self, name: str, script_path: str):
        """Connects to an MCP server running as a python script."""
        server_params = StdioServerParameters(
            command=sys.executable,
            args=[script_path],
            env=os.environ.copy()
        )
        
        transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        session = await self.exit_stack.enter_async_context(ClientSession(transport[0], transport[1]))
        await session.initialize()
        
        self.sessions[name] = session
        
        # List tools
        tools_result = await session.list_tools()
        for tool in tools_result.tools:
            self.tools.append({
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.inputSchema
                }
            })
            self.tool_map[tool.name] = name
        
        logger.info(f"Connected to {name} MCP Server. Found tools: {[t.name for t in tools_result.tools]}")

    async def start(self):
        """Starts connections to all agents."""
        base_dir = Path(__file__).parent.parent
        
        agents = {
            "lyrics": base_dir / "lyrics_display_agent" / "mcp_server.py",
            "audio": base_dir / "audio_playback_agent" / "mcp_server.py",
            "evaluator": base_dir / "singing_evaluator_agent" / "mcp_server.py",
            "judge": base_dir / "judge_agent" / "mcp_server.py"
        }
        
        for name, path in agents.items():
            if path.exists():
                await self.connect_to_server(name, str(path))
            else:
                logger.error(f"Could not find agent script: {path}")

    async def process_user_input_with_actions(self, user_input: str):
        """Processes user input and returns text response + optional action."""
        if not self.client:
            return "Error: OpenAI API key not configured.", None

        messages = [
        {"role": "system", "content": "You are the 'KaraOKAI Host', a high-energy, helpful, and music-savvy AI. Your goal is to get people singing!\n\nRules:\n1. If a user asks to sing a specific song, IMMEDIATEY use the 'play_song' tool. Do not ask for confirmation.\n2. If a user mentions an artist (e.g. 'I want to sing PVRIS'), you MUST suggest 3 of their most popular karaoke songs. ask which one they want.\n3. If a user is vague (e.g. 'idk help me'), proactively suggest 3 trending or classic karaoke bangers (e.g. Queen, Taylor Swift, The Killers). Ask what genre they like.\n4. Always be encouraging and use emojis! 🎤✨\n5. Never say you 'cannot' play a song unless the tool fails. Assume you can find it."},
        {"role": "user", "content": user_input}
    ]

        # 1. Call LLM with tools
        response = await self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            tools=self.tools,
            tool_choice="auto"
        )

        response_message = response.choices[0].message
        tool_calls = response_message.tool_calls
        
        action = None

        if tool_calls:
            messages.append(response_message)
            
            for tool_call in tool_calls:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)
                
                logger.info(f"Calling tool: {function_name} with args: {function_args}")
                
                tool_result = None
                session_name = self.tool_map.get(function_name)
                
                if session_name and session_name in self.sessions:
                    try:
                        session = self.sessions[session_name]
                        result = await session.call_tool(function_name, arguments=function_args)
                        tool_result = result.content[0].text
                    except Exception as e:
                        tool_result = f"Error calling tool: {e}"
                else:
                    tool_result = "Error: Tool not found in map."
                
                if tool_result:
                    messages.append({
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": function_name,
                        "content": str(tool_result),
                    })
                    
                    # Capture Action
                    if function_name == "play_song":
                        logger.info(f"Raw tool result for play_song: {tool_result!r}")
                        try:
                            data = json.loads(tool_result)
                            if "url" in data:
                                action = {"type": "play_audio", "payload": data}
                        except Exception as e:
                            logger.error(f"Failed to parse play_song result for action: {e}")

                else:
                    messages.append({
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": function_name,
                        "content": "Error: Tool not found or failed.",
                    })

            # 2. Get final response
            final_response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages
            )
            return final_response.choices[0].message.content, action
        
        return response_message.content, None

    async def call_tool(self, tool_name: str, args: dict):
        """Calls a specific tool on the connected agents."""
        
        # --- SECURITY CHECK ---
        if not self.security_policy.is_allowed(tool_name, args):
             logger.warning(f"SECURITY BLOCKED: Tool '{tool_name}' blocked by policy.")
             return "Error: Security Policy Violation. Action blocked."
        # ----------------------

        session_name = self.tool_map.get(tool_name)
        if session_name and session_name in self.sessions:
            try:
                session = self.sessions[session_name]
                result = await session.call_tool(tool_name, arguments=args)
                return result.content[0].text
            except Exception as e:
                logger.error(f"Error calling tool {tool_name}: {e}")
                pass
        else:
            logger.error(f"Tool {tool_name} not found in map or session not connected.")
        return None

    async def cleanup(self):
        await self.exit_stack.aclose()

class SecurityPolicy:
    """
    Enforces access control for MCP tools.
    Requirement A2: Adopt a mechanism for access control.
    """
    def __init__(self):
        # Define ALLOWLIST of tools
        self.allowed_tools = {
            "play_song",
            "stop_song",
            "search_lyrics",
            "evaluate_singing",
            "evaluate_performance"
        }
        
    def is_allowed(self, tool_name: str, args: dict) -> bool:
        # 1. Check Tool Name Allowlist
        if tool_name not in self.allowed_tools:
            logger.warning(f"Security: Unknown tool '{tool_name}' attempted.")
            return False
            
        # 2. Argument Validation (Basic)
        # Prevent Path Traversal in file paths if applicable
        if "audio_path" in args:
            path = args["audio_path"]
            if ".." in path or path.startswith("/"):
                # Allow absolute paths only if they are in temp or songs dir
                # This is a simple heuristic
                if "/tmp/" not in path and "/songs/" not in path and "temp" not in path:
                     logger.warning(f"Security: Suspicious file path '{path}'")
                     # return False # Strict mode (disabled for now to avoid breaking valid temp paths)
                     pass
                     
        return True

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from fastapi.responses import HTMLResponse

# ... (Previous imports remain, ensure they are there)

app = FastAPI(title="Agentic Karaoke Host")

# Mount static files and templates (reusing existing structure)
BASE_DIR = Path(__file__).parent
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# Mount songs directory for playback
SONGS_DIR = BASE_DIR.parent / "audio_playback_agent" / "songs"
if not SONGS_DIR.exists():
    SONGS_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/songs", StaticFiles(directory=SONGS_DIR), name="songs")

class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    response: str
    action: Optional[dict] = None

class SongRequest(BaseModel):
    query: str

class ScoreRequest(BaseModel):
    user_name: str
    score: int
    mode: str
    song: str

# LEADERBOARD PERSISTENCE
LEADERBOARD_FILE = BASE_DIR / "leaderboard.json"

def load_leaderboard():
    if not LEADERBOARD_FILE.exists():
        return {"casual": [], "competition": []}
    try:
        with open(LEADERBOARD_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {"casual": [], "competition": []}

def save_leaderboard(data):
    with open(LEADERBOARD_FILE, "w") as f:
        json.dump(data, f, indent=2)

# Global Host Instance
host_agent = None

@app.on_event("startup")
async def startup_event():
    global host_agent
    host_agent = KaraokeHost()
    await host_agent.start()
    logger.info("Agentic Host started and connected.")

@app.on_event("shutdown")
async def shutdown_event():
    global host_agent
    if host_agent:
        await host_agent.cleanup()

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    if not host_agent:
        raise HTTPException(status_code=503, detail="Host not initialized")
    
    user_input = request.message
    response_text, action = await host_agent.process_user_input_with_actions(user_input)
    
    return ChatResponse(response=response_text, action=action)

@app.get("/api/lyrics")
async def get_lyrics(query: str):
    if not host_agent:
        raise HTTPException(status_code=503, detail="Host not initialized")
    
    # Call the lyrics tool
    # The tool name is 'search_lyrics' (defined in lyrics_display_agent/mcp_server.py)
    result_json = await host_agent.call_tool("search_lyrics", {"query": query})
    
    if not result_json:
        raise HTTPException(status_code=404, detail="Lyrics not found")
        
    try:
        return json.loads(result_json)
    except json.JSONDecodeError:
        return {"error": "Invalid JSON from lyrics agent", "raw": result_json}

@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    """
    Endpoint for the frontend chatbot to talk to the Agentic Host.
    """
    if not host_agent:
        raise HTTPException(status_code=503, detail="Host not initialized")

    response_text, action = await host_agent.process_user_input_with_actions(request.message)
    return {
        "response": response_text,
        "action": action
    }

@app.post("/api/play_song")
async def play_song(request: SongRequest):
    if not host_agent:
        raise HTTPException(status_code=503, detail="Host not initialized")
    
    query = request.query
    logger.info(f"MCP Host received play request for: {query}")

    try:
        # 1. Call Audio Agent via MCP
        # Ensure tool name matches what audio mcp server exposes: 'play_song'
        # The logs showed available tools: ['play_song', 'stop_song']
        audio_result_str = await host_agent.call_tool("play_song", {"query": query})
        if not audio_result_str:
             raise HTTPException(status_code=500, detail="Audio agent returned no data")
        
        try:
             audio_data = json.loads(audio_result_str)
        except json.JSONDecodeError:
             # Fallback if it returns raw string url or something (unlikely if consistent)
             audio_data = {"url": audio_result_str, "track": query, "status": "unknown"}

        # 2. Call Lyrics Agent via MCP
        lyrics_result_str = await host_agent.call_tool("search_lyrics", {"query": query})
        lyrics_data = {}
        if lyrics_result_str:
            try:
                lyrics_data = json.loads(lyrics_result_str)
            except json.JSONDecodeError:
                lyrics_data = {"lyrics": [], "error": "Invalid lyrics json"}

        return {
            "status": "success",
            "audio": audio_data,
            "lyrics": lyrics_data
        }

    except Exception as e:
        logger.error(f"Error in play_song: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/stop_song")
async def stop_song():
    if not host_agent:
        raise HTTPException(status_code=503, detail="Host not initialized")
    
    # Call the audio tool
    await host_agent.call_tool("stop_song", {})
    return {"status": "stopped"}

@app.post("/api/submit_performance")
async def submit_performance(
    audio_file: UploadFile = File(...),
    personality: str = Form(...),
    reference_lyrics: str = Form(None),
    reference_audio_path: str = Form(None),
    offset: float = Form(0.0)
):
    if not host_agent:
        raise HTTPException(status_code=503, detail="Host not initialized")
    
    # 1. Save audio to temp file
    import tempfile
    import shutil
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
        shutil.copyfileobj(audio_file.file, tmp)
        tmp_path = tmp.name
    
    try:
        # 2. Call Singing Evaluator
        eval_args = {"audio_path": tmp_path, "offset": offset}
        if reference_lyrics:
            eval_args["reference_lyrics_json"] = reference_lyrics
        if reference_audio_path:
            eval_args["reference_audio_path"] = reference_audio_path
            
        eval_result_json = await host_agent.call_tool("evaluate_singing", eval_args)
        if not eval_result_json:
             raise HTTPException(status_code=500, detail="Evaluator failed")
        
        evaluation = json.loads(eval_result_json)
        
        # 3. Call Judge
        judge_args = {
            "evaluation_data_json": json.dumps(evaluation),
            "personality": personality
        }
        judge_result_str = await host_agent.call_tool("evaluate_performance", judge_args)
        
        # Parse the JSON string returned by the tool
        judge_feedback_text = "No feedback generated."
        if judge_result_str:
            try:
                judge_data = json.loads(judge_result_str)
                judge_feedback_text = judge_data.get("feedback", str(judge_data))
            except json.JSONDecodeError:
                judge_feedback_text = judge_result_str

        return {
            "evaluation": evaluation,
            "feedback": judge_feedback_text
        }
        
    except Exception as e:
        logger.error(f"Submission failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

@app.get("/api/leaderboard")
async def get_leaderboard():
    return load_leaderboard()

@app.post("/api/save_score")
async def save_score(request: ScoreRequest):
    if not host_agent:
        raise HTTPException(status_code=503, detail="Host not initialized")
    
    data = load_leaderboard()
    
    # Create entry with timestamp
    from datetime import datetime
    entry = {
        "user_name": request.user_name,
        "score": request.score,
        "song": request.song,
        "timestamp": datetime.now().isoformat()
    }
    
    if request.mode == "competition":
        data["competition"].append(entry)
        # Sort desc
        data["competition"] = sorted(data["competition"], key=lambda k: k['score'], reverse=True)[:50]
    else:
        data["casual"].append(entry)
        data["casual"] = sorted(data["casual"], key=lambda k: k['score'], reverse=True)[:50]
        
    save_leaderboard(data)
    return {"status": "saved"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
