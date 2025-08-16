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

# --- Hosted envs (Render, etc.) sometimes reuse the loop
nest_asyncio.apply()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("kalyana")

# -----------------------------
# Helpers for parsing & matching
# -----------------------------
# Accept bullets -, •, – , —
_BULLET_RE = re.compile(r"^[\s\u200b]*([-•–—])\s*(.+)$")

# Strip trailing Khmer/Latin punctuation & spaces; drop common leading particles
_KH_PUNCT_RE = re.compile(r"[?។!…\s]+$")
def _clean_q(s: str) -> str:
    s = (s or "").strip()
    s = _KH_PUNCT_RE.sub("", s)
    s = re.sub(r"^(តើ|សូម)\s+", "", s)  # remove leading "តើ ", "សូម "
    return s

def _qid(text: str) -> str:
    return "q" + hashlib.sha1(text.encode("utf-8")).hexdigest()[:10]

def _extract_q_from_line(line: str) -> str | None:
    m = _BULLET_RE.match(line.strip())
    return m.group(2).strip() if m else None

# -----------------------------
# Optional online fallback
# -----------------------------
try:
    from handlers.kalyan import ask_kalyan  # def ask_kalyan(text: str, api_key: str) -> str
except Exception:
    ask_kalyan = None

# -----------------------------
# Build / refresh the deep-link map
# -----------------------------
QUESTION_MAP_KEY = "question_map"  # bot_data cache: { qid: {"q": str, "reply": str|None} }

def _resolve_offline_answer(q: str) -> str | None:
    """Find the best offline answer for a question string with normalization + fallback."""
    clean = _clean_q(q)
    bm = best_match(clean) or best_match(q)
    reply = bm.get("reply") if bm else None
    if reply:
        return reply
    # Try top suggestion then resolve it
    sugg = top_suggestions(clean, k=1) or top_suggestions(q, k=1)
    if sugg:
        bm = best_match(sugg[0])
        return bm.get("reply") if bm else None
    return None

def _rebuild_qmap(context: ContextTypes.DEFAULT_TYPE) -> dict:
    """(Re)parse the offline outline and precompute answers so deep links always work."""
    help_text = get_offline_help_text() or ""
    qmap: dict[str, dict] = {}
    for line in help_text.splitlines():
        q = _extract_q_from_line(line)
        if not q:
            continue
        qid = _qid(q)
        reply = _resolve_offline_answer(q)
        qmap[qid] = {"q": q, "reply": reply}
    context.application.bot_data[QUESTION_MAP_KEY] = qmap
    return qmap

# -----------------------------
# Answering helpers (typed text)
# -----------------------------
async def _answer_offline(msg_obj, user_text: str) -> bool:
    """Try offline answer first; if not found, suggest similar questions."""
    clean = _clean_q(user_text)
    m = best_match(clean) or best_match(user_text)
    if m and m.get("reply"):
        await msg_obj.reply_text(f"❓ {user_text}\n\n📜 {m['reply']}")
        return True

    sugg = top_suggestions(clean, k=4) or top_suggestions(user_text, k=4)
    if sugg:
        txt = "💡 សាកល្បងសំណួរទាំងនេះ (offline):\n" + "\n".join(f"• {s}" for s in sugg)
        await msg_obj.reply_text(txt)
        return True
    return False

# -----------------------------
# /ask (API / online)
# -----------------------------
async def ask_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

# -----------------------------
# /start (handles deep-link too)
# -----------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # If user clicked a deep link: /start <qid>
    if context.args:
        payload = (context.args[0] or "").strip()
        qmap = context.application.bot_data.get(QUESTION_MAP_KEY) or _rebuild_qmap(context)
        item = qmap.get(payload)
        if item:
            q = item.get("q") or "សំណួរ"
            reply = item.get("reply")
            if not reply:
                reply = _resolve_offline_answer(q)
                item["reply"] = reply  # memoize
            if reply:
                await update.message.reply_text(f"❓ {q}\n\n📜 {reply}")
            else:
                await update.message.reply_text(f"❓ {q}\n\n❌ មិនមានចម្លើយ Offline។")
            return

    # Normal welcome
    user = update.effective_user.first_name or "អ្នកប្រើ"
    txt = (
        f"🤖 ស្វាគមន៍ {user}\n\n"
        "អ្វីដែលខ្ញុំអាចធ្វើបាន:\n"
        "• ឆ្លើយសំណួរអំពីប្រធានបទណាមួយ\n"
        "• ព័ត៌មាន Offline អំពីសាលា NGS PREAKLEAP\n\n"
        "🔰 ពាក្យបញ្ជា:\n"
        "• /schoolinfo – បង្ហាញសំណួរ Offline (ចុចបាន)\n"
        "• /ask <សំណួរ> – សួរតាម API (Online)\n"
        "• /ai <សំណួរ> – ដូច /ask\n\n"
        "✏️ កល្យាណ បង្កើតដោយសិស្ស NGS PREAKLEAP\n"
        "📞 https://t.me/Cheukeat"
    )
    await update.message.reply_text(txt)

# -----------------------------
# /schoolinfo (blue deep-links only; NO buttons)
# -----------------------------
async def schoolinfo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot_username = context.bot.username
    help_text = get_offline_help_text() or ""

    # Build/refresh qmap so deep links always work even after restart
    qmap = _rebuild_qmap(context)

    # Replace bullet lines with deep-links (HTML)
    lines_out = []
    for line in help_text.splitlines():
        q = _extract_q_from_line(line)
        if q:
            qid = _qid(q)
            qmap_entry = qmap.get(qid)  # already filled by _rebuild_qmap
            if not qmap_entry:
                # safety net
                qmap[qid] = {"q": q, "reply": _resolve_offline_answer(q)}
            link = f"https://t.me/{bot_username}?start={qid}"
            lines_out.append(f'- <a href="{link}">{q}</a>')
        else:
            lines_out.append(line)

    await update.message.reply_text(
        "\n".join(lines_out),
        parse_mode="HTML",
        disable_web_page_preview=True,
    )

# -----------------------------
# Free text router
# -----------------------------
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

# -----------------------------
# Boot (long-polling)
# -----------------------------
async def run_bot():
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("schoolinfo", schoolinfo))
    app.add_handler(CommandHandler("ask", ask_cmd))
    app.add_handler(CommandHandler("ai", ask_cmd))  # alias
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_router))

    print("🟢 Long-polling…")
    await app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    try:
        asyncio.run(run_bot())
    except RuntimeError:
        # Some hosts keep a running loop; ignore close errors
        pass
