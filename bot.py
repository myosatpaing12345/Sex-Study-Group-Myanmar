from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

TOKEN = "8905518813:AAFTbzsu9BWXa4AokyEr0oPBCEZpng7ZXnA"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📝 Register", callback_data="register")]
    ]

    await update.message.reply_text(
        "🔞 Sex Study Group Myanmar\n\n"
        "Welcome!\n\n"
        "This community is for adults (18+) only.\n\n"
        "Please register to continue.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "register":
        keyboard = [
            [InlineKeyboardButton("✅ Yes, I'm 18+", callback_data="age_yes")],
            [InlineKeyboardButton("❌ No", callback_data="age_no")]
        ]

        await query.edit_message_text(
            "🔞 Age Verification\n\n"
            "Are you 18 years old or above?",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif query.data == "age_yes":
        keyboard = [
            [InlineKeyboardButton("👨 Male", callback_data="male")],
            [InlineKeyboardButton("👩 Female", callback_data="female")],
            [InlineKeyboardButton("⚪ Non-binary", callback_data="nonbinary")]
        ]

        await query.edit_message_text(
            "👤 Choose Your Gender",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif query.data == "age_no":
        await query.edit_message_text(
            "Sorry, this community is only for adults (18+)."
        )

app = Application.builder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(button))

app.run_polling()
