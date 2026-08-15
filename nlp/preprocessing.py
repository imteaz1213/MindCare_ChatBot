import re
import string


def clean_text(text: str) -> str:
    
    if not text:
        return ""

    text = text.strip().lower()
    text = re.sub(r"\s+", " ", text)

    keep = "?!।"  
    remove_chars = "".join(c for c in string.punctuation if c not in keep)
    text = text.translate(str.maketrans("", "", remove_chars))
    return text.strip()


def tokenize(text: str) -> list:
    return clean_text(text).split()


def preprocess(raw_text: str, source: str = "text") -> dict:

    cleaned = clean_text(raw_text)
    return {
        "raw_text": raw_text,
        "clean_text": cleaned,
        "tokens": tokenize(raw_text),
        "source": source,  # "text" or "voice"
        "length": len(cleaned),
    }
