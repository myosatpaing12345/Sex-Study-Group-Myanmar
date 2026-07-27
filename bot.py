import os
import sqlite3
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

# --- Render Keep-Alive Web Server ---
class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running!")

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), SimpleHTTPRequestHandler)
    server.serve_forever()

# --- Telegram Bot Config ---
TOKEN = "8905518813:AAFLofvwp-CrznhC8SEk4rjH2OGoEUb2Taw"  # <--- သင့် Bot Token ကို ဒီမှာ ပြန်ထည့်ပါ

# Conversation States
GENDER, ASK_AGE_INPUT, LOCATION, PROFILE_NAME, INTEREST, MEDIA, SEND_MESSAGE_LIKE = range(7)

# --- SQLite Database Setup ---
def init_db():
    conn = sqlite3.connect("match_bot.db")
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            gender TEXT,
            age INTEGER,
            city TEXT,
            profile_name TEXT,
            interest TEXT,
            media_id TEXT,
            media_type TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS matches (
            user_id INTEGER,
            target_id INTEGER,
            action TEXT,
            message_text TEXT,
            PRIMARY KEY (user_id, target_id)
        )
    ''')
    conn.commit()
    conn.close()

def save_user_profile(user_id, username, data):
    conn = sqlite3.connect("match_bot.db")
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO users (user_id, username, gender, age, city, profile_name, interest, media_id, media_type)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        user_id,
        username,
        data.get('gender'),
        data.get('age'),
        data.get('city'),
        data.get('profile_name'),
        data.get('interest'),
        data.get('media_id'),
        data.get('media_type')
    ))
    conn.commit()
    conn.close()

def get_user_profile(user_id):
    conn = sqlite3.connect("match_bot.db")
    cursor = conn.cursor()
    cursor.execute('SELECT gender, age, city, profile_name, interest, media_id, media_type, username FROM users WHERE user_id = ?', (user_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {
            'gender': row[0],
            'age': row[1],
            'city': row[2],
            'profile_name': row[3],
            'interest': row[4],
            'media_id': row[5],
            'media_type': row[6],
            'username': row[7]
        }
    return None

def get_main_menu_keyboard():
    keyboard = [["1 🚀", "2", "3"]]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

async def send_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    menu_text = (
        "1. View profiles.\n"
        "2. My profile.\n"
        "3. Edit profile."
    )
    await update.message.reply_text(menu_text, reply_markup=get_main_menu_keyboard())

# --- Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    profile = get_user_profile(user_id)
    
    if profile:
        await send_main_menu(update, context)
        return ConversationHandler.END

    return await start_registration(update, context)

async def start_registration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reply_keyboard = [["Male", "Female", "Other"]]
    welcome_text = (
        "Welcome to Sex Study Group 🍷\n"
        "Everyone Sex partnerရှာလိုက်ကြရအောင်🤪💋\n\n"
        "Choose your Gender"
    )
    await update.message.reply_text(
        welcome_text,
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True),
    )
    return ASK_AGE_INPUT

async def send_my_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    profile = get_user_profile(user_id)
    
    if not profile:
        await update.message.reply_text("Profile not found. Please type /start to register.")
        return

    caption = (
        f"👤 **Your Profile**\n\n"
        f"📝 Name: {profile['profile_name']}\n"
        f"🚻 Gender: {profile['gender']}\n"
        f"🎂 Age: {profile['age']}\n"
        f"📍 City: {profile['city']}\n"
        f"🎯 Interested in: {profile['interest']}"
    )
    
    if profile.get('media_id'):
        if profile.get('media_type') == 'video':
            await update.message.reply_video(video=profile['media_id'], caption=caption, parse_mode='Markdown')
        else:
            await update.message.reply_photo(photo=profile['media_id'], caption=caption, parse_mode='Markdown')
    else:
        await update.message.reply_text(caption, parse_mode='Markdown')

    await send_main_menu(update, context)

async def ask_age(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['gender'] = update.message.text
    await update.message.reply_text("How old are you? (example- 18):", reply_markup=ReplyKeyboardRemove())
    return LOCATION

async def ask_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        age = int(update.message.text)
        context.user_data['age'] = age
    except ValueError:
        await update.message.reply_text("Please enter numbers only for age (example- 18):")
        return LOCATION

    await update.message.reply_text("Where do you live? (example- Yangon, Mandalay):")
    return PROFILE_NAME

async def ask_profile_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['city'] = update.message.text
    await update.message.reply_text("Enter your Profile Name (Nickname) to display in bot:")
    return INTEREST

async def ask_interest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['profile_name'] = update.message.text
    reply_keyboard = [["Male", "Female", "Anyone"]]
    await update.message.reply_text(
        "Who are you interested in?",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True),
    )
    return MEDIA

async def ask_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['interest'] = update.message.text
    await update.message.reply_text(
        "📸 Send a Profile Photo or 📹 Video:",
        reply_markup=ReplyKeyboardRemove()
    )
    return 6

async def complete_registration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.photo:
        context.user_data['media_id'] = update.message.photo[-1].file_id
        context.user_data['media_type'] = 'photo'
    elif update.message.video:
        context.user_data['media_id'] = update.message.video.file_id
        context.user_data['media_type'] = 'video'
    else:
        await update.message.reply_text("Please send a Photo or Video:")
        return 6

    user = update.effective_user
    save_user_profile(user.id, user.username, context.user_data)
    
    await update.message.reply_text("🎉 Profile setup successful!")
    await send_main_menu(update, context)
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Cancelled.")
    await send_main_menu(update, context)
    return ConversationHandler.END

# --- Matching System ---
async def find_match(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_prof = get_user_profile(user_id)
    
    if not user_prof:
        await update.message.reply_text("Please register first.")
        return

    await update.message.reply_text("✨ 🔍")

    conn = sqlite3.connect("match_bot.db")
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT user_id, profile_name, gender, age, city, media_id, media_type FROM users 
        WHERE user_id != ? AND user_id NOT IN (
            SELECT target_id FROM matches WHERE user_id = ?
        ) LIMIT 1
    ''', (user_id, user_id))
    
    target = cursor.fetchone()
    conn.close()

    if not target:
        await update.message.reply_text("No new matches found at the moment. Please try again later!")
        await send_main_menu(update, context)
        return ConversationHandler.END

    context.user_data['current_target'] = target[0]
    
    reply_keyboard = [["❤️", "💌 / 📹", "👎", "💤"]]
    markup = ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True)

    caption = (
        f"{target[1]}, {target[3]}, {target[4]}\n\n"
        f"🚻 Gender: {target[2]}"
    )

    media_id = target[5]
    media_type = target[6]

    if media_id:
        if media_type == 'video':
            await update.message.reply_video(video=media_id, caption=caption, reply_markup=markup)
        else:
            await update.message.reply_photo(photo=media_id, caption=caption, reply_markup=markup)
    else:
        await update.message.reply_text(caption, reply_markup=markup)

