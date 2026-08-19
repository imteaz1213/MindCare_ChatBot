import os

from dotenv import load_dotenv

load_dotenv()  # reads .env into environment variables -- must run before Config reads them

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class Config:

    VERIFY_TOKEN = "imteaz"  
    WHATSAPP_TOKEN = "EAAVsbzq8yD0BSXX35B8RsZBhRQY2TGVDRq22fDq4ZC7e4G5Q31QDMvEvUTPEeHdZBS4YtYbCMFEh1LAVo1hfIEuDLmJEPzFlgmjnAqFQJmYa0gf5tBmKzjZC6YYq2yc8IsygTc8fPEdEo3e4dMePeXBSxrn1WKh5GeiWvGh4Gcv4BbhadsZBOeFOFEXKMSBdHb482Xc7zIyH4xM9BmWDElZC5T9eAlE4MiZCDZCNkqJdu23S4Nk7Wuqgq8ABkZAXscLtJ3MZBZCBWe9BlpovyUubeCdPtFZCRQZDZD"   
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