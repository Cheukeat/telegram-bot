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
if not TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKEN.endswith("ABCDEF..."):
    raise SystemExit("Please set TELEGRAM_BOT_TOKEN to your real bot token.")

# ================= Logging =================
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("kalyana")

# ============== Offline outline & Q/A ==============
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
- តើ Flipped Classroom មានអ្វី?

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
        "កល្យាណកើតនៅថ្ងៃទីប៉ុន្មាន?":
            "📅 កល្យាណកើតនៅថ្ងៃទី ១២-មេសា-២០០៥។",

        "កល្យាណត្រូវបានបង្កើតដោយនរណា?":
            "👤 កល្យាណត្រូវបានបង្កើតឡើងដោយក្រុមសិស្ស NGS-PL។",

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

        "អគារ ក មានអ្វីខ្លះ?":
            "🏢 អគារ ក:\n"
            "• 💻 ICT៖ 3\n"
            "• 📚 បណ្ណាល័យ៖ 1",

        "អគារ ខ មានអ្វីខ្លះ?":
            "🏢 អគារ ខ:\n"
            "• ⚗️ គីមីវិទ្យា៖ 5",

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

        "សិស្សចំនួនប៉ុន្មាន?":
            "👩‍🎓 2024-2025៖ 1470 នាក់\n"
            "👨‍🎓 2023-2024៖ 1320 នាក់",

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
        "• 📺 សិក្សាមេរៀននៅផ្ទះ → 👥 រៀនតាមក្រុម → 👨‍🏫 គ្រូជួយពន្យល់\n\n"
        "🔍 Inquiry-Based Learning (IBL)\n"
        "• ❓ សួរសំណួរ → 👀 សង្កេត → 🔬 ស្រាវជ្រាវ → 🧪 ពិសោធន៍\n\n"
        "🛠 Project-Based Learning\n"
        "• 📁 Project Basic & 🎯 Project-Based Learning → 🧵 ផលិតផលជាក់ស្តែង\n\n"
        "🧩 Problem-Based Learning\n"
        "• ⚠️ ចាប់ផ្តើមពីបញ្ហា → 🔍 ស្រាវជ្រាវ → 💡 ដំណោះស្រាយ\n\n"
        "🌟 5Es Model\n"
        "• 🎈 Engage → 🧭 Explore → 🗣 Explain → 🧠 Elaborate → 📊 Evaluate\n\n"
        "🤝 Collaborative Learning\n"
        "• 👥 ក្រុមតូចៗ → 🔄 រៀនពីគ្នា → 🏫 បរិយាកាសសកម្ម\n\n"
        "🎨 Teaching Strategies\n"
        "• 💭 Think-Pair-Share\n"
        "• 🧩 Jigsaw\n"
        "• 🗺 Mind Mapping\n"
        "• 🖼 Gallery Walk\n"
        "• 🗣 Debate\n"
        "• ☕️ World Café / 🔄 Carousel Brainstorm",

        "តើ Collaborative Learning មានអ្វី?":
            "🤝 Collaborative Learning:\n"
            "• ក្រុមតូចៗ មានតួនាទីច្បាស់\n"
            "• រៀនពីគ្នាទៅវិញទៅមក\n"
            "• បរិយាកាសសិក្សាសកម្ម និងចូលរួម",

        # --- Rules ---
        "តើអាចយកទូរស័ព្ទមកសាលាទេ?":
            "📵 មិនអនុញ្ញាតឲ្យយកទូរស័ព្ទចូលសាលា",

        "តើសិស្សអាចស្លៀកអាវខ្មៅបានទេ?":
            "👕 មិនអាចស្លៀកអាវខ្មៅ\n✅ ត្រូវស្លៀកអាវពណ៌ស",

        "តើមកក្រោយម៉ោង ៧:៣០ អាចចូលទេ?":
            "⏰ មកក្រោយម៉ោង ៧:៣០ មិនអនុញ្ញាតឱ្យចូល",

        # --- Exams ---
        "ត្រូវយកអ្វីចូលបន្ទប់ប្រឡង?":
        "📝 ត្រូវយក:\n"
        "• 🖊 ប៊ិក (ខ្មៅ ឬ ខៀវ)\n"
        "• 📏 បន្ទាត់\n"
        "• 🧲 ដែកឈាន\n"
        "• 🆔 ប័ណ្ណសម្គាល់ \n"
        "• 🧃 ទឹកផ្អែម (មិនអនុញ្ញាត)",

    "ច្បាប់សម្រាប់បេក្ខជន?":
        "🎓 បទបញ្ជាពេលប្រឡង:\n"
        "• ⏰ មកមុនម៉ោង ៦:៤៥ ព្រឹក / ១២:៤៥ រសៀល\n"
        "• 👕 ពាក់ឯកសណ្ឋានសិស្សឲ្យត្រឹមត្រូវ\n"
        "• 🖊 យកប៊ិក, 📏 បន្ទាត់, 🧲 ដែកឈាន\n"
        "• 🚪 មិនអាចចូលក្រោយចាប់ផ្តើម\n"
        "• 🎒 ហាមយកកាបូប, អាវុធ, ឧបករណ៍អេឡិចត្រូនិច\n"
        "• 📵 ហាមទូរស័ព្ទ\n"
        "• 📄 ហាមសំណៅឯកសារផ្សេងៗ\n"
        "• 🧼 ហាមទឹកលុប\n"
        "• 🚫 ហាមចម្លង ឬចែកចម្លើយ\n"
        "• 🔒 មិនអាចចេញពីបន្ទប់មុនពេលកំណត់\n"
        "• 🤫 រក្សាសុភាព និងសុចរិតភាព\n"
        "• 🧠 ប្រើចំណេះដឹងផ្ទាល់ខ្លួនដោយស្មោះត្រង់",
}
# ============== Khmer normalization & matching ==============
_ZWSP = "\u200b"
_TRAIL_PUNCT_RE = re.compile(r"[?\u17d4-\u17da.!៖។\s]+$")

def normalize_kh(text: str) -> str:
    s = unicodedata.normalize("NFKC", text or "")
    s = s.replace(_ZWSP, "").replace("\u00A0", " ").strip()
    s = _TRAIL_PUNCT_RE.sub("", s)
    s = re.sub(r"\s+", " ", s)
    return s

_NORM_QA = {normalize_kh(k): v for k, v in OFFLINE_QA.items()}

def best_match(user_text: str) -> Optional[dict]:
    qn = normalize_kh(user_text)
    if qn in _NORM_QA:
        original_q = next(q for q in OFFLINE_QA if normalize_kh(q) == qn)
        return {"question": original_q, "reply": OFFLINE_QA[original_q]}
    # simple containment score
    best_q, best_score = None, 0
    for q in OFFLINE_QA:
        n = normalize_kh(q)
        score = 0
        if qn and n and (qn in n or n in qn):
            score = min(len(qn), len(n)) / max(len(qn), len(n))
        if score > best_score:
            best_q, best_score = q, score
    if best_q and best_score >= 0.5:
        return {"question": best_q, "reply": OFFLINE_QA[best_q]}
    return None

def top_suggestions(user_text: str, k: int = 4) -> list[str]:
    qn = normalize_kh(user_text)
    scored = []
    for q in OFFLINE_QA:
        n = normalize_kh(q)
        common = len(set(qn.split()) & set(n.split()))
        total = len(set(qn.split()) | set(n.split())) or 1
        scored.append((common / total, q))
    scored.sort(reverse=True)
    return [q for s, q in scored[:k] if s > 0]

# ============== Deep-link helpers ==============
_BULLET_RE = re.compile(r"^[\s\u200b]*([-•–—])\s*(.+)$")

def _extract_q_from_line(line: str) -> Optional[str]:
    m = _BULLET_RE.match((line or "").strip())
    return m.group(2).strip() if m else None

def _qid(text: str) -> str:
    return "q" + hashlib.sha1(normalize_kh(text).encode("utf-8")).hexdigest()[:10]

def _questions_from_outline() -> list[str]:
    out: list[str] = []
    for line in OFFLINE_OUTLINE.splitlines():
        q = _extract_q_from_line(line)
        if q:
            out.append(q)
    return out

# ============== Reply helpers ==============
async def answer_offline(msg, question_text: str) -> bool:
    m = best_match(question_text)
    if m:
        await msg.reply_text(f"❓ {m['question']}\n\n{m['reply']}")
        return True
    sugg = top_suggestions(question_text, k=4)
    if sugg:
        await msg.reply_text("💡 សាកល្បងសំណួរទាំងនេះ (offline):\n" + "\n".join(f"• {s}" for s in sugg))
        return True
    return False

# ============== /ask (Gemini) ==============
_GENAI_READY = False
try:
    if GEMINI_API_KEY:
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)
        _model = genai.GenerativeModel("gemini-1.5-flash")
        _GENAI_READY = True
except Exception as _e:
    log.warning("Gemini not initialized: %s", _e)

async def ask_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _GENAI_READY:
        await update.message.reply_text(
            "⚠️ /ask មិនអាចប្រើបានទេ ព្រោះ GEMINI_API_KEY មិនបានកំណត់។\n"
            "ដាក់ env var GEMINI_API_KEY ហើយចាប់ផ្តើមឡើងវិញ។"
        )
        return

    parts = context.args or []
    if parts:
        prompt = " ".join(parts).strip()
    elif update.message and update.message.reply_to_message and update.message.reply_to_message.text:
        prompt = update.message.reply_to_message.text.strip()
    else:
        await update.message.reply_text(
            "🧠 ឧទាហរណ៍៖\n"
            "• /ask អ្វីទៅជា AI?\n"
            "• ឬ reply ទៅលើសារណាមួយ ហើយវាយ /ask",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    try:
        resp = _model.generate_content(prompt)
        answer = (resp.text or "").strip() or "❌ API មិនឆ្លើយតប។"
    except Exception as e:
        answer = f"⚠️ កំហុសពេលហៅ API: {e}"

    await update.message.reply_text(f"❓ {prompt}\n\n{answer}")

# ============== Handlers ==============
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

        qtext = " ".join(args)
        if await answer_offline(update.message, qtext):
            return
        await update.message.reply_text("❌ មិនមានចម្លើយ Offline។")
        return

    user = update.effective_user.first_name or "អ្នកប្រើ"
    await update.message.reply_text(
        f"🤖 ស្វាគមន៍ {user}\n\n"
        "អ្វី​ដែល​ខ្ញុំ​អាច​ធ្វើ​បាន:\n"
        "• ✅ ឆ្លើយសំណួរ Offline ដែលជាព័ត៌មានទាក់ទងនិងសាលា NGS PREAKLEAP\n"
        "• 📚 សំណួរដែលអាចសួរបាននៅពេល Offline (ចុច /schoolinfo)\n"
        "• ❓ សំណួរដែលមិនមានក្នុង Offline អាចសួរតាម API (Gemini)\n"
        "• 🌐 សួរតាម API ដើម្បីទទួលបានព័ត៌មានថ្មីៗ\n"
        "• 🚀💬 /ask <សំណួរ> – សួរតាម API (ជាជម្រើស)\n\n"

        "🔰 ពាក្យបញ្ជា:\n"
        "• /schoolinfo – បង្ហាញសំណួរ Offline (ចុចតំណខៀវ)\n"
        "• /ask <សំណួរ> – សួរតាម API (ជាជម្រើស)\n\n"
        "✏️ កល្យាណ បង្កើតដោយសិស្ស NGS PREAKLEAP\n"
        "📞 https://t.me/Cheukeat"
    )

async def schoolinfo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot_username = context.bot.username
    lines_out: list[str] = []
    for line in OFFLINE_OUTLINE.splitlines():
        q = _extract_q_from_line(line)
        if q:
            qid = _qid(q)
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
    text = (update.message.text or "").strip()
    if text:
        if await answer_offline(update.message, text):
            return
        await update.message.reply_text("🤖 សំណួរនេះមិនមានក្នុង Offline ទេ។ សូមសាកល្បងពាក្យផ្សេងៗ!")

# ============== Boot (no asyncio plumbing) ==============
def main():
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("schoolinfo", schoolinfo))
    app.add_handler(CommandHandler("ask", ask_cmd)) 
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_router))

    log.info("🟢 Starting long-polling…")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