async def handle_match_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id
    target_id = context.user_data.get('current_target')

    if text == "💤":
        await send_main_menu(update, context)
        return ConversationHandler.END

    if text == "💌 / 📹":
        await update.message.reply_text(
            "📝 Write a message or send a Video/Voice message to send with your Like:\n(Or send /cancel to go back)",
            reply_markup=ReplyKeyboardRemove()
        )
        return SEND_MESSAGE_LIKE

    action = "like" if text == "❤️" else "pass"
    await process_like_or_pass(update, context, user_id, target_id, action)
    return ConversationHandler.END

async def receive_like_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    target_id = context.user_data.get('current_target')
    
    user_prof = get_user_profile(user_id)
    
    # Message notification sent to target user
    msg_text = update.message.text if update.message.text else "Sent a video/media message!"
    
    notify_text = f"💌 **Someone liked your profile with a message!**\n\nFrom: **{user_prof['profile_name']}**\nMessage: _{msg_text}_"
    
    try:
        if update.message.video:
            await context.bot.send_video(chat_id=target_id, video=update.message.video.file_id, caption=notify_text, parse_mode='Markdown')
        elif update.message.voice:
            await context.bot.send_voice(chat_id=target_id, voice=update.message.voice.file_id, caption=notify_text, parse_mode='Markdown')
        else:
            await context.bot.send_message(chat_id=target_id, text=notify_text, parse_mode='Markdown')
    except Exception:
        pass

    await process_like_or_pass(update, context, user_id, target_id, "like", msg_text)
    return ConversationHandler.END

async def process_like_or_pass(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id, target_id, action, custom_msg=""):
    conn = sqlite3.connect("match_bot.db")
    cursor = conn.cursor()
    cursor.execute('INSERT OR REPLACE INTO matches (user_id, target_id, action, message_text) VALUES (?, ?, ?, ?)', (user_id, target_id, action, custom_msg))
    
    if action == "like":
        cursor.execute('SELECT action FROM matches WHERE user_id = ? AND target_id = ?', (target_id, user_id))
        match_status = cursor.fetchone()
        
        if match_status and match_status[0] == "like":
            user_prof = get_user_profile(user_id)
            target_prof = get_user_profile(target_id)
            
            user_link = f"https://t.me/{user_prof['username']}" if user_prof.get('username') else f"tg://user?id={user_id}"
            target_link = f"https://t.me/{target_prof['username']}" if target_prof.get('username') else f"tg://user?id={target_id}"

            msg_for_me = (
                f"🎉 **Match Successful!** 🎉\n\n"
                f"You and **{target_prof['profile_name']}** liked each other!\n\n"
                f"💬 Tap to chat: [{target_prof['profile_name']}]({target_link})"
            )
            await update.message.reply_text(msg_for_me, parse_mode='Markdown')
            
            msg_for_target = (
                f"🎉 **Match Successful!** 🎉\n\n"
                f"You and **{user_prof['profile_name']}** liked each other!\n\n"
                f"💬 Tap to chat: [{user_prof['profile_name']}]({user_link})"
            )
            try:
                await context.bot.send_message(chat_id=target_id, text=msg_for_target, parse_mode='Markdown')
            except Exception:
                pass
    
    conn.commit()
    conn.close()
    
    await find_match(update, context)

def main():
    init_db()

    web_thread = threading.Thread(target=run_web_server, daemon=True)
    web_thread.start()

    app = Application.builder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            MessageHandler(filters.Regex("^3$"), start_registration),
            MessageHandler(filters.Regex("^1 🚀$"), find_match),
            CommandHandler("find", find_match)
        ],
        states={
            ASK_AGE_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_age)],
            LOCATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_location)],
            PROFILE_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_profile_name)],
            INTEREST: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_interest)],
            MEDIA: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_media)],
            6: [MessageHandler(filters.PHOTO | filters.VIDEO, complete_registration)],
            SEND_MESSAGE_LIKE: [MessageHandler(filters.TEXT | filters.VIDEO | filters.VOICE, receive_like_message)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(conv_handler)
    app.add_handler(MessageHandler(filters.Regex("^2$"), send_my_profile))
    app.add_handler(MessageHandler(filters.Regex("^(❤️|💌 / 📹|👎|💤)$"), handle_match_action))

    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
