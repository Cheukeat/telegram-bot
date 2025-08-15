# handlers/school_query.py
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from utils.matcher import best_match, top_suggestions, related_suggestions_for_key

async def handle_school_query(update, context):
    text = update.message.text.strip()
    match = best_match(text)

    if match:
        # 1) send the answer
        await update.message.reply_text(match["reply"])

        # 2) offer related follow-ups (clickable)
        related = related_suggestions_for_key(match["key"], k=4)
        if related:
            kb = [[InlineKeyboardButton(q, callback_data=q)] for q in related]
            await update.message.reply_text("🔎 សំណួរដែលពាក់ព័ន្ធ:", reply_markup=InlineKeyboardMarkup(kb))
        return

    # fallback (unsure): show suggestions
    sugg = top_suggestions(text, k=4)
    if sugg:
        kb = [[InlineKeyboardButton(s, callback_data=s)] for s in sugg]
        await update.message.reply_text("🤔 ខ្ញុំគិតថាអ្នកអាចសួរអំពី:", reply_markup=InlineKeyboardMarkup(kb))
    else:
        await update.message.reply_text("❌ ខ្ញុំមិនទាន់យល់សំណួរនេះទេ។ សូមសាកល្បងសរសេរឡើងវិញ!")
