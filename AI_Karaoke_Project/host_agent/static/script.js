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
// ... (Previous code remains)

// === RECORDING LOGIC ===
let mediaRecorder;
let audioChunks = [];
let isRecording = false;

const recordBtn = document.getElementById('record-btn');
const judgeSection = document.getElementById('judge-section');
const feedbackDiv = document.getElementById('judge-feedback');
const scoreDiv = document.getElementById('score-display');

if (recordBtn) {
    recordBtn.addEventListener('click', async () => {
        if (!isRecording) {
            startRecording();
        } else {
            stopRecordingAndJudge();
        }
    });
}

async function startRecording() {
    try {
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
            throw new Error("Browser API 'navigator.mediaDevices.getUserMedia' is not available. This usually happens if you are not using HTTPS or localhost. Please ensure you are accessing the app via http://localhost:8000.");
        }
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        mediaRecorder = new MediaRecorder(stream);
        audioChunks = [];

        mediaRecorder.ondataavailable = event => {
            audioChunks.push(event.data);
        };

        mediaRecorder.start();
        isRecording = true;
        recordBtn.textContent = "⏹ Stop & Judge";
        recordBtn.classList.add("recording");
        statusDiv.textContent = "🎤 Recording... Sing your heart out!";

        // Clear previous results
        judgeSection.style.display = 'none';
        feedbackDiv.textContent = "";
        scoreDiv.textContent = "";

    } catch (err) {
        console.error("Error accessing microphone:", err);
        let msg = "Could not access microphone.";
        if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
            msg += " Permission denied. Please allow microphone access in your browser settings.";
        } else if (err.name === 'NotFoundError' || err.name === 'DevicesNotFoundError') {
            msg += " No microphone found.";
        } else {
            msg += " Error: " + err.message;
        }
        alert(msg);
    }
}

async function stopRecordingAndJudge() {
    if (!mediaRecorder) return;

    mediaRecorder.stop();
    isRecording = false;
    recordBtn.textContent = "🎤 Start Recording";
    recordBtn.classList.remove("recording");
    statusDiv.textContent = "Processing performance...";

    mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
        await submitPerformance(audioBlob);
    };
}

async function submitPerformance(audioBlob) {
    const formData = new FormData();
    formData.append("audio_file", audioBlob, "performance.wav");

    // Get selected personality (assuming a dropdown exists, or default)
    const personality = document.getElementById('personality-select')?.value || "strict_judge";
    formData.append("personality", personality);

    // Send current lyrics for timing analysis
    if (currentLyrics && currentLyrics.length > 0) {
        formData.append("reference_lyrics", JSON.stringify(currentLyrics));
    }

    try {
        const response = await fetch('/api/submit_performance', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            throw new Error(`Server error: ${response.statusText}`);
        }

        const data = await response.json();
        displayResults(data);

    } catch (error) {
        statusDiv.textContent = "Error getting feedback: " + error.message;
        console.error(error);
    }
}

function displayResults(data) {
    statusDiv.textContent = "Feedback Received!";
    judgeSection.style.display = 'block';

    // Display Scores
    const scores = data.evaluation;
    scoreDiv.innerHTML = `
        <p><strong>Pitch Accuracy:</strong> ${(scores.pitch_accuracy_score * 100).toFixed(0)}%</p>
        <p><strong>Rhythm:</strong> ${(scores.rhythm_score * 100).toFixed(0)}%</p>
        <p><strong>Lyrics:</strong> ${(scores.lyrics_score * 100).toFixed(0)}%</p>
        <p><strong>Vocal Power:</strong> ${scores.vocal_power}</p>
    `;

    // Display Judge Feedback
    feedbackDiv.innerHTML = `<em>"${data.feedback}"</em>`;

    // Display Pitch Detail
    if (scores.pitch_detail) {
        const p = scores.pitch_detail;
        const bar = document.getElementById('pitch-bar');
        // Simple flex bar
        bar.innerHTML = `
            <div style="width: ${p.low * 100}%; background-color: #ff4d4d;" title="Too Low: ${(p.low * 100).toFixed(0)}%"></div>
            <div style="width: ${p.perfect * 100}%; background-color: #4caf50;" title="Perfect: ${(p.perfect * 100).toFixed(0)}%"></div>
            <div style="width: ${p.high * 100}%; background-color: #ff9800;" title="Too High: ${(p.high * 100).toFixed(0)}%"></div>
        `;
    }

    // Display Lyrics Diff
    if (scores.lyrics_diff) {
        const diffDiv = document.getElementById('lyrics-diff');
        diffDiv.innerHTML = scores.lyrics_diff.map(item => {
            if (item.status === 'matched') return `<span class="word-matched">${item.word} </span>`;
            if (item.status === 'missing') return `<span class="word-missing">${item.word} </span>`;
            if (item.status === 'wrong') {
                let html = `<span class="word-wrong">${item.word}</span>`;
                if (item.heard) {
                    html += ` <span class="word-heard">(${item.heard})</span>`;
                }
                return html + ' ';
            }
            if (item.status === 'extra') return `<span class="word-extra">+${item.word} </span>`;
            return '';
        }).join('');
    }

    // Scroll to feedback
    judgeSection.scrollIntoView({ behavior: 'smooth' });
}
