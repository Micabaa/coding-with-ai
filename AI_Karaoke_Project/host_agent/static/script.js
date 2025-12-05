let currentLyrics = [];
const audioPlayer = document.getElementById('audio-player');
const lyricsDiv = document.getElementById('lyrics-content');
const statusDiv = document.getElementById('status-message');

document.getElementById('play-btn').addEventListener('click', async () => {
    const query = document.getElementById('song-query').value;

    if (!query) {
        alert("Please enter a song name!");
        return;
    }

    statusDiv.textContent = "Searching and downloading... (this may take a moment)";
    lyricsDiv.innerHTML = '<p class="placeholder">Loading...</p>';

    // Reset player
    audioPlayer.pause();
    audioPlayer.style.display = 'none';
    audioPlayer.src = "";
    document.querySelector('.sync-controls').style.display = 'none';

    // Reset offset
    lyricOffset = 0.0;
    updateOffsetDisplay();

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

        // Handle Audio
        if (data.audio.url) {
            audioPlayer.src = data.audio.url;
            audioPlayer.style.display = 'block';
            document.querySelector('.sync-controls').style.display = 'flex';
            audioPlayer.play().catch(e => console.log("Auto-play prevented:", e));
        }

        // Handle Lyrics and Sync
        if (data.lyrics && data.lyrics.lyrics) {
            currentLyrics = data.lyrics.lyrics;
            renderLyrics(currentLyrics);
        } else {
            lyricsDiv.innerHTML = '<p class="placeholder">No lyrics found.</p>';
            currentLyrics = [];
        }

    } catch (error) {
        statusDiv.textContent = "Error: " + error.message;
        console.error(error);
    }
});

document.getElementById('stop-btn').addEventListener('click', async () => {
    audioPlayer.pause();
    audioPlayer.currentTime = 0;
    statusDiv.textContent = "Stopped.";
    // Optional: Call server to ensure backend processes stop if any
    try {
        await fetch('/api/stop_song', { method: 'POST' });
    } catch (error) {
        console.error(error);
    }
});

function renderLyrics(lyrics) {
    lyricsDiv.innerHTML = '';
    lyrics.forEach((line, index) => {
        const p = document.createElement('p');
        p.textContent = line.text;
        p.id = `line-${index}`;
        // Store timestamp for debugging or clicks
        p.dataset.timestamp = line.timestamp;
        lyricsDiv.appendChild(p);
    });
}

let lastHighlightedIndex = -1;
let lyricOffset = 0.0;

function updateOffsetDisplay() {
    const display = document.getElementById('offset-display');
    const sign = lyricOffset >= 0 ? '+' : '';
    display.textContent = `Offset: ${sign}${lyricOffset.toFixed(1)}s`;
}

document.getElementById('offset-minus').addEventListener('click', () => {
    lyricOffset -= 0.5;
    updateOffsetDisplay();
});

document.getElementById('offset-plus').addEventListener('click', () => {
    lyricOffset += 0.5;
    updateOffsetDisplay();
});

function highlightLine(index) {
    if (index === lastHighlightedIndex) return;

    // Remove previous highlight
    if (lastHighlightedIndex !== -1) {
        const prev = document.getElementById(`line-${lastHighlightedIndex}`);
        if (prev) prev.classList.remove('highlight');
    }

    // Add new highlight
    const current = document.getElementById(`line-${index}`);
    if (current) {
        current.classList.add('highlight');

        // Scroll into view
        current.scrollIntoView({
            behavior: 'smooth',
            block: 'center'
        });
    }

    lastHighlightedIndex = index;
}

// Synchronization Logic
audioPlayer.addEventListener('timeupdate', () => {
    const currentTime = audioPlayer.currentTime;
    // Apply offset: adjusted time is what we compare against lyrics timestamps
    // If audio is 10s, and offset is -2s (lyrics delayed), we look for timestamp 8s.
    const effectiveTime = currentTime + lyricOffset;

    if (!currentLyrics.length) return;

    // Find the active line
    let activeIndex = -1;

    for (let i = 0; i < currentLyrics.length; i++) {
        if (currentLyrics[i].timestamp <= effectiveTime) {
            activeIndex = i;
        } else {
            break;
        }
    }

    // Highlight
    if (activeIndex !== -1) {
        highlightLine(activeIndex);
    }
});
