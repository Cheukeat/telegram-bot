import os, re, sys, asyncio, hashlib, logging, unicodedata
from typing import Optional
from dotenv import load_dotenv

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, filters
)

# Windows fix
if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# ============ ENV ============
load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
GEMINI_API_KEY     = os.getenv("GEMINI_API_KEY", "").strip()
WEBHOOK_URL        = (os.getenv("WEBHOOK_URL") or "").strip()
WEBHOOK_SECRET     = (os.getenv("WEBHOOK_SECRET") or "").strip()
PORT               = int(os.getenv("PORT", "8080"))
FORCE_POLLING      = (os.getenv("FORCE_POLLING") or "").lower() in {"1","true","yes"}

if not TELEGRAM_BOT_TOKEN:
    raise SystemExit("⚠️ Missing TELEGRAM_BOT_TOKEN")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("kalyana")

# ============ Offline outline + QA ============
OFFLINE_OUTLINE = """📚 សំណួរដែលអ្នកអាចសួរបាននៅពេល Offline:
- នាយកសាលា NGS-PL ជានរណា?
- នាយិការងឱ្យអ្វីខ្លះ?
- ប្រវត្តិសាលា NGS-PL?
"""

OFFLINE_QA = {
    "នាយកសាលា NGS-PL ជានរណា?": "👨‍💼 លោក នាយក ឆុំ សុភក្តិ",
    "នាយិការងឱ្យអ្វីខ្លះ?": "👩‍💼 លោកស្រី នាយិការង វ៉ៅ សំអូន\n• 🛠 បច្ចេកទេស\n• 🏫 បឋមភូមិ\n...",
    "ប្រវត្តិសាលា NGS-PL?": "📜 សាលាត្រូវបានបង្កើតឡើងក្នុងឆ្នាំ ១៩៨០ ..."
}

# Normalization
def normalize_kh(text: str) -> str:
    s = unicodedata.normalize("NFKC", text or "")
    s = re.sub(r"[\u200b\u00A0]+", "", s).strip()
    s = re.sub(r"[?\u17d4-\u17da.!៖។\s]+$", "", s)
    s = re.sub(r"\s+", " ", s)
    return s

def _qid(text: str) -> str:
    return "q" + hashlib.sha1(normalize_kh(text).encode("utf-8")).hexdigest()[:10]

def _extract_q_from_line(line: str) -> Optional[str]:
    m = re.match(r"^[\s\u200b]*[-•–—]\s*(.+)$", line.strip())
    return m.group(1).strip() if m else None

def _questions_from_outline() -> list[str]:
    return [q for line in OFFLINE_OUTLINE.splitlines() if (q := _extract_q_from_line(line))]

# Offline answers
async def answer_offline(msg, text: str) -> bool:
    qn = normalize_kh(text)
    for q, a in OFFLINE_QA.items():
        if normalize_kh(q) == qn:
            await msg.reply_text(f"❓ {q}\n\n{a}")
            return True
    return False

# ============ Gemini ============
_GENAI_READY = False
try:
    if GEMINI_API_KEY:
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)
        _model = genai.GenerativeModel("gemini-1.5-flash")
        _GENAI_READY = True
except Exception as e:
    log.warning("Gemini not ready: %s", e)

# ============ Handlers ============
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args or []
    if args:
        payload = args[0].strip()
        if payload.startswith("q") and len(payload) == 11:
            for q in _questions_from_outline():
                if _qid(q) == payload:
                    if await answer_offline(update.message, q):
                        return
                    await update.message.reply_text(f"❓ {q}\n\n❌ មិនមានចម្លើយ Offline។")
                    return

    user = update.effective_user.first_name or "អ្នកប្រើ"
    await update.message.reply_text(
        f"🤖 ស្វាគមន៍ {user}\n\n"
        "• /schoolinfo – សំណួរ Offline\n"
        "• វាយសារ​ធម្មតា → ឆ្លើយដោយ Gemini API"
    )

async def schoolinfo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot_username = context.bot.username
    lines_out = []
    for line in OFFLINE_OUTLINE.splitlines():
        q = _extract_q_from_line(line)
        if q:
            qid = _qid(q)
            lines_out.append(f'- <a href="tg://resolve?domain={bot_username}&start={qid}">{q}</a>')
        else:
            lines_out.append(line)
    await update.message.reply_text("\n".join(lines_out), parse_mode=ParseMode.HTML)

async def text_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    if not text: return
    if await answer_offline(update.message, text):
        return
    if not _GENAI_READY:
        await update.message.reply_text("⚠️ GEMINI_API_KEY មិនត្រឹមត្រូវ។")
        return
    try:
        resp = _model.generate_content(text)
        answer = (resp.text or "").strip() or "❌ API មិនឆ្លើយតប។"
    except Exception as e:
        answer = f"⚠️ កំហុស API: {e}"
    await update.message.reply_text(answer)

# ============ Boot ============
import os, re, sys, asyncio, hashlib, logging, unicodedata
from typing import Optional
from dotenv import load_dotenv

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, filters
)

# Windows fix
if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# ============ ENV ============
load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
GEMINI_API_KEY     = os.getenv("GEMINI_API_KEY", "").strip()
WEBHOOK_URL        = (os.getenv("WEBHOOK_URL") or "").strip()
WEBHOOK_SECRET     = (os.getenv("WEBHOOK_SECRET") or "").strip()
PORT               = int(os.getenv("PORT", "8080"))
FORCE_POLLING      = (os.getenv("FORCE_POLLING") or "").lower() in {"1","true","yes"}

