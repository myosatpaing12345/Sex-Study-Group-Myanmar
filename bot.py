import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
import psycopg2
from psycopg2.extras import RealDictCursor

# Logging setup
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Database URL ယူရန် (Render Environment မှ)
DATABASE_URL = os.environ.get("DATABASE_URL")

def get_db_connection():
    if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
        url = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    else:
        url = DATABASE_URL
    return psycopg2.connect(url, cursor_factory=RealDictCursor)

# Database Tables ဖန်တီးရန်
def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id BIGINT PRIMARY KEY,
            profile_name TEXT,
            gender TEXT,
            target_gender TEXT,
            bio TEXT,
            media_id TEXT,
            media_type TEXT
        );
    """)
    conn.commit()
    cur.close()
    conn.close()

init_db()

# User Profile ထုတ်ရန် Helper Function
def get_user_profile(user_id):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE user_id = %s;", (user_id,))
        user = cur.fetchone()
        cur.close()
        conn.close()
        return user
    except Exception as e:
        logger.error(f"Database Error: {e}")
        return None

# /start Command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    
    user_prof = get_user_profile(user_id)
    
    if user_prof:
        # Profile ရှိပြီးသားဆိုရင် LeoMatch ပုံစံ Menu ပြမည်
        keyboard = [
            [InlineKeyboardButton("🔍 Find Partner (Match)", callback_data="find_match")],
            [InlineKeyboardButton("👤 My Profile", callback_data="view_profile")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            f"Welcome back, **{user_prof['profile_name']}**!🍷\nEveryone Sex partnerရှာလိုက်ကြရအောင်😜💋\n\nChoose an option:",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    else:
        # Profile မရှိသေးရင် အသစ်စဆောက်မည်
        keyboard = [
            [InlineKeyboardButton("Male 👨", callback_data="reg_male"),
             InlineKeyboardButton("Female 👩", callback_data="reg_female")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "Welcome to Sex Study Group🍷\nEveryone Sex partnerရှာလိုက်ကြရအောင်😜💋\n\nChoose your Gender",
            reply_markup=reply_markup
        )

# Gender ရွေးချယ်ခြင်း Handler
async def gender_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = query.from_user.id
    
    if data in ["reg_male", "reg_female"]:
        gender = "Male" if data == "reg_male" else "Female"
        context.user_data['gender'] = gender
        
        await query.message.edit_text("Enter your Profile Name (Nickname) to display in bot:")
        context.user_data['state'] = "WAITING_NAME"

# Message များကို လက်ခံစစ်ဆေးခြင်း (Registration & Messages)
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    state = context.user_data.get('state')
    
    if state == "WAITING_NAME":
        profile_name = update.message.text
        context.user_data['profile_name'] = profile_name
        
        keyboard = [
            [InlineKeyboardButton("Male 👨", callback_data="target_male"),
             InlineKeyboardButton("Female 👩", callback_data="target_female")],
            [InlineKeyboardButton("Everyone 🔥", callback_data="target_everyone")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("Who are you interested in?", reply_markup=reply_markup)
        context.user_data['state'] = "WAITING_TARGET"
        
    elif state == "WAITING_MEDIA":
        # Photo သို့မဟုတ် Video ပို့သည်ကို စစ်ဆေးခြင်း
        media_id = None
        media_type = None
        
        if update.message.photo:
            media_id = update.message.photo[-1].file_id
            media_type = "photo"
        elif update.message.video:
            media_id = update.message.video.file_id
            media_type = "video"
        else:
            await update.message.reply_text("📸 Send a Profile Photo or 🎬 Video:")
            return
            
        gender = context.user_data.get('gender')
        profile_name = context.user_data.get('profile_name')
        target_gender = context.user_data.get('target_gender')
        
        # Database ထဲသို့ အချက်အလက်များ သိမ်းဆည်းခြင်း
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO users (user_id, profile_name, gender, target_gender, media_id, media_type)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (user_id) DO UPDATE 
                SET profile_name = EXCLUDED.profile_name,
                    gender = EXCLUDED.gender,
                    target_gender = EXCLUDED.target_gender,
                    media_id = EXCLUDED.media_id,
                    media_type = EXCLUDED.media_type;
            """, (user_id, profile_name, gender, target_gender, media_id, media_type))
            conn.commit()
            cur.close()
            conn.close()
        except Exception as e:
            logger.error(f"DB Save Error: {e}")
            await update.message.reply_text("Database Error ဖြစ်သွားပါသည်၊ /start ဖြင့် ပြန်စမ်းပါ။")
            return
            
        context.user_data['state'] = None
        
        keyboard = [
            [InlineKeyboardButton("🔍 Find Partner (Match)", callback_data="find_match")],
            [InlineKeyboardButton("👤 My Profile", callback_data="view_profile")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("✅ Profile Created Successfully! 🎉", reply_markup=reply_markup)

# Target Gender ရွေးချယ်ခြင်း
async def target_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    if "target_" in data:
        target = data.replace("target_", "")
        context.user_data['target_gender'] = target
        
        await query.message.edit_text("📸 Send a Profile Photo or 🎬 Video:")
        context.user_data['state'] = "WAITING_MEDIA"

# Like Message သို့မဟုတ် Match ပြုလုပ်ခြင်း Callback များနှင့် Crash မဖြစ်အောင် Safety Check
async def receive_like_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    user_prof = get_user_profile(user_id)
    
    # ⚠️ Profile မရှိရင် Bot Crash မသွားအောင် Safety Check
    if not user_prof:
        await query.message.reply_text("သင်၏ Profile အချက်အလက် မရှိတော့ပါ သို့မဟုတ် Database ပြောင်းသွားပါသည်။ ကျေးဇူးပြု၍ /start နှိပ်၍ Profile အသစ် ပြန်ဆောက်ပေးပါ။")
        return

    profile_name = user_prof.get('profile_name', 'Anonymous')
    await query.message.reply_text(f"Welcome back, {profile_name}!")

# Main Function
def main():
    token = os.environ.get("8905518813:AAFLofvwp-CrznhC8SEk4rjH2OGoEUb2Taw")
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN not found in environment variables!")
        return

    application = Application.builder().token(token).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(gender_handler, pattern="^reg_"))
    application.add_handler(CallbackQueryHandler(target_handler, pattern="^target_"))
    application.add_handler(CallbackQueryHandler(receive_like_message, pattern="^find_match$"))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(MessageHandler(filters.PHOTO | filters.VIDEO, handle_message))

    print("Bot is running...")
    application.run_polling()

if __name__ == "__main__":
    main()
    
