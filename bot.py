import logging
import sqlite3
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

# Conversation States for Registration
ASK_AGE_INPUT, LOCATION, PROFILE_NAME, INTEREST, PHOTO = range(5)

# Conversation States for Editing Profile
EDIT_CHOICE, EDIT_VALUE = range(5, 7)

TOKEN = "YOUR_NEW_BOT_TOKEN_HERE"

# --- SQLite Database Setup ---

def init_db():
    conn = sqlite3.connect("match_bot.db")
    cursor = conn.cursor()
    # Users Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            gender TEXT,
            age INTEGER,
            city TEXT,
            latitude REAL,
            longitude REAL,
            profile_name TEXT,
            interest TEXT,
            photo_id TEXT
        )
    ''')
    # Likes & Matches Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_likes (
            from_user_id INTEGER,
            to_user_id INTEGER,
            action TEXT,
            PRIMARY KEY (from_user_id, to_user_id)
        )
    ''')
    conn.commit()
    conn.close()

def save_user_profile(user_data):
    conn = sqlite3.connect("match_bot.db")
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO users 
        (user_id, gender, age, city, latitude, longitude, profile_name, interest, photo_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        user_data['user_id'],
        user_data.get('gender', 'Not specified'),
        user_data.get('age'),
        user_data.get('city', 'Unknown'),
        user_data.get('lat'),
        user_data.get('lng'),
        user_data.get('profile_name'),
        user_data.get('interest'),
        user_data.get('photo_id')
    ))
    conn.commit()
    conn.close()

def update_user_field(user_id, field_name, value):
    conn = sqlite3.connect("match_bot.db")
    cursor = conn.cursor()
    cursor.execute(f'''
        UPDATE users 
        SET {field_name} = ?
        WHERE user_id = ?
    ''', (value, user_id))
    conn.commit()
    conn.close()

def update_user_location(user_id, city, lat, lng):
    conn = sqlite3.connect("match_bot.db")
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE users 
        SET city = ?, latitude = ?, longitude = ?
        WHERE user_id = ?
    ''', (city, lat, lng, user_id))
    conn.commit()
    conn.close()

def get_next_candidate(current_user_id):
    conn = sqlite3.connect("match_bot.db")
    cursor = conn.cursor()
    # Find users who are not self and not yet liked/passed
    cursor.execute('''
        SELECT user_id, gender, age, city, profile_name, interest, photo_id 
        FROM users 
        WHERE user_id != ? AND user_id NOT IN (
            SELECT to_user_id FROM user_likes WHERE from_user_id = ?
        )
        LIMIT 1
    ''', (current_user_id, current_user_id))
    candidate = cursor.fetchone()
    conn.close()
    return candidate

def record_like_action(from_id, to_id, action):
    conn = sqlite3.connect("match_bot.db")
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO user_likes (from_user_id, to_user_id, action)
        VALUES (?, ?, ?)
    ''', (from_id, to_id, action))
    conn.commit()
    
    # Check if mutual match exists
    is_match = False
    if action == 'like':
        cursor.execute('''
            SELECT action FROM user_likes 
            WHERE from_user_id = ? AND to_user_id = ? AND action = 'like'
        ''', (to_id, from_id))
        if cursor.fetchone():
            is_match = True

    conn.close()
    return is_match

def get_user_profile(user_id):
    conn = sqlite3.connect("match_bot.db")
    cursor = conn.cursor()
    cursor.execute('SELECT profile_name FROM users WHERE user_id = ?', (user_id,))
    res = cursor.fetchone()
    conn.close()
    return res[0] if res else "Someone"

# --- Start & Button Callbacks ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📝 Register", callback_data="register")],
        [InlineKeyboardButton("✏️ Edit Profile", callback_data="edit_profile")],
        [InlineKeyboardButton("🔍 Find Matches", callback_data="find_matches")]
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

    elif query.data == "find_matches":
        await show_next_match(query.message.chat_id, context, update.effective_user.id)

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
    context.user_data['user_id'] = update.effective_user.id

    save_user_profile(context.user_data)

    await update.message.reply_text(
        "🎉 Profile registration completed and saved successfully!\n"
        "Use /find to discover nearby matches or /edit to modify your profile."
    )
    return ConversationHandler.END

# --- Edit Profile Flow ---

async def start_edit_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("✏️ Name", callback_data="field_profile_name"), InlineKeyboardButton("✏️ Age", callback_data="field_age")],
        [InlineKeyboardButton("✏️ Interest", callback_data="field_interest"), InlineKeyboardButton("✏️ Location", callback_data="field_location")],
        [InlineKeyboardButton("🖼️ Photo/Video", callback_data="field_photo_id")]
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
    elif selected_field == "photo_id":
        await query.edit_message_text("Please upload a new photo or video:")

    return EDIT_VALUE

async def receive_edit_value(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    field = context.user_data.get('editing_field')

    if field == "age":
        try:
            age = int(update.message.text)
            if age < 18:
                await update.message.reply_text("You must be at least 18 years old.")
                return EDIT_VALUE
            update_user_field(user_id, "age", age)
        except ValueError:
            await update.message.reply_text("Please enter a valid number for age.")
            return EDIT_VALUE

    elif field == "location":
        if update.message.location:
            lat = update.message.location.latitude
            lng = update.message.location.longitude
            city = "GPS Location"
        else:
            lat, lng = None, None
            city = update.message.text
        
        update_user_location(user_id, city, lat, lng)

    elif field == "photo_id":
        if update.message.photo:
            file_id = update.message.photo[-1].file_id
        elif update.message.video:
            file_id = update.message.video.file_id
        else:
            await update.message.reply_text("Please send a valid photo or video.")
            return EDIT_VALUE
        
        update_user_field(user_id, "photo_id", file_id)

    else:
        new_val = update.message.text
        update_user_field(user_id, field, new_val)

    await update.message.reply_text(
        f"✅ Your {field.replace('_', ' ')} has been updated in database successfully!",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Operation cancelled.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

# --- Matching & Like System ---

async def show_next_match(chat_id, context: ContextTypes.DEFAULT_TYPE, current_user_id):
    candidate = get_next_candidate(current_user_id)
    if not candidate:
        await context.bot.send_message(chat_id=chat_id, text="🚫 No more profiles available right now. Check back later!")
        return

    cand_id, gender, age, city, name, interest, photo_id = candidate
    
    caption = (
        f"👤 **{name}**, {age}\n"
        f"📍 Location: {city}\n"
        f"🎯 Interested in: {interest}"
    )

    keyboard = [
        [
            InlineKeyboardButton("❤️ Like", callback_data=f"match_like_{cand_id}"),
            InlineKeyboardButton("❌ Pass", callback_data=f"match_pass_{cand_id}")
        ]
    ]

    try:
        await context.bot.send_photo(
            chat_id=chat_id,
            photo=photo_id,
            caption=caption,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception:
        # Fallback if photo_id is a video or failed
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"Profile:\n{caption}",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

async def handle_match_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data
    from_user_id = update.effective_user.id

    if data.startswith("match_like_"):
        to_user_id = int(data.replace("match_like_", ""))
        is_match = record_like_action(from_user_id, to_user_id, "like")

        await query.delete_message()

        if is_match:
            # Notify both users!
            user_a_name = get_user_profile(from_user_id)
            user_b_name = get_user_profile(to_user_id)

            await context.bot.send_message(
                chat_id=from_user_id,
                text=f"🎉 **It's a Match!**\nYou and **{user_b_name}** liked each other!"
            )
            try:
                await context.bot.send_message(
                    chat_id=to_user_id,
                    text=f"🎉 **It's a Match!**\nYou and **{user_a_name}** liked each other!"
                )
            except Exception:
                pass  # If user blocked the bot

        # Show next candidate
        await show_next_match(query.message.chat_id, context, from_user_id)

    elif data.startswith("match_pass_"):
        to_user_id = int(data.replace("match_pass_", ""))
        record_like_action(from_user_id, to_user_id, "pass")

        await query.delete_message()
        await show_next_match(query.message.chat_id, context, from_user_id)

async def find_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_next_match(update.message.chat_id, context, update.effective_user.id)

# --- Application Main ---

def main():
    init_db()

    app = Application.builder().token(TOKEN).build()

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
    app.add_handler(CommandHandler("find", find_command))
    app.add_handler(CallbackQueryHandler(button_click, pattern="^(register|age_yes|age_no|find_matches)$"))
    app.add_handler(CallbackQueryHandler(handle_match_action, pattern="^match_(like|pass)_"))
    app.add_handler(reg_conv_handler)
    app.add_handler(edit_conv_handler)

    app.run_polling()

if __name__ == "__main__":
    main()
    
