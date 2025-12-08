let currentLyrics = [];
let lyricOffset = 0.0;
const videoPlayer = document.getElementById('video-player');
const lyricsDiv = document.getElementById('lyrics-content');
const statusDiv = document.getElementById('status-message');
const judgeSection = document.getElementById('judge-section');
const feedbackDiv = document.getElementById('judge-feedback');
const scoreDiv = document.getElementById('score-display');


// Global stream to hold permission
let audioStream = null;
let currentSongPath = null;

document.getElementById('play-btn').addEventListener('click', async () => {
    const query = document.getElementById('song-query').value;

    if (!query) {
        alert("Please enter a song name!");
        return;
    }

    // 1. Get Microphone Permission IMMEDIATELY (User Gesture)
    try {
        audioStream = await navigator.mediaDevices.getUserMedia({
            audio: {
                echoCancellation: true,
                noiseSuppression: true,
                autoGainControl: true
            }
        });
    } catch (err) {
        console.error("Mic access failed:", err);
        alert("Microphone access is required for karaoke scoring! Please allow it.");
        return;
    }

    statusDiv.textContent = "Downloading video... (this may take 10-30 seconds)";
    lyricsDiv.innerHTML = '<p class="placeholder">Loading...</p>';

    // Reset player
    videoPlayer.pause();
    videoPlayer.style.display = 'none';
    videoPlayer.src = "";
    document.querySelector('.sync-controls').style.display = 'none';

    // Reset offset
    updateOffsetDisplay(0.0);

    // Clear previous results
    document.getElementById('judge-section').style.display = 'none';
    document.getElementById('judge-feedback').textContent = "";
    document.getElementById('score-display').textContent = "";

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

        const duration = videoPlayer.duration;
        statusDiv.textContent = `Playing: ${data.audio.track} [${duration ? duration.toFixed(0) + 's' : 'Unknown'}] (Recording Started 🔴)`;

        // Update duration if it loads later
        videoPlayer.addEventListener('loadedmetadata', () => {
            statusDiv.textContent = `Playing: ${data.audio.track} [${videoPlayer.duration.toFixed(0)}s] (Recording Started 🔴)`;
        });

        // Handle Video
        if (data.audio.url) {
            videoPlayer.src = data.audio.url;
            videoPlayer.style.display = 'block';
            document.querySelector('.sync-controls').style.display = 'flex';

            // Do NOT start recording immediately.
            // Wait for 'playing' event to sync with video start.

            videoPlayer.play().catch(e => console.log("Auto-play prevented:", e));

            // Auto-Offset Removed - User will sync manually
            updateOffsetDisplay(0.0);
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

// Event listener for precise sync
videoPlayer.addEventListener('playing', () => {
    if (audioStream && !isRecording) {
        console.log("Video started playing - Starting Recording...");
        startRecording(audioStream);
    }
});

document.getElementById('stop-btn').addEventListener('click', async () => {
    // 1. Stop Video
    videoPlayer.pause();

    // 2. Stop Recording & Submit
    if (isRecording) {
        stopRecordingAndJudge();
    } else {
        statusDiv.textContent = "Stopped (No recording was active).";
    }

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
        lyricsDiv.appendChild(p);
    });
}

function updateOffsetDisplay(newOffset) {
    if (newOffset !== undefined) {
        lyricOffset = newOffset;
    }
    const display = document.getElementById('offset-display');
    const sign = lyricOffset >= 0 ? '+' : '';
    display.textContent = `Offset: ${sign}${lyricOffset.toFixed(1)}s`;
}

document.getElementById('offset-minus').addEventListener('click', () => {
    updateOffsetDisplay(lyricOffset - 0.5);
});

document.getElementById('offset-plus').addEventListener('click', () => {
    updateOffsetDisplay(lyricOffset + 0.5);
});

document.getElementById('sync-start-btn').addEventListener('click', () => {
    if (!currentLyrics.length) {
        alert("No lyrics loaded to sync with!");
        return;
    }

    // Find the timestamp of the FIRST lyric line
    const firstLineTime = currentLyrics[0].timestamp; // Assuming sorted lyrics
    const currentTime = videoPlayer.currentTime;

    // Offset = FirstLine - Current
    const newOffset = firstLineTime - currentTime;
    updateOffsetDisplay(newOffset);

    // Feedback
    statusDiv.textContent = `Synced to start! Offset: ${newOffset.toFixed(2)}s`;
});

let lastHighlightedIndex = -1;

function highlightLine(index) {
    if (index === lastHighlightedIndex) return;

    if (lastHighlightedIndex !== -1) {
        const prev = document.getElementById(`line-${lastHighlightedIndex}`);
        if (prev) prev.classList.remove('highlight');
    }

    const current = document.getElementById(`line-${index}`);
    if (current) {
        current.classList.add('highlight');
    }

    lastHighlightedIndex = index;
}

// Synchronization Logic using HTML5 Video Event
videoPlayer.addEventListener('timeupdate', () => {
    const currentTime = videoPlayer.currentTime;
    const effectiveTime = currentTime + lyricOffset; // Apply offset

    if (!currentLyrics.length) return;

    let activeIndex = -1;
    for (let i = 0; i < currentLyrics.length; i++) {
        if (currentLyrics[i].timestamp <= effectiveTime) {
            activeIndex = i;
        } else {
            break;
        }
    }

    if (activeIndex !== -1) {
        highlightLine(activeIndex);
    }
});


// === RECORDING LOGIC ===
let mediaRecorder;
let audioChunks = [];
let isRecording = false;

// Remove/Ignore manual record button listeners if they exist
// We rely on auto-start

function startRecording(stream) {
    if (!stream) {
        console.error("No stream provided to startRecording");
        return;
    }

    try {
        mediaRecorder = new MediaRecorder(stream);
        audioChunks = [];

        mediaRecorder.ondataavailable = event => {
            if (event.data && event.data.size > 0) {
                audioChunks.push(event.data);
                // console.log(`Got audio chunk: ${event.data.size} bytes`);
            }
        };

        mediaRecorder.onerror = (e) => {
            console.error('MediaRecorder Error:', e);
            statusDiv.textContent = `Recording Error: ${e.error.name}`;
            alert("Recording failed! See console.");
        };

        // Check track status
        stream.getAudioTracks().forEach(track => {
            track.onended = () => {
                console.warn("Microphone track ended unexpectedly!");
                statusDiv.textContent += " (Mic disconnected)";
            };
        });

        // Use 1000ms timeslice to ensure data is flushed regularly
        mediaRecorder.start(1000);
        isRecording = true;
        console.log("MediaRecorder started (1s timeslice)");

    } catch (err) {
        console.error("MediaRecorder error:", err);
    }
}

async function stopRecordingAndJudge() {
    if (!mediaRecorder) return;

    mediaRecorder.stop();
    isRecording = false;
    isRecording = false;
    // recordBtn lines removed since button is deleted
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
        // IMPORTANT: Adjust timestamps by the user's offset!
        // User sees lyric at T_vid = Timestamp - Offset.
        // User sings at T_vid.
        // Evaluator expects lyric at T_vid.
        // So NewTimestamp = Timestamp - Offset.
        const adjustedLyrics = currentLyrics.map(line => ({
            ...line,
            timestamp: line.timestamp - lyricOffset
        }));
        formData.append("reference_lyrics", JSON.stringify(adjustedLyrics));
    }

    // Send reference audio path if available
    if (currentSongPath) {
        formData.append("reference_audio_path", currentSongPath);
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
        <p style="font-size: 0.8em; color: gray;">Debug: Recorded ${scores.audio_duration ? scores.audio_duration.toFixed(1) : '?'}s</p>
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

// === CHAT LOGIC ===
const chatInput = document.getElementById('chat-input');
const sendChatBtn = document.getElementById('send-chat-btn');
const chatHistory = document.getElementById('chat-history');

function appendMessage(sender, text) {
    const div = document.createElement('div');
    div.className = `message ${sender.toLowerCase()}`;
    div.innerHTML = `<strong>${sender}:</strong> ${text}`;
    div.style.marginBottom = "5px";
    chatHistory.appendChild(div);
    chatHistory.scrollTop = chatHistory.scrollHeight;
}

async function sendChat() {
    const message = chatInput.value.trim();
    if (!message) return;

    appendMessage("You", message);
    chatInput.value = "";

    try {
        const response = await fetch('/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: message })
        });

        if (!response.ok) throw new Error("Chat failed");

        const data = await response.json();
        appendMessage("Host", data.response);

        if (data.action && data.action.type === 'play_audio') {
            handlePlayAction(data.action.payload);
        }

    } catch (error) {
        console.error(error);
        appendMessage("System", "Error: " + error.message);
    }
}

sendChatBtn.addEventListener('click', sendChat);
chatInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') sendChat();
});

async function handlePlayAction(data) {
    console.log("Handling Play Action:", data);

    // 1. Get Mic Permission if needed
    if (!audioStream) {
        try {
            audioStream = await navigator.mediaDevices.getUserMedia({
                audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true }
            });
        } catch (err) {
            alert("Microphone access is required! Please allow it.");
            return;
        }
    }

    // 2. Reset UI
    statusDiv.textContent = `Playing: ${data.track} (Recording Started 🔴)`;
    lyricsDiv.innerHTML = '<p class="placeholder">Loading lyrics...</p>';

    videoPlayer.pause();
    videoPlayer.style.display = 'none';
    videoPlayer.src = "";
    document.querySelector('.sync-controls').style.display = 'none';

    // Clear previous results
    document.getElementById('judge-section').style.display = 'none';
    document.getElementById('judge-feedback').textContent = "";
    document.getElementById('score-display').textContent = "";

    // 3. Setup Video
    if (data.url) {
        videoPlayer.src = data.url;
        videoPlayer.style.display = 'block';
        document.querySelector('.sync-controls').style.display = 'flex';

        // Show Stop Button
        const stopBtn = document.getElementById('stop-evaluate-btn');
        if (stopBtn) stopBtn.style.display = 'inline-block';

        videoPlayer.play().catch(e => console.log("Auto-play prevented:", e));
        updateOffsetDisplay(0.0);
    }

    // 4. Fetch Lyrics (The Host might have done this, but for now we fetch again or need it in payload)
    // The play_song tool in agentic_host returns {url, track, file_path}. It does NOT return lyrics.
    // The Host should ideally call lyrics tool too and pass it.
    // BUT, for now, let's just fetch lyrics here using the track name, OR rely on the Host to have called it?
    // The Agentic Host logic in process_user_input_with_actions only captures 'play_song' action.
    // It doesn't capture 'search_lyrics'.
    // So we need to fetch lyrics here.

    // Store file path for evaluation
    if (data.file_path) {
        currentSongPath = data.file_path;
    }

    fetchLyrics(data.track);
}

