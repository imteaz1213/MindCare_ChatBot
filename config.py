import os

from dotenv import load_dotenv

load_dotenv()  # reads .env into environment variables -- must run before Config reads them

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class Config:
   
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
   
    GEMINI_MODEL = os.environ.get(
    "GEMINI_MODEL",
    "gemini-3.6-flash",
)
    KNOWLEDGE_BASE_PATH = os.environ.get(
        "KNOWLEDGE_BASE_PATH",
        os.path.join(BASE_DIR, "data", "knowledge_base.csv"),
    )
    RETRIEVAL_SIMILARITY_THRESHOLD = float(
        os.environ.get("RETRIEVAL_SIMILARITY_THRESHOLD", 0.70)
    )

    
    SAFETY_RULES_PATH = os.environ.get(
        "SAFETY_RULES_PATH",
        os.path.join(BASE_DIR, "data", "safety_rules.xlsx"),
    )

    ENABLE_TTS = os.environ.get("ENABLE_TTS", "false").lower() == "true"

    DEBUG = os.environ.get("FLASK_DEBUG", "true").lower() == "true"
    PORT = int(os.environ.get("PORT", 5000))