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

if __name__ == "__main__":
    import uvicorn
    # 🚨 Wichtig: Startet den Server auf dem definierten Port
    uvicorn.run(app, host="0.0.0.0", port=8001)