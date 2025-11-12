from flask import Flask, request, jsonify

app = Flask(__name__)

# Sample data for demonstration purposes
lyrics_database = {
    "song1": "These are the lyrics for song 1.",
    "song2": "These are the lyrics for song 2.",
}

@app.route('/lyrics/<song_id>', methods=['GET'])
def get_lyrics(song_id):
    lyrics = lyrics_database.get(song_id)
    if lyrics:
        return jsonify({"lyrics": lyrics}), 200
    else:
        return jsonify({"error": "Lyrics not found"}), 404

if __name__ == '__main__':
    app.run(port=5001)