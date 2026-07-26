import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

# Define Conversation States for Registration
ASK_AGE_INPUT, LOCATION, PROFILE_NAME, INTEREST, PHOTO = range(5)

# Define Conversation States for Editing Profile
EDIT_CHOICE, EDIT_VALUE = range(5, 7)

TOKEN = "YOUR_NEW_BOT_TOKEN_HERE"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📝 Register", callback_data="register")],
        [InlineKeyboardButton("✏️ Edit Profile", callback_data="edit_profile")]
    ]

    await update.message.reply_text(
        "🔞 Sex Study Group Myanmar\n\n"
        "Welcome!\n\n"
        "This community is for adults (18+) only.\n\n"
        "Please register or manage your profile to continue.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
            [InlineKeyboardButton("👨 Male", callback_data="gender_male")],
            [InlineKeyboardButton("👩 Female", callback_data="gender_female")],
            [InlineKeyboardButton("⚪ Non-binary", callback_data="gender_nonbinary")]
        ]

        await query.edit_message_text(
            "👤 Choose Your Gender",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif query.data == "age_no":
        await query.edit_message_text(
            "Sorry, this community is only for adults (18+)."
        )

# --- Registration Flow ---

async def handle_gender_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    selected_gender = query.data.replace("gender_", "")
    context.user_data['gender'] = selected_gender

    await query.edit_message_text(
        f"Selected Gender: {selected_gender.capitalize()}\n\n"
        "Please enter your exact age (e.g., 22):"
    )
    return ASK_AGE_INPUT

async def receive_age_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        age = int(update.message.text)
        if age < 18:
            await update.message.reply_text("You must be at least 18 years old to proceed.")
            return ASK_AGE_INPUT

        context.user_data['age'] = age

        location_btn = KeyboardButton(text="📍 Share Current Location", request_location=True)
        markup = ReplyKeyboardMarkup([[location_btn]], resize_keyboard=True, one_time_keyboard=True)

        await update.message.reply_text(
            "Please share your location to find nearby matches, or type your city name:",
            reply_markup=markup
        )
        return LOCATION

    except ValueError:
        await update.message.reply_text("Please enter a valid numerical age (e.g., 22).")
        return ASK_AGE_INPUT

async def receive_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.location:
        context.user_data['lat'] = update.message.location.latitude
        context.user_data['lng'] = update.message.location.longitude
        context.user_data['city'] = "GPS Location"
    else:
        context.user_data['city'] = update.message.text
        context.user_data['lat'] = None
        context.user_data['lng'] = None

    await update.message.reply_text(
        "Enter your Profile Display Name:",
        reply_markup=ReplyKeyboardRemove()
    )
    return PROFILE_NAME

async def receive_profile_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['profile_name'] = update.message.text

    keyboard = [["Men", "Women", "Everyone"]]
    markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)

    await update.message.reply_text(
        "Choose your interest:",
        reply_markup=markup
    )
    return INTEREST

async def receive_interest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['interest'] = update.message.text

    await update.message.reply_text(
        "Please upload your Profile Photo or Video:",
        reply_markup=ReplyKeyboardRemove()
    )
    return PHOTO

async def receive_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.photo:
        file_id = update.message.photo[-1].file_id
    elif update.message.video:
        file_id = update.message.video.file_id
    else:
        await update.message.reply_text("Please send a valid photo or video.")
        return PHOTO

    context.user_data['photo_id'] = file_id

    print("User Registration Data:", context.user_data)

    await update.message.reply_text(
        "🎉 Profile registration completed successfully!\n"
        "Use /find to discover nearby matches or /edit to modify your profile."
    )
    return ConversationHandler.END

# --- Edit Profile Flow ---

async def start_edit_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("✏️ Name", callback_data="field_profile_name"), InlineKeyboardButton("✏️ Age", callback_data="field_age")],
        [InlineKeyboardButton("✏️ Interest", callback_data="field_interest"), InlineKeyboardButton("✏️ Location", callback_data="field_location")],
        [InlineKeyboardButton("🖼️ Photo/Video", callback_data="field_photo")]
    ]
    markup = InlineKeyboardMarkup(keyboard)

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text("Select the field you want to edit:", reply_markup=markup)
    else:
        await update.message.reply_text("Select the field you want to edit:", reply_markup=markup)
        
    return EDIT_CHOICE

async def handle_edit_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    selected_field = query.data.replace("field_", "")
    context.user_data['editing_field'] = selected_field

    if selected_field == "profile_name":
        await query.edit_message_text("Enter your new Display Name:")
    elif selected_field == "age":
        await query.edit_message_text("Enter your new Age:")
    elif selected_field == "interest":
        keyboard = [["Men", "Women", "Everyone"]]
        markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
        await context.bot.send_message(chat_id=query.message.chat_id, text="Choose your new interest:", reply_markup=markup)
    elif selected_field == "location":
        location_btn = KeyboardButton(text="📍 Share Current Location", request_location=True)
        markup = ReplyKeyboardMarkup([[location_btn]], resize_keyboard=True, one_time_keyboard=True)
        await context.bot.send_message(chat_id=query.message.chat_id, text="Share your new location or type your city name:", reply_markup=markup)
    elif selected_field == "photo":
        await query.edit_message_text("Please upload a new photo or video:")

    return EDIT_VALUE

async def receive_edit_value(update: Update, context: ContextTypes.DEFAULT_TYPE):
    field = context.user_data.get('editing_field')

    if field == "age":
        try:
            age = int(update.message.text)
            if age < 18:
                await update.message.reply_text("You must be at least 18 years old.")
                return EDIT_VALUE
            context.user_data['age'] = age
        except ValueError:
            await update.message.reply_text("Please enter a valid number for age.")
            return EDIT_VALUE

    elif field == "location":
        if update.message.location:
            context.user_data['lat'] = update.message.location.latitude
            context.user_data['lng'] = update.message.location.longitude
            context.user_data['city'] = "GPS Location"
        else:
            context.user_data['city'] = update.message.text

    elif field == "photo":
        if update.message.photo:
            context.user_data['photo_id'] = update.message.photo[-1].file_id
        elif update.message.video:
            context.user_data['photo_id'] = update.message.video.file_id
        else:
            await update.message.reply_text("Please send a valid photo or video.")
            return EDIT_VALUE
            
    else:
        # For profile_name or interest
        context.user_data[field] = update.message.text

    await update.message.reply_text(
        f"✅ Your {field.replace('_', ' ')} has been updated successfully!",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Operation cancelled.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

# --- Application Setup ---

app = Application.builder().token(TOKEN).build()

# Registration Handler
reg_conv_handler = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(handle_gender_selection, pattern="^gender_")
    ],
    states={
        ASK_AGE_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_age_input)],
        LOCATION: [MessageHandler((filters.LOCATION | filters.TEXT) & ~filters.COMMAND, receive_location)],
        PROFILE_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_profile_name)],
        INTEREST: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_interest)],
        PHOTO: [MessageHandler((filters.PHOTO | filters.VIDEO) & ~filters.COMMAND, receive_photo)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)

# Edit Profile Handler
edit_conv_handler = ConversationHandler(
    entry_points=[
        CommandHandler("edit", start_edit_profile),
        CallbackQueryHandler(start_edit_profile, pattern="^edit_profile$")
    ],
    states={
        EDIT_CHOICE: [CallbackQueryHandler(handle_edit_choice, pattern="^field_")],
        EDIT_VALUE: [MessageHandler((filters.TEXT | filters.LOCATION | filters.PHOTO | filters.VIDEO) & ~filters.COMMAND, receive_edit_value)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(button_click, pattern="^(register|age_yes|age_no)$"))
app.add_handler(reg_conv_handler)
app.add_handler(edit_conv_handler)

app.run_polling()
