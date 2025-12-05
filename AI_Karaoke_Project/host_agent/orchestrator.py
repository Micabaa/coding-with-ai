import asyncio
import sys
import os
import json
import base64
import sounddevice as sd
import numpy as np
import scipy.io.wavfile as wav
import io
import argparse
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Configuration
SAMPLE_RATE = 44100
CHANNELS = 1

def record_audio(duration):
    """Records audio from the microphone."""
    print(f"🎤 Recording for {duration} seconds...")
    recording = sd.rec(int(duration * SAMPLE_RATE), samplerate=SAMPLE_RATE, channels=CHANNELS, dtype='int16')
    sd.wait()
    print("✅ Recording complete.")
    return recording

def audio_to_base64(audio_data):
    """Converts numpy array audio to base64 string."""
    with io.BytesIO() as wav_buffer:
        wav.write(wav_buffer, SAMPLE_RATE, audio_data)
        wav_bytes = wav_buffer.getvalue()
        return base64.b64encode(wav_bytes).decode('utf-8')

async def run_karaoke_session(song_query):
    print("\n--- 🎵 AI Karaoke Orchestrator 🎵 ---")
    
    # Define server parameters
    env = os.environ.copy()
    python_cmd = sys.executable
    
    # Paths to servers
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    lyrics_script = os.path.join(base_dir, "lyrics_display_agent", "lyrics_server.py")
    playback_script = os.path.join(base_dir, "audio_playback_agent", "playback_server.py")
    evaluator_script = os.path.join(base_dir, "singing_evaluator_agent", "evaluator_server.py")
    judge_script = os.path.join(base_dir, "judge_agent", "judge_server.py")

    # 1. Connect to Lyrics Agent
    print(f"🔍 Searching lyrics for: {song_query}")
    lyrics_data = None
    
    async with stdio_client(StdioServerParameters(command=python_cmd, args=[lyrics_script], env=env)) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool("search_lyrics", arguments={"query": song_query})
            if result.content:
                try:
                    lyrics_data = json.loads(result.content[0].text)
                    print(f"✅ Found lyrics for: {lyrics_data.get('title')}")
                except:
                    print(f"❌ Error parsing lyrics: {result.content[0].text}")
                    return

    if not lyrics_data:
        return

    # 2. Connect to Playback Agent
    print(f"🎧 Searching and playing audio for: {song_query}")
    
    # We need to keep the playback session open while recording? 
    # Actually, the playback agent uses subprocess.Popen, so it might persist if we close the session?
    # Let's try keeping it open or just calling it. FastMCP tools return immediately.
    # But if the server process dies, the subprocess might die too depending on how it's handled.
    # For now, let's assume we can call it and then move on.
    
    async with stdio_client(StdioServerParameters(command=python_cmd, args=[playback_script], env=env)) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool("search_and_play", arguments={"query": song_query})
            print(f"▶️  Playback status: {result.content[0].text}")

    # 3. Record User Singing
    # In a real app, we would stream this. Here we record for a fixed duration (e.g., 15s for demo)
    RECORD_DURATION = 15 
    print(f"🎤 Get ready to sing! Recording {RECORD_DURATION}s...")
    user_audio = record_audio(RECORD_DURATION)
    audio_b64 = audio_to_base64(user_audio)

    # Stop Playback
    async with stdio_client(StdioServerParameters(command=python_cmd, args=[playback_script], env=env)) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            await session.call_tool("stop_audio")
            print("⏹️  Playback stopped.")

    # 4. Evaluate Singing
    print("📊 Evaluating performance...")
    evaluation_result = None
    
    # Prepare lyrics for evaluation (just the list of objects)
    reference_lyrics_json = json.dumps(lyrics_data.get('lyrics', []))
    
    async with stdio_client(StdioServerParameters(command=python_cmd, args=[evaluator_script], env=env)) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool("evaluate_singing", arguments={
                "audio_data": audio_b64,
                "performance_segment_id": "session_001",
                "reference_lyrics": reference_lyrics_json
            })
            if result.content:
                evaluation_result = json.loads(result.content[0].text)
                print(f"✅ Evaluation complete. Score: {evaluation_result.get('overall_score', 0):.2f}")

    if not evaluation_result:
        print("❌ Evaluation failed.")
        return

    # 5. Judge Feedback
    print("👨‍⚖️  Judge is deliberating...")
    
    # Add the song title to the evaluation data for context
    evaluation_result["user_input"] = f"Singing {lyrics_data.get('title')}"
    
    async with stdio_client(StdioServerParameters(command=python_cmd, args=[judge_script], env=env)) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool("evaluate_performance", arguments={
                "evaluation_data": evaluation_result,
                "personality": "simon_cowell" # Let's default to a fun one
            })
            print("\n" + "="*40)
            print("📢 JUDGE'S VERDICT:")
            print(result.content[0].text)
            print("="*40 + "\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AI Karaoke Orchestrator")
    parser.add_argument("song", help="Name of the song to sing")
    args = parser.parse_args()
    
    try:
        asyncio.run(run_karaoke_session(args.song))
    except KeyboardInterrupt:
        print("\nSession cancelled.")
