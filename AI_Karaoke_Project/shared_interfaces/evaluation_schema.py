EVALUATION_DATA_TEMPLATE = {
    "performance_segment_id": None,
    "feedback_type": "detail",  # "detail" | "instant" | "final"

    # 1. Core analysis
    "overall_score": 0.0,
    "pitch_accuracy_score": 0.0,
    "rhythm_score": 0.0,

    # 2. State & extended analysis
    "vocal_power": "low",
    "emotion_detected": "neutral",

    # 3. Error summary
    "error_summary": {
        "pitch_errors_count": 0,
        "rhythm_errors_count": 0
    },

    # 4. Instant trigger details (used when feedback_type == "instant")
    "instant_trigger": {
        "triggered": False,
        "trigger_type": None,
        "time_ms": None,
        "severity": 0.0
    },

    # 5. Aggregated performance summary (used when feedback_type == "final")
    "aggregated_segments": [],  # list of segment summaries or IDs
    "average_scores": {
        "overall": None,
        "pitch_accuracy": None,
        "rhythm": None
    }
}
