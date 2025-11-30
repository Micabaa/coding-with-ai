import asyncio
import base64
import json
import numpy as np
import scipy.io.wavfile as wav
import io
import os
import sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Generate synthetic audio
def create_audio_b64():
    sample_rate = 22050
    duration = 1.0
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    audio = 0.5 * np.sin(2 * np.pi * 440 * t) # 440Hz sine wave
    audio_int16 = (audio * 32767).astype(np.int16)
    
    with io.BytesIO() as wav_buffer:
        wav.write(wav_buffer, sample_rate, audio_int16)
        wav_bytes = wav_buffer.getvalue()
        return base64.b64encode(wav_bytes).decode('utf-8')

async def test_singing_evaluator():
    print("\n--- Testing Singing Evaluator (MCP) ---")
    
    # Path to the server script
    server_script = os.path.abspath("singing_evaluator_agent/evaluator_server.py")
    
    server_params = StdioServerParameters(
        command=sys.executable, # Use the same python interpreter
        args=[server_script],
        env=os.environ.copy()
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            audio_b64 = create_audio_b64()
            
            # Dummy lyrics: Expect singing from 0.0 to 1.0s (matches our generated audio)
            dummy_lyrics = json.dumps([
                {"start_time": 0.0, "end_time": 1.0, "text": "La la la"}
            ])
            
            result = await session.call_tool("evaluate_singing", arguments={
                "audio_data": audio_b64,
                "performance_segment_id": "mcp_test_001",
                "reference_lyrics": dummy_lyrics
            })
            
            # FastMCP returns a list of TextContent or ImageContent
            # We assume the tool returns the result as text (JSON string) or just the dict if FastMCP handles it.
            # FastMCP tools return the return value of the function.
            # If the return value is a dict, FastMCP converts it to TextContent with JSON string.
            
            print("Result:", result)
            
            # Parse the content
            if result.content and hasattr(result.content[0], 'text'):
                data = json.loads(result.content[0].text)
                return data
            return None

async def test_judge_agent(evaluation_data):
    print("\n--- Testing Judge Agent (MCP) ---")
    
    server_script = os.path.abspath("judge_agent/judge_server.py")
    
    server_params = StdioServerParameters(
        command=sys.executable,
        args=[server_script],
        env=os.environ.copy()
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            result = await session.call_tool("evaluate_performance", arguments={
                "evaluation_data": evaluation_data,
                "personality": "strict_judge"
            })
            
            print("Feedback:", result)
            return result

async def main():
    eval_result = await test_singing_evaluator()
    if eval_result:
        await test_judge_agent(eval_result)

if __name__ == "__main__":
    asyncio.run(main())
