import librosa
import numpy as np
import os
import logging
from rapidfuzz import fuzz
from openai import OpenAI
from dotenv import load_dotenv
from fastdtw import fastdtw
from scipy.spatial.distance import euclidean

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()
client = OpenAI()

def transcribe_audio(audio_path, prompt=""):
    """
    Transcribes audio using OpenAI Whisper.
    """
    try:
        with open(audio_path, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model="whisper-1", 
                file=audio_file,
                language="en",
                prompt=prompt[:500] # Provide context (lyrics) to guide Whisper, limit length
            )
        return transcript.text
    except Exception as e:
        logger.error(f"Whisper STT failed: {e}")
        return ""

def calculate_lyrics_accuracy(transcribed_text, reference_lyrics_data):
    """
    Compares transcribed text with reference lyrics using fuzzy matching.
    """
    if not transcribed_text or not reference_lyrics_data:
        return 0.0
    
    # Extract text from reference lyrics objects
    ref_text = " ".join([l.get('text', '') for l in reference_lyrics_data])
    
    # Calculate similarity ratio (0-100)
    ratio = fuzz.ratio(transcribed_text.lower(), ref_text.lower())
    return ratio / 100.0

def calculate_timing_score(y, sr, reference_lyrics):
    """
    Calculates timing score by comparing voice activity with reference lyrics timestamps.
    """
    if not reference_lyrics:
        return 0.0

    # 1. Detect Voice Activity (VAD)
    # Lower top_db to catch quieter singing
    intervals = librosa.effects.split(y, top_db=15)
    singing_intervals = librosa.samples_to_time(intervals, sr=sr)
    
    # 2. Calculate Overlap
    total_overlap_duration = 0.0
    total_lyric_duration = 0.0
    
    # Sort lyrics by timestamp just in case
    # Handle 'timestamp' vs 'start_time' mismatch
    sorted_lyrics = sorted(reference_lyrics, key=lambda x: x.get('timestamp', x.get('start_time', 0)))
    
    for i, lyric in enumerate(sorted_lyrics):
        # Support both 'timestamp' (from lyrics_server) and 'start_time'
        start = float(lyric.get('timestamp', lyric.get('start_time', 0)))
        
        # Infer end time from next line or default duration
        if i < len(sorted_lyrics) - 1:
            next_start = float(sorted_lyrics[i+1].get('timestamp', sorted_lyrics[i+1].get('start_time', 0)))
            end = next_start
        else:
            end = start + 5.0 # Default 5s for last line
            
        duration = end - start
        
        if duration <= 0:
            continue
            
        total_lyric_duration += duration
        
        # Check overlap
        for sing_start, sing_end in singing_intervals:
            overlap_start = max(start, sing_start)
            overlap_end = min(end, sing_end)
            
            if overlap_end > overlap_start:
                total_overlap_duration += (overlap_end - overlap_start)
    
    if total_lyric_duration > 0:
        score = min(1.0, total_overlap_duration / total_lyric_duration)
    else:
        score = 0.0
        
    return score

# ... (rest of file) ...

