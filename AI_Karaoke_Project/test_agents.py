import subprocess
import time
import requests
import os
import signal
import sys

# Configuration
AUDIO_SERVER_URL = "http://localhost:8001"
LYRICS_SERVER_URL = "http://localhost:8002"
AUDIO_SERVER_FILE = "audio_playback_agent/playback_server.py"
LYRICS_SERVER_FILE = "lyrics_display_agent/lyrics_server.py"

def start_server(file_path, port):
    print(f"Starting server: {file_path} on port {port}")
    process = subprocess.Popen(
        [sys.executable, file_path],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    # Wait a bit for server to start
    time.sleep(3)
    return process

def test_audio_agent_dynamic():
    print("\n--- Testing Audio Agent (Dynamic) ---")
    
    # Test Search and Play
    # We'll use a very short query or a known safe one. 
    # "Happy Birthday" is usually safe and short.
    query = "Happy Birthday"
    print(f"Searching and playing: {query}")
    
    try:
        # This might take a few seconds to download
        start_time = time.time()
        resp = requests.post(f"{AUDIO_SERVER_URL}/search_and_play", json={"query": query}, timeout=60)
        duration = time.time() - start_time
        
        print(f"Response ({duration:.2f}s): {resp.status_code}")
        if resp.status_code == 200:
            print(f"  Result: {resp.json()}")
            assert resp.json()['status'] == 'playing'
            
            # Let it play for 3 seconds then stop
            time.sleep(3)
            requests.post(f"{AUDIO_SERVER_URL}/stop")
            print("  Stopped playback.")
            return True
        else:
            print(f"  Error: {resp.text}")
            return False
            
    except Exception as e:
        print(f"Failed to connect/timeout: {e}")
        return False

def test_lyrics_agent_dynamic():
    print("\n--- Testing Lyrics Agent (Dynamic) ---")
    
    # Test Search Lyrics
    # Note: Without a token, this might fail or we test the mock fallback
    query = "Happy Birthday"
    print(f"Searching lyrics for: {query}")
    
    try:
        resp = requests.get(f"{LYRICS_SERVER_URL}/search_lyrics", params={"query": query})
        print(f"Response: {resp.status_code}")
        
        if resp.status_code == 200:
            data = resp.json()
            print(f"  Found: {data['title']}")
            assert len(data['lyrics']) > 0
            return True
        elif resp.status_code == 503:
            print("  Skipping: Genius Token not configured (Expected behavior without token)")
            return True # Not a failure of code, just config
        else:
            print(f"  Error: {resp.text}")
            return False

    except Exception as e:
        print(f"Failed to connect: {e}")
        return False

def main():
    # Start servers
    audio_proc = start_server(AUDIO_SERVER_FILE, 8001)
    lyrics_proc = start_server(LYRICS_SERVER_FILE, 8002)

    try:
        # Run tests
        audio_ok = test_audio_agent_dynamic()
        lyrics_ok = test_lyrics_agent_dynamic()

        if audio_ok and lyrics_ok:
            print("\n✅ All dynamic tests passed!")
        else:
            print("\n❌ Some tests failed.")

    finally:
        # Cleanup
        print("\nStopping servers...")
        audio_proc.terminate()
        lyrics_proc.terminate()
        audio_proc.wait()
        lyrics_proc.wait()

if __name__ == "__main__":
    main()
