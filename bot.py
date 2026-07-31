import os
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
import psycopg2
from psycopg2.extras import RealDictCursor

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Database Connection
DATABASE_URL = os.environ.get("DATABASE_URL")

def get_db_connection():
    if not DATABASE_URL:
        return None
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)

def init_db():
    conn = get_db_connection()
    if not conn:
        logger.error("DATABASE_URL not found!")
        return
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id BIGINT PRIMARY KEY,
            profile_name TEXT,
            age TEXT,
            gender TEXT,
            target_gender TEXT,
            city TEXT,
            bio TEXT,
            media_id TEXT,
            media_type TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    try:
        cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS city TEXT;")
    except Exception as e:
        logger.info(f"City column check/add info: {e}")

    cur.execute("""
        CREATE TABLE IF NOT EXISTS matches (
            user_id BIGINT,
            target_id BIGINT,
            action TEXT,
            message_text TEXT,
            PRIMARY KEY (user_id, target_id)
        )
    """)
    conn.commit()
    cur.close()
    conn.close()

init_db()

def get_user_profile(user_id):
    conn = get_db_connection()
    if not conn:
        return None
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
    user = cur.fetchone()
    cur.close()
    conn.close()
    return user

def get_main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔍 Find Match", callback_data="find_match")],
        [InlineKeyboardButton("👤 My Profile", callback_data="my_profile"),
         InlineKeyboardButton("⚙️ Edit Profile", callback_data="edit_profile")]
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    
    user_prof = get_user_profile(user_id)
    
    if user_prof and user_prof.get('age'):
        saved_age = user_prof.get('age')
        reply_markup = ReplyKeyboardMarkup(
            [[KeyboardButton(str(saved_age))]],
            resize_keyboard=True,
            one_time_keyboard=True
        )
    else:
        reply_markup = ReplyKeyboardRemove()

    await update.message.reply_text(
        "Welcome back Sex Study Group Myanmar🎉\nEveryone Sex Partnerကိုရှာလိုက်ကြရအောင်🤪💋\n\nHow old are you?\n\n⚠️ Profiles with an inaccurate age may be restricted",
        reply_markup=reply_markup
    )
    context.user_data['step'] = 'waiting_age'