def analyze_audio(audio_path, reference_lyrics=None, reference_audio_path=None):
    """
    Analyzes an audio file to extract pitch, rhythm, and other metrics.
    """
    try:
        y, sr = librosa.load(audio_path, sr=None)
        
        # 1. Pitch Analysis using YIN (Faster)
        f0 = librosa.yin(y, fmin=librosa.note_to_hz('C2'), fmax=librosa.note_to_hz('C7'))
        valid_f0 = f0[~np.isnan(f0)]
        
        # Pitch Compatibility (DTW)
        dtw_score = calculate_dtw_score(y, sr, reference_audio_path)
        
        # Detailed Pitch Breakdown
        pitch_detail = analyze_pitch_detail(y, sr, reference_audio_path)
        
        # Combined Pitch Score
        # REMOVED pitch_stability as it penalizes dynamic singing.
        # DTW is the best metric for accuracy.
        pitch_accuracy_score = dtw_score

        # 2. Rhythm/Timing Analysis
        if reference_lyrics:
            rhythm_score = calculate_timing_score(y, sr, reference_lyrics)
        else:
            tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
            rhythm_score = 0.8 if tempo > 0 else 0.0
        
        # 3. Lyrics Accuracy (STT)
        # Prepare prompt from RELEVANT lyrics
        prompt_text = ""
        if relevant_lyrics:
             prompt_text = " ".join([l.get('text', '') for l in relevant_lyrics])
             
        transcribed_text = transcribe_audio(audio_path, prompt=prompt_text)
        lyrics_score = calculate_lyrics_accuracy(transcribed_text, relevant_lyrics)
        
        # Detailed Lyrics Diff
        lyrics_diff = analyze_lyrics_diff(transcribed_text, relevant_lyrics)
        
        logger.info(f"Transcribed: '{transcribed_text}' -> Score: {lyrics_score}")

        # 4. Energy/Volume
        rms = librosa.feature.rms(y=y)
        avg_rms = float(np.mean(rms))
        vocal_power = "high" if avg_rms > 0.1 else "medium" if avg_rms > 0.05 else "low"

        # 5. Construct Result
        overall_score = (pitch_accuracy_score + rhythm_score + lyrics_score) / 3
        
        result = {
            "overall_score": overall_score,
            "pitch_accuracy_score": pitch_accuracy_score,
            "rhythm_score": rhythm_score,
            "lyrics_score": lyrics_score,
            "vocal_power": vocal_power,
            "transcribed_text": transcribed_text,
            "pitch_detail": pitch_detail,
            "lyrics_diff": lyrics_diff,
            "emotion_detected": "neutral",
            "average_scores": {
                "overall": overall_score,
                "pitch": pitch_accuracy_score,
                "rhythm": rhythm_score,
                "lyrics": lyrics_score
            }
        }
        
        logger.info(f"Audio analysis complete: {result}")
        return result

    except Exception as e:
        logger.error(f"Error analyzing audio: {e}")
        return {
            "overall_score": 0.0,
            "pitch_accuracy_score": 0.0,
            "rhythm_score": 0.0,
            "lyrics_score": 0.0,
            "vocal_power": "unknown",
            "transcribed_text": "",
            "error": str(e)
        }

def calculate_dtw_score(y_user, sr_user, reference_audio_path):
    """
    Calculates the similarity between user audio and reference audio using Dynamic Time Warping (DTW)
    on Chroma features. This aligns the two sequences in time and measures distance.
    """
    if not reference_audio_path or not os.path.exists(reference_audio_path):
        return 0.5 # Default if no reference

    try:
        # Load reference audio (resample to match user)
        # Load only first 60s to save compute if needed, or full song
        y_ref, _ = librosa.load(reference_audio_path, sr=sr_user, duration=60) 
        
        # Extract Chroma Features (Pitch Class Profile)
        # We use CQT (Constant-Q Transform) for better musical relevance
        chroma_user = librosa.feature.chroma_cqt(y=y_user, sr=sr_user)
        chroma_ref = librosa.feature.chroma_cqt(y=y_ref, sr=sr_user)
        
        # Transpose for fastdtw (needs [n_samples, n_features])
        chroma_user = chroma_user.T
        chroma_ref = chroma_ref.T
        
        # Compute DTW
        # dist is the unnormalized distance (lower is better)
        distance, path = fastdtw(chroma_user, chroma_ref, dist=euclidean)
        
        # Normalize distance
        # A perfect match has distance 0.
        # We need to scale this to a 0-1 score.
        # The distance grows with length, so we normalize by path length.
        avg_dist = distance / len(path)
        
        # Heuristic mapping: 
        # avg_dist 0.0 -> Score 1.0
        # avg_dist > 0.5 -> Score drops rapidly
        # This mapping might need tuning based on testing
        score = np.exp(-avg_dist * 2) 
        
        logger.info(f"DTW Analysis: Distance={distance:.2f}, Avg={avg_dist:.4f} -> Score={score:.4f}")
        return float(score)

    except Exception as e:
        logger.error(f"DTW analysis failed: {e}")
        return 0.0

import difflib

import re

def normalize_text(text):
    """
    Normalizes text for comparison:
    1. Lowercase
    2. Remove punctuation
    3. Standardize common contractions (optional, but 'in' vs 'ing' is handled by fuzzy logic usually, 
       but here we are doing word-diff. Let's just strip non-alphanumeric).
    """
    # Remove punctuation using regex, keep spaces
    text = re.sub(r'[^\w\s]', '', text.lower())
    return text

def analyze_lyrics_diff(transcribed_text, reference_lyrics_data):
    """
    Compares transcribed text with reference lyrics word by word.
    Returns a list of words with status: 'matched', 'missing', 'extra', 'wrong'.
    """
    if not reference_lyrics_data:
        return []
    
    # Extract text from reference lyrics objects
    ref_text = " ".join([l.get('text', '') for l in reference_lyrics_data])
    
    # Normalize for comparison
    ref_norm = normalize_text(ref_text)
    trans_norm = normalize_text(transcribed_text) if transcribed_text else ""
    
    # Tokenize
    ref_words = ref_norm.split()
    trans_words = trans_norm.split()
    
    # We also need the original words for display (with punctuation)
    # This is tricky because indices will shift if we just split by space on original.
    # Let's try to map back or just use the normalized words for display to be safe/cleaner?
    # Or better: split original by space, strip punctuation for comparison only.
    
    ref_display_words = ref_text.split()
    # Ensure lengths match (normalization might remove words? unlikely if just punctuation)
    # If lengths differ, we fallback to normalized for display.
    if len(ref_display_words) != len(ref_words):
        ref_display_words = ref_words

    matcher = difflib.SequenceMatcher(None, ref_words, trans_words)
    diff_result = []
    
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == 'equal':
            for k in range(i1, i2):
                diff_result.append({"word": ref_display_words[k], "status": "matched"})
        elif tag == 'replace':
            # Capture what was heard instead
            heard_chunk = trans_words[j1:j2]
            ref_chunk = ref_display_words[i1:i2]
            
            n_ref = len(ref_chunk)
            n_heard = len(heard_chunk)
            
            if n_ref > n_heard:
                # Case: User sang fewer words than expected (e.g. missed a whole line but sang the last word)
                # Mark the excess as "missing"
                n_missing = n_ref - n_heard
                
                # First n_missing words are missing
                for k in range(n_missing):
                    diff_result.append({"word": ref_chunk[k], "status": "missing"})
                
                # Remaining words are wrong (mismatched) or fuzzy matched
                for k in range(n_missing, n_ref):
                    # Map heard word 1-to-1 if possible
                    heard_idx = k - n_missing
                    heard_word = heard_chunk[heard_idx] if heard_idx < n_heard else ""
                    
                    # FUZZY CHECK: If pronunciation is close enough, count it!
                    if heard_word and fuzz.ratio(ref_chunk[k], heard_word) > 65:
                        diff_result.append({"word": ref_chunk[k], "status": "matched"})
                    else:
                        diff_result.append({"word": ref_chunk[k], "status": "wrong", "heard": heard_word})
            else:
                # Case: User sang same amount or more (total mismatch)
                # Try to fuzzy match 1-to-1
                
                for k, word in enumerate(ref_chunk):
                    heard_word = heard_chunk[k] # Guaranteed to exist since n_heard >= n_ref
                    
                    if fuzz.ratio(word, heard_word) > 65:
                        diff_result.append({"word": word, "status": "matched"})
                    else:
                        item = {"word": word, "status": "wrong", "heard": heard_word}
                        diff_result.append(item)
                
        elif tag == 'delete':
            for k in range(i1, i2):
                diff_result.append({"word": ref_display_words[k], "status": "missing"})
        elif tag == 'insert':
            # Extra words sung by user
            for word in trans_words[j1:j2]:
                diff_result.append({"word": word, "status": "extra"})
                
    return diff_result

def analyze_pitch_detail(y_user, sr_user, reference_audio_path):
    """
     detailed pitch analysis: High / Low / Perfect percentages.
    """
    if not reference_audio_path or not os.path.exists(reference_audio_path):
        return {"high": 0, "low": 0, "perfect": 0}

    try:
        # Load reference (first 60s)
        y_ref, _ = librosa.load(reference_audio_path, sr=sr_user, duration=60)
        
        # Extract F0 (Pitch) using YIN (faster than pYIN)
        f0_user = librosa.yin(y_user, fmin=librosa.note_to_hz('C2'), fmax=librosa.note_to_hz('C7'))
        f0_ref = librosa.yin(y_ref, fmin=librosa.note_to_hz('C2'), fmax=librosa.note_to_hz('C7'))
        
        # Clean NaNs
        f0_user = np.nan_to_num(f0_user)
        f0_ref = np.nan_to_num(f0_ref)
        
        # Align using DTW on F0 directly (simplified for speed) or Chroma
        # Using Chroma for alignment is safer, then map indices
        chroma_user = librosa.feature.chroma_cqt(y=y_user, sr=sr_user).T
        chroma_ref = librosa.feature.chroma_cqt(y=y_ref, sr=sr_user).T
        
        _, path = fastdtw(chroma_user, chroma_ref, dist=euclidean)
        
        high_count = 0
        low_count = 0
        perfect_count = 0
        total_voiced = 0
        
        for idx_user, idx_ref in path:
            p_user = f0_user[idx_user]
            p_ref = f0_ref[idx_ref]
            
            # Only compare if both are voiced (pitch > 0)
            if p_user > 0 and p_ref > 0:
                total_voiced += 1
                # Calculate ratio (cents would be better but ratio is ok)
                # 1 semitone ~= 1.059 ratio
                ratio = p_user / p_ref
                
                if 0.94 < ratio < 1.06: # Within +/- 1 semitone
                    perfect_count += 1
                elif ratio >= 1.06:
                    high_count += 1
                else:
                    low_count += 1
                    
        if total_voiced == 0:
            return {"high": 0, "low": 0, "perfect": 0}
            
        return {
            "high": round(high_count / total_voiced, 2),
            "low": round(low_count / total_voiced, 2),
            "perfect": round(perfect_count / total_voiced, 2)
        }

    except Exception as e:
        logger.error(f"Detailed pitch analysis failed: {e}")
        return {"high": 0, "low": 0, "perfect": 0}

