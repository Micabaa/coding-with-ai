<<<<<<< HEAD
<<<<<<< HEAD
from fastapi import FastAPI
from pydantic import BaseModel
import os
# Stelle sicher, dass "openai" und "python-dotenv" in requirements.txt sind!
from openai import OpenAI
from dotenv import load_dotenv

# Lade Umgebungsvariablen (z.B. OPENAI_API_KEY) aus der .env Datei
load_dotenv()
app = FastAPI(title="Judge Agent (MCP Server)")

# Initialisierung des OpenAI Clients (wird nur einmal beim Start des Servers ausgeführt)
try:
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
except Exception as e:
    print(f"WARNUNG: OpenAI Client konnte nicht initialisiert werden. Fehlt der API Key? Fehler: {e}")
    client = None

# Struktur des Datenobjekts, das vom Evaluator Agent gesendet wird (Pydantic Modell für MCP-Kommunikation)
class EvaluationFeedback(BaseModel):
    # Diese Werte sind im Prototyp fiktiv
    accuracy_score: float  # Tonhöhengenauigkeit (0.0 bis 1.0)
    rhythm_score: float    # Rhythmusgenauigkeit (0.0 bis 1.0)
    personality: str       # Gewünschte Judge-Persönlichkeit
    user_input: str        # Die "gesungenen" Lyrics/Text

def load_personality_prompt(name: str) -> str:
    """Lädt den System-Prompt für die Judge-Persönlichkeit aus der Textdatei."""
    # Ersetze Leerzeichen und sichere Pfadkonstruktion
    file_name = f"{name.lower().replace(' ', '_')}.txt"
    try:
        path = os.path.join(os.path.dirname(__file__), "personality_prompts", file_name)
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        print(f"WARNUNG: Persönlichkeits-Datei '{file_name}' nicht gefunden.")
        return "Du bist ein neutraler Kritiker, der kurz und sachlich Feedback gibt."

# MCP Server Endpunkt: Generiert Feedback
@app.post("/generate_feedback/")
async def generate_feedback(feedback: EvaluationFeedback):
    """
    Empfängt die Bewertung vom Singing Evaluator Agent und generiert eine
    personalisierte Antwort mithilfe des LLMs.
    """
    if not client:
        return {"judge_commentary": "LLM Service ist nicht verfügbar (API Key fehlt).", "status": "error"}

    system_prompt = load_personality_prompt(feedback.personality)
    
    # Nutzer-Prompt fasst die strukturierten Daten zusammen
    user_prompt = f"""
    Bewerte diese Performance als {feedback.personality}. Die Performance-Metriken sind:
    - Tonhöhengenauigkeit: {feedback.accuracy_score*100:.0f}%
    - Rhythmus-Score: {feedback.rhythm_score*100:.0f}%
    - Gesungener Text: "{feedback.user_input}"

    Generiere einen kurzen, unterhaltsamen und kreativen Kommentar (maximal 2 Sätze), der die Persönlichkeit widerspiegelt und die Scores berücksichtigt.
    """

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo", 
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7
        )
        commentary = response.choices[0].message.content
        return {"judge_commentary": commentary, "status": "success"}
    except Exception as e:
        # Hier könnten Sie spezifischere API-Fehler behandeln
        return {"judge_commentary": f"Fehler bei der KI-Generierung: {e}", "status": "error"}
=======
# judge_server.py
"""
MCP-compatible Judge Server for the AI Karaoke project.
Provides structured evaluation feedback based on personality and performance data.
Author: An My Behrendt & Mia Baudri
"""

=======
import os
>>>>>>> 923da81 (c)
import json
import logging
import traceback
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
from mcp.server.fastmcp import FastMCP

# === ENVIRONMENT & CONFIG ===
load_dotenv()
MODEL = "gpt-4o-mini"
PROMPTS_DIR = Path(__file__).parent / "personality_prompts"

