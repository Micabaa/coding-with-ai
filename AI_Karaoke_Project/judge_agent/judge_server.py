# judge_server.py
"""
MCP-compatible Judge Server for the AI Karaoke project.
Provides structured evaluation feedback based on personality and performance data.
Author: An My Behrendt & Mia Baudri
"""

import json
import logging
import traceback
from pathlib import Path
import google.generativeai as genai
from mcp.server import Server

# === SETTINGS ===
MODEL = "gemini-1.5-pro"
PROMPTS_DIR = Path(__file__).parent / "personality_prompts"

# === LOGGING CONFIGURATION ===
LOG_FILE = Path(__file__).parent / "judge_server.log"
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger("JudgeAgent")

# === INITIALIZE OPENAI CLIENT AND MCP SERVER ===
genai.configure(api_key="YOUR_GEMINI_KEY")  # or set via env var: GOOGLE_API_KEY
server = Server("judge-agent")


# === HELPER FUNCTIONS ===
def load_prompt(personality: str, feedback_type: str) -> str:
    """Load the correct personality-specific prompt template."""
    prompt_file = f"{personality}_{feedback_type}.txt"
    prompt_path = PROMPTS_DIR / prompt_file

    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt file not found: {prompt_path}")

    with open(prompt_path, "r", encoding="utf-8") as f:
        return f.read()


def run_llm(prompt: str) -> str:
    """Send the prompt to Gemini and return the response text."""
    response = genai.GenerativeModel(MODEL).generate_content(prompt)
    return response.text.strip()



# === MCP FUNCTION ===
@server.function("evaluate_performance")
def evaluate_performance(evaluation_data: dict, personality: str = "strict_judge"):
    """
    Receives evaluation data JSON and returns personality-based singing feedback.
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

        return {"content": {"feedback": feedback_text}}

    except FileNotFoundError as e:
        logger.error(f"Missing prompt: {e}")
        return {"content": {"error": f"Prompt not found: {str(e)}"}}

    except Exception as e:
        logger.error(f"Unexpected error: {e}\n{traceback.format_exc()}")
        return {"content": {"error": f"Unexpected error: {str(e)}"}}



# === ENTRY POINT ===
if __name__ == "__main__":
    import asyncio

    print("🎤 Starting Judge Agent MCP Server...")
    logger.info("Judge Agent MCP Server started.")

    try:
        asyncio.run(server.run())
    except KeyboardInterrupt:
        logger.info("Server stopped manually.")
        print("\n Server stopped by user.")