def analyze_audio(audio_path, reference_lyrics=None, reference_audio_path=None):
    """
    Analyzes an audio file to extract pitch, rhythm, and other metrics.
    """
    try:
        y, sr = librosa.load(audio_path, sr=None)
        
        # 1. Pitch Analysis using YIN (Faster)
        f0 = librosa.yin(y, fmin=librosa.note_to_hz('C2'), fmax=librosa.note_to_hz('C7'))
        valid_f0 = f0[~np.isnan(f0)]
        
        if len(valid_f0) > 0:
            pitch_variance = float(np.var(valid_f0))
            pitch_stability = max(0.0, min(1.0, 1.0 - (pitch_variance / 10000.0)))
        else:
            pitch_stability = 0.0

        # Filter lyrics to only those within the audio duration (plus a small buffer)
        # This prevents marking the rest of the song as "missing" if the user stops early.
        audio_duration = librosa.get_duration(y=y, sr=sr)
        relevant_lyrics = []
        if reference_lyrics:
            for line in reference_lyrics:
                start = float(line.get('timestamp', line.get('start_time', 0)))
                if start < audio_duration + 5.0: # 5s buffer to be safe
                    relevant_lyrics.append(line)
        
        # Pitch Compatibility (DTW & Key Matching)
        dtw_score = calculate_dtw_score(y, sr, reference_audio_path)
        
        # Detailed Pitch Breakdown
        pitch_detail = analyze_pitch_detail(y, sr, reference_audio_path)
        
        # Combined Pitch Score
        pitch_accuracy_score = (pitch_stability * 0.2) + (dtw_score * 0.8)

        # 2. Rhythm/Timing Analysis
        if reference_lyrics:
            rhythm_score = calculate_timing_score(y, sr, reference_lyrics)
        else:
            tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
            rhythm_score = 0.8 if tempo > 0 else 0.0
        
        # 3. Lyrics Accuracy (STT)
        transcribed_text = transcribe_audio(audio_path)
        lyrics_score = calculate_lyrics_accuracy(transcribed_text, reference_lyrics)
        
        # Detailed Lyrics Diff
        lyrics_diff = analyze_lyrics_diff(transcribed_text, reference_lyrics)
        
        logger.info(f"Transcribed: '{transcribed_text}' -> Score: {lyrics_score}")

        # 4. Energy/Volume
        rms = librosa.feature.rms(y=y)
        avg_rms = float(np.mean(rms))
        vocal_power = "high" if avg_rms > 0.1 else "medium" if avg_rms > 0.05 else "low"

        # 5. Construct Result
        overall_score = (pitch_accuracy_score + rhythm_score + lyrics_score) / 3
        
        result = {
            "overall_score": overall_score,
            "pitch_accuracy_score": pitch_accuracy_score,
            "rhythm_score": rhythm_score,
            "lyrics_score": lyrics_score,
            "vocal_power": vocal_power,
            "transcribed_text": transcribed_text,
            "pitch_detail": pitch_detail,
            "lyrics_diff": lyrics_diff,
            "emotion_detected": "neutral",
            "average_scores": {
                "overall": overall_score,
                "pitch": pitch_accuracy_score,
                "rhythm": rhythm_score,
                "lyrics": lyrics_score
            }
        }
        
        logger.info(f"Audio analysis complete: {result}")
        return result

    except Exception as e:
        logger.error(f"Error analyzing audio: {e}")
        return {
            "overall_score": 0.0,
            "pitch_accuracy_score": 0.0,
            "rhythm_score": 0.0,
            "lyrics_score": 0.0,
            "vocal_power": "unknown",
            "transcribed_text": "",
            "error": str(e)
        }
