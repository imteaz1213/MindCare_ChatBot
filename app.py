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


if __name__ == "__main__":
    app = create_app()
    app.run(
        host="0.0.0.0",
        port=Config.PORT,
        debug=Config.DEBUG,
    )

    
