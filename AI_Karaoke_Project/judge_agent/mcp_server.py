import logging
import os
import json
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
from mcp.server.fastmcp import FastMCP

# === ENVIRONMENT & CONFIG ===
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)
MODEL = "gpt-4o-mini"
PROMPTS_DIR = Path(__file__).parent / "personality_prompts"

# === LOGGING CONFIGURATION ===
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("JudgeMCP")

# === INITIALIZE CLIENT ===
api_key = os.getenv("OPENAI_API_KEY")
client = None
if not api_key:
    logger.warning("Missing OPENAI_API_KEY in .env file. Running in MOCK mode.")
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
        fallback_path = PROMPTS_DIR / "strict_judge_detail.txt"
        if fallback_path.exists():
            return fallback_path.read_text(encoding="utf-8")
        return "You are a karaoke judge. Provide feedback."

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

@mcp.tool()
def evaluate_performance(evaluation_data_json: str, personality: str = "strict_judge") -> str:
    """
    Generates personality-based singing feedback based on evaluation data.
    
    Args:
        evaluation_data_json: JSON string containing pitch_score, rhythm_score, etc.
        personality: The personality of the judge (e.g., "strict_judge", "kind_judge").
        
    Returns:
        JSON string containing the feedback text.
    """
    try:
        evaluation_data = json.loads(evaluation_data_json)
        
        logger.info(f"Received evaluation for personality={personality}")

        feedback_type = evaluation_data.get("feedback_type", "detail")
        prompt_template = load_prompt(personality, feedback_type)
        
        full_prompt = prompt_template.replace(
            "[INSERT THE EVALUATION DATA JSON HERE]",
            json.dumps(evaluation_data, indent=2)
        )

        feedback_text = run_llm(full_prompt)
        logger.info(f"Feedback successfully generated: {feedback_text[:80]}...")

        return json.dumps({"feedback": feedback_text})

    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return json.dumps({"error": str(e)})

@mcp.tool()
def create_persona(name: str, description: str) -> str:
    """
    Creates a new judge personality by generating a system prompt.
    Requirement B4: Meta-programming (AI generating its own config).
    
    Args:
        name: The name of the personality (e.g., "gangster", "yoda").
        description: Description of how they should talk (e.g., "Talks like a 1920s mobster").
        
    Returns:
        Status message.
    """
    if not client:
        return "Error: OpenAI API key missing."
        
    try:
        # 1. Ask LLM to generate the prompt
        meta_prompt = f"""
        You are an expert Prompt Engineer.
        Create a System Prompt for an AI Karaoke Judge who has the following personality:
        "{description}"
        
        The system prompt must include the placeholder [INSERT THE EVALUATION DATA JSON HERE] where the scores will be inserted.
        The prompt should instruct the AI to be funny, specific, and stay in character.
        Return ONLY the prompt text, nothing else.
        """
        
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": meta_prompt}],
            temperature=0.7
        )
        
        generated_prompt = response.choices[0].message.content.strip()
        
        # 2. Save to file
        filename = f"{name}_detail.txt"
        file_path = PROMPTS_DIR / filename
        
        if not PROMPTS_DIR.exists():
            PROMPTS_DIR.mkdir(parents=True, exist_ok=True)
            
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(generated_prompt)
            
        logger.info(f"Created new persona: {name}")
        return json.dumps({
            "status": "success", 
            "message": f"Created new judge personality: '{name}'. You can now use it!",
            "file": str(file_path)
        })
        
    except Exception as e:
        logger.error(f"Failed to create persona: {e}")
        return json.dumps({"error": str(e)})

if __name__ == "__main__":
    mcp.run()
