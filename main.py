# main.py
import os
import re
import hashlib
import logging
import asyncio
import nest_asyncio

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, filters
)

from config import TELEGRAM_BOT_TOKEN, GEMINI_API_KEY
from utils.matcher import best_match, top_suggestions, get_offline_help_text

# Patch event loop for hosted envs (Render, etc.)
nest_asyncio.apply()

# --- Bullet parsing for outline lines (- • – —)
_BULLET_RE = re.compile(r"^[\s\u200b]*([-•–—])\s*(.+)$")
def _extract_q_from_line(line: str) -> str | None:
    m = _BULLET_RE.match(line.strip())
    return m.group(2).strip() if m else None

# Optional online fallback (Gemini)
try:
    from handlers.kalyan import ask_kalyan  # def ask_kalyan(text: str, api_key: str) -> str
except Exception:
    ask_kalyan = None

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("kalyana")

QUESTION_MAP_KEY = "question_map"

def _qid(text: str) -> str:
    return "q" + hashlib.sha1(text.encode("utf-8")).hexdigest()[:10]

def _extract_questions() -> list[str]:
    text = get_offline_help_text() or ""
    qs: list[str] = []
    for line in text.splitlines():
        q = _extract_q_from_line(line)
        if q:
            qs.append(q)
    return qs

async def _answer_offline(msg_obj, user_text: str) -> bool:
    """
    Try offline answer first. If no exact reply, suggest similar questions
    as plain text (NO buttons).
    """
    m = best_match(user_text)
    if m:
        await msg_obj.reply_text(f"❓ {user_text}\n\n{m['reply']}")
        return True

    sugg = top_suggestions(user_text, k=4)
    if sugg:
        txt = "💡 សាកល្បងសំណួរទាំងនេះ (offline):\n" + "\n".join(f"• {s}" for s in sugg)
        await msg_obj.reply_text(txt)
        return True
    return False

# ---------- /ask (API / online) ----------
async def ask_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /ask <question> (alias: /ai)
    Always uses online API (ask_kalyan), separate from offline.
    You can also reply to any message with /ask.
    """
    parts = context.args or []
    if parts:
        prompt = " ".join(parts).strip()
    elif update.message and update.message.reply_to_message and update.message.reply_to_message.text:
        prompt = update.message.reply_to_message.text.strip()
    else:
        await update.message.reply_text(
            "🧠 ប្រើឧទាហរណ៍៖\n"
            "• `/ask អ្វីទៅជា AI?`\n"
            "• ឬ reply ទៅលើសារណាមួយ ហើយវាយ `/ask`",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    if not ask_kalyan or not GEMINI_API_KEY:
        await update.message.reply_text("⚠️ API មិនបានកំណត់ (GEMINI_API_KEY/ask_kalyan មិនមាន).")
        return

    try:
        reply = ask_kalyan(prompt, api_key=GEMINI_API_KEY) or "❌ API មិនឆ្លើយតប។"
    except Exception as e:
        reply = f"⚠️ កំហុសពេលហៅ API: {e}"

    await update.message.reply_text(f"❓ {prompt}\n\n{reply}")

# ---------- /start ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Handle deep-link payload ?start=<id> from /schoolinfo links
    if context.args:
        payload = context.args[0]
        qmap = context.application.bot_data.get(QUESTION_MAP_KEY, {})
        q_text = qmap.get(payload)
        if q_text:
            if await _answer_offline(update.message, q_text):
                return
            await update.message.reply_text(f"❓ {q_text}\n\n❌ មិនមានចម្លើយ Offline។")
            return

    # Normal welcome
    user = update.effective_user.first_name or "អ្នកប្រើ"
    txt = (
        f"🤖 ស្វាគមន៍ {user}\n\n"
        "អ្វីដែលខ្ញុំអាចធ្វើបាន:\n"
        "• ឆ្លើយសំណួរអំពីប្រធានបទណាមួយ\n"
        "• ព័ត៌មាន Offline អំពីសាលា NGS PREAKLEAP\n\n"
        "🔰 ពាក្យបញ្ជា:\n"
        "• /start\n"
        "• /schoolinfo – បង្ហាញសំណួរ Offline (ចុចបាន)\n"
        "• /ask <សំណួរ> – សួរតាម API\n"
        "• /ai <សំណួរ> – ដូច /ask\n\n"
        "✏️ កល្យាណ បង្កើតដោយសិស្ស NGS PREAKLEAP\n"
        "📞 https://t.me/Cheukeat"
    )
    await update.message.reply_text(txt)

# ---------- /schoolinfo (blue links; NO buttons) ----------
async def schoolinfo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot_username = context.bot.username
    help_text = get_offline_help_text() or ""
    qmap = context.application.bot_data.setdefault(QUESTION_MAP_KEY, {})

    # BLUE, clickable deep-links inside the outline (HTML)
    lines_out = []
    for line in help_text.splitlines():
        q = _extract_q_from_line(line)
        if q:
            qid = _qid(q)
            qmap[qid] = q
            link = f"https://t.me/{bot_username}?start={qid}"
            lines_out.append(f'- <a href="{link}">{q}</a>')
        else:
            lines_out.append(line)

    await update.message.reply_text(
        "\n".join(lines_out),
        parse_mode="HTML",
        disable_web_page_preview=True
    )

# ---------- Free text router ----------
async def message_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    if not text:
        return

    # 1) Offline first
    if await _answer_offline(update.message, text):
        return

    # 2) Online fallback
    if ask_kalyan and GEMINI_API_KEY:
        try:
            reply = ask_kalyan(text, api_key=GEMINI_API_KEY)
        except Exception:
            reply = "⚠️ បណ្ដាញមានបញ្ហា។ សូមសាកល្បងម្ដងទៀត!"
    else:
        reply = "🤖 សំណួរនេះមិនមានក្នុង Offline ទេ។ សូមប្រើ /ask ដើម្បីសួរតាម API!"
    await update.message.reply_text(reply)

# ---------- Boot ----------
async def run_bot():
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("schoolinfo", schoolinfo))
    app.add_handler(CommandHandler("ask", ask_cmd))
    app.add_handler(CommandHandler("ai", ask_cmd))  # alias
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_router))

    # Webhook (optional) or long polling (default)
    WEBHOOK_URL = os.getenv("WEBHOOK_URL", "").strip()
    WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "").strip()
    PORT = int(os.getenv("PORT", "8080"))
    PATH = "/" + (
        WEBHOOK_URL.split("/", 3)[-1] if WEBHOOK_URL and "/" in WEBHOOK_URL[8:] else "telegram"
    )

    if WEBHOOK_URL:
        print(f"🌐 Webhook on {PORT}{PATH}")
        await app.bot.set_webhook(
            url=WEBHOOK_URL,
            secret_token=WEBHOOK_SECRET or None,
            drop_pending_updates=True,
        )
        await app.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=PATH.lstrip("/"),
            webhook_url=WEBHOOK_URL,
            secret_token=WEBHOOK_SECRET or None,
        )
    else:
        print("🟢 Long-polling…")
        await app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    try:
        asyncio.run(run_bot())
    except RuntimeError:
        # Some hosts keep a loop alive; ignore close errors
        pass