if not TELEGRAM_BOT_TOKEN:
    raise SystemExit("⚠️ Missing TELEGRAM_BOT_TOKEN")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("kalyana")

# ============ Offline outline + QA ============
OFFLINE_OUTLINE = """📚 សំណួរដែលអ្នកអាចសួរបាននៅពេល Offline:
- នាយកសាលា NGS-PL ជានរណា?
- នាយិការងឱ្យអ្វីខ្លះ?
- ប្រវត្តិសាលា NGS-PL?
"""

OFFLINE_QA = {
    "នាយកសាលា NGS-PL ជានរណា?": "👨‍💼 លោក នាយក ឆុំ សុភក្តិ",
    "នាយិការងឱ្យអ្វីខ្លះ?": "👩‍💼 លោកស្រី នាយិការង វ៉ៅ សំអូន\n• 🛠 បច្ចេកទេស\n• 🏫 បឋមភូមិ\n...",
    "ប្រវត្តិសាលា NGS-PL?": "📜 សាលាត្រូវបានបង្កើតឡើងក្នុងឆ្នាំ ១៩៨០ ..."
}

# Normalization
def normalize_kh(text: str) -> str:
    s = unicodedata.normalize("NFKC", text or "")
    s = re.sub(r"[\u200b\u00A0]+", "", s).strip()
    s = re.sub(r"[?\u17d4-\u17da.!៖។\s]+$", "", s)
    s = re.sub(r"\s+", " ", s)
    return s

def _qid(text: str) -> str:
    return "q" + hashlib.sha1(normalize_kh(text).encode("utf-8")).hexdigest()[:10]

def _extract_q_from_line(line: str) -> Optional[str]:
    m = re.match(r"^[\s\u200b]*[-•–—]\s*(.+)$", line.strip())
    return m.group(1).strip() if m else None

def _questions_from_outline() -> list[str]:
    return [q for line in OFFLINE_OUTLINE.splitlines() if (q := _extract_q_from_line(line))]

# Offline answers
async def answer_offline(msg, text: str) -> bool:
    qn = normalize_kh(text)
    for q, a in OFFLINE_QA.items():
        if normalize_kh(q) == qn:
            await msg.reply_text(f"❓ {q}\n\n{a}")
            return True
    return False

# ============ Gemini ============
_GENAI_READY = False
try:
    if GEMINI_API_KEY:
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)
        _model = genai.GenerativeModel("gemini-1.5-flash")
        _GENAI_READY = True
except Exception as e:
    log.warning("Gemini not ready: %s", e)

# ============ Handlers ============
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args or []
    if args:
        payload = args[0].strip()
        if payload.startswith("q") and len(payload) == 11:
            for q in _questions_from_outline():
                if _qid(q) == payload:
                    if await answer_offline(update.message, q):
                        return
                    await update.message.reply_text(f"❓ {q}\n\n❌ មិនមានចម្លើយ Offline។")
                    return

    user = update.effective_user.first_name or "អ្នកប្រើ"
    await update.message.reply_text(
        f"🤖 ស្វាគមន៍ {user}\n\n"
        "• /schoolinfo – សំណួរ Offline\n"
        "• វាយសារ​ធម្មតា → ឆ្លើយដោយ Gemini API"
    )

async def schoolinfo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot_username = context.bot.username
    lines_out = []
    for line in OFFLINE_OUTLINE.splitlines():
        q = _extract_q_from_line(line)
        if q:
            qid = _qid(q)
            lines_out.append(f'- <a href="tg://resolve?domain={bot_username}&start={qid}">{q}</a>')
        else:
            lines_out.append(line)
    await update.message.reply_text("\n".join(lines_out), parse_mode=ParseMode.HTML)

async def text_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    if not text: return
    if await answer_offline(update.message, text):
        return
    if not _GENAI_READY:
        await update.message.reply_text("⚠️ GEMINI_API_KEY មិនត្រឹមត្រូវ។")
        return
    try:
        resp = _model.generate_content(text)
        answer = (resp.text or "").strip() or "❌ API មិនឆ្លើយតប។"
    except Exception as e:
        answer = f"⚠️ កំហុស API: {e}"
    await update.message.reply_text(answer)

# ============ Boot ============
def main():
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    # handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("schoolinfo", schoolinfo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_router))

    # --- decide webhook vs polling ---
    use_webhook = (not FORCE_POLLING)

    if use_webhook:
        base_url = (os.getenv("WEBHOOK_BASE_URL")
                    or os.getenv("RENDER_EXTERNAL_URL")
                    or WEBHOOK_URL).rstrip("/")

        if not base_url:
            # No URL available → fall back to polling
            log.warning("No base URL found (RENDER_EXTERNAL_URL/WEBHOOK_BASE_URL/WEBHOOK_URL). Using polling.")
            app.run_polling(drop_pending_updates=True)
            return

        path = f"telegram/{TELEGRAM_BOT_TOKEN}"      # must match webhook_url path
        final_url = f"{base_url}/{path}"

        log.info("🌐 Webhook URL: %s", final_url)
        log.info("🚀 Running webhook on 0.0.0.0:%s path=%s", PORT, path)

        app.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=path,
            webhook_url=final_url,
            # secret_token=(WEBHOOK_SECRET or None),  # re-enable after it works
            drop_pending_updates=True,
        )
    else:
        log.info("🟢 Long-polling…")
        app.run_polling(drop_pending_updates=True)



if __name__ == "__main__":
    main()
