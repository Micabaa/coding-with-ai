import React, { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import { Search, Play, Square, Mic, Volume2, Eye, EyeOff, Minus, Plus } from 'lucide-react';
import './SingingPage.css';

const SingingPage = ({ mode = 'casual' }) => {
    // States: 'search', 'playing', 'evaluation'
    const [viewState, setViewState] = useState('search');

    // Data
    const [query, setQuery] = useState('');
    const [songData, setSongData] = useState(null);
    const [lyrics, setLyrics] = useState([]);

    // Playback State
    const [isPlaying, setIsPlaying] = useState(false);
    const [currentTime, setCurrentTime] = useState(0);
    const [videoUrl, setVideoUrl] = useState('');

    // Sync/Offset
    const [videoVisible, setVideoVisible] = useState(true);
    const [offset, setOffset] = useState(0); // in seconds

    // Refs
    const videoRef = useRef(null);
    const lyricsContainerRef = useRef(null);

    // Evaluation Data
    const [evaluation, setEvaluation] = useState(null);
    const [feedback, setFeedback] = useState("");
    const [isSubmitting, setIsSubmitting] = useState(false);

    // Search Handler
    const handleSearch = async (e) => {
        e.preventDefault();
        if (!query.trim()) return;

        try {
            // Reset
            setSongData(null);
            setLyrics([]);
            setVideoUrl('');

            // Call Host Agent
            const res = await axios.post('/api/play_song', { query });
            const { audio, lyrics: lyricsData } = res.data;

            setSongData({
                title: audio.track,
                artist: "Unknown", // Backend doesn't return artist explicitly yet
                file_path: audio.file_path,
                is_sing_king: audio.is_sing_king
            });

            setVideoUrl(audio.url);
            setLyrics(lyricsData.lyrics || []);
            setViewState('playing');

        } catch (err) {
            console.error(err);
            alert("Failed to load song. Please try again.");
        }
    };

    // Video Time Update
    const onTimeUpdate = () => {
        if (videoRef.current) {
            setCurrentTime(videoRef.current.currentTime);
        }
    };

    const getActiveLineIndex = () => {
        // Find the last line where timestamp <= currentTime + offset
        let activeIdx = -1;
        for (let i = 0; i < lyrics.length; i++) {
            const time = lyrics[i].timestamp !== undefined ? lyrics[i].timestamp : lyrics[i].start_time;
            if (time + offset <= currentTime) {
                activeIdx = i;
            } else {
                break;
            }
        }
        // Debug Log
        if (Math.random() < 0.05 || !isPlaying) { // Don't spam too much unless paused
            console.log(`[SyncDebug] Time: ${currentTime.toFixed(2)}, Offset: ${offset}, ActiveIdx: ${activeIdx}`);
        }
        return activeIdx;
    };

    const params = { activeLineIndex: getActiveLineIndex() };

    // Auto-scroll Lyrics
    useEffect(() => {
        if (params.activeLineIndex !== -1 && lyricsContainerRef.current) {
            const activeEl = lyricsContainerRef.current.children[params.activeLineIndex];
            if (activeEl) {
                activeEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }
        }
    }, [params.activeLineIndex]);

    // Stop Handler
    const handleStop = async () => {
        if (videoRef.current) videoRef.current.pause();
        await finishSong();
    };

    // ... (rest of file)

    <div className="offset-control">
        <label>Offset: {offset.toFixed(1)}s</label>
        <div className="offset-btns">
            <button onClick={() => setOffset(o => o - 0.5)}><Minus size={14} /></button>
            <button onClick={() => setOffset(o => o + 0.5)}><Plus size={14} /></button>
        </div>
    </div>

    // Use a mock submission for now since we can't easily record microphone in browser 
    // AND send it to the backend without MediaRecorder setup.
    // Wait, the user wants "Evaluated". To evaluate, we need to RECORD the user.
    // I need to implement MediaRecorder in the browser!
    // The previous task "Fixing Karaoke Recording" implied the frontend records.

    const mediaRecorderRef = useRef(null);
    const audioChunksRef = useRef([]);

    const startRecording = async () => {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            mediaRecorderRef.current = new MediaRecorder(stream);
            audioChunksRef.current = [];

            mediaRecorderRef.current.ondataavailable = (event) => {
                if (event.data.size > 0) audioChunksRef.current.push(event.data);
            };

            mediaRecorderRef.current.start();
        } catch (err) {
            console.error("Mic access denied", err);
            alert("Microphone access is required for scoring!");
        }
    };

    const stopRecording = () => {
        if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
            mediaRecorderRef.current.stop();
        }
    };

    // Play/Pause Handler
    const handlePlayPause = () => {
        if (videoRef.current) {
            if (isPlaying) {
                videoRef.current.pause();
                setIsPlaying(false);
            } else {
                videoRef.current.play();
                setIsPlaying(true);
            }
        }
    };

    // Modified play effect
    useEffect(() => {
        if (viewState === 'playing') {
            startRecording();
            if (videoRef.current) {
                const playPromise = videoRef.current.play();
                if (playPromise !== undefined) {
                    playPromise
                        .then(() => setIsPlaying(true))
                        .catch(e => {
                            console.log("Autoplay blocked", e);
                            setIsPlaying(false);
                        });
                }
            }
        }
        return () => {
            // Cleanup
            if (mediaRecorderRef.current) {
                // mediaRecorderRef.current.stop(); // Don't stop on unmount if we want to process?
            }
        };
    }, [viewState]);

    const finishSong = async () => {
        stopRecording();
        setIsSubmitting(true);
        if (videoRef.current) videoRef.current.pause();

        // Wait for recorder to stop and chunks to gather
        setTimeout(async () => {
            const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/wav' });
            const formData = new FormData();
            formData.append('audio_file', audioBlob, 'performance.wav');
            formData.append('personality', mode === 'competition' ? 'strict_judge' : 'friendly');
            formData.append('reference_lyrics', JSON.stringify(lyrics)); // Pass lyrics for better sync check
            formData.append('offset', offset.toString()); // Pass sync offset

            try {
                const res = await axios.post('/api/submit_performance', formData, {
                    headers: { 'Content-Type': 'multipart/form-data' }
                });

                setEvaluation(res.data.evaluation);
                setFeedback(res.data.feedback);
                setViewState('evaluation');

                // Save Score
                const userName = localStorage.getItem('karaoke_user_name') || 'Anonymous';
                const score = Math.floor((res.data.evaluation.overall_score || 0) * 10000);

                // Only save if score > 0
                if (score > 0) {
                    await axios.post('/api/save_score', {
                        user_name: userName,
                        score: score,
                        mode: mode,
                        song: songData.title
                    });
                }

            } catch (err) {
                console.error(err);
                alert("Evaluation failed.");
                setViewState('search');
            } finally {
                setIsSubmitting(false);
            }
        }, 1000);
    };

    const handleVideoEnded = () => {
        finishSong();
    }

    if (viewState === 'search') {
        return (
            <div className="search-container">
                <h1 className="text-glow-magenta title-huge">Ready to Sing?</h1>
                <form onSubmit={handleSearch} className="search-box box-glow">
                    <Search className="search-icon" />
                    <input
                        type="text"
                        placeholder="Search for a song..."
                        value={query}
                        onChange={e => setQuery(e.target.value)}
                        autoFocus
                    />
                    <button type="submit">GO</button>
                </form>
            </div>
        );
    }

    if (viewState === 'evaluation') {
        const score = evaluation ? Math.floor(evaluation.overall_score * 10000) : 0;
        let grade = 'D';
        if (score > 9000) grade = 'S';
        else if (score > 8000) grade = 'A';
        else if (score > 7000) grade = 'B';
        else if (score > 6000) grade = 'C';

        return (
            <div className="evaluation-container">
                <h1 className="text-glow-gold">Performance Report</h1>

                <div className="score-card box-glow">
                    <div className={`grade-circle grade-${grade}`}>
                        {grade}
                    </div>
                    <div className="score-details">
                        <h2>Total Score: {score}</h2>
                        <div className="metrics">
                            <div className="metric-item">
                                <span className="label">Pitch</span>
                                <div className="progress-bar">
                                    <div className="fill" style={{ width: `${(evaluation.pitch_accuracy_score || 0) * 100}%` }}></div>
                                </div>
                                <span className="value">{Math.round((evaluation.pitch_accuracy_score || 0) * 100)}%</span>
                            </div>
                            <div className="metric-item">
                                <span className="label">Rhythm</span>
                                <div className="progress-bar">
                                    <div className="fill" style={{ width: `${(evaluation.rhythm_score || 0) * 100}%` }}></div>
                                </div>
                                <span className="value">{Math.round((evaluation.rhythm_score || 0) * 100)}%</span>
                            </div>
                            <div className="metric-item">
                                <span className="label">Lyrics</span>
                                <div className="progress-bar">
                                    <div className="fill" style={{ width: `${(evaluation.lyrics_score || 0) * 100}%` }}></div>
                                </div>
                                <span className="value">{Math.round((evaluation.lyrics_score || 0) * 100)}%</span>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Pitch Breakdown */}
                {evaluation.pitch_detail && (
                    <div className="pitch-breakdown box-glow">
                        <h3>Pitch Analysis</h3>
                        <div className="pitch-bars">
                            <div className="pitch-bar-group">
                                <span className="label">Perfect</span>
                                <div className="bar-container">
                                    <div className="bar perfect" style={{ width: `${evaluation.pitch_detail.perfect * 100}%` }}></div>
                                </div>
                                <span className="value">{Math.round(evaluation.pitch_detail.perfect * 100)}%</span>
                            </div>
                            <div className="pitch-bar-group">
                                <span className="label">Close (High/Low)</span>
                                <div className="bar-container">
                                    <div className="bar close" style={{ width: `${(evaluation.pitch_detail.high + evaluation.pitch_detail.low) * 100}%` }}></div>
                                </div>
                                <span className="value">{Math.round((evaluation.pitch_detail.high + evaluation.pitch_detail.low) * 100)}%</span>
                            </div>
                        </div>
                    </div>
                )}

                {/* Lyrics Diff */}
                {evaluation.lyrics_diff && (
                    <div className="lyrics-feedback box-glow">
                        <h3>Lyrics Accuracy</h3>
                        <div className="diff-text">
                            {evaluation.lyrics_diff.map((wordObj, idx) => (
                                <span
                                    key={idx}
                                    className={`diff-word diff-${wordObj.status}`}
                                    title={wordObj.status === 'wrong' ? `Heard: "${wordObj.heard}"` : ''}
                                >
                                    {wordObj.word}{' '}
                                </span>
                            ))}
                        </div>
                    </div>
                )}

                <div className="feedback-box">
                    <h3>Judge's Comments</h3>
                    <p>{feedback}</p>
                </div>

                <button className="retry-btn" onClick={() => setViewState('search')}>
                    Sing Another Song
                </button>
            </div>
        );
    }

    return (
        <div className="singing-interface">
            {isSubmitting && <div className="overlay-loading">Evaluating Performance...</div>}

            <div className="song-header">
                <h2 className="text-glow-cyan">{songData?.title}</h2>
                <div className="controls-top">
                    <button className="control-btn" onClick={handlePlayPause}>
                        {isPlaying ? <span style={{ display: 'flex', gap: 5 }}><Square size={20} /> Pause</span> : <span style={{ display: 'flex', gap: 5 }}><Play size={20} /> Play</span>}
                    </button>
                    <button className="stop-btn" onClick={handleStop}>
                        <Square size={20} fill="currentColor" /> Stop/Finish
                    </button>
                </div>
            </div>

            <div className="main-stage">
                <div className="lyrics-display" ref={lyricsContainerRef}>
                    {lyrics.length === 0 ? (
                        <p className="no-lyrics">Instrumental / No Lyrics Found</p>
                    ) : (
                        lyrics.map((line, idx) => (
                            <p
                                key={idx}
                                className={`lyric-line ${idx === params.activeLineIndex ? 'active text-glow-magenta' : ''}`}
                            >
                                {line.text}
                            </p>
                        ))
                    )}
                </div>

                <div className={`video-sidebar ${!videoVisible ? 'hidden-video' : ''}`}>
                    <div className="video-wrapper box-glow">
                        <video
                            ref={videoRef}
                            src={videoUrl}
                            onTimeUpdate={onTimeUpdate}
                            onEnded={handleVideoEnded}
                            controls={false} // Custom controls
                            className="mini-video"
                        />
                    </div>

                    <div className="sync-controls">
                        <div className="video-toggle">
                            <button
                                className={`toggle-btn ${!videoVisible ? 'synced' : ''}`}
                                onClick={() => setVideoVisible(!videoVisible)}
                            >
                                {videoVisible ? <Eye size={16} /> : <EyeOff size={16} />}
                                {videoVisible ? ' Visibile' : ' Synced (Hidden)'}
                            </button>
                            <span className="tooltip">Hide video when synced!</span>
                        </div>

                        <div className="offset-control">
                            <label>Offset: {offset.toFixed(1)}s</label>
                            <div className="offset-btns">
                                <button onClick={() => setOffset(o => o - 0.5)}><Minus size={14} /></button>
                                <button onClick={() => setOffset(o => o + 0.5)}><Plus size={14} /></button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default SingingPage;
