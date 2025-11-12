from mcp.client import Client
import asyncio

async def main():
    client = Client("judge-agent")
    await client.connect()

    evaluation_data = {
        "performance_segment_id": "seg_001",
        "feedback_type": "detail",
        "overall_score": 0.77,
        "pitch_accuracy_score": 0.69,
        "rhythm_score": 0.84,
        "vocal_power": "medium",
        "emotion_detected": "neutral",
        "error_summary": {"pitch_errors_count": 3, "rhythm_errors_count": 1},
        "instant_trigger": {"triggered": False}
    }

    result = await client.call("evaluate_performance", {
        "evaluation_data": evaluation_data,
        "personality": "strict_judge"
    })

    print("Judge feedback:", result.content.get("feedback", result.content.get("error")))

asyncio.run(main())
