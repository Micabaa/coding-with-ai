import base64
import tempfile
import os
import logging
from mcp.server.fastmcp import FastMCP
from audio_tools.audio_analysis import analyze_audio

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SingingEvaluator")

# Initialize FastMCP Server
mcp = FastMCP("Singing Evaluator")

@mcp.tool()
def evaluate_singing(audio_data: str, performance_segment_id: str = None, reference_lyrics: str = None) -> dict:
    """
    Analyzes singing audio to provide pitch and rhythm scores.
    
    Args:
        audio_data: Base64 encoded audio string (WAV format preferred).
        performance_segment_id: Optional ID for the performance segment.
        reference_lyrics: Optional JSON string containing list of lyric objects with start_time, end_time, text.
    """
    try:
        if not audio_data:
            return {"error": "No audio_data provided"}

        # Parse reference lyrics if provided
        lyrics_data = None
        if reference_lyrics:
            try:
                import json
                lyrics_data = json.loads(reference_lyrics)
            except Exception as e:
                logger.warning(f"Failed to parse reference_lyrics JSON: {e}")

        # Decode base64 to temp file
        temp_audio_path = None
        try:
            audio_bytes = base64.b64decode(audio_data)
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_audio:
                temp_audio.write(audio_bytes)
                temp_audio_path = temp_audio.name
        except Exception as e:
            logger.error(f"Failed to decode audio: {e}")
            return {"error": "Invalid base64 audio data"}

        # Analyze audio
        try:
            logger.info(f"Analyzing audio file: {temp_audio_path}")
            evaluation_result = analyze_audio(temp_audio_path, reference_lyrics=lyrics_data)
            
            # Add segment ID if provided
            if performance_segment_id:
                evaluation_result["performance_segment_id"] = performance_segment_id
            
            return evaluation_result
        finally:
            # Cleanup temp file
            if temp_audio_path and os.path.exists(temp_audio_path):
                os.remove(temp_audio_path)
                logger.info(f"Cleaned up temp file: {temp_audio_path}")

    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return {"error": str(e)}

if __name__ == '__main__':
    print("🎤 Starting Singing Evaluator Agent MCP Server...")
    mcp.run()