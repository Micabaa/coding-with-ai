<<<<<<< HEAD
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
=======
import requests
import json
import time

# --- Agent Adressen (MCP Server Ports) ---
# Im Prototyp laufen alle lokal auf verschiedenen Ports
JUDGE_AGENT_URL = "http://127.0.0.1:8001"
# EVALUATOR_AGENT_URL = "http://127.0.0.1:8002" # Wird später hinzugefügt
# PLAYBACK_AGENT_URL = "http://127.0.0.1:8003" # Wird später hinzugefügt

class HostCoordinator:
    """
    Der Host Agent orchestriert den gesamten Karaoke-Fluss.
    Er agiert als Client, der die Funktionen der MCP-Server (Judge, Evaluator etc.) aufruft.
    """

    def __init__(self):
        print("🎤 AI Karaoke Host Coordinator gestartet.")

    def run_prototype(self):
        """
        Führt einen einfachen textbasierten Karaoke-Durchlauf aus (Prototyp Phase).
        Datenfluss: User Input (simuliert) -> Fiktive Scores -> Judge Agent (LLM) -> Feedback
        """
        
        print("\n--- Start des Prototypen (Text-Input) ---")
        
        # 1. Benutzer-Input simulieren
        song_title = "Bohemian Rhapsody"
        user_lyrics = "Mama, just killed a man, put a gun against his head, pulled my trigger, now he's dead."
        
        # 2. Fiktives Feedback generieren (Normalerweise Aufgabe des Singing Evaluator Agent)
        # Wir simulieren hier ein Ergebnis, um den Judge Agent zu füttern
        fictional_scores = {
            "accuracy_score": 0.55,  # Mäßige Genauigkeit
            "rhythm_score": 0.88,    # Guter Rhythmus
            "personality": "Strict Judge", # Wechseln Sie hier zu "Supportive Grandma" zum Testen
            "user_input": user_lyrics
        }
        
        print(f"Lied: **{song_title}**")
        print(f"Gesungen (simuliert): '{user_lyrics[:40]}...'")
        print(f"Scores (fiktiv): {fictional_scores['accuracy_score']*100:.0f}% Pitch, {fictional_scores['rhythm_score']*100:.0f}% Rhythm.")

        # 3. Judge Agent (MCP Server) aufrufen
        print(f"\n=> Aufruf des Judge Agent ({fictional_scores['personality']})...")
        
        feedback_url = f"{JUDGE_AGENT_URL}/generate_feedback/"
        
        try:
            # Sende das EvaluationFeedback Pydantic-Modell als JSON
            response = requests.post(
                feedback_url,
                json=fictional_scores,
                timeout=10
            )
            response.raise_for_status() # Löst Ausnahme bei schlechtem Statuscode (4xx, 5xx)

            judge_response = response.json()
            
            # 4. Feedback anzeigen
            if judge_response.get("status") == "success":
                print("\n✅ KI-Feedback erhalten:")
                print(f"» **{judge_response['judge_commentary']}**")
            else:
                print(f"\n❌ Fehler beim Judge Agent: {judge_response.get('judge_commentary', 'Unbekannter Fehler')}")

        except requests.exceptions.ConnectionError:
            print(f"\n❌ VERBINDUNGSFEHLER: Judge Agent unter {JUDGE_AGENT_URL} ist nicht erreichbar.")
            print("Stellen Sie sicher, dass Sie den Server gestartet haben: uvicorn judge_server:app --reload --port 8001")
        except requests.exceptions.RequestException as e:
            print(f"\n❌ Ein HTTP-Fehler ist aufgetreten: {e}")


if __name__ == "__main__":
    
    # 🚨 WICHTIG: Sie müssen zuerst den Judge Agent in einem separaten Terminal starten:
    # 
    # Navigieren Sie zu /AI_Karaoke_Project/judge_agent und führen Sie aus:
    # uvicorn judge_server:app --reload --port 8001
    
    # Optional: Fügen Sie Ihre OpenAI API Key in einer .env Datei im judge_agent Ordner hinzu.

    time.sleep(1) # Kurze Pause zum Starten
    coordinator = HostCoordinator()
    coordinator.run_prototype()
>>>>>>> 5b7bbed (agents setup)
