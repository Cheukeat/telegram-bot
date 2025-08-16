# main.py  (python-telegram-bot v21.x)
import os
import re
import hashlib
import logging
from typing import Optional

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, filters
)

from config import TELEGRAM_BOT_TOKEN, GEMINI_API_KEY
from utils.matcher import best_match, top_suggestions, get_offline_help_text

# ---------------- Logging ----------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("kalyana")

# -------- Bullet parsing for outline -----
_BULLET_RE = re.compile(r"^[\s\u200b]*([-•–—])\s*(.+)$")
def _extract_q_from_line(line: str) -> Optional[str]:
    m = _BULLET_RE.match(line.strip())
    return m.group(2).strip() if m else None

def _qid(text: str) -> str:
    return "q" + hashlib.sha1(text.encode("utf-8")).hexdigest()[:10]

def _all_questions() -> list[str]:
    text = get_offline_help_text() or ""
    out: list[str] = []
    for line in text.splitlines():
        q = _extract_q_from_line(line)
        if q:
            out.append(q)
    return out

# ------------- Optional online -----------
try:
    from handlers.kalyan import ask_kalyan  # def ask_kalyan(text: str, api_key: str) -> str
except Exception:
    ask_kalyan = None

# ------------- Helpers -------------------
async def answer_offline(msg, question_text: str) -> bool:
    """
    Try to answer from the offline brain. Return True if replied/suggested.
    """
    m = best_match(question_text)
    if m:
        await msg.reply_text(f"❓ {question_text}\n\n{m['reply']}")
        return True

    sugg = top_suggestions(question_text, k=4)
    if sugg:
        txt = "💡 សាកល្បងសំណួរទាំងនេះ (offline):\n" + "\n".join(f"• {s}" for s in sugg)
        await msg.reply_text(txt)
        return True

    return False

# ------------- Commands ------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handles /start and deep-links /start <qid>.
    """
    args = context.args or []
    if args:
        payload = args[0].strip()

        # deep-link id?
        if payload.startswith("q") and len(payload) == 11:
            for q in _all_questions():
                if _qid(q) == payload:
                    if await answer_offline(update.message, q):
                        return
                    await update.message.reply_text(f"❓ {q}\n\n❌ មិនមានចម្លើយ Offline។")
                    return

        # If not a qid, treat as free question text
        qtext = " ".join(args)
        if await answer_offline(update.message, qtext):
            return
        await update.message.reply_text("❌ មិនមានចម្លើយ Offline។")
        return

    # Normal welcome
    user = update.effective_user.first_name or "អ្នកប្រើ"
    txt = (
        f"🤖 ស្វាគមន៍ {user}\n\n"
        "អ្វីដែលខ្ញុំអាចធ្វើបាន:\n"
        "• ឆ្លើយសំណួរអំពីប្រធានបទណាមួយ (Offline first)\n"
        "• ព័ត៌មាន Offline អំពីសាលា NGS PREAKLEAP\n\n"
        "🔰 ពាក្យបញ្ជា:\n"
        "• /start\n"
        "• /schoolinfo – បង្ហាញសំណួរ Offline ជា link ពណ៌ខៀវ (ចុចបាន)\n"
        "• /ask <សំណួរ> – សួរតាម API (Online) [ជាជម្រើស]\n\n"
        "✏️ កល្យាណ បង្កើតដោយសិស្ស NGS PREAKLEAP\n"
        "📞 https://t.me/Cheukeat"
    )
    await update.message.reply_text(txt)

async def schoolinfo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Send the offline outline with BLUE clickable deep-links.
    Clicking opens /start <qid>, then we answer that question.
    """
    bot_username = context.bot.username
    help_text = get_offline_help_text() or ""

    lines_out: list[str] = []
    for line in help_text.splitlines():
        q = _extract_q_from_line(line)
        if q:
            qid = _qid(q)
            link = f"https://t.me/{bot_username}?start={qid}"
            lines_out.append(f'- <a href="{link}">{q}</a>')
        else:
            lines_out.append(line)

    await update.message.reply_text(
        "\n".join(lines_out),
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True,
    )

async def ask_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /ask <question> – force online answer (if API configured).
    """
    if not (ask_kalyan and GEMINI_API_KEY):
        await update.message.reply_text("⚠️ API មិនបានកំណត់ (GEMINI_API_KEY/ask_kalyan មិនមាន).")
        return

    parts = context.args or []
    if parts:
        prompt = " ".join(parts).strip()
    elif update.message and update.message.reply_to_message and update.message.reply_to_message.text:
        prompt = update.message.reply_to_message.text.strip()
    else:
        await update.message.reply_text(
            "🧠 ប្រើឧទាហរណ៍៖\n"
            "• /ask អ្វីទៅជា AI?\n"
            "• ឬ reply ទៅលើសារណាមួយ ហើយវាយ /ask",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    try:
        reply = ask_kalyan(prompt, api_key=GEMINI_API_KEY) or "❌ API មិនឆ្លើយតប។"
    except Exception as e:
        reply = f"⚠️ កំហុសពេលហៅ API: {e}"

    await update.message.reply_text(f"❓ {prompt}\n\n{reply}")

async def message_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    if not text:
        return

    if await answer_offline(update.message, text):
        return

    if ask_kalyan and GEMINI_API_KEY:
        try:
            reply = ask_kalyan(text, api_key=GEMINI_API_KEY)
        except Exception:
            reply = "⚠️ បណ្ដាញមានបញ្ហា។ សូមសាកល្បងម្ដងទៀត!"
    else:
        reply = "🤖 សំណួរនេះមិនមានក្នុង Offline ទេ។ សូមប្រើ /ask ដើម្បីសួរតាម API!"
    await update.message.reply_text(reply)

# ------------- Boot (Render webhook or polling) -------------
async def run_bot():
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("schoolinfo", schoolinfo))
    app.add_handler(CommandHandler("ask", ask_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_router))

    WEBHOOK_URL = (os.getenv("WEBHOOK_URL") or "").strip()  # e.g. https://<service>.onrender.com/telegram
    WEBHOOK_SECRET = (os.getenv("WEBHOOK_SECRET") or "").strip()
    PORT = int(os.getenv("PORT", "8080"))

    if WEBHOOK_URL:
        # If the URL does not end with the bot token, append it (Telegram best practice)
        final_url = WEBHOOK_URL
        if not final_url.endswith(TELEGRAM_BOT_TOKEN):
            if not final_url.endswith("/"):
                final_url += "/"
            final_url += TELEGRAM_BOT_TOKEN

        log.info("🌐 Setting webhook to %s", final_url)
        await app.bot.set_webhook(
            url=final_url,
            secret_token=(WEBHOOK_SECRET or None),
            drop_pending_updates=True,
        )

        # The path (route) is whatever comes after your domain.
        url_path = final_url.split("/", 3)[-1]  # includes the token path
        log.info("🚀 Running webhook on 0.0.0.0:%s path=%s", PORT, url_path)
        await app.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=url_path,
            webhook_url=final_url,
            secret_token=(WEBHOOK_SECRET or None),
        )
    else:
        log.info("🟢 Long-polling…")
        await app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    import asyncio
    try:
        asyncio.run(run_bot())
    except RuntimeError:
        # Some hosts reuse a running loop — ignore close errors
        pass
