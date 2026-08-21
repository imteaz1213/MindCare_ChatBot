import os

from dotenv import load_dotenv

load_dotenv()  

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class Config:

    VERIFY_TOKEN = "imteaz"  
    WHATSAPP_TOKEN = "EAAVsbzq8yD0BSa9vgNZBisPaTdVd39LItDP1FwEMCkJUogeD2zHfMeuU4V41A1S9HyitEe4ejZAVGnv3J1rD3fnUz3Oj7BzJD0ZChykL7JAVnJKyBi0mJoprGZCT759uqSZBeD2UM35l18tH1ob3v2GKBOTH4XBrhkfz0Rp9r3FFZAt0IFRCQLadXCUxJzjNYkjwZDZD"   
    PHONE_NUMBER_ID = "1333868569803384" 
   
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