async def handle_age(update: Update, context: ContextTypes.DEFAULT_TYPE):
    age_text = update.message.text
    context.user_data['reg_age'] = age_text
    
    reply_markup = ReplyKeyboardMarkup(
        [[KeyboardButton("👨 Male"), KeyboardButton("👩 Female")]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    
    await update.message.reply_text(
        "To get started, please select your gender:",
        reply_markup=reply_markup
    )
    context.user_data['step'] = 'waiting_gender'

async def gender_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    
    if "Male" in text:
        gender = "male"
    elif "Female" in text:
        gender = "female"
    else:
        return

    context.user_data['reg_gender'] = gender
    
    reply_markup = ReplyKeyboardMarkup(
        [[KeyboardButton("👨 Male"), KeyboardButton("👩 Female")],
         [KeyboardButton("🌐 No matter")]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    
    await update.message.reply_text(
        "🎯 Who are you looking for?",
        reply_markup=reply_markup
    )
    context.user_data['step'] = 'waiting_target'

async def target_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    
    if "Male" in text:
        target = "male"
    elif "Female" in text:
        target = "female"
    elif "No matter" in text:
        target = "any"
    else:
        return

    context.user_data['reg_target'] = target
    
    user_id = update.effective_user.id
    user_prof = get_user_profile(user_id)
    
    if user_prof and user_prof.get('profile_name'):
        saved_name = user_prof.get('profile_name')
        reply_markup = ReplyKeyboardMarkup(
            [[KeyboardButton(saved_name)]],
            resize_keyboard=True,
            one_time_keyboard=True
        )
        await update.message.reply_text(
            "✍️ Please enter your **Profile Name**:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            "✍️ Please enter your **Profile Name**:",
            reply_markup=ReplyKeyboardRemove(),
            parse_mode='Markdown'
        )
    
    context.user_data['step'] = 'waiting_name'

async def show_my_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    user_prof = get_user_profile(user_id)
    
    if not user_prof:
        await query.message.reply_text("⚠️ Profile not found. Please type /start to begin.")
        return

    caption = (
        f"👤 **Your Profile**\n\n"
        f"📝 Name: {user_prof['profile_name']}\n"
        f"🎂 Age: {user_prof.get('age', 'N/A')}\n"
        f"🚻 Gender: {user_prof['gender']}\n"
        f"🎯 Target: {user_prof['target_gender']}\n"
        f"🏙 City: {user_prof.get('city', 'N/A')}\n"
        f"💬 Bio: {user_prof.get('bio', 'N/A')}"
    )
    
    if user_prof.get('media_id'):
        if user_prof.get('media_type') == 'video':
            await query.message.reply_video(video=user_prof['media_id'], caption=caption, parse_mode='Markdown', reply_markup=get_main_menu())
        else:
            await query.message.reply_photo(photo=user_prof['media_id'], caption=caption, parse_mode='Markdown', reply_markup=get_main_menu())
    else:
        await query.message.reply_text(caption, parse_mode='Markdown', reply_markup=get_main_menu())

async def edit_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user_prof = get_user_profile(user_id)
    
    if user_prof and user_prof.get('age'):
        saved_age = user_prof.get('age')
        reply_markup = ReplyKeyboardMarkup(
            [[KeyboardButton(str(saved_age))]],
            resize_keyboard=True,
            one_time_keyboard=True
        )
    else:
        reply_markup = ReplyKeyboardRemove()

    await query.message.reply_text(
        "How old are you?\n\n⚠️ Profiles with an inaccurate age may be restricted",
        reply_markup=reply_markup
    )
    context.user_data['step'] = 'waiting_age'

async def find_match(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    user_prof = get_user_profile(user_id)
    if not user_prof:
        await query.message.reply_text("⚠️ Please create a profile first using /start.")
        return

    conn = get_db_connection()
    if not conn:
        return
    cur = conn.cursor()
    
    cur.execute("""
        SELECT * FROM users 
        WHERE user_id != %s AND user_id NOT IN (
            SELECT target_id FROM matches WHERE user_id = %s
        ) LIMIT 1
    """, (user_id, user_id))
    
    target = cur.fetchone()
    cur.close()
    conn.close()

    if not target:
        await query.message.edit_text(
            "😔 No more new profiles available right now. Please check back later.",
            reply_markup=get_main_menu()
        )
        return

    context.user_data['current_target'] = target['user_id']
    
    keyboard = [
        [InlineKeyboardButton("❤️ Like", callback_data="match_like"),
         InlineKeyboardButton("💌 Message with Like", callback_data="match_msg_like")],
        [InlineKeyboardButton("👎 Pass", callback_data="match_pass"),
         InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]
    ]
    
    caption = (
        f"👤 **{target['profile_name']}**\n"
        f"🎂 Age: {target.get('age', 'N/A')}\n"
        f"🚻 Gender: {target['gender']}\n"
        f"🏙 City: {target.get('city', 'N/A')}\n"
        f"💬 Bio: {target.get('bio', 'N/A')}"
    )
    
    if target.get('media_id'):
        if target.get('media_type') == 'video':
            await query.message.reply_video(video=target['media_id'], caption=caption, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await query.message.reply_photo(photo=target['media_id'], caption=caption, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await query.message.reply_text(caption, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def match_action_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    action_type = query.data
    user_id = query.from_user.id
    target_id = context.user_data.get('current_target')

    if action_type == "main_menu":
        await query.message.edit_text("🏠 Returned to Main Menu.", reply_markup=get_main_menu())
        return

    if action_type == "match_pass":
        conn = get_db_connection()
        if conn:
            cur = conn.cursor()
            cur.execute("INSERT INTO matches (user_id, target_id, action) VALUES (%s, %s, 'pass') ON CONFLICT (user_id, target_id) DO UPDATE SET action = 'pass'", (user_id, target_id))
            conn.commit()
            cur.close()
            conn.close()
        await find_match(update, context)
        return

    if action_type == "match_like":
        await process_like(update, context, user_id, target_id, "like")
        return

    if action_type == "match_msg_like":
        await query.message.edit_text("💌 Please send your message (or photo/video) to send along with your like:")
        context.user_data['step'] = 'waiting_like_message'
        return

async def skip_bio_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    context.user_data['reg_bio'] = "N/A"
    user_id = query.from_user.id
    user_prof = get_user_profile(user_id)
    
    if user_prof and user_prof.get('media_id'):
        reply_markup = ReplyKeyboardMarkup(
            [
                [KeyboardButton("Leave current")],
                [KeyboardButton("Take from my Telegram profile")]
            ],
            resize_keyboard=True,
            one_time_keyboard=True
        )
    else:
        reply_markup = ReplyKeyboardRemove()

    await query.message.edit_text(
        "Tell more about yourself. Who are you looking for? What do you want to do? I'll find the best matches."
    )
    await query.message.reply_text(
        "Send your photo or record a video (up to 15 sec).\n"
        "Profiles with a visible face get more likes ❤️\n\n"
        "❗️Photos of others and images from the internet are not allowed",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    context.user_data['step'] = 'waiting_media'

async def save_user_profile(user_id, context, media_id, media_type):
    name = context.user_data.get('reg_name')
    age = context.user_data.get('reg_age')
    gender = context.user_data.get('reg_gender')
    target = context.user_data.get('reg_target')
    city = context.user_data.get('reg_city')
    bio = context.user_data.get('reg_bio', 'N/A')

    conn = get_db_connection()
    if conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO users (user_id, profile_name, age, gender, target_gender, city, bio, media_id, media_type)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (user_id) DO UPDATE SET
            profile_name = EXCLUDED.profile_name,
            age = EXCLUDED.age,
            gender = EXCLUDED.gender,
            target_gender = EXCLUDED.target_gender,
            city = EXCLUDED.city,
            bio = EXCLUDED.bio,
            media_id = EXCLUDED.media_id,
            media_type = EXCLUDED.media_type
        """, (user_id, name, age, gender, target, city, bio, media_id, media_type))
        conn.commit()
        cur.close()
        conn.close()

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    step = context.user_data.get('step')
    text = update.message.text if update.message.text else ""

    if step == 'waiting_age':
        await handle_age(update, context)
        return

    elif step == 'waiting_gender':
        if "Male" in text or "Female" in text:
            await gender_text_handler(update, context)
        return
        
    elif step == 'waiting_target':
        if "Male" in text or "Female" in text or "No matter" in text:
            await target_text_handler(update, context)
        return

    elif step == 'waiting_name':
        context.user_data['reg_name'] = text
        user_prof = get_user_profile(user_id)
        
        if user_prof and user_prof.get('city'):
            saved_city = user_prof.get('city')
            reply_markup = ReplyKeyboardMarkup(
                [[KeyboardButton(saved_city)]],
                resize_keyboard=True,
                one_time_keyboard=True
            )
        else:
            reply_markup = ReplyKeyboardRemove()

        await update.message.reply_text(
            "🏙 **Please enter your City (မြို့နယ်/မြို့):**",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        context.user_data['step'] = 'waiting_city'
        return

    elif step == 'waiting_city':
        context.user_data['reg_city'] = text
        
        user_prof = get_user_profile(user_id)
        if user_prof and user_prof.get('media_id'):
            reply_markup = ReplyKeyboardMarkup(
                [
                    [KeyboardButton("Leave current")],
                    [KeyboardButton("Take from my Telegram profile")]
                ],
                resize_keyboard=True,
                one_time_keyboard=True
            )
        else:
            reply_markup = ReplyKeyboardRemove()

        skip_keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("⏭ Skip", callback_data="skip_bio")]])

        await update.message.reply_text(
            "Tell more about yourself. Who are you looking for? What do you want to do? I'll find the best matches.",
            reply_markup=skip_keyboard
        )
        context.user_data['step'] = 'waiting_bio'
        return

    elif step == 'waiting_bio':
        context.user_data['reg_bio'] = text
        user_prof = get_user_profile(user_id)
        
        if user_prof and user_prof.get('media_id'):
            reply_markup = ReplyKeyboardMarkup(
                [
                    [KeyboardButton("Leave current")],
                    [KeyboardButton("Take from my Telegram profile")]
                ],
                resize_keyboard=True,
                one_time_keyboard=True
            )
        else:
            reply_markup = ReplyKeyboardRemove()

        await update.message.reply_text(
            "Send your photo or record a video (up to 15 sec).\n"
            "Profiles with a visible face get more likes ❤️\n\n"
            "❗️Photos of others and images from the internet are not allowed",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        context.user_data['step'] = 'waiting_media'
        return

    elif step == 'waiting_media':
        media_id = None
        media_type = None

        if text == "Leave current":
            user_prof = get_user_profile(user_id)
            if user_prof:
                media_id = user_prof.get('media_id')
                media_type = user_prof.get('media_type', 'photo')
            else:
                await update.message.reply_text("⚠️ No previous profile found. Please send a photo or video.")
                return

        elif text == "Take from my Telegram profile":
            try:
                photos = await context.bot.get_user_profile_photos(user_id, limit=1)
                if photos.total_count > 0:
                    media_id = photos.photos[0][-1].file_id
                    media_type = 'photo'
                else:
                    await update.message.reply_text("⚠️ No photos found in your Telegram profile. Please send a photo manually.")
                    return
            except Exception:
                await update.message.reply_text("⚠️ Could not fetch Telegram profile photo. Please send a photo manually.")
                return

        else:
            if update.message.photo:
                media_id = update.message.photo[-1].file_id
                media_type = 'photo'
            elif update.message.video:
                media_id = update.message.video.file_id
                media_type = 'video'
            else:
                await update.message.reply_text("⚠️ Please send a valid Photo or Video or use the options below!")
                return

        await save_user_profile(user_id, context, media_id, media_type)
        context.user_data.clear()
        
        await update.message.reply_text(
            "✅ Your profile has been successfully saved! 🎉",
            reply_markup=ReplyKeyboardRemove()
        )
        await update.message.reply_text(
            "🏠 **Main Menu**",
            parse_mode='Markdown',
            reply_markup=get_main_menu()
        )
        return

    elif step == 'waiting_like_message':
        target_id = context.user_data.get('current_target')
        msg_text = update.message.text if update.message.text else "Sent a message"
        
        context.user_data.pop('step', None)
        await process_like(update, context, user_id, target_id, "like", custom_msg=msg_text)
        return

    user_prof = get_user_profile(user_id)
    if not user_prof:
        await update.message.reply_text("⚠️ Profile not found. Please click /start.")
        return

class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running!")

def run_web_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), SimpleHandler)
    server.serve_forever()

def main():
    server_thread = threading.Thread(target=run_web_server, daemon=True)
    server_thread.start()

    token = "8905518813:AAGfks_BGJM_g3uj0qu8ElzI0K3b6vFVj7Q"

    application = Application.builder().token(token).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(find_match, pattern="^find_match$"))
    application.add_handler(CallbackQueryHandler(show_my_profile, pattern="^my_profile$"))
    application.add_handler(CallbackQueryHandler(edit_profile, pattern="^edit_profile$"))
    application.add_handler(CallbackQueryHandler(skip_bio_handler, pattern="^skip_bio$"))
    application.add_handler(CallbackQueryHandler(match_action_handler, pattern="^(match_|main_menu)"))
    
    application.add_handler(MessageHandler((filters.TEXT | filters.PHOTO | 
