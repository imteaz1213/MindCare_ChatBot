import os
import requests
from flask import Flask, request, jsonify

from config import Config
from nlp.preprocessing import preprocess
from engines.rule_engine import RuleBasedEngine
from engines.retrieval_engine import RetrievalEngine
from engines.generative_engine import GenerativeEngine
from engines.orchestrator import Orchestrator
from utils.response_merger import merge_response


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    rule_engine = RuleBasedEngine(Config.SAFETY_RULES_PATH)

    retrieval_engine = RetrievalEngine(
        Config.KNOWLEDGE_BASE_PATH,
        Config.RETRIEVAL_SIMILARITY_THRESHOLD,
    )

    generative_engine = GenerativeEngine(
        gemini_api_key=Config.GEMINI_API_KEY,
        gemini_model=Config.GEMINI_MODEL,
    )

    orchestrator = Orchestrator(
        rule_engine,
        retrieval_engine,
        generative_engine,
    )

    @app.route("/health", methods=["GET"])
    def health():
        return jsonify(
            {
                "status": "ok",
                "safety_rules_loaded": len(rule_engine.rules),
                "knowledge_base_loaded": len(retrieval_engine.entries),
                "gemini_enabled": bool(Config.GEMINI_API_KEY),
                "gemini_model": Config.GEMINI_MODEL,
            }
        )

    @app.route("/chat", methods=["POST"])
    def chat():
        body = request.get_json(silent=True) or {}

        user_text = (body.get("text") or "").strip()
        source = body.get("source", "text")
        output_mode = body.get("output_mode", "text")

        if not user_text:
            return jsonify(
                {"error": "Field 'text' is required."}
            ), 400

        processed = preprocess(user_text, source=source)
        routed = orchestrator.route(processed)
        result = merge_response(
            routed,
            output_mode=output_mode,
        )

        return jsonify(result)

    # -------------------------------------------------------------
    # WHATSAPP WEBHOOK (META INTEGRATION)
    # -------------------------------------------------------------
    VERIFY_TOKEN = getattr(Config, "VERIFY_TOKEN", "my_secret_token_123")
    WHATSAPP_TOKEN = getattr(Config, "WHATSAPP_TOKEN", "")
    PHONE_NUMBER_ID = getattr(Config, "PHONE_NUMBER_ID", "")

    @app.route("/webhook", methods=["GET"])
    def verify_webhook():
        mode = request.args.get("hub.mode")
        token = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge")

        if mode == "subscribe" and token == VERIFY_TOKEN:
            return challenge, 200
        return "Forbidden", 403

    @app.route("/webhook", methods=["POST"])
    def whatsapp_webhook():
        body = request.get_json(silent=True) or {}

        try:
            entries = body.get("entry", [])
            if entries:
                changes = entries[0].get("changes", [])
                if changes:
                    value = changes[0].get("value", {})
                    messages = value.get("messages", [])
                    if messages:
                        msg = messages[0]
                        from_number = msg.get("from")
                        user_text = msg.get("text", {}).get("body", "").strip()

                        if user_text:
                            # 1. Orchestrator দিয়ে উত্তর প্রসেস করা
                            processed = preprocess(user_text, source="whatsapp")
                            routed = orchestrator.route(processed)
                            merged_res = merge_response(routed, output_mode="text")

                            # আপনার Orchestrator Response থেকে টেক্সট বের করা
                            bot_reply = merged_res.get("response", "Internal Error") if isinstance(merged_res, dict) else str(merged_res)

                            # 2. Meta WhatsApp API-তে রিপ্লাই ব্যাক করা
                            url = f"https://graph.facebook.com/v18.0/{PHONE_NUMBER_ID}/messages"
                            headers = {
                                "Authorization": f"Bearer {WHATSAPP_TOKEN}",
                                "Content-Type": "application/json"
                            }
                            payload = {
                                "messaging_product": "whatsapp",
                                "to": from_number,
                                "text": {"body": bot_reply}
                            }
                            requests.post(url, json=payload, headers=headers)

        except Exception as e:
            print("Webhook Error:", e)

        return jsonify({"status": "EVENT_RECEIVED"}), 200

    @app.route("/reload-data", methods=["POST"])
    def reload_data():
        rule_engine.reload(Config.SAFETY_RULES_PATH)
        retrieval_engine.reload(Config.KNOWLEDGE_BASE_PATH)

        return jsonify(
            {
                "status": "reloaded",
                "safety_rules_loaded": len(rule_engine.rules),
                "knowledge_base_loaded": len(retrieval_engine.entries),
            }
        )

    return app


# Vercel-এর জন্য গ্লোবালি app অবজেক্ট তৈরি করা হলো
app = create_app()

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=Config.PORT,
        debug=Config.DEBUG,
    )