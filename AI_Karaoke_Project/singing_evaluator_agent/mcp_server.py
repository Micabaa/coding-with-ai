import asyncio
import logging
import json
import os
import tempfile
import base64
from mcp.server.fastmcp import FastMCP
from audio_tools.audio_analysis import analyze_audio

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SingingEvaluatorMCP")

# Initialize FastMCP Server
mcp = FastMCP("Singing Evaluator")

@mcp.tool()
def evaluate_singing(audio_path: str, reference_lyrics_json: str = None, reference_audio_path: str = None) -> str:
    """
    Analyzes singing audio to provide pitch and rhythm scores.
    
    Args:
        audio_path: Path to the WAV audio file.
        reference_lyrics_json: JSON string of lyrics with timing data.
        reference_audio_path: Path to the original song audio file (for comparison).
        
    Returns:
        JSON string containing the evaluation results (pitch_score, rhythm_score, etc.)
    """
    try:
        # Verify file exists
        if not os.path.exists(audio_path):
            return json.dumps({"error": f"Audio file not found: {audio_path}"})

        # Parse lyrics
        lyrics_data = None
        if reference_lyrics_json:
            try:
                lyrics_data = json.loads(reference_lyrics_json)
            except Exception as e:
                logger.warning(f"Failed to parse reference_lyrics JSON: {e}")

        # Analyze
        logger.info(f"Analyzing audio file: {audio_path}")
        result = analyze_audio(
            audio_path,
            reference_lyrics=lyrics_data,
            reference_audio_path=reference_audio_path
        )
        
        return json.dumps(result)

    except Exception as e:
        logger.error(f"Error in evaluate_singing: {e}")
        return json.dumps({"error": str(e)})

if __name__ == "__main__":
    mcp.run()
