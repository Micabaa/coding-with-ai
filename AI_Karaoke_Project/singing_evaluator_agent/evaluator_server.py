import base64
import tempfile
import os
import logging
import json
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from pydantic import BaseModel
from audio_tools.audio_analysis import analyze_audio

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SingingEvaluator")

app = FastAPI(title="Singing Evaluator Agent")

class EvaluationRequest(BaseModel):
    audio_data: str # Base64 encoded
    performance_segment_id: str = None
    reference_lyrics: str = None # JSON string

@app.post("/evaluate_singing")
async def evaluate_singing(
    audio_file: UploadFile = File(None),
    reference_lyrics: str = Form(None),
    performance_segment_id: str = Form(None),
    reference_audio_path: str = Form(None),
    offset: float = Form(0.0)
):
    """
    Analyzes singing audio to provide pitch and rhythm scores.
    Accepts multipart/form-data with an audio file.
    """
    temp_audio_path = None
    try:
        # Save uploaded file to temp
        if not audio_file:
             raise HTTPException(status_code=400, detail="No audio file provided")
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_audio:
            content = await audio_file.read()
            temp_audio.write(content)
            temp_audio_path = temp_audio.name

        # Parse reference lyrics if provided
        lyrics_data = None
        if reference_lyrics:
            try:
                lyrics_data = json.loads(reference_lyrics)
            except Exception as e:
                logger.warning(f"Failed to parse reference_lyrics JSON: {e}")

        # Analyze audio
        logger.info(f"Analyzing audio file: {temp_audio_path}")
        evaluation_result = analyze_audio(
            temp_audio_path, 
            reference_lyrics=lyrics_data,
            reference_audio_path=reference_audio_path
        )
        
        # Add segment ID if provided
        if performance_segment_id:
            evaluation_result["performance_segment_id"] = performance_segment_id
        
        return evaluation_result

    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
        
    finally:
        # Cleanup temp file
        if temp_audio_path and os.path.exists(temp_audio_path):
            os.remove(temp_audio_path)
            logger.info(f"Cleaned up temp file: {temp_audio_path}")

if __name__ == '__main__':
    import uvicorn
    print("🎤 Starting Singing Evaluator Agent FastAPI Server...")
    uvicorn.run(app, host="0.0.0.0", port=8003)