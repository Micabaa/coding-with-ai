import requests
import base64
import json
import numpy as np
import scipy.io.wavfile as wav
import io
import time

def generate_sine_wave(frequency=440, duration=1.0, sample_rate=22050):
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    audio = 0.5 * np.sin(2 * np.pi * frequency * t)
    return audio, sample_rate

def create_audio_b64():
    audio, sr = generate_sine_wave()
    # Convert to 16-bit PCM
    audio_int16 = (audio * 32767).astype(np.int16)
    
    with io.BytesIO() as wav_buffer:
        wav.write(wav_buffer, sr, audio_int16)
        wav_bytes = wav_buffer.getvalue()
        return base64.b64encode(wav_bytes).decode('utf-8')

def test_singing_evaluator():
    print("\n--- Testing Singing Evaluator ---")
    url = "http://localhost:5002/evaluate"
    audio_b64 = create_audio_b64()
    
    payload = {
        "audio_data": audio_b64,
        "performance_segment_id": "test_segment_001"
    }
    
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        result = response.json()
        print("Success! Result:")
        print(json.dumps(result, indent=2))
        return result
    except Exception as e:
        print(f"Error testing Singing Evaluator: {e}")
        return None

def test_judge_agent(evaluation_data):
    print("\n--- Testing Judge Agent ---")
    url = "http://localhost:8000/evaluate_performance"
    
    payload = {
        "evaluation_data": evaluation_data,
        "personality": "strict_judge"
    }
    
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        result = response.json()
        print("Success! Feedback:")
        print(result.get("feedback"))
        return result
    except Exception as e:
        print(f"Error testing Judge Agent: {e}")
        return None

if __name__ == "__main__":
    # Wait for servers to start
    print("Waiting for servers to be ready...")
    time.sleep(5) 
    
    eval_result = test_singing_evaluator()
    if eval_result:
        test_judge_agent(eval_result)
