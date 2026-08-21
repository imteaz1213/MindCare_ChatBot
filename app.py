
import json
import requests
from flask import Flask, jsonify, request

from config import Config
from engines.generative_engine import GenerativeEngine
from engines.orchestrator import Orchestrator
from engines.retrieval_engine import RetrievalEngine
from engines.rule_engine import RuleBasedEngine
from nlp.preprocessing import preprocess
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

    VERIFY_TOKEN = getattr(Config, "VERIFY_TOKEN", "")
    WHATSAPP_TOKEN = getattr(Config, "WHATSAPP_TOKEN", "")
    PHONE_NUMBER_ID = getattr(Config, "PHONE_NUMBER_ID", "")

    @app.route("/", methods=["GET"])
    def home():
        return (
            jsonify({
                "status": "ok",
                "message": "Mind Care Chatbot API is running",
                "service": "Flask API",
                "whatsapp_webhook": "/webhook",
                "chat_endpoint": "/chat",
                "health_endpoint": "/health",
            }),
            200,
        )

    @app.route("/health", methods=["GET"])
    def health():
        return (
            jsonify({
                "status": "ok",
                "safety_rules_loaded": len(rule_engine.rules),
                "knowledge_base_loaded": len(retrieval_engine.entries),
                "gemini_enabled": bool(Config.GEMINI_API_KEY),
                "gemini_model": Config.GEMINI_MODEL,
            }),
            200,
        )

    @app.route("/chat", methods=["POST"])
    def chat():
        body = request.get_json(silent=True) or {}
        user_text = (body.get("text") or "").strip()
        source = body.get("source", "text")
        output_mode = body.get("output_mode", "text")

        if not user_text:
            return jsonify({"error": "Field 'text' is required."}), 400

        try:
            processed = preprocess(user_text, source=source)
            routed = orchestrator.route(processed)
            result = merge_response(routed, output_mode=output_mode)
            return jsonify(result), 200

        except Exception as e:
            print("Chat Error:", repr(e))
            return jsonify({"error": "Internal server error."}), 500

    @app.route("/webhook", methods=["GET"])
    def verify_webhook():
        mode = request.args.get("hub.mode")
        token = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge")

        if mode == "subscribe" and token and token == VERIFY_TOKEN:
            return challenge, 200

        return "Forbidden", 403

    @app.route("/webhook", methods=["POST"])
    def whatsapp_webhook():
        body = request.get_json(silent=True) or {}

        try:
            print("DEBUG Webhook Body:\n", json.dumps(body, indent=2, ensure_ascii=False))

            # ১. Postman বা কাস্টম Direct Testing
            if "text" in body and isinstance(body["text"], str):
                user_text = body["text"].strip()
                processed = preprocess(user_text, source="postman")
                routed = orchestrator.route(processed)
                merged_response = merge_response(routed, output_mode="text")

                bot_reply = (
                    merged_response.get("response")
                    or merged_response.get("answer")
                    if isinstance(merged_response, dict)
                    else str(merged_response)
                )

                return jsonify({
                    "debug_status": "Received Successfully",
                    "user_input": user_text,
                    "bot_reply": bot_reply,
                    "received_body": body
                }), 200

            # ২. Meta WhatsApp Official Webhook Processing
            if body.get("object") == "whatsapp_business_account":
                entries = body.get("entry", [])

                for entry in entries:
                    changes = entry.get("changes", [])
                    for change in changes:
                        value = change.get("value", {})
                        messages = value.get("messages", [])

                        if not messages:
                            continue

                        for message in messages:
                            if message.get("type") != "text":
                                continue

                            from_number = message.get("from")
                            text_data = message.get("text", {})
                            user_text = (text_data.get("body", "") or "").strip()

                            if not from_number or not user_text:
                                continue

                            processed = preprocess(user_text, source="whatsapp")
                            routed = orchestrator.route(processed)
                            merged_response = merge_response(routed, output_mode="text")

                            if isinstance(merged_response, dict):
                                bot_reply = (
                                    merged_response.get("response")
                                    or merged_response.get("answer")
                                    or "দুঃখিত, এই মুহূর্তে উত্তর দিতে পারছি না।"
                                )
                            else:
                                bot_reply = str(merged_response)

                            bot_reply = str(bot_reply).strip() or "দুঃখিত, এই মুহূর্তে উত্তর দিতে পারছি না।"

                            # WhatsApp Message Send API Logic
                            if WHATSAPP_TOKEN and PHONE_NUMBER_ID:
                                whatsapp_url = f"https://graph.facebook.com/v18.0/{PHONE_NUMBER_ID}/messages"
                                headers = {
                                    "Authorization": f"Bearer {WHATSAPP_TOKEN}",
                                    "Content-Type": "application/json",
                                }
                                payload = {
                                    "messaging_product": "whatsapp",
                                    "to": from_number,
                                    "type": "text",
                                    "text": {"body": bot_reply},
                                }

                                response = requests.post(
                                    whatsapp_url,
                                    json=payload,
                                    headers=headers,
                                    timeout=10,
                                )

                                if not response.ok:
                                    print("WhatsApp API Error:", response.status_code, response.text)
                            else:
                                print("WhatsApp credentials are missing in Config.")

            return jsonify({"status": "EVENT_RECEIVED"}), 200

        except Exception as e:
            print("WhatsApp Webhook Error:", repr(e))
            return jsonify({"status": "EVENT_RECEIVED"}), 200

    @app.route("/reload-data", methods=["POST"])
    def reload_data():
        try:
            rule_engine.reload(Config.SAFETY_RULES_PATH)
            retrieval_engine.reload(Config.KNOWLEDGE_BASE_PATH)
            return (
                jsonify({
                    "status": "reloaded",
                    "safety_rules_loaded": len(rule_engine.rules),
                    "knowledge_base_loaded": len(retrieval_engine.entries),
                }),
                200,
            )
        except Exception as e:
            print("Reload Error:", repr(e))
            return jsonify({"status": "error", "message": "Failed to reload data."}), 500

    return app


app = create_app()

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=getattr(Config, "PORT", 5000),
        debug=getattr(Config, "DEBUG", False),
    )