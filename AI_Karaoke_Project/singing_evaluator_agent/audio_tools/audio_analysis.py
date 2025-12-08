import librosa
import numpy as np
import os
import logging
from rapidfuzz import fuzz
from openai import OpenAI
from dotenv import load_dotenv
from fastdtw import fastdtw
from scipy.spatial.distance import euclidean
import difflib
import re

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()
client = OpenAI()

import soundfile as sf

def transcribe_audio(audio_path, prompt=""):
    """
    Transcribes audio using OpenAI Whisper.
    Normalizes audio first to boost volume.
    """
    try:
        if not os.path.exists(audio_path):
             logger.error(f"Audio file not found: {audio_path}")
             return ""
        
        # Load and Normalize
        y, sr = librosa.load(audio_path, sr=None)
        y_norm = librosa.util.normalize(y)
        
        # Save to temp file
        temp_path = audio_path.replace(".wav", "_norm.wav")
        sf.write(temp_path, y_norm, sr)

        with open(temp_path, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model="whisper-1", 
                file=audio_file,
                language="en",
                prompt=prompt[:500] 
            )
        
        # Cleanup
        if os.path.exists(temp_path):
            os.remove(temp_path)
            
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
    # partial_ratio might be better if transcribed is a subset, but we want full match of expected segment
    # ratio is stricter.
    ratio = fuzz.ratio(transcribed_text.lower(), ref_text.lower())
    return ratio / 100.0

def calculate_timing_score(y, sr, reference_lyrics):
    """
    Calculates timing score by comparing voice activity with reference lyrics timestamps.
    """
    if not reference_lyrics:
        return 0.0

    # 1. Detect Voice Activity (VAD)
    intervals = librosa.effects.split(y, top_db=20)
    singing_intervals = librosa.samples_to_time(intervals, sr=sr)
    
    # 2. Calculate Overlap
    total_overlap_duration = 0.0
    total_lyric_duration = 0.0
    
    sorted_lyrics = sorted(reference_lyrics, key=lambda x: x.get('timestamp', x.get('start_time', 0)))
    
    for i, lyric in enumerate(sorted_lyrics):
        start = float(lyric.get('timestamp', lyric.get('start_time', 0)))
        
        # Infer end time
        if i < len(sorted_lyrics) - 1:
            next_start = float(sorted_lyrics[i+1].get('timestamp', sorted_lyrics[i+1].get('start_time', 0)))
            time_gap = next_start - start
        else:
            time_gap = 5.0
            
        words = lyric.get('text', '').split()
        num_words = len(words) if words else 1
        estimated_duration = num_words * 0.6 
        target_duration = min(time_gap, estimated_duration)
        target_duration = max(0.5, target_duration)
            
        total_lyric_duration += target_duration
        
        # Window: allow slightly early start (-1.5s)
        window_start = start - 1.5 
        window_end = start + max(time_gap, target_duration) + 1.0 # Buffer
        
        overlap_found = 0.0
        for sing_start, sing_end in singing_intervals:
             # Check overlap
            o_start = max(window_start, sing_start)
            o_end = min(window_end, sing_end)
            
            if o_end > o_start:
                overlap_found += (o_end - o_start)
                
        # Cap overlap
        total_overlap_duration += min(overlap_found, target_duration * 1.5)
    
    if total_lyric_duration > 0:
        score = min(1.0, total_overlap_duration / total_lyric_duration)
        if score > 0.1: score = min(1.0, score + 0.1)
    else:
        score = 0.0
        
    return score

def calculate_dtw_score(y_user, sr_user, reference_audio_path):
    """
    Calculates the similarity between user audio and reference audio using Dynamic Time Warping (DTW)
    on Chroma features.
    """
    if not reference_audio_path or not os.path.exists(reference_audio_path):
        return 0.5 # Default if no reference

    try:
        # Load reference audio (resample to match user)
        # Load only first 60s to save compute if needed, or full song
        y_ref, _ = librosa.load(reference_audio_path, sr=sr_user, duration=60) 
        
        # Extract Chroma Features (Pitch Class Profile)
        chroma_user = librosa.feature.chroma_cqt(y=y_user, sr=sr_user)
        chroma_ref = librosa.feature.chroma_cqt(y=y_ref, sr=sr_user)
        
        # Transpose for fastdtw (needs [n_samples, n_features])
        chroma_user = chroma_user.T
        chroma_ref = chroma_ref.T
        
        # Compute DTW
        distance, path = fastdtw(chroma_user, chroma_ref, dist=euclidean)
        
        # Normalize distance
        avg_dist = distance / len(path)
        
        # Heuristic mapping
        score = np.exp(-avg_dist * 2) 
        
        logger.info(f"DTW Analysis: Distance={distance:.2f}, Avg={avg_dist:.4f} -> Score={score:.4f}")
        return float(score)

    except Exception as e:
        logger.error(f"DTW analysis failed: {e}")
        return 0.0

def normalize_text(text):
    """
    Normalizes text for comparison.
    """
    text = re.sub(r'[^\w\s]', '', text.lower())
    return text

def analyze_lyrics_diff(transcribed_text, reference_lyrics_data):
    """
    Compares transcribed text with reference lyrics word by word.
    Returns a list of words with status: 'matched', 'missing', 'extra', 'wrong'.
    """
    if not reference_lyrics_data:
        return []
    
    ref_text = " ".join([l.get('text', '') for l in reference_lyrics_data])
    
    ref_norm = normalize_text(ref_text)
    trans_norm = normalize_text(transcribed_text) if transcribed_text else ""
    
    ref_words = ref_norm.split()
    trans_words = trans_norm.split()
    
    ref_display_words = ref_text.split()
    if len(ref_display_words) != len(ref_words):
        ref_display_words = ref_words

    matcher = difflib.SequenceMatcher(None, ref_words, trans_words)
    diff_result = []
    
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == 'equal':
            for k in range(i1, i2):
                diff_result.append({"word": ref_display_words[k], "status": "matched"})
        elif tag == 'replace':
            heard_chunk = trans_words[j1:j2]
            ref_chunk = ref_display_words[i1:i2]
            n_ref = len(ref_chunk)
            n_heard = len(heard_chunk)
            
            if n_ref > n_heard:
                n_missing = n_ref - n_heard
                for k in range(n_missing):
                    diff_result.append({"word": ref_chunk[k], "status": "missing"})
                for k in range(n_missing, n_ref):
                    heard_idx = k - n_missing
                    heard_word = heard_chunk[heard_idx] if heard_idx < n_heard else ""
                    if heard_word and fuzz.ratio(ref_chunk[k], heard_word) > 65:
                        diff_result.append({"word": ref_chunk[k], "status": "matched"})
                    else:
                        diff_result.append({"word": ref_chunk[k], "status": "wrong", "heard": heard_word})
            else:
                for k, word in enumerate(ref_chunk):
                    heard_word = heard_chunk[k]
                    if fuzz.ratio(word, heard_word) > 65:
                        diff_result.append({"word": word, "status": "matched"})
                    else:
                        diff_result.append({"word": word, "status": "wrong", "heard": heard_word})
                
        elif tag == 'delete':
            for k in range(i1, i2):
                diff_result.append({"word": ref_display_words[k], "status": "missing"})
        elif tag == 'insert':
            for word in trans_words[j1:j2]:
                diff_result.append({"word": word, "status": "extra"})
                
    return diff_result

def analyze_pitch_detail(y_user, sr_user, reference_audio_path):
    """
    Detailed pitch analysis using CHROMA (Harmonic) comparison.
    Robust for polyphonic backing tracks (MP4/Youtube).
    """
    if not reference_audio_path or not os.path.exists(reference_audio_path):
        return {"high": 0, "low": 0, "perfect": 0}

    try:
        # Load reference (limit duration to match user ~ roughly)
        user_duration = librosa.get_duration(y=y_user, sr=sr_user)
        y_ref, _ = librosa.load(reference_audio_path, sr=sr_user, duration=user_duration + 5)
        
        # Extract Chroma (12 bins: C, C#, D...)
        chroma_user = librosa.feature.chroma_cqt(y=y_user, sr=sr_user)
        chroma_ref = librosa.feature.chroma_cqt(y=y_ref, sr=sr_user)
        
        # Align using DTW on Chroma
        # Transpose for fastdtw [frames, features]
        dist, path = fastdtw(chroma_user.T, chroma_ref.T, dist=euclidean)
        
        high_count = 0
        low_count = 0
        perfect_count = 0
        total_frames = 0
        
        for idx_user, idx_ref in path:
            # Compare DOMINANT note in each frame
            # (Which note 0-11 has highest energy)
            # Threshold energy to ignore silence
            if np.max(chroma_user[:, idx_user]) < 0.1:
                continue
                
            note_user = np.argmax(chroma_user[:, idx_user])
            note_ref = np.argmax(chroma_ref[:, idx_ref])
            
            total_frames += 1
            
            diff = abs(note_user - note_ref)
            # Handle wrapping
            if diff > 6: diff = 12 - diff
            
            # Allow Consonant Intervals (0=Unison, 3/4=3rds, 5=4th, 7=5th -> wrap to 5)
            # diff is 0 to 6.
            # 0: Unison
            # 1: Minor 2nd (Dissonant)
            # 2: Major 2nd (Ok-ish)
            # 3: Minor 3rd (Consonant)
            # 4: Major 3rd (Consonant)
            # 5: Perfect 4th (Consonant)
            # 6: Tritone (Dissonant) - Wait, 7 semitones (5th) -> 12-7=5. So diff 5 covers 4th and 5th.
            
            if diff == 0:
                perfect_count += 1
            elif diff in [3, 4, 5]: # Allow 3rds, 4ths, 5ths as "Harmony" (Good)
                perfect_count += 1 # Count as perfect for scoring
            elif diff == 2:
                high_count += 1 # Close
            else:
                low_count += 1
                    
        if total_frames == 0:
            return {"high": 0, "low": 0, "perfect": 0}
            
        return {
            "high": round(high_count / total_frames, 2),
            "low": round(low_count / total_frames, 2),
            "perfect": round(perfect_count / total_frames, 2)
        }

    except Exception as e:
        logger.error(f"Detailed pitch analysis failed: {e}")
        return {"high": 0, "low": 0, "perfect": 0}

def analyze_audio(audio_path, reference_lyrics=None, reference_audio_path=None, offset=0.0):
    """
    Analyzes an audio file to extract pitch, rhythm, and other metrics.
    """
    try:
        y, sr = librosa.load(audio_path, sr=None)
        
        # 1. Pitch Analysis using YIN
        f0 = librosa.yin(y, fmin=librosa.note_to_hz('C2'), fmax=librosa.note_to_hz('C7'))
        valid_f0 = f0[~np.isnan(f0)]
        
        if len(valid_f0) > 0:
            pitch_variance = float(np.var(valid_f0))
            pitch_stability = max(0.0, min(1.0, 1.0 - (pitch_variance / 10000.0)))
        else:
            pitch_stability = 0.0

        # Filter lyrics to only those within the audio duration (plus buffer)
        # This prevents marking the rest of the song as "missing" if the user stops early.
        audio_duration = librosa.get_duration(y=y, sr=sr)
        logger.info(f"Audio Duration: {audio_duration:.2f}s, Offset: {offset}s")
        
        relevant_lyrics = []
        if reference_lyrics:
            logger.info(f"Total Reference Lyrics: {len(reference_lyrics)}")
            if len(reference_lyrics) > 0:
                first_ts = reference_lyrics[0].get('timestamp', reference_lyrics[0].get('start_time', 'N/A'))
                logger.info(f"First Lyric Timestamp (Original): {first_ts}")
                
            for line in reference_lyrics:
                orig_start = float(line.get('timestamp', line.get('start_time', 0)))
                # Shift timestamp by offset to match recording time
                adjusted_start = orig_start - offset
                
                # If the line starts within the audio range (with small buffers)
                if -2.0 < adjusted_start < audio_duration + 5.0: 
                    # Create copy with adjusted timestamp
                    new_line = line.copy()
                    new_line['timestamp'] = adjusted_start
                    relevant_lyrics.append(new_line)
        
        logger.info(f"Relevant Lyrics Count: {len(relevant_lyrics)}")
        if not relevant_lyrics and reference_lyrics:
             logger.warning("No relevant lyrics found! Checking timestamps vs duration.")
        
        # Pitch Compatibility (DTW)
        dtw_score = calculate_dtw_score(y, sr, reference_audio_path)
        
        # Detailed Pitch Breakdown
        pitch_detail = analyze_pitch_detail(y, sr, reference_audio_path)
        
        # Combined Pitch Score - Use Perfect% from Chroma as main driver if valid
        # because dtw_score is raw distance, pitch_detail is logic-based.
        chroma_score = pitch_detail["perfect"] + (pitch_detail["high"] * 0.5)
        pitch_accuracy_score = (pitch_stability * 0.1) + (chroma_score * 0.9)

        # 2. Rhythm/Timing Analysis
        if relevant_lyrics:
             # Use relevant_lyrics instead of full reference_lyrics
            rhythm_score = calculate_timing_score(y, sr, relevant_lyrics)
        else:
            tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
            rhythm_score = 0.8 if tempo > 0 else 0.0
        
        # 3. Lyrics Accuracy (STT)
        # Prepare prompt from RELEVANT lyrics
        prompt_text = ""
        if relevant_lyrics:
             prompt_text = " ".join([l.get('text', '') for l in relevant_lyrics])
             
        # Transcribe with Prompt
        transcribed_text = transcribe_audio(audio_path, prompt=prompt_text)
        
        # Compare with RELEVANT lyrics (not full song)
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
            "audio_duration": audio_duration, # Return Duration!
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
