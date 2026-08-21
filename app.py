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

    # =========================================================
    # FLASK APP
    # =========================================================

    app = Flask(__name__)
    app.config.from_object(Config)

    # =========================================================
    # INITIALIZE ENGINES
    # =========================================================

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

    # =========================================================
    # ORCHESTRATOR
    # =========================================================

    orchestrator = Orchestrator(
        rule_engine=rule_engine,
        retrieval_engine=retrieval_engine,
        generative_engine=generative_engine,
    )

    # =========================================================
    # WHATSAPP CONFIGURATION
    # =========================================================

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

    # =========================================================
    # PROCESSED MESSAGE IDS
    # =========================================================

    processed_message_ids = set()

    # =========================================================
    # HOME
    # =========================================================

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

    # =========================================================
    # HEALTH
    # =========================================================

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

    # =========================================================
    # NORMAL CHAT API
    # =========================================================

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

            print("\n========================================")
            print("              CHAT REQUEST")
            print("========================================")

            print("User Text:")
            print(user_text)

            # -------------------------------------------------
            # PREPROCESS
            # -------------------------------------------------

            processed = preprocess(
                user_text,
                source=source
            )

            print("\n[PREPROCESS]")
            print(processed)

            # -------------------------------------------------
            # ORCHESTRATOR
            # -------------------------------------------------

            routed = orchestrator.route(
                processed
            )

            print("\n[ORCHESTRATOR]")
            print(routed)

            # -------------------------------------------------
            # MERGE
            # -------------------------------------------------

            result = merge_response(
                routed,
                output_mode=output_mode
            )

            print("\n[FINAL RESPONSE]")
            print(result)

            print("========================================\n")

            return jsonify(
                result
            ), 200

        except Exception as e:

            print("\n========== CHAT ERROR ==========")

            print(
                "Error:",
                repr(e)
            )

            traceback.print_exc()

            print(
                "================================\n"
            )

            return jsonify({
                "error": "Internal server error."
            }), 500

    # =========================================================
    # WHATSAPP WEBHOOK VERIFICATION
    # =========================================================

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

        print("\n========================================")
        print("       WHATSAPP WEBHOOK VERIFY")
        print("========================================")

        print("Mode:", mode)
        print(
            "Token received:",
            bool(token)
        )
        print(
            "Challenge:",
            challenge
        )

        # -----------------------------------------------------
        # Verify Meta Request
        # -----------------------------------------------------

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

    # =========================================================
    # WHATSAPP WEBHOOK MESSAGE
    # =========================================================

    @app.route("/webhook", methods=["POST"])
    def whatsapp_webhook():

        body = request.get_json(
            silent=True
        )

        print("\n\n========================================")
        print("         WHATSAPP WEBHOOK")
        print("========================================")

        print("Webhook Body:")
        print(body)

        print("========================================")

        # =====================================================
        # VALIDATE BODY
        # =====================================================

        if not body:

            print(
                "[ERROR] Empty webhook body."
            )

            return jsonify({
                "status": "EVENT_RECEIVED"
            }), 200

        try:

            # =================================================
            # CHECK META OBJECT
            # =================================================

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

            # =================================================
            # ENTRIES
            # =================================================

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

            # =================================================
            # ENTRY LOOP
            # =================================================

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

                # =============================================
                # CHANGE LOOP
                # =============================================

                for change in changes:

                    field = change.get(
                        "field"
                    )

                    print(
                        "\nWebhook Field:",
                        field
                    )

                    # -------------------------------------------------
                    # Only messages event
                    # -------------------------------------------------

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

                    # =============================================
                    # STATUS EVENTS
                    # =============================================

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

                    # =============================================
                    # MESSAGES
                    # =============================================

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

                    # =============================================
                    # MESSAGE LOOP
                    # =============================================

                    for message in messages:

                        print(
                            "\n----------------------------------------"
                        )

                        print(
                            "PROCESSING MESSAGE"
                        )

                        print(
                            "----------------------------------------"
                        )

                        # -----------------------------------------
                        # MESSAGE ID
                        # -----------------------------------------

                        message_id = message.get(
                            "id"
                        )

                        print(
                            "Message ID:",
                            message_id
                        )

                        # -----------------------------------------
                        # DUPLICATE CHECK
                        # -----------------------------------------

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

                        # -----------------------------------------
                        # MESSAGE TYPE
                        # -----------------------------------------

                        message_type = message.get(
                            "type"
                        )

                        print(
                            "Message Type:",
                            message_type
                        )

                        # -----------------------------------------
                        # ONLY TEXT
                        # -----------------------------------------

                        if message_type != "text":

                            print(
                                "[INFO] "
                                "Non-text message ignored."
                            )

                            continue

                        # -----------------------------------------
                        # SENDER
                        # -----------------------------------------

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

                        # -----------------------------------------
                        # TEXT
                        # -----------------------------------------

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

                        # =================================================
                        # CHATBOT PIPELINE
                        # =================================================

                        print(
                            "\n========== CHATBOT PIPELINE =========="
                        )

                        # -------------------------------------------------
                        # 1. PREPROCESS
                        # -------------------------------------------------

                        processed = preprocess(
                            user_text,
                            source="whatsapp"
                        )

                        print(
                            "\n[1] PREPROCESSED INPUT"
                        )

                        print(
                            processed
                        )

                        # -------------------------------------------------
                        # 2. ORCHESTRATOR
                        # -------------------------------------------------

                        routed = orchestrator.route(
                            processed
                        )

                        print(
                            "\n[2] ORCHESTRATOR RESULT"
                        )

                        print(
                            routed
                        )

                        # -------------------------------------------------
                        # 3. MERGE RESPONSE
                        # -------------------------------------------------

                        merged_response = merge_response(
                            routed,
                            output_mode="text"
                        )

                        print(
                            "\n[3] MERGED RESPONSE"
                        )

                        print(
                            merged_response
                        )

                        # =================================================
                        # EXTRACT BOT RESPONSE
                        # =================================================

                        bot_reply = ""

                        # -------------------------------------------------
                        # Dictionary
                        # -------------------------------------------------

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

                        # -------------------------------------------------
                        # String
                        # -------------------------------------------------

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

                        # =================================================
                        # FALLBACK TO ORCHESTRATOR
                        # =================================================

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

                        # =================================================
                        # FINAL FALLBACK
                        # =================================================

                        if not bot_reply:

                            bot_reply = (
                                "দুঃখিত, এই মুহূর্তে "
                                "উত্তর দিতে পারছি না।"
                            )

                        print(
                            "\n[4] FINAL BOT RESPONSE"
                        )

                        print(
                            bot_reply
                        )

                        # =================================================
                        # WHATSAPP CONFIG CHECK
                        # =================================================

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

                        # =================================================
                        # WHATSAPP API URL
                        # =================================================

                        whatsapp_url = (
                            "https://graph.facebook.com/"
                            f"{WHATSAPP_API_VERSION}/"
                            f"{PHONE_NUMBER_ID}/messages"
                        )

                        # =================================================
                        # HEADERS
                        # =================================================

                        headers = {
                            "Authorization":
                                f"Bearer {WHATSAPP_TOKEN}",

                            "Content-Type":
                                "application/json"
                        }

                        # =================================================
                        # PAYLOAD
                        # =================================================

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

                        print(
                            "\n========== WHATSAPP SEND =========="
                        )

                        print(
                            "URL:",
                            whatsapp_url
                        )

                        print(
                            "Recipient:",
                            from_number
                        )

                        # =================================================
                        # SEND
                        # =================================================

                        response = requests.post(
                            whatsapp_url,
                            headers=headers,
                            json=payload,
                            timeout=15
                        )

                        # =================================================
                        # RESPONSE
                        # =================================================

                        print(
                            "Status Code:",
                            response.status_code
                        )

                        print(
                            "Response:",
                            response.text
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

            # =================================================
            # ACKNOWLEDGE META
            # =================================================

            print(
                "\n[SUCCESS] "
                "Webhook event processed."
            )

            return jsonify({
                "status": "EVENT_RECEIVED"
            }), 200

        except Exception as e:

            print(
                "\n========================================"
            )

            print(
                "       WHATSAPP WEBHOOK ERROR"
            )

            print(
                "========================================"
            )

            print(
                "Error:",
                repr(e)
            )

            traceback.print_exc()

            print(
                "========================================"
            )

            return jsonify({
                "status": "EVENT_RECEIVED"
            }), 200

    # =========================================================
    # RELOAD DATA
    # =========================================================

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

            print(
                "\n========== RELOAD ERROR =========="
            )

            print(
                repr(e)
            )

            traceback.print_exc()

            print(
                "=================================="
            )

            return jsonify({
                "status": "error",
                "message": "Failed to reload data."
            }), 500

    # =========================================================
    # RETURN APP
    # =========================================================

    return app


# =============================================================
# CREATE APP
# =============================================================

app = create_app()


# =============================================================
# RUN
# =============================================================

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