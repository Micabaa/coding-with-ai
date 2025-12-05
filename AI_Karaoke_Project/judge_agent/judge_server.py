import os
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
    print("🎤 Starting Judge Agent MCP Server...")
    # FastMCP runs on stdio by default when called directly
    mcp.run()
