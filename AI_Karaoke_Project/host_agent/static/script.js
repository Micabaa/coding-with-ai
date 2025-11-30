document.getElementById('play-btn').addEventListener('click', async () => {
    const query = document.getElementById('song-query').value;
    const statusDiv = document.getElementById('status-message');
    const lyricsDiv = document.getElementById('lyrics-content');

    if (!query) {
        alert("Please enter a song name!");
        return;
    }

    statusDiv.textContent = "Searching and downloading... (this may take a moment)";
    lyricsDiv.innerHTML = '<p class="placeholder">Loading...</p>';

    try {
        const response = await fetch('/api/play_song', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ query: query })
        });

        if (!response.ok) {
            throw new Error(`Server error: ${response.statusText}`);
        }

        const data = await response.json();
        
        statusDiv.textContent = `Playing: ${data.audio.track}`;
        
        // Display Lyrics
        if (data.lyrics && data.lyrics.lyrics) {
            lyricsDiv.innerHTML = '';
            data.lyrics.lyrics.forEach(line => {
                const p = document.createElement('p');
                p.textContent = line.text;
                lyricsDiv.appendChild(p);
            });
        } else {
            lyricsDiv.innerHTML = '<p class="placeholder">No lyrics found.</p>';
        }

    } catch (error) {
        statusDiv.textContent = "Error: " + error.message;
        console.error(error);
    }
});

document.getElementById('stop-btn').addEventListener('click', async () => {
    try {
        await fetch('/api/stop_song', { method: 'POST' });
        document.getElementById('status-message').textContent = "Stopped.";
    } catch (error) {
        console.error(error);
    }
});
