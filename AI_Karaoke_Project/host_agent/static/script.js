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

        statusDiv.textContent = data.audio_status;

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

// --- Recording Logic ---
let mediaRecorder;
let audioChunks = [];

const recordBtn = document.getElementById('record-btn');
const stopRecordBtn = document.getElementById('stop-record-btn');
const feedbackDiv = document.getElementById('feedback-content');
const statusDiv = document.getElementById('status-message');

recordBtn.addEventListener('click', async () => {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        mediaRecorder = new MediaRecorder(stream);
        audioChunks = [];

        mediaRecorder.ondataavailable = (event) => {
            audioChunks.push(event.data);
        };

        mediaRecorder.onstop = async () => {
            const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
            const reader = new FileReader();
            reader.readAsDataURL(audioBlob);
            reader.onloadend = async () => {
                const base64Audio = reader.result.split(',')[1]; // Remove "data:audio/wav;base64,"

                statusDiv.textContent = "Analyzing performance...";
                feedbackDiv.innerHTML = '<p class="placeholder">Judge is thinking...</p>';

                try {
                    const response = await fetch('/api/submit_recording', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            audio_data: base64Audio,
                            song_id: "user_recording"
                        })
                    });

                    const result = await response.json();

                    if (result.status === 'success') {
                        statusDiv.textContent = "Feedback received!";

                        // Format Feedback
                        let html = `<h4>Scores</h4>`;
                        if (result.scores && !result.scores.error) {
                            html += `<ul>`;
                            for (const [key, value] of Object.entries(result.scores)) {
                                if (key !== 'performance_segment_id') {
                                    html += `<li><strong>${key}:</strong> ${value}</li>`;
                                }
                            }
                            html += `</ul>`;
                        }

                        html += `<h4>Judge's Verdict</h4>`;
                        html += `<p>${result.feedback}</p>`;

                        feedbackDiv.innerHTML = html;
                    } else {
                        feedbackDiv.innerHTML = `<p style="color:red">Error: ${JSON.stringify(result)}</p>`;
                    }

                } catch (e) {
                    console.error(e);
                    statusDiv.textContent = "Error submitting recording.";
                    feedbackDiv.innerHTML = `<p style="color:red">${e.message}</p>`;
                }
            };
        };

        mediaRecorder.start();
        recordBtn.disabled = true;
        stopRecordBtn.disabled = false;
        statusDiv.textContent = "Recording...";
        feedbackDiv.innerHTML = '<p class="placeholder">Recording...</p>';

    } catch (err) {
        console.error("Error accessing microphone:", err);
        alert("Could not access microphone. Please allow permissions.");
    }
});

stopRecordBtn.addEventListener('click', () => {
    if (mediaRecorder && mediaRecorder.state !== 'inactive') {
        mediaRecorder.stop();
        recordBtn.disabled = false;
        stopRecordBtn.disabled = true;
        statusDiv.textContent = "Processing...";
    }
});
