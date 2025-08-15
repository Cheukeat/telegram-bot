# offline/brain_school.py
# Robust loader + Khmer-friendly fuzzy matching
import os, json, unicodedata, re
from math import inf

# ---------- Load OFFLINE data (supports json or python dict) ----------
BASE_DIR = os.path.dirname(__file__)
_CANDIDATES = ["offline.json", "schoolinfo.json"]

def _load_offline():
    # 1) JSON files next to this module
    for name in _CANDIDATES:
        p = os.path.join(BASE_DIR, name)
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f)
    # 2) Python file: offline/offline.py with OFFLINE = {...}
    try:
        from .offline import OFFLINE as data  # type: ignore
        return data
    except Exception:
        pass
    raise FileNotFoundError(
        "Offline KB not found. Place one of these next to brain_school.py:\n"
        " - offline.json (UTF-8)\n - schoolinfo.json (UTF-8)\n"
        " - offline.py (defines OFFLINE = {...})"
    )

OFFLINE = _load_offline()

# ---------- Khmer normalization ----------
_KH_DIGITS = str.maketrans("០១២៣៤៥៦៧៨៩", "0123456789")
_PUNCT = r"[។៕៖,\.!?~\-_/\\()\[\]{}«»“”\"'`]|[‐-–—]+"

def normalize(text: str) -> str:
    if not text:
        return ""
    t = text.strip().lower()
    t = re.sub(r"[\u200b-\u200f\u202a-\u202e\u2060\uFE00-\uFE0F]", "", t)  # zero-widths
    t = re.sub(r"\s+", " ", t)
    t = t.translate(_KH_DIGITS)  # Khmer digits → ASCII
    t = re.sub(_PUNCT, "", t)
    return unicodedata.normalize("NFC", t)

# ---------- Fuzzy matcher ----------
try:
    from rapidfuzz.string_metric import levenshtein
    _HAS_RF = True
except Exception:
    _HAS_RF = False

_EXCLUDE_KEYS = {"សំណួរបែប Offline"}

def _char_ngrams(s: str, n: int = 3) -> set[str]:
    s = normalize(s)
    if not s:
        return set()
    if len(s) <= n:
        return {s}
    return {s[i:i+n] for i in range(len(s) - n + 1)}

def _jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 0.0
    u = len(a | b)
    return (len(a & b) / u) if u else 0.0

def _lev_sim(a: str, b: str) -> float:
    a, b = normalize(a), normalize(b)
    if not a and not b:
        return 1.0
    if _HAS_RF:
        dist = levenshtein(a, b)
    else:
        dist = abs(len(a) - len(b))  # cheap lower bound
    m = max(len(a), len(b), 1)
    return 1.0 - (dist / m)

def _keyword_boost(query: str, key: str, reply: str) -> float:
    q, k, r = normalize(query), normalize(key), normalize(reply)
    score = 0.0
    if q and (q in k or k in q):
        score += 0.7
    if q and q in r:
        score += 0.4
    if set(q.split()) & set(k.split()):
        score += 0.6
    return score

def best_match(user_text: str):
    """Return dict {key, reply, score} or None."""
    q = normalize(user_text)
    if not q:
        return None
    qg = _char_ngrams(q, 3)

    best = {"key": None, "reply": None, "score": -inf}
    for key, reply in OFFLINE.items():
        if key in _EXCLUDE_KEYS:
            continue
        kn, rn = normalize(key), normalize(reply)
        score = (
            1.2 * _jaccard(qg, _char_ngrams(kn, 3)) +
            0.6 * _jaccard(qg, _char_ngrams(rn, 3)) +
            0.9 * _lev_sim(q, kn) +
            _keyword_boost(q, kn, rn)
        )
        if score > best["score"]:
            best = {"key": key, "reply": reply, "score": score}

    return best if best["score"] >= 1.35 else None

def top_suggestions(user_text: str, k: int = 3) -> list[str]:
    """Return top-k closest keys for guidance."""
    qg = _char_ngrams(user_text, 3)
    cand = []
    for key in OFFLINE.keys():
        if key in _EXCLUDE_KEYS:
            continue
        cand.append((_jaccard(qg, _char_ngrams(key, 3)), key))
    cand.sort(reverse=True)
    return [k for _, k in cand[:k]]
