import os
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
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

# Database Connection (Render PostgreSQL သို့မဟုတ် URL သုံးရန်)
DATABASE_URL = os.environ.get("DATABASE_URL")

def get_db_connection():
    if not DATABASE_URL:
        return None
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)

# Database Table များ ဖန်တီးခြင်း
def init_db():
    conn = get_db_connection()
    if not conn:
        logger.error("DATABASE_URL not found!")
        return
    cur = conn.cursor()
    # Users Table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id BIGINT PRIMARY KEY,
            profile_name TEXT,
            gender TEXT,
            target_gender TEXT,
            bio TEXT,
            media_id TEXT,
            media_type TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    cur.close()
    conn.close()

init_db()

# User Profile ရှာရန် Helper Function
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

# /start Command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    
    # Database ထဲမှာ ရှိပြီးသားလား စစ်မည်
    user_prof = get_user_profile(user_id)
    
    if user_prof and user_prof.get('profile_name'):
        # Profile ရှိပြီးသားဆိုရင် Welcome ပြန်လုပ်မည်
        await update.message.reply_text(
            f"Welcome back, {user_prof['profile_name']}! 🎉\nသင်၏ Profile အဆင်သင့် ဖြစ်နေပါပြီ။",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔍 Match ရှာမည်", callback_data="find_match")]
            ])
        )
        return

    # အသစ်ဆိုရင် Gender ရွေးခိုင်းမည်
    keyboard = [
        [InlineKeyboardButton("👨 Male (ကျား)", callback_data="reg_male")],
        [InlineKeyboardButton("👩 Female (မ)", callback_data="reg_female")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "👋 မင်္ဂလာပါ LeoMatch မှ ကြိုဆိုပါတယ်။\nစတင်ရန် ကျေးဇူးပြု၍ သင်၏ ကျား/မ ကို ရွေးချယ်ပါ -",
        reply_markup=reply_markup
    )

# Gender ရွေးချယ်မှု Handler
async def gender_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    gender = query.data.split("_")[1] # male or female
    
    # Temporary State သိမ်းရန်
    context.user_data['reg_gender'] = gender
    
    # Target Gender ရွေးခိုင်းရန်
    keyboard = [
        [InlineKeyboardButton("👨 Male (ကျား)", callback_data="target_male")],
        [InlineKeyboardButton("👩 Female (မ)", callback_data="target_female")],
        [InlineKeyboardButton("🌐 Anyone (အားလုံး)", callback_data="target_any")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.edit_text(
        "🎯 သင် ဘယ်သူတွေကို ရှာချင်ပါသလဲ?",
        reply_markup=reply_markup
    )

# Target ရွေးချယ်မှု Handler
async def target_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    target = query.data.split("_")[1] # male, female, any
    context.user_data['reg_target'] = target
    
    await query.message.edit_text(
        "✍️ ကျေးဇူးပြု၍ သင်၏ **နာမည် (Profile Name)** ကို ရိုက်ထည့်ပေးပါ။"
    )
    context.user_data['step'] = 'waiting_name'

# Text / Media Handler
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    step = context.user_data.get('step')
    
    if step == 'waiting_name':
        name = update.message.text
        context.user_data['reg_name'] = name
        context.user_data['step'] = 'waiting_media'
        
        await update.message.reply_text(
            "📸 ကျေးဇူးပြု၍ သင်၏ **ဓာတ်ပုံ သို့မဟုတ် ဗီဒီယို** တစ်ခု ပို့ပေးပါ။"
        )
        return
        
    elif step == 'waiting_media':
        media_id = None
        media_type = None
        
        if update.message.photo:
            media_id = update.message.photo[-1].file_id
            media_type = 'photo'
        elif update.message.video:
            media_id = update.message.video.file_id
            media_type = 'video'
        else:
            await update.message.reply_text("⚠️ ကျေးဇူးပြု၍ ဓာတ်ပုံ (သို့) ဗီဒီယိုသာ ပို့ပေးပါ။")
            return
            
        # အချက်အလက်များကို Database ထဲသို့ သိမ်းမည်
        gender = context.user_data.get('reg_gender')
        target = context.user_data.get('reg_target')
        name = context.user_data.get('reg_name')
        
        conn = get_db_connection()
        if conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO users (user_id, profile_name, gender, target_gender, media_id, media_type)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (user_id) DO UPDATE SET
                profile_name = EXCLUDED.profile_name,
                gender = EXCLUDED.gender,
                target_gender = EXCLUDED.target_gender,
                media_id = EXCLUDED.media_id,
                media_type = EXCLUDED.media_type
            """, (user_id, name, gender, target, media_id, media_type))
            conn.commit()
            cur.close()
            conn.close()
            
        # Clear step
        context.user_data.clear()
        
        await update.message.reply_text(
            "✅ သင်၏ Profile ကို အောင်မြင်စွာ သိမ်းဆည်းပြီးပါပြီ! 🎉",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔍 Match ရှာမည်", callback_data="find_match")]
            ])
        )
        return

    user_prof = get_user_profile(user_id)
    if not user_prof:
        await update.message.reply_text("⚠️ သင်၏ Profile မရှိသေးပါ။ /start ကိုနှိပ်ပြီး အစကနေ စတင်ပါ။")
        return

# Render အတွက် Dummy Web Server (Port ပြဿနာ ဖြေရှင်းရန်)
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running!")

def run_web_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), SimpleHandler)
    server.serve_forever()

# Main Function
def main():
    # 1. Web Server ကို Background မှာ အရင် စတင်ပေးမည်
    server_thread = threading.Thread(target=run_web_server, daemon=True)
    server_thread.start()

    # 2. Telegram Bot Token
    token = "8905518813:AAFLofvwp-CrznhC8SEk4rjH20GoEub2Taw"

    application = Application.builder().token(token).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(gender_handler, pattern="^reg_"))
    application.add_handler(CallbackQueryHandler(target_handler, pattern="^target_"))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(MessageHandler(filters.PHOTO | filters.VIDEO, handle_message))

    print("Bot is running...")
    application.run_polling()

if __name__ == "__main__":
    main()
