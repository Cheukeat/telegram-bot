import unicodedata, re

_KH_DIGITS = str.maketrans("០១២៣៤៥៦៧៨៩", "0123456789")
_PUNCT = r"[។៕៖,\.!?~\-_/\\()\[\]{}«»“”\"'`]|[‐-–—]+"

def normalize(text: str) -> str:
    if not text:
        return ""
    t = text.strip().lower()
    t = re.sub(r"[\u200b-\u200f\u202a-\u202e\u2060\uFE00-\uFE0F]", "", t)  # zero-widths
    t = re.sub(r"\s+", " ", t)
    t = t.translate(_KH_DIGITS)                 # Khmer → ASCII digits
    t = re.sub(_PUNCT, "", t)                   # Khmer + Latin punctuation
    return unicodedata.normalize("NFC", t)
