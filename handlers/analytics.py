# handlers/analytics.py
import csv, os, datetime

LOG_PATH = os.path.join(os.path.dirname(__file__), "..", "logs", "qa_events.csv")

def log_event(kind: str, text: str, chosen: str | None = None, user_id: int | None = None):
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    with open(LOG_PATH, "a", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow([datetime.datetime.utcnow().isoformat(), kind, text, chosen or "", user_id or ""])
