# scraper/utils/cleaner.py
import re
from bs4 import BeautifulSoup
from langdetect import detect

def clean_html(raw_text: str) -> str:
    """Supprime les balises HTML et normalise les espaces."""
    if not raw_text:
        return ""
    text = BeautifulSoup(str(raw_text), "lxml").get_text(separator=" ")
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def normalize_text(text: str) -> str:
    """Normalise les caractères spéciaux."""
    if not text:
        return ""
    text = text.replace('\u2019', "'").replace('\u201c', '"').replace('\u201d', '"')
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', text)
    return text.strip()

def detect_language(text: str) -> str:
    """Détecte la langue du texte."""
    try:
        return detect(str(text)[:500]) if len(str(text)) > 20 else "unknown"
    except:
        return "unknown"