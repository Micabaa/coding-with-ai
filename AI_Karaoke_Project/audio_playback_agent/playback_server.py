from flask import Flask, request, jsonify
import os

app = Flask(__name__)

# Directory to store audio files
AUDIO_DIR = 'path/to/audio/files'

@app.route('/play', methods=['POST'])
def play_audio():
    data = request.json
    track_name = data.get('track_name')

    if not track_name:
        return jsonify({'error': 'No track name provided'}), 400

    track_path = os.path.join(AUDIO_DIR, track_name)

    if not os.path.exists(track_path):
        return jsonify({'error': 'Track not found'}), 404

    # Logic to play the audio track
    # This is a placeholder for actual audio playback logic
    return jsonify({'message': f'Playing {track_name}'}), 200

if __name__ == '__main__':
    app.run(port=5000)