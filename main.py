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
        "អ្វី​ដែល​ខ្ញុំ​អាច​ធ្វើ​បាន:\n"
        "• 🔹 ចុច /schoolinfo ដើម្បីមើលសំណួរ Offline (ជា link ពណ៌ខៀវ)\n"
        "• 🔹 វាយសារ​ធម្មតា — ខ្ញុំនឹងឆ្លើយតាម Gemini API (Online)\n\n"
        "🔰 ពាក្យបញ្ជា:\n"
        "• /start — បង្ហាញសារ​ស្វាគមន៍\n"
        "• /schoolinfo — បង្ហាញសំណួរ Offline (ចុចលើតំណខៀវដើម្បីឃើញចម្លើយ)\n\n"
        "✏️ កល្យាណ បង្កើតដោយសិស្ស NGS PREAKLEAP\n"
        "📞 https://t.me/Cheukeat"
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

        path = f"telegram/{TELEGRAM_BOT_TOKEN}"  
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