// Wire up the new Stop & Evaluate button
document.getElementById('stop-evaluate-btn')?.addEventListener('click', async () => {
    // Hide button
    document.getElementById('stop-evaluate-btn').style.display = 'none';

    // Stop Video
    videoPlayer.pause();

    // Stop Recording & Submit
    if (isRecording) {
        stopRecordingAndJudge();
    } else {
        statusDiv.textContent = "Stopped (No recording was active).";
    }

    // Also call API stop
    try {
        await fetch('/api/stop_song', { method: 'POST' });
    } catch (error) {
        console.error(error);
    }
});

async function fetchLyrics(query) {
    try {
        // We can use the lyrics agent directly via the Host proxy? 
        // Or just use the old endpoint if it still exists?
        // The old endpoint was /api/play_song which did both.
        // We probably need a new endpoint /api/lyrics or similar.
        // OR, we can just ask the Agentic Host "Give me lyrics for X"?
        // No, that's chat.

        // Let's assume we can hit the lyrics agent directly or via a proxy.
        // Since we are moving to MCP, the frontend shouldn't hit agents directly.
        // But we haven't built a proxy yet.
        // However, the lyrics_server is running on port 8002.
        // We can try to hit localhost:8002/search_lyrics if CORS allows.
        // OR, we can add a /api/lyrics endpoint to agentic_host.py.

        // Let's add /api/lyrics to agentic_host.py in the next step.
        // For now, I'll write the fetch call assuming /api/lyrics exists.

        const response = await fetch(`/api/lyrics?query=${encodeURIComponent(query)}`);
        const data = await response.json();

        if (data.lyrics) {
            currentLyrics = data.lyrics;
            renderLyrics(currentLyrics);
        } else {
            lyricsDiv.innerHTML = '<p class="placeholder">No lyrics found.</p>';
        }

    } catch (e) {
        console.error("Lyrics fetch failed:", e);
        lyricsDiv.innerHTML = '<p class="placeholder">Lyrics failed to load.</p>';
    }
}
