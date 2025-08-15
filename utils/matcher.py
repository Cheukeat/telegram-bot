# utils/matcher.py
import json, re, unicodedata, importlib.util
from pathlib import Path
from typing import Dict

def _load_offline() -> Dict[str, str]:
    here = Path(__file__).resolve()
    root = here.parent.parent  # repo root

    candidates = [
        root / "offline" / "schoolinfo.json",
        root / "offline" / "offline.json",
        root / "offline.json",
    ]
    for path in candidates:
        if path.exists():
            with path.open("r", encoding="utf-8") as f:
                return json.load(f)

    py_mod = root / "offline" / "offline.py"
    if py_mod.exists():
        spec = importlib.util.spec_from_file_location("offline.offline", str(py_mod))
        mod = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        spec.loader.exec_module(mod)  # type: ignore
        if hasattr(mod, "OFFLINE") and isinstance(mod.OFFLINE, dict):
            return {str(k): str(v) for k, v in mod.OFFLINE.items()}

    raise FileNotFoundError(
        "No offline data found. Create offline/schoolinfo.json (or offline.json / offline/offline.py)."
    )

OFFLINE: Dict[str, str] = _load_offline()

# Khmer normalization
_KH_DIGITS = str.maketrans("០១២៣៤៥៦៧៨៩", "0123456789")
_PUNCT = r"[។៕៖,\.!?~\-_/\\()\[\]{}«»“”\"'`]|[‐-–—]+"
_STOP = {"តើ", "ទេ", "មែនទេ", "អី", "អ្វី", "ឬ", "ញ៉ាំ", "ឬអត់"}

def normalize(text: str) -> str:
    if not text:
        return ""
    t = text.strip().lower()
    t = re.sub(r"[\u200b-\u200f\u202a-\u202e\u2060\uFE00-\uFE0F]", "", t)
    t = re.sub(r"\s+", " ", t)
    t = t.translate(_KH_DIGITS)
    t = re.sub(_PUNCT, "", t)
    return unicodedata.normalize("NFC", t)

def _strip_stopwords(t: str) -> str:
    toks = [w for w in t.split() if w not in _STOP]
    return " ".join(toks) if toks else t

def _char_ngrams(s: str, n: int = 3) -> set[str]:
    if not s: return set()
    if len(s) < n: return {s}
    return {s[i:i+n] for i in range(len(s)-n+1)}

def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b: return 0.0
    return len(a & b) / len(a | b)

def _lev_sim(a: str, b: str) -> float:
    if a == b: return 1.0
    la, lb = len(a), len(b)
    if la == 0 or lb == 0: return 0.0
    dp = list(range(lb+1))
    for i, ca in enumerate(a, 1):
        prev = dp[0]; dp[0] = i
        for j, cb in enumerate(b, 1):
            cost = 0 if ca == cb else 1
            dp[j], prev = min(dp[j]+1, dp[j-1]+1, prev+cost), dp[j]
    dist = dp[-1]
    return 1.0 - dist / max(la, lb)

_EXCLUDE_KEYS = {"សំណួរបែប Offline"}

def get_offline_help_text() -> str:
    return OFFLINE.get("សំណួរបែប Offline", "")

def best_match(user_text: str) -> dict | None:
    q = _strip_stopwords(normalize(user_text))
    if not q: return None
    qg = _char_ngrams(q, 3)
    best = {"key": None, "reply": None, "score": float("-inf")}
    for key, reply in OFFLINE.items():
        if key in _EXCLUDE_KEYS: continue
        kn, rn = normalize(key), normalize(reply)
        score = (
            1.2*_jaccard(qg, _char_ngrams(kn,3)) +
            0.6*_jaccard(qg, _char_ngrams(rn,3)) +
            0.9*_lev_sim(q, kn)
        )
        if score > best["score"]:
            best = {"key": key, "reply": reply, "score": score}
    return best if best["key"] and best["score"] >= 1.05 else None

def top_suggestions(user_text: str, k: int = 4) -> list[str]:
    q = _strip_stopwords(normalize(user_text))
    grams_q = _char_ngrams(q, 3)
    if not grams_q: return []
    scored = []
    for key in OFFLINE.keys():
        if key in _EXCLUDE_KEYS: continue
        grams_k = _char_ngrams(normalize(key), 3)
        scored.append((_jaccard(grams_q, grams_k), key))
    scored.sort(reverse=True)
    return [key for _, key in scored[:k]]
