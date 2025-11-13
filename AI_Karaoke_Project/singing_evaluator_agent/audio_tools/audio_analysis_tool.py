"""
Singing Evaluator Agent for AI Karaoke Project
Simulates 20–30 second performance segment evaluations and communicates with the Judge Agent.
"""

import time
import random
import requests
import uuid

JUDGE_URL = "http://localhost:8000/evaluate_performance"

# === Evaluation data schema ===
def create_new_evaluation_data(segment_id, feedback_type="detail"):
    """Creates a clean evaluation JSON structure."""
    return {
        "performance_segment_id": segment_id,
        "feedback_type": feedback_type,
        "overall_score": 0.0,
        "pitch_accuracy_score": 0.0,
        "rhythm_score": 0.0,
        "vocal_power": "low",
        "emotion_detected": "neutral",
        "error_summary": {"pitch_errors_count": 0, "rhythm_errors_count": 0},
        "instant_trigger": {
            "triggered": False,
            "trigger_type": None,
            "time_ms": None,
            "severity": 0.0
        },
        "aggregated_segments": [],
        "average_scores": {"overall": None, "pitch_accuracy": None, "rhythm": None}
    }

# === Simulated analysis ===
def analyze_segment():
    """Simulate audio evaluation (replace later with real pitch/rhythm detection)."""
    pitch = round(random.uniform(0.6, 0.95), 2)
    rhythm = round(random.uniform(0.6, 0.95), 2)
    overall = round((pitch + rhythm) / 2, 2)
    power = random.choice(["low", "medium", "strong"])
    emotion = random.choice(["neutral", "happy", "sad"])
    pitch_errors = random.randint(0, 3)
    rhythm_errors = random.randint(0, 2)

    return {
        "overall_score": overall,
        "pitch_accuracy_score": pitch,
        "rhythm_score": rhythm,
        "vocal_power": power,
        "emotion_detected": emotion,
        "error_summary": {
            "pitch_errors_count": pitch_errors,
            "rhythm_errors_count": rhythm_errors
        }
    }

# === Communication with Judge ===
def send_to_judge(evaluation_data, personality="strict_judge"):
    """Send JSON to the Judge Agent and print response."""
    payload = {"evaluation_data": evaluation_data, "personality": personality}
    response = requests.post(JUDGE_URL, json=payload)
    if response.ok:
        feedback = response.json().get("feedback") or response.json().get("error")
        print(f"Judge Feedback: {feedback}")
    else:
        print(f"Error from Judge Agent: {response.status_code} - {response.text}")

# === Compute final evaluation ===
def compute_final_evaluation(segment_history):
    """Aggregate segment data for final evaluation."""
    num_segments = len(segment_history)
    if num_segments == 0:
        return None

    avg_overall = sum(s["overall_score"] for s in segment_history) / num_segments
    avg_pitch = sum(s["pitch_accuracy_score"] for s in segment_history) / num_segments
    avg_rhythm = sum(s["rhythm_score"] for s in segment_history) / num_segments
    last_state = segment_history[-1]

    return {
        "feedback_type": "final",
        "aggregated_segments": [s["performance_segment_id"] for s in segment_history],
        "average_scores": {
            "overall": round(avg_overall, 2),
            "pitch_accuracy": round(avg_pitch, 2),
            "rhythm": round(avg_rhythm, 2),
        },
        "vocal_power": last_state.get("vocal_power", "unknown"),
        "emotion_detected": last_state.get("emotion_detected", "neutral")
    }

# === Main loop ===
if __name__ == "__main__":
    print("🎙️ Singing Evaluator Agent started.")
    segment_history = []

    # Simulate 3 performance segments
    for i in range(3):
        segment_id = f"segment_{uuid.uuid4().hex[:6]}"
        print(f"\n🎵 Evaluating segment {i+1} ({segment_id}) ...")

        data = create_new_evaluation_data(segment_id)
        data.update(analyze_segment())

        # simulate chance of an instant error trigger
        if random.random() < 0.2:
            data["instant_trigger"]["triggered"] = True
            data["instant_trigger"]["trigger_type"] = "critical_pitch_deviation"
            data["instant_trigger"]["severity"] = 0.95
            data["feedback_type"] = "instant"

        segment_history.append(data)
        send_to_judge(data)
        time.sleep(2)

    # Compute and send final summary
    final_data = compute_final_evaluation(segment_history)
    if final_data:
        print("\n🏁 Sending final evaluation...")
        send_to_judge(final_data)
