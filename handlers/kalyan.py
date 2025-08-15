# handlers/kalyan.py
import google.generativeai as genai
from config import GEMINI_API_KEY

def ask_kalyan(prompt: str, api_key: str | None = None) -> str:
    """
    Online answer via Gemini. Khmer-friendly.
    """
    try:
        key = api_key or GEMINI_API_KEY
        if not key:
            return "⚠️ គ្មាន API KEY (GEMINI_API_KEY) ត្រូវបានកំណត់។"
        genai.configure(api_key=key)
        model = genai.GenerativeModel("gemini-pro")
        full_prompt = "ជាអ្នកជំនួយផ្នែកសិក្សាដែលនិយាយភាសាខ្មែរ។ " + prompt
        resp = model.generate_content(full_prompt)
        return (resp.text or "").strip() or "⚠️ API មិនបង្ហាញអត្ថបទចម្លើយ។"
    except Exception as e:
        return f"❌ មានបញ្ហាពេលហៅ API: {e}"
