# main.py
import os
import re
import hashlib
import logging
import unicodedata
from typing import Optional

from dotenv import load_dotenv
load_dotenv()

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, filters
)

# ================= ENV =================
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
GEMINI_API_KEY     = os.getenv("GEMINI_API_KEY", "").strip()
WEBHOOK_URL        = (os.getenv("WEBHOOK_URL") or "").strip()    # optional (Render)
WEBHOOK_SECRET     = (os.getenv("WEBHOOK_SECRET") or "").strip() # optional (Render)
PORT               = int(os.getenv("PORT", "8080"))

if not TELEGRAM_BOT_TOKEN:
    raise SystemExit("Please set TELEGRAM_BOT_TOKEN to your real bot token.")

# ================= Logging =================
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("kalyana")

# ================= Offline outline & Q/A =================
OFFLINE_OUTLINE = """📚 សំណួរដែលអ្នកអាចសួរបាននៅពេល Offline:

👨‍💼/👩‍💼 អំពីគ្រូ និង នាយក
- នាយកសាលា NGS-PL ជានរណា?
- នាយិការងឱ្យអ្វីខ្លះ?
- តួនាទីនាយករង?

🎓 កល្យាណ
- កល្យាណកើតនៅថ្ងៃទីប៉ុន្មាន?
- កល្យាណត្រូវបានបង្កើតដោយនរណា?
- តើអ្នកណាដឹកនាំក្រុមកល្យាណ?

🏫 ព័ត៌មានអគារ និងសាលា
- ប្រវត្តិសាលា NGS-PL?
- អគារ ក មានអ្វីខ្លះ?
- អគារ ខ មានអ្វីខ្លះ?
- អគារ គ មានអ្វីខ្លះ?
- អគារ ឃ មានអ្វីខ្លះ?
- អគារ​ ង មានអ្វីខ្លះ?
- សិស្សចំនួនប៉ុន្មាន?
- ចំនួនគ្រូតាមមុខវិជ្ជា?

📋 វិធីបង្រៀន
- វិធីសាស្ត្របង្រៀន?
- តើ Collaborative Learning មានអ្វី?

🛡 បទបញ្ជា និងវិន័យ
- តើអាចយកទូរស័ព្ទមកសាលាទេ?
- តើសិស្សអាចស្លៀកអាវខ្មៅបានទេ?
- តើមកក្រោយម៉ោង ៧:៣០ អាចចូលទេ?

🧪 ព័ត៌មានប្រឡង
- ត្រូវយកអ្វីចូលបន្ទប់ប្រឡង?
- ច្បាប់សម្រាប់បេក្ខជន?

💡 Narirat អាចឆ្លើយសំណួរទាំងនេះបាន ទោះបី API អត់ដំណើរការ!
"""

