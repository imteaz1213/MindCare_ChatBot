import traceback
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


    rule_engine = RuleBasedEngine(
        Config.SAFETY_RULES_PATH
    )

    retrieval_engine = RetrievalEngine(
        Config.KNOWLEDGE_BASE_PATH,
        Config.RETRIEVAL_SIMILARITY_THRESHOLD,
    )

    generative_engine = GenerativeEngine(
        gemini_api_key=Config.GEMINI_API_KEY,
        gemini_model=Config.GEMINI_MODEL,
    )


    orchestrator = Orchestrator(
        rule_engine=rule_engine,
        retrieval_engine=retrieval_engine,
        generative_engine=generative_engine,
    )


    VERIFY_TOKEN = getattr(
        Config,
        "VERIFY_TOKEN",
        ""
    )

    WHATSAPP_TOKEN = getattr(
        Config,
        "WHATSAPP_TOKEN",
        ""
    )

    PHONE_NUMBER_ID = getattr(
        Config,
        "PHONE_NUMBER_ID",
        ""
    )

    WHATSAPP_API_VERSION = getattr(
        Config,
        "WHATSAPP_API_VERSION",
        "v23.0"
    )


    processed_message_ids = set()


    @app.route("/", methods=["GET"])
    def home():

        return jsonify({
            "status": "ok",
            "message": "Mind Care Chatbot API is running",
            "service": "Flask API",
            "whatsapp_webhook": "/webhook",
            "chat_endpoint": "/chat",
            "health_endpoint": "/health"
        }), 200


    @app.route("/health", methods=["GET"])
    def health():

        return jsonify({
            "status": "ok",
            "safety_rules_loaded": len(
                rule_engine.rules
            ),
            "knowledge_base_loaded": len(
                retrieval_engine.entries
            ),
            "gemini_enabled": bool(
                Config.GEMINI_API_KEY
            ),
            "gemini_model": Config.GEMINI_MODEL,
            "whatsapp_configured": bool(
                WHATSAPP_TOKEN and PHONE_NUMBER_ID
            )
        }), 200

   

    @app.route("/chat", methods=["POST"])
    def chat():

        body = request.get_json(
            silent=True
        ) or {}

        user_text = (
            body.get("text") or ""
        ).strip()

        source = body.get(
            "source",
            "text"
        )

        output_mode = body.get(
            "output_mode",
            "text"
        )

        if not user_text:

            return jsonify({
                "error": "Field 'text' is required."
            }), 400

        try:

            processed = preprocess(
                user_text,
                source=source
            )

            print("\n[PREPROCESS]")
            print(processed)

            routed = orchestrator.route(
                processed
            )

            result = merge_response(
                routed,
                output_mode=output_mode
            )

            return jsonify(
                result
            ), 200

        except Exception as e:

            return jsonify({
                "error": "Internal server error."
            }), 500


    @app.route("/webhook", methods=["GET"])
    def verify_webhook():

        mode = request.args.get(
            "hub.mode"
        )

        token = request.args.get(
            "hub.verify_token"
        )

        challenge = request.args.get(
            "hub.challenge"
        )


        if (
            mode == "subscribe"
            and token == VERIFY_TOKEN
        ):

            print(
                "[SUCCESS] "
                "Webhook verified successfully."
            )

            return challenge, 200

        print(
            "[ERROR] "
            "Webhook verification failed."
        )

        return "Forbidden", 403


    @app.route("/webhook", methods=["POST"])
    def whatsapp_webhook():

        body = request.get_json(
            silent=True
        )


        if not body:

            print(
                "[ERROR] Empty webhook body."
            )

            return jsonify({
                "status": "EVENT_RECEIVED"
            }), 200

        try:


            if body.get(
                "object"
            ) != "whatsapp_business_account":

                print(
                    "[INFO] "
                    "Not a WhatsApp Business webhook."
                )

                return jsonify({
                    "status": "IGNORED"
                }), 200


            entries = body.get(
                "entry",
                []
            )

            if not entries:

                print(
                    "[INFO] No entries found."
                )

                return jsonify({
                    "status": "EVENT_RECEIVED"
                }), 200


            for entry in entries:

                changes = entry.get(
                    "changes",
                    []
                )

                if not changes:

                    print(
                        "[INFO] No changes found."
                    )

                    continue

                for change in changes:

                    field = change.get(
                        "field"
                    )

                    print(
                        "\nWebhook Field:",
                        field
                    )


                    if field != "messages":

                        print(
                            "[INFO] "
                            "Ignoring field:",
                            field
                        )

                        continue

                    value = change.get(
                        "value",
                        {}
                    )

                    if not value:

                        print(
                            "[INFO] Empty value."
                        )

                        continue


                    statuses = value.get(
                        "statuses",
                        []
                    )

                    if statuses:

                        print(
                            "[INFO] "
                            "WhatsApp status event."
                        )

                        for status in statuses:

                            print(
                                "Status:",
                                status.get(
                                    "status"
                                )
                            )

                        continue


                    messages = value.get(
                        "messages",
                        []
                    )

                    if not messages:

                        print(
                            "[INFO] "
                            "No messages found."
                        )

                        continue


                    for message in messages:

                        message_id = message.get(
                            "id"
                        )

                        if message_id:

                            if (
                                message_id
                                in processed_message_ids
                            ):

                                print(
                                    "[INFO] "
                                    "Duplicate message ignored."
                                )

                                continue

                            processed_message_ids.add(
                                message_id
                            )

                        message_type = message.get(
                            "type"
                        )


                        if message_type != "text":

                            print(
                                "[INFO] "
                                "Non-text message ignored."
                            )

                            continue


                        from_number = message.get(
                            "from"
                        )

                        print(
                            "From:",
                            from_number
                        )

                        if not from_number:

                            print(
                                "[ERROR] "
                                "Sender number missing."
                            )

                            continue


                        text_data = message.get(
                            "text",
                            {}
                        )

                        if not isinstance(
                            text_data,
                            dict
                        ):

                            print(
                                "[ERROR] "
                                "Invalid text data."
                            )

                            continue

                        user_text = (
                            text_data.get(
                                "body"
                            ) or ""
                        ).strip()

                        print(
                            "User Message:",
                            user_text
                        )

                        if not user_text:

                            print(
                                "[ERROR] "
                                "Empty user message."
                            )

                            continue


                        processed = preprocess(
                            user_text,
                            source="whatsapp"
                        )

                        print(
                            "\n[1] PREPROCESSED INPUT"
                        )

                      

                        routed = orchestrator.route(
                            processed
                        )


                        merged_response = merge_response(
                            routed,
                            output_mode="text"
                        )


                        bot_reply = ""

                        if isinstance(
                            merged_response,
                            dict
                        ):

                            bot_reply = (
                                merged_response.get(
                                    "response"
                                )
                                or
                                merged_response.get(
                                    "answer"
                                )
                                or
                                merged_response.get(
                                    "bot_response"
                                )
                                or
                                merged_response.get(
                                    "text"
                                )
                                or
                                ""
                            )


                        elif isinstance(
                            merged_response,
                            str
                        ):

                            bot_reply = (
                                merged_response
                            )

                        bot_reply = str(
                            bot_reply
                        ).strip()


                        if not bot_reply:

                            print(
                                "[WARNING] "
                                "Merged response empty."
                            )

                            if isinstance(
                                routed,
                                dict
                            ):

                                bot_reply = str(
                                    routed.get(
                                        "response"
                                    ) or ""
                                ).strip()


                        if not bot_reply:

                            bot_reply = (
                                "দুঃখিত, এই মুহূর্তে "
                                "উত্তর দিতে পারছি না।"
                            )


                        if not WHATSAPP_TOKEN:

                            print(
                                "[ERROR] "
                                "WHATSAPP_TOKEN is missing."
                            )

                            continue

                        if not PHONE_NUMBER_ID:

                            print(
                                "[ERROR] "
                                "PHONE_NUMBER_ID is missing."
                            )

                            continue

                        whatsapp_url = (
                            "https://graph.facebook.com/"
                            f"{WHATSAPP_API_VERSION}/"
                            f"{PHONE_NUMBER_ID}/messages"
                        )

                        headers = {
                            "Authorization":
                                f"Bearer {WHATSAPP_TOKEN}",

                            "Content-Type":
                                "application/json"
                        }


                        payload = {
                            "messaging_product":
                                "whatsapp",

                            "recipient_type":
                                "individual",

                            "to":
                                from_number,

                            "type":
                                "text",

                            "text": {
                                "preview_url":
                                    False,

                                "body":
                                    bot_reply
                            }
                        }

                        response = requests.post(
                            whatsapp_url,
                            headers=headers,
                            json=payload,
                            timeout=15
                        )

                        if response.ok:

                            print(
                                "[SUCCESS] "
                                "WhatsApp reply sent successfully!"
                            )

                        else:

                            print(
                                "[ERROR] "
                                "WhatsApp API Error!"
                            )

                            print(
                                "Status:",
                                response.status_code
                            )

                            print(
                                "Details:",
                                response.text
                            )

                        print(
                            "===================================="
                        )


            print(
                "\n[SUCCESS] "
                "Webhook event processed."
            )

            return jsonify({
                "status": "EVENT_RECEIVED"
            }), 200

        except Exception as e:

            return jsonify({
                "status": "EVENT_RECEIVED"
            }), 200


    @app.route("/reload-data", methods=["POST"])
    def reload_data():

        try:

            rule_engine.reload(
                Config.SAFETY_RULES_PATH
            )

            retrieval_engine.reload(
                Config.KNOWLEDGE_BASE_PATH
            )

            print(
                "[SUCCESS] "
                "Data reloaded."
            )

            return jsonify({
                "status": "reloaded",
                "safety_rules_loaded": len(
                    rule_engine.rules
                ),
                "knowledge_base_loaded": len(
                    retrieval_engine.entries
                )
            }), 200

        except Exception as e:

            return jsonify({
                "status": "error",
                "message": "Failed to reload data."
            }), 500

    return app


app = create_app()


if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=getattr(
            Config,
            "PORT",
            5000
        ),
        debug=getattr(
            Config,
            "DEBUG",
            False
        )
    )