import requests
import time
import sys

BASE_URL = "http://localhost:8000"

def wait_for_server():
    print("Waiting for server to start...")
    for _ in range(30):
        try:
            requests.get(BASE_URL)
            print("✅ Server is up!")
            return True
        except requests.exceptions.ConnectionError:
            time.sleep(1)
    print("❌ Server failed to start.")
    return False

def test_chat():
    print("\n--- Testing /chat ---")
    payload = {"message": "I want to sing Shape of You"}
    try:
        resp = requests.post(f"{BASE_URL}/chat", json=payload, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        print(f"Response: {data['response']}")
        if data.get('action'):
            print(f"Action: {data['action']}")
            if data['action']['type'] == 'play_audio':
                print("✅ Action type is correct.")
            else:
                print("❌ Unexpected action type.")
        else:
            print("⚠️ No action returned (might be just chat).")
    except Exception as e:
        print(f"❌ Chat test failed: {e}")

def test_lyrics():
    print("\n--- Testing /api/lyrics ---")
    try:
        resp = requests.get(f"{BASE_URL}/api/lyrics", params={"query": "Bohemian Rhapsody"}, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if 'lyrics' in data:
            print(f"✅ Lyrics found for: {data.get('title', 'Unknown')}")
            print(f"First line: {data['lyrics'][0] if data['lyrics'] else 'Empty'}")
        else:
            print("❌ No lyrics field in response.")
    except Exception as e:
        print(f"❌ Lyrics test failed: {e}")

if __name__ == "__main__":
    if wait_for_server():
        test_chat()
        test_lyrics()
