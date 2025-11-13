import os
import json
import logging
import traceback
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
from fastapi import FastAPI
from pydantic import BaseModel

# === ENVIRONMENT & CONFIG ===
load_dotenv()  # loads variables from .env file
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
if not api_key:
    raise RuntimeError("Missing OPENAI_API_KEY in .env file")

client = OpenAI(api_key=api_key)
server = FastAPI(title="Judge Agent API")

# === Pydantic model for request ===
class EvaluationRequest(BaseModel):
    evaluation_data: dict
    personality: str = "strict_judge"


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
    """Send the prompt to OpenAI and return the feedback text."""
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": "You are the Karaoke Judge Agent."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.8,
    )
    return response.choices[0].message.content.strip()


# === ENDPOINT ===
@server.post("/evaluate_performance")
def evaluate_performance(request: EvaluationRequest):
    """Receives evaluation data JSON and returns personality-based singing feedback."""
    evaluation_data = request.evaluation_data
    personality = request.personality

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

        return {"feedback": feedback_text}

    except FileNotFoundError as e:
        logger.error(f"Missing prompt: {e}")
        return {"error": f"Prompt not found: {str(e)}"}

    except Exception as e:
        logger.error(f"Unexpected error: {e}\n{traceback.format_exc()}")
        return {"error": f"Unexpected error: {str(e)}"}


# === RUN SERVER LOCALLY ===
# Run with: uvicorn judge_server:server --reload
if __name__ == "__main__":
    import uvicorn

    print("🎤 Starting Judge Agent FastAPI Server...")
    logger.info("Judge Agent FastAPI Server started.")
    uvicorn.run("judge_server:server", host="0.0.0.0", port=8000, reload=True)
