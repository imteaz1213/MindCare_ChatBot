def merge_response(routed_result: dict, output_mode: str = "text") -> dict:
    """Response Merger / Priority Logic node from the diagram.

    Shapes the final payload for the requested output channel(s):
    text, voice, or both.
    """
    payload = {
        "text_output": routed_result["response"],
        "engine_used": routed_result["engine_used"],
        "category": routed_result.get("category"),
    }

    if output_mode in ("voice", "both"):
        payload["voice_output"] = {
            "text_for_tts": routed_result["response"],
            "note": "Pass text_for_tts to your TTS provider to get audio.",
        }

    return payload