OFFLINE_QA = {
    # --- Admin/Staff ---
    "នាយកសាលា NGS-PL ជានរណា?":
        "👨‍💼 លោក នាយក ឆុំ សុភក្តិ\n"
        "• 🗂 ទទួលបន្ទុកការងាររួម\n"
        "• 🔒 អធិការកិច្ចអចិន្ត្រៃយ៍\n"
        "• 📡 ទំនាក់ទំនង",

    "នាយិការងឱ្យអ្វីខ្លះ?":
        "👩‍💼 លោកស្រី នាយិការង វ៉ៅ សំអូន\n"
        "• 🛠 បច្ចេកទេស\n"
        "• 🏫 បឋមភូមិ\n"
        "• 🎨 គេហវិជ្ជា និងសិល្បៈ\n"
        "• 🛡 សន្តិសុខ, វិន័យ, បរិស្ថាន\n"
        "• 📋 អធិការកិច្ចគ្រប់មុខ",

    "តួនាទីនាយករង":
        "👨‍💼 លោក នាយករង យក់ សោភ័ណ\n"
        "• 📂 រដ្ឋបាល\n"
        "• 🏛 ទុតិយភូមិ\n"
        "• 💰 គណនេយ្យ, បេឡា\n"
        "• 🏅 កីឡា, កសិកម្ម, រោងជាង\n"
        "• 💻 ព័ត៌មានវិទ្យា\n"
        "• 🧑‍⚕️ កាកបាទក្រហម-កាយរឹត\n"
        "• 🛡 សន្តិសុខ និងវិន័យ",

    # --- Personal Info ---
    "កល្យាណកើតនៅថ្ងៃទីប៉ុន្មាន?": "📅 កល្យាណកើតនៅថ្ងៃទី ១២-មេសា-២០០៥។",
    "កល្យាណត្រូវបានបង្កើតដោយនរណា?": "👤 កល្យាណត្រូវបានបង្កើតឡើងដោយក្រុមសិស្ស NGS-PL។",
    "តើអ្នកណាដឹកនាំក្រុមកល្យាណ?":
        "👥 អ្នកដឹកនាំក្រុមកល្យាណមានដូចជា៖\n"
        "👨‍🏫 លោកគ្រូអ៊ុត ណង\n"
        "👨‍🏫 លោកគ្រូផល អេងលី\n"
        "👨‍🏫 សម្របសម្រួលដោយលោកគ្រូ៖ សំ មករា",

    # --- School Info ---
    "ប្រវត្តិសាលា NGS-PL?":
        "📜 សាលាត្រូវបានបង្កើតឡើងក្នុងឆ្នាំ ១៩៨០ ជាអនុវិទ្យាល័យ ព្រែកលៀប។\n"
        "📅 ថ្ងៃ ១២-មេសា-២០០៥ ក្រសួងអប់រំ យុវជន និងកីឡា បានប្រកាសជាវិទ្យាល័យ។\n"
        "🚀 ឆ្នាំសិក្សា ២០១៧-២០១៨ ចាប់ផ្តើមកម្មវិធីសាលាជំនាន់ថ្មី (ថ្នាក់ទី ៧ និង ៨)\n"
        "🎯 គោលបំណង៖ កែលម្អគុណភាពអប់រំនៅកម្ពុជា",

    "អគារ ក មានអ្វីខ្លះ?": "🏢 អគារ ក:\n• 💻 ICT៖ 3\n• 📚 បណ្ណាល័យ៖ 1",
    "អគារ ខ មានអ្វីខ្លះ?": "🏢 អគារ ខ:\n• ⚗️ គីមីវិទ្យា៖ 5",
    "អគារ គ មានអ្វីខ្លះ?":
        "🏢 អគារ គ:\n"
        "• ⚛️ រូបវិទ្យា៖ 5\n"
        "• 🗃 ទីចាត់ការ៖ 1\n"
        "• 🏥 បន្ទប់ពេទ្យ៖ 1\n"
        "• 🧪 បន្ទប់ប្រីកក្សា៖ 1",
    "អគារ ឃ មានអ្វីខ្លះ?":
        "🏢 អគារ ឃ:\n"
        "• ➗ គណិតវិទ្យា៖ 7\n"
        "• 📝 ភាសាខ្មែរ៖ 7\n"
        "• 🏺 ប្រវត្តិវិទ្យា៖ 2\n"
        "• 🌍 ភូមិវិទ្យា៖ 2\n"
        "• 🌋 ផែនដីវិទ្យា៖ 1\n"
        "• 🧭 សិលធម៌ពលរដ្ឋ៖ 2",
    "អគារ ង មានអ្វីខ្លះ?":
        "🏢 អគារ ង:\n"
        "• 🧬 ជីវវិទ្យា៖ 5\n"
        "• 🇬🇧 អង់គ្លេស៖ 7\n"
        "• 🇫🇷 បារាំង៖ 1\n"
        "• 🇨🇳 ចិន៖ 1\n"
        "• 🏛 បន្ទប់ប្រជុំតូច៖ 1",
    "សិស្សចំនួនប៉ុន្មាន?": "👩‍🎓 2024-2025៖ 1470 នាក់\n👨‍🎓 2023-2024៖ 1320 នាក់",
    "ចំនួនគ្រូតាមមុខវិជ្ជា?":
        "👩‍🏫 ចំនួនគ្រូតាមមុខវិជ្ជា៖\n"
        "• ➗ គណិតវិទ្យា៖ 15\n"
        "• 📝 ភាសាខ្មែរ៖ 12\n"
        "• ⚛️ រូបវិទ្យា៖ 9\n"
        "• ⚗️ គីមីវិទ្យា៖ 9\n"
        "• 💻 ព័ត៌មានវិទ្យា៖ 6\n"
        "• 🧭 សិលធម៌-ពលរដ្ឋ៖ 5\n"
        "• 🧬 ជីវវិទ្យា៖ 9\n"
        "• 🇬🇧 អង់គ្លេស៖ 9\n"
        "• 🌍 ភូមិវិទ្យា៖ 4\n"
        "• 🏺 ប្រវត្តិវិទ្យា៖ 4\n"
        "• 🌋 ផែនដីវិទ្យា៖ 2\n"
        "• 🧑‍🎓 បំណិនជីវិត៖ 1\n"
        "• 🏃‍♂️ អប់រំកាយ៖ 1\n"
        "• 🇨🇳 ភាសាចិន៖ 2\n"
        "• 🇫🇷 ភាសាបារាំង៖ 1\n\n"
        "📊 សរុបគ្រូទាំងអស់៖ 89 នាក់",

    # --- Teaching ---
    "វិធីសាស្ត្របង្រៀន?":
        "📚 វិធីសាស្ត្របង្រៀន:\n"
        "🔄 Flipped Classroom\n"
        "🔍 Inquiry-Based Learning\n"
        "🛠 Project-Based Learning\n"
        "🧩 Problem-Based Learning\n"
        "🌟 5Es Model\n"
        "🤝 Collaborative Learning\n"
        "🎨 Teaching Strategies (Think-Pair-Share, Jigsaw, Mind Map, Gallery Walk, Debate, World Café)",

    "តើ Collaborative Learning មានអ្វី?":
        "🤝 Collaborative Learning:\n• ក្រុមតូចៗ មានតួនាទីច្បាស់\n• រៀនពីគ្នាទៅវិញទៅមក\n• បរិយាកាសសកម្ម",

    # --- Rules ---
    "តើអាចយកទូរស័ព្ទមកសាលាទេ?": "📵 មិនអនុញ្ញាតឲ្យយកទូរស័ព្ទចូលសាលា",
    "តើសិស្សអាចស្លៀកអាវខ្មៅបានទេ?": "👕 មិនអាចស្លៀកអាវខ្មៅ\n✅ ត្រូវស្លៀកអាវពណ៌ស",
    "តើមកក្រោយម៉ោង ៧:៣០ អាចចូលទេ?": "⏰ មកក្រោយម៉ោង ៧:៣០ មិនអនុញ្ញាតឱ្យចូល",

    # --- Exams ---
    "ត្រូវយកអ្វីចូលបន្ទប់ប្រឡង?":
        "📝 ត្រូវយកប៊ិក/បន្ទាត់/ដែកឈាន និងប័ណ្ណសម្គាល់ (មិនអនុញ្ញាតទឹកផ្អែម)",
    "ច្បាប់សម្រាប់បេក្ខជន?":
        "🎓 មកទាន់ពេល ពាក់ឯកសណ្ឋានត្រឹមត្រូវ ហាមទូរស័ព្ទ សម្ងាត់ និងសុចរិតភាព",
}

# ================= Khmer normalization =================
_ZWSP = "\u200b"
_TRAIL_PUNCT_RE = re.compile(r"[?\u17d4-\u17da.!៖។\s]+$")

def normalize_kh(text: str) -> str:
    s = unicodedata.normalize("NFKC", text or "")
    s = s.replace(_ZWSP, "").replace("\u00A0", " ").strip()
    s = _TRAIL_PUNCT_RE.sub("", s)
    s = re.sub(r"\s+", " ", s)
    return s

# map for deep-link answers
def _qid(text: str) -> str:
    return "q" + hashlib.sha1(normalize_kh(text).encode("utf-8")).hexdigest()[:10]

_BULLET_RE = re.compile(r"^[\s\u200b]*([-•–—])\s*(.+)$")
def _extract_q_from_line(line: str) -> Optional[str]:
    m = _BULLET_RE.match((line or "").strip());  return m.group(2).strip() if m else None

def _questions_from_outline() -> list[str]:
    out: list[str] = []
    for line in OFFLINE_OUTLINE.splitlines():
        q = _extract_q_from_line(line)
        if q: out.append(q)
    return out

# ================= Offline reply helper (only for deep-links) =================
async def answer_offline(msg, question_text: str) -> bool:
    qn = normalize_kh(question_text)
    # exact match
    for q, a in OFFLINE_QA.items():
        if normalize_kh(q) == qn:
            await msg.reply_text(f"❓ {q}\n\n{a}")
            return True
    return False

# ================= Gemini (free-text) =================
_GENAI_READY = False
try:
    if GEMINI_API_KEY:
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)
        _model = genai.GenerativeModel("gemini-1.5-flash")
        _GENAI_READY = True
except Exception as _e:
    log.warning("Gemini not initialized: %s", _e)

# ================= Handlers =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # deep-link payload ?start=<qid>
    args = context.args or []
    if args:
        payload = (args[0] or "").strip()
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
        "អ្វី​ដែល​ខ្ញុំ​អាច​ធ្វើ​បាន:\n"
        "• ✅ ចុច /schoolinfo ដើម្បីមើលសំណួរ Offline (ចុចបាន)\n"
        "• 🌐 វាយសារ​ធម្មតា — ខ្ញុំនឹងឆ្លើយតាម Gemini API\n\n"
        "🔰 ពាក្យបញ្ជា: /start, /schoolinfo"
    )

async def schoolinfo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot_username = context.bot.username
    lines_out: list[str] = []
    for line in OFFLINE_OUTLINE.splitlines():
        q = _extract_q_from_line(line)
        if q:
            qid = _qid(q)
            # deep link that works on mobile + desktop clients
            link = f"tg://resolve?domain={bot_username}&start={qid}"
            lines_out.append(f'- <a href="{link}">{q}</a>')
        else:
            lines_out.append(line)

    await update.message.reply_text(
        "\n".join(lines_out),
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True,
    )

async def text_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Any normal text → Gemini API (no /ask)."""
    text = (update.message.text or "").strip()
    if not text:
        return
    if not _GENAI_READY:
        await update.message.reply_text("⚠️ GEMINI_API_KEY មិនបានកំណត់ ឬ មិនត្រឹមត្រូវ។")
        return
    try:
        resp = _model.generate_content(text)
        answer = (resp.text or "").strip() or "❌ API មិនឆ្លើយតប។"
    except Exception as e:
        answer = f"⚠️ កំហុសពេលហៅ API: {e}"
    await update.message.reply_text(answer)

# ================= Boot: webhook if configured, else polling =================
async def run_bot():
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("schoolinfo", schoolinfo))
    # NOTE: no /ask command anymore
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_router))

    if WEBHOOK_URL:
        final_url = WEBHOOK_URL
        if not final_url.endswith(TELEGRAM_BOT_TOKEN):
            if not final_url.endswith("/"):
                final_url += "/"
            final_url += TELEGRAM_BOT_TOKEN

        log.info("🌐 Setting webhook: %s", final_url)
        await app.bot.set_webhook(
            url=final_url,
            secret_token=(WEBHOOK_SECRET or None),
            drop_pending_updates=True,
        )
        url_path = final_url.split("/", 3)[-1]
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
    asyncio.run(run_bot())