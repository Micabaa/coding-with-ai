import React, { useState, useRef, useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import axios from 'axios';
import { Search, Play, Square, Mic, Volume2, Eye, EyeOff, Minus, Plus } from 'lucide-react';
import './SingingPage.css';
import LoadingOverlay from '../components/LoadingOverlay';

const SingingPage = ({ mode = 'casual' }) => {
    // States: 'search', 'playing', 'evaluation', 'battle_setup', 'battle_intermission', 'battle_reveal'
    const [viewState, setViewState] = useState(mode === 'competition' ? 'battle_setup' : 'search');
    const location = useLocation();

    // Battle Mode Data
    const [battlePlayers, setBattlePlayers] = useState({ p1: '', p2: '' });
    const [battleScores, setBattleScores] = useState({ p1: null, p2: null });
    const [currentTurn, setCurrentTurn] = useState('p1'); // 'p1' or 'p2'

    // Data
    const [query, setQuery] = useState('');
    const [songData, setSongData] = useState(null);
    const [lyrics, setLyrics] = useState([]);
    const [isLoadingSong, setIsLoadingSong] = useState(false);

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

    // Judge Selection
    const [judgePersonality, setJudgePersonality] = useState(mode === 'competition' ? 'strict_judge' : 'kind_grandma');
    const [availablePersonalities, setAvailablePersonalities] = useState(['strict_judge', 'kind_grandma']);

    // Create Persona State
    const [showCreatePersona, setShowCreatePersona] = useState(false);
    const [newPersonaName, setNewPersonaName] = useState('');
    const [newPersonaDesc, setNewPersonaDesc] = useState('');
    const [isCreatingPersona, setIsCreatingPersona] = useState(false);
    const [createPersonaStatus, setCreatePersonaStatus] = useState('');

    // Load Personalities
    useEffect(() => {
        const fetchPersonalities = async () => {
            try {
                const res = await axios.get('/api/personalities');
                if (res.data.personalities) {
                    setAvailablePersonalities(res.data.personalities);
                }
            } catch (err) {
                console.error("Failed to load personalities", err);
            }
        };
        fetchPersonalities();
    }, []);

    const fetchAndPlaySong = async (searchQuery) => {
        try {
            // Reset
            setSongData(null);
            setLyrics([]);
            setVideoUrl('');

            // Call Host Agent
            setIsLoadingSong(true);
            const res = await axios.post('/api/play_song', { query: searchQuery });
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
        } finally {
            setIsLoadingSong(false);
        }
    };

    // Auto-Play Effect
    useEffect(() => {
        if (location.state?.autoPlaySong) {
            const songToPlay = location.state.autoPlaySong;
            setQuery(songToPlay);
            // Clear state so it doesn't loop if we go back (though react router state usually persists)
            // Ideally we'd replace history but for now just running it is fine.
            fetchAndPlaySong(songToPlay);
            // Clear the state from history to prevent replay on refresh? requires navigate replace.
            window.history.replaceState({}, document.title);
        }
    }, [location.state]); // Depend on location.state

    const handleCreatePersona = async () => {
        if (!newPersonaName || !newPersonaDesc) {
            setCreatePersonaStatus("Error: Please fill in both fields.");
            return;
        }

        const name = newPersonaName.trim().toLowerCase().replace(/\s+/g, '_');
        setIsCreatingPersona(true);
        setCreatePersonaStatus("Generating prompt... (this takes ~5s)");

        try {
            const res = await axios.post('/api/create_persona', {
                name: name,
                description: newPersonaDesc
            });

            if (res.data.status === 'success') {
                setCreatePersonaStatus("Success! Created " + name);
                // Refresh list
                const listRes = await axios.get('/api/personalities');
                if (listRes.data.personalities) {
                    setAvailablePersonalities(listRes.data.personalities);
                }
                setJudgePersonality(name);
                setNewPersonaName('');
                setNewPersonaDesc('');
                setTimeout(() => {
                    setShowCreatePersona(false);
                    setCreatePersonaStatus('');
                }, 2000);
            } else {
                setCreatePersonaStatus("Error: " + (res.data.error || "Unknown"));
            }
        } catch (err) {
            setCreatePersonaStatus("Network Error");
        } finally {
            setIsCreatingPersona(false);
        }
    };

    // Handle Start Battle
    const handleStartBattle = (e) => {
        e.preventDefault();
        if (battlePlayers.p1 && battlePlayers.p2) {
            setViewState('search');
        } else {
            alert("Please enter both player names!");
        }
    };

    // Search Handler
    const handleSearch = async (e) => {
        e.preventDefault();
        if (!query.trim()) return;
        await fetchAndPlaySong(query);
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

            mediaRecorderRef.current.start(1000); // Collect chunks every second
        } catch (err) {
            console.error("Mic access denied", err);
            alert("Microphone access is required for scoring!");
        }
    };

    const stopRecording = () => {
        return new Promise((resolve) => {
            if (!mediaRecorderRef.current || mediaRecorderRef.current.state === 'inactive') {
                resolve();
                return;
            }

            mediaRecorderRef.current.onstop = () => {
                console.log("Recorder stopped, chunks:", audioChunksRef.current.length);
                resolve();
            };

            mediaRecorderRef.current.stop();
        });
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
        if (videoRef.current) videoRef.current.pause();

        // Wait for recording to actually stop and flush data
        await stopRecording();

        setIsSubmitting(true);

        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/wav' });
        console.log("Final Blob Size:", audioBlob.size);

        const formData = new FormData();
        formData.append('audio_file', audioBlob, 'performance.wav');
        formData.append('personality', judgePersonality);
        formData.append('reference_lyrics', JSON.stringify(lyrics)); // Pass lyrics for better sync check
        formData.append('offset', offset.toString()); // Pass sync offset
        if (songData && songData.file_path) {
            formData.append('reference_audio_path', songData.file_path);
        }

        try {
            const res = await axios.post('/api/submit_performance', formData, {
                headers: { 'Content-Type': 'multipart/form-data' }
            });

            // Calculate Score
            const rawScore = res.data.evaluation.overall_score || 0;
            const score = Math.floor(rawScore * 10000);

            // BATTLE MODE LOGIC
            if (mode === 'competition') {
                if (currentTurn === 'p1') {
                    setBattleScores(prev => ({ ...prev, p1: { score, evaluation: res.data.evaluation, feedback: res.data.feedback } }));
                    setViewState('battle_intermission');
                } else {
                    setBattleScores(prev => ({ ...prev, p2: { score, evaluation: res.data.evaluation, feedback: res.data.feedback } }));
                    setViewState('battle_reveal');
                }
            } else {
                // CASUAL MODE (Existing Logic)
                setEvaluation(res.data.evaluation);
                setFeedback(res.data.feedback);
                setViewState('evaluation');
            }

            // Save Score to Leaderboard (Always separate entries for history)
            // Use battle names if in battle mode
            const userName = mode === 'competition'
                ? (currentTurn === 'p1' ? battlePlayers.p1 : battlePlayers.p2)
                : (localStorage.getItem('karaoke_user_name') || 'Anonymous');

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
    };

    const handleVideoEnded = () => {
        finishSong();
    }

    // Start Player 2 Turn
    const startP2Turn = () => {
        setCurrentTurn('p2');
        setOffset(0); // Reset offset? Maybe keep it if P1 tuned it? Let's reset for fairness or allow tuning again.
        // Restart video
        if (videoRef.current) {
            videoRef.current.currentTime = 0;
            videoRef.current.play();
            setIsPlaying(true);
        }
        setViewState('playing');
    };

    if (viewState === 'battle_intermission') {
        return (
            <div className="intermission-container">
                <h1 className="text-glow-cyan">{battlePlayers.p1} FINISHED!</h1>
                <p>Score Hidden 🤫</p>
                <div className="vs-badge large">VS</div>
                <h2 className="text-glow-magenta">Ready {battlePlayers.p2}?</h2>
                <p>Sing "{songData?.title}" to win!</p>
                <button className="battle-start-btn" onClick={startP2Turn}>
                    START ROUND 2 🎤
                </button>
            </div>
        );
    }

    if (viewState === 'battle_reveal') {
        const p1Score = battleScores.p1?.score || 0;
        const p2Score = battleScores.p2?.score || 0;
        const winner = p1Score > p2Score ? battlePlayers.p1 : battlePlayers.p2;
        const isDraw = p1Score === p2Score;

        return (
            <div className="reveal-container">
                <h1 className="title-huge text-glow-gold">🏆 WINNER 🏆</h1>

                <div className="winner-display">
                    <div className={`winner-avatar ${p1Score > p2Score ? 'p1-win' : 'p2-win'}`}>
                        {isDraw ? "IT'S A DRAW!" : winner}
                    </div>
                </div>

                <div className="score-comparison box-glow">
                    <div className="p-score">
                        <h3>{battlePlayers.p1}</h3>
                        <span className="score-val">{p1Score.toLocaleString()}</span>
                        <div className="stats-breakdown">
                            <div className="stat-row"><span>🎤 Pitch:</span> {Math.floor((battleScores.p1?.evaluation?.pitch_accuracy_score || 0) * 100)}%</div>
                            <div className="stat-row"><span>🥁 Rhythm:</span> {Math.floor((battleScores.p1?.evaluation?.rhythm_score || 0) * 100)}%</div>
                            <div className="stat-row"><span>📜 Lyrics:</span> {Math.floor((battleScores.p1?.evaluation?.lyrics_score || 0) * 100)}%</div>
                        </div>
                    </div>
                    <div className="vs-divider">VS</div>
                    <div className="p-score">
                        <h3>{battlePlayers.p2}</h3>
                        <span className="score-val">{p2Score.toLocaleString()}</span>
                        <div className="stats-breakdown">
                            <div className="stat-row"><span>🎤 Pitch:</span> {Math.floor((battleScores.p2?.evaluation?.pitch_accuracy_score || 0) * 100)}%</div>
                            <div className="stat-row"><span>🥁 Rhythm:</span> {Math.floor((battleScores.p2?.evaluation?.rhythm_score || 0) * 100)}%</div>
                            <div className="stat-row"><span>📜 Lyrics:</span> {Math.floor((battleScores.p2?.evaluation?.lyrics_score || 0) * 100)}%</div>
                        </div>
                    </div>
                </div>

                <button className="retry-btn" onClick={() => window.location.reload()}>
                    NEW BATTLE
                </button>
            </div>
        );
    }
    if (viewState === 'battle_setup') {
        return (
            <div className="battle-setup-container">
                <h1 className="text-glow-magenta title-huge">🎤 1v1 BATTLE 🥊</h1>
                <div className="battle-form box-glow">
                    <div className="player-input">
                        <label>Player 1 (Challenger)</label>
                        <input
                            type="text"
                            placeholder="Enter Name..."
                            value={battlePlayers.p1}
                            onChange={e => setBattlePlayers({ ...battlePlayers, p1: e.target.value })}
                        />
                    </div>
                    <div className="vs-badge">VS</div>
                    <div className="player-input">
                        <label>Player 2 (Defender)</label>
                        <input
                            type="text"
                            placeholder="Enter Name..."
                            value={battlePlayers.p2}
                            onChange={e => setBattlePlayers({ ...battlePlayers, p2: e.target.value })}
                        />
                    </div>
                    <button className="battle-start-btn" onClick={handleStartBattle}>
                        PICK SONG & FIGHT!
                    </button>
                </div>
            </div>
        );
    }

    if (viewState === 'search') {
        return (
            <div className="search-container">
                {isLoadingSong && <LoadingOverlay message="Fetching Song & Lyrics..." />}
                <h1 className="text-glow-magenta title-huge">Ready to Sing?</h1>
                <form onSubmit={handleSearch} className="search-box box-glow">
                    <Search className="search-icon" />
                    <input
                        type="text"
                        placeholder={isLoadingSong ? "Fetching song..." : "Enter song title..."}
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                        disabled={isLoadingSong}
                    />
                    <button type="submit">GO</button>
                </form>

                <div className="judge-toggle-container">
                    <span className="judge-label">Judge:</span>
                    {mode === 'competition' ? (
                        <div className="judge-locked-banner">
                            🔒 <strong>COMPETITION MODE</strong>: Strict Judge Enforced
                        </div>
                    ) : (
                        <div className="judge-selection-wrapper">
                            <div className="judge-toggle">
                                {availablePersonalities.map(p => (
                                    <button
                                        key={p}
                                        className={`judge-btn ${judgePersonality === p ? 'active' : ''}`}
                                        onClick={() => setJudgePersonality(p)}
                                        title={p.replace(/_/g, ' ')}
                                    >
                                        {p === 'strict_judge' ? '👨‍⚖️ Strict' :
                                            p === 'kind_grandma' ? '👵 Grandma' :
                                                p.charAt(0).toUpperCase() + p.slice(1).replace(/_/g, ' ')}
                                    </button>
                                ))}
                            </div>

                            {/* Create New Persona UI */}
                            <div className="create-persona-section" style={{ marginTop: '15px', borderTop: '1px solid #444', paddingTop: '10px' }}>
                                <button
                                    className="text-link"
                                    onClick={() => setShowCreatePersona(!showCreatePersona)}
                                    style={{ background: 'none', border: 'none', color: '#a29bfe', cursor: 'pointer', textDecoration: 'underline' }}
                                >
                                    {showCreatePersona ? '- Cancel' : '+ Create New Personality'}
                                </button>

                                {showCreatePersona && (
                                    <div className="create-persona-form box-glow" style={{ marginTop: '10px', padding: '10px', background: '#2d3436' }}>
                                        <input
                                            type="text"
                                            placeholder="Name (e.g. gangster)"
                                            value={newPersonaName}
                                            onChange={e => setNewPersonaName(e.target.value)}
                                            style={{ width: '100%', marginBottom: '5px', padding: '5px', borderRadius: '4px', border: 'none' }}
                                        />
                                        <textarea
                                            placeholder="Description (e.g. Talks like a 1920s mobster...)"
                                            value={newPersonaDesc}
                                            onChange={e => setNewPersonaDesc(e.target.value)}
                                            style={{ width: '100%', marginBottom: '5px', padding: '5px', borderRadius: '4px', border: 'none' }}
                                            rows={2}
                                        />
                                        <button
                                            onClick={handleCreatePersona}
                                            disabled={isCreatingPersona}
                                            style={{ width: '100%', padding: '5px', background: '#6c5ce7', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}
                                        >
                                            {isCreatingPersona ? 'Generating...' : 'Generate AI Persona'}
                                        </button>
                                        {createPersonaStatus && (
                                            <p style={{ fontSize: '0.8em', color: createPersonaStatus.includes('Error') ? '#ff7675' : '#55efc4', marginTop: '5px' }}>
                                                {createPersonaStatus}
                                            </p>
                                        )}
                                    </div>
                                )}
                            </div>
                        </div>
                    )}
                </div>
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
                        {/* Debug Log */}
                        {console.log("Evaluation Data:", evaluation)}

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
                        {evaluation.transcribed_text && (
                            <div className="transcribed-text" style={{ marginTop: '1rem', borderTop: '1px solid #333', paddingTop: '1rem' }}>
                                <p style={{ color: '#888', fontSize: '0.9rem' }}>What we heard:</p>
                                <p style={{ fontStyle: 'italic', color: '#ccc' }}>"{evaluation.transcribed_text}"</p>
                            </div>
                        )}

                        <div className="lyrics-legend">
                            <div className="legend-item">
                                <span className="diff-word diff-matched">Correct</span>
                            </div>
                            <div className="legend-item">
                                <span className="diff-word diff-wrong">Mispronounced</span>
                            </div>
                            <div className="legend-item">
                                <span className="diff-word diff-missing">Missed</span>
                            </div>
                            <div className="legend-item">
                                <span className="diff-word diff-extra">Extra</span>
                            </div>
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
            {isLoadingSong && <LoadingOverlay message="Fetching Song & Lyrics..." />}
            {isSubmitting && <LoadingOverlay message="Analyzing Performance..." />}

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
