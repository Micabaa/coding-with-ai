# Konstante für die Nennung des Schemas
SCHEMA_NAME = "EvaluationDataSchema"

# Die definierte Datenstruktur (als Typ-Definition oder initiales Dictionary)
EVALUATION_DATA_TEMPLATE = {
    "performance_segment_id": None, 
    "feedback_type": "detail", # Standardwert
    
    # 1. Kern-Analyse
    "overall_score": 0.0, 
    "pitch_accuracy_score": 0.0, 
    "rhythm_score": 0.0, 

    # 2. Zustand & erweiterte Analyse
    "vocal_power": "low", 
    "emotion_detected": "neutral", 

    # 3. Fehler-Zusammenfassung
    "error_summary": {
        "pitch_errors_count": 0,
        "rhythm_errors_count": 0
    },

    # 4. Instant-Loop-Details
    "instant_trigger": {
        "triggered": False,
        "trigger_type": None,
        "time_ms": None,
        "severity": 0.0
    }
}

def create_new_evaluation_data(segment_id, feedback_type="detail"):
    """Erstellt ein sauberes, neues Datenobjekt zur Befüllung durch den Evaluator."""
    data = EVALUATION_DATA_TEMPLATE.copy()
    data["performance_segment_id"] = segment_id
    data["feedback_type"] = feedback_type
    return data