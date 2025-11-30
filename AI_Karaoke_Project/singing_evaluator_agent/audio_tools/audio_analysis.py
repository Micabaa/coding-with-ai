import librosa
import numpy as np
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def calculate_timing_score(y, sr, reference_lyrics):
    """
    Calculates timing score by comparing voice activity with reference lyrics timestamps.
    
    Args:
        y: Audio time series.
        sr: Sampling rate.
        reference_lyrics: List of dicts with 'start_time', 'end_time' (in seconds).
        
    Returns:
        float: Timing score between 0.0 and 1.0.
    """
    if not reference_lyrics:
        return 0.0

    # 1. Detect Voice Activity (VAD)
    # Split audio into non-silent intervals (where singing happens)
    # top_db=20 means anything 20dB below max is considered silence
    intervals = librosa.effects.split(y, top_db=20)
    
    # Convert samples to seconds
    singing_intervals = librosa.samples_to_time(intervals, sr=sr)
    
    # 2. Calculate Overlap
    total_overlap_duration = 0.0
    total_lyric_duration = 0.0
    
    for lyric in reference_lyrics:
        lyric_start = float(lyric.get('start_time', 0))
        lyric_end = float(lyric.get('end_time', 0))
        duration = lyric_end - lyric_start
        
        if duration <= 0:
            continue
            
        total_lyric_duration += duration
        
        # Check overlap with any singing interval
        for sing_start, sing_end in singing_intervals:
            # Intersection of [lyric_start, lyric_end] and [sing_start, sing_end]
            overlap_start = max(lyric_start, sing_start)
            overlap_end = min(lyric_end, sing_end)
            
            if overlap_end > overlap_start:
                total_overlap_duration += (overlap_end - overlap_start)
    
    # 3. Score Calculation
    # Simple metric: What % of the lyric duration was covered by singing?
    # We could also penalize singing during silence, but let's start simple.
    if total_lyric_duration > 0:
        score = min(1.0, total_overlap_duration / total_lyric_duration)
    else:
        score = 0.0
        
    logger.info(f"Timing Analysis: Overlap={total_overlap_duration:.2f}s / Lyrics={total_lyric_duration:.2f}s -> Score={score:.2f}")
    return score

def analyze_audio(audio_path, reference_lyrics=None):
    """
    Analyzes an audio file to extract pitch, rhythm, and other metrics.
    
    Args:
        audio_path (str): Path to the audio file.
        reference_lyrics (list, optional): List of timestamped lyrics.
        
    Returns:
        dict: A dictionary containing evaluation metrics matching the schema.
    """
    try:
        # Load audio file
        # sr=None preserves the native sampling rate
        y, sr = librosa.load(audio_path, sr=None)
        
        # 1. Pitch Analysis (Fundamental Frequency - F0)
        # f0 is the fundamental frequency over time
        f0, voiced_flag, voiced_probs = librosa.pyin(
            y, 
            fmin=librosa.note_to_hz('C2'), 
            fmax=librosa.note_to_hz('C7')
        )
        
        # Filter out NaNs (unvoiced segments)
        valid_f0 = f0[~np.isnan(f0)]
        
        if len(valid_f0) > 0:
            avg_pitch = float(np.mean(valid_f0))
            pitch_variance = float(np.var(valid_f0))
            # Normalize pitch accuracy score (simplified logic)
            # Lower variance might indicate better control, but this is a heuristic
            # We'll map variance to a 0-1 score roughly
            pitch_accuracy_score = max(0.0, min(1.0, 1.0 - (pitch_variance / 10000.0)))
        else:
            avg_pitch = 0.0
            pitch_accuracy_score = 0.0

        # 2. Rhythm/Timing Analysis
        if reference_lyrics:
            # Use lyrics-based timing if available
            rhythm_score = calculate_timing_score(y, sr, reference_lyrics)
        else:
            # Fallback to tempo-based heuristic
            tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
            rhythm_score = 0.8 if tempo > 0 else 0.0
        
        # 3. Energy/Volume Analysis (RMS)
        rms = librosa.feature.rms(y=y)
        avg_rms = float(np.mean(rms))
        
        vocal_power = "low"
        if avg_rms > 0.1:
            vocal_power = "high"
        elif avg_rms > 0.05:
            vocal_power = "medium"

        # 4. Construct Result Dictionary
        result = {
            "overall_score": (pitch_accuracy_score + rhythm_score) / 2,
            "pitch_accuracy_score": pitch_accuracy_score,
            "rhythm_score": rhythm_score,
            "vocal_power": vocal_power,
            "emotion_detected": "neutral", # Placeholder for more advanced analysis
            "error_summary": {
                "pitch_errors_count": 0, # Placeholder
                "rhythm_errors_count": 0 # Placeholder
            },
            "average_scores": {
                "overall": (pitch_accuracy_score + rhythm_score) / 2,
                "pitch_accuracy": pitch_accuracy_score,
                "rhythm": rhythm_score
            }
        }
        
        logger.info(f"Audio analysis complete: {result}")
        return result

    except Exception as e:
        logger.error(f"Error analyzing audio: {e}")
        # Return a safe default in case of error
        return {
            "overall_score": 0.0,
            "pitch_accuracy_score": 0.0,
            "rhythm_score": 0.0,
            "vocal_power": "unknown",
            "emotion_detected": "neutral",
            "error_summary": {"pitch_errors_count": 0, "rhythm_errors_count": 0}
        }