# === LOGGING CONFIGURATION ===
LOG_FILE = Path(__file__).parent / "judge_server.log"
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger("JudgeAgent")

# === INITIALIZE CLIENT ===
api_key = os.getenv("OPENAI_API_KEY")
client = None
if not api_key:
    logger.warning("Missing OPENAI_API_KEY in .env file. Running in MOCK mode.")
    print("⚠️  WARNING: OPENAI_API_KEY not found. Judge Agent running in MOCK mode.")
else:
    client = OpenAI(api_key=api_key)

# Initialize FastMCP Server
mcp = FastMCP("Judge Agent")

# === HELPER FUNCTIONS ===
def load_prompt(personality: str, feedback_type: str) -> str:
    """Load the correct personality-specific prompt template."""
    prompt_file = f"{personality}_{feedback_type}.txt"
    prompt_path = PROMPTS_DIR / prompt_file
>>>>>>> 866fc75 (...)

    if not prompt_path.exists():
        # Fallback to strict_judge_detail if specific prompt missing
        logger.warning(f"Prompt {prompt_file} not found, falling back to strict_judge_detail.txt")
        return (PROMPTS_DIR / "strict_judge_detail.txt").read_text(encoding="utf-8")

    with open(prompt_path, "r", encoding="utf-8") as f:
        return f.read()

def run_llm(prompt: str) -> str:
    """Send the prompt to OpenAI and return the feedback text."""
    if not client:
        return "[MOCK FEEDBACK] The API key is missing, so here is a placeholder response. Your singing was... interesting! (Mock mode)"
        
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": "You are the Karaoke Judge Agent."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.8,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"OpenAI API Error: {e}")
        return f"Error generating feedback: {str(e)}"

# === TOOLS ===

@mcp.tool()
def evaluate_performance(evaluation_data: dict, personality: str = "strict_judge") -> str:
    """
    Generates personality-based singing feedback based on evaluation data.
    
    Args:
        evaluation_data: JSON object containing pitch, rhythm, and performance metrics.
        personality: The personality of the judge (e.g., 'strict_judge', 'supportive_grandma').
    """
    try:
        feedback_type = evaluation_data.get("feedback_type", "detail")
        logger.info(
            f"Received evaluation for segment={evaluation_data.get('performance_segment_id')} "
            f"with personality={personality}, feedback_type={feedback_type}"
        )

        prompt_template = load_prompt(personality, feedback_type)
        full_prompt = prompt_template.replace(
            "[INSERT THE EVALUATION DATA JSON HERE]",
            json.dumps(evaluation_data, indent=2)
        )

        feedback_text = run_llm(full_prompt)
        logger.info(f"Feedback successfully generated: {feedback_text[:80]}...")

        return feedback_text

    except Exception as e:
        logger.error(f"Unexpected error: {e}\n{traceback.format_exc()}")
        return f"Error: {str(e)}"

if __name__ == "__main__":
<<<<<<< HEAD
<<<<<<< HEAD
<<<<<<< HEAD
    import uvicorn
    # 🚨 Wichtig: Startet den Server auf dem definierten Port
    uvicorn.run(app, host="0.0.0.0", port=8001)
=======
    import asyncio

    print("🎤 Starting Judge Agent MCP Server...")
    logger.info("Judge Agent MCP Server started.")

    try:
        asyncio.run(server.run())
    except KeyboardInterrupt:
        logger.info("Server stopped manually.")
        print("\n Server stopped by user.")
>>>>>>> 866fc75 (...)
=======
    import uvicorn

    print("🎤 Starting Judge Agent FastAPI Server...")
    logger.info("Judge Agent FastAPI Server started.")
    uvicorn.run("judge_server:server", host="0.0.0.0", port=8000, reload=True)
>>>>>>> 923da81 (c)
=======
    print("🎤 Starting Judge Agent MCP Server...")
    # FastMCP runs on stdio by default when called directly
    mcp.run()

>>>>>>> c653189 (singing evaluation)
