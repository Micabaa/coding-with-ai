import asyncio
import base64
import json
import os
import sys
import argparse
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def evaluate_file(audio_path, lyrics_path=None):
    print(f"\n--- Testing Singing Evaluator with file: {audio_path} ---")
    
    if not os.path.exists(audio_path):
        print(f"Error: Audio file not found at {audio_path}")
        return

    # Read and encode audio
    with open(audio_path, "rb") as audio_file:
        audio_bytes = audio_file.read()
        audio_b64 = base64.b64encode(audio_bytes).decode('utf-8')

    # Load lyrics if provided
    reference_lyrics = None
    if lyrics_path:
        if os.path.exists(lyrics_path):
            with open(lyrics_path, "r") as f:
                reference_lyrics = f.read() # Expecting JSON string in file
                print(f"Loaded lyrics from {lyrics_path}")
        else:
            print(f"Warning: Lyrics file not found at {lyrics_path}")

    # Path to the server script
    # Assuming we are running from the project root
    server_script = os.path.abspath("singing_evaluator_agent/evaluator_server.py")
    
    server_params = StdioServerParameters(
        command=sys.executable,
        args=[server_script],
        env=os.environ.copy()
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            arguments = {
                "audio_data": audio_b64,
                "performance_segment_id": "real_audio_test"
            }
            
            if reference_lyrics:
                arguments["reference_lyrics"] = reference_lyrics
            
            print("Sending request to Singing Evaluator...")
            result = await session.call_tool("evaluate_singing", arguments=arguments)
            
            print("\n--- Evaluation Result ---")
            if result.content and hasattr(result.content[0], 'text'):
                data = json.loads(result.content[0].text)
                print(json.dumps(data, indent=2))
            else:
                print(result)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test Singing Evaluator with a real audio file.")
    parser.add_argument("audio_file", help="Path to the audio file (WAV, MP3, etc.)")
    parser.add_argument("--lyrics", help="Path to a JSON file containing lyrics timestamps", default=None)
    
    args = parser.parse_args()
    asyncio.run(evaluate_file(args.audio_file, args.lyrics))
