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

# --- Render Web Service Port Scan Keep-Alive Server ---
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
TOKEN = "YOUR_BOT_TOKEN_HERE"  # <--- သင့် Bot Token ကို ဒီမှာ ထည့်ပါ

# Conversation States
GENDER, ASK_AGE_INPUT, LOCATION, PROFILE_NAME, INTEREST, PHOTO = range(6)

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
            photo_id TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS matches (
            user_id INTEGER,
            target_id INTEGER,
            action TEXT,
            PRIMARY KEY (user_id, target_id)
        )
    ''')
    conn.commit()
    conn.close()

def save_user_profile(user_id, username, data):
    conn = sqlite3.connect("match_bot.db")
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO users (user_id, username, gender, age, city, profile_name, interest, photo_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        user_id,
        username,
        data.get('gender'),
        data.get('age'),
        data.get('city'),
        data.get('profile_name'),
        data.get('interest'),
        data.get('photo_id')
    ))
    conn.commit()
    conn.close()

def get_user_profile(user_id):
    conn = sqlite3.connect("match_bot.db")
    cursor = conn.cursor()
    cursor.execute('SELECT gender, age, city, profile_name, interest, photo_id, username FROM users WHERE user_id = ?', (user_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {
            'gender': row[0],
            'age': row[1],
            'city': row[2],
            'profile_name': row[3],
            'interest': row[4],
            'photo_id': row[5],
            'username': row[6]
        }
    return None

# --- Registration Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    profile = get_user_profile(user_id)
    if profile:
        caption = (
            f"မင်္ဂလာပါ {profile['profile_name']}! သင့် Profile ရှိပြီးသားဖြစ်ပါသည်။\n\n"
            f"👤 Gender: {profile['gender']}\n"
            f"🎂 Age: {profile['age']}\n"
            f"📍 City: {profile['city']}\n"
            f"🎯 Interest: {profile['interest']}\n\n"
            f"Match ရှာရန် /find ကို နှိပ်ပါ။"
        )
        if profile.get('photo_id'):
            await update.message.reply_photo(photo=profile['photo_id'], caption=caption)
        else:
            await update.message.reply_text(caption)
        return ConversationHandler.END

    reply_keyboard = [["ကျား (Male)", "မ (Female)", "အခြား (Other)"]]
    welcome_text = (
        "Welcome to Sex Study Group 🍷\n"
        "Everyone Sex partnerရှာလိုက်ကြ‌ရအောင်🤪💋\n\n"
        "Choose your Gender"
    )
    await update.message.reply_text(
        welcome_text,
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True),
    )
    return ASK_AGE_INPUT

async def ask_age(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['gender'] = update.message.text
    await update.message.reply_text("How Old are you (example- 18):", reply_markup=ReplyKeyboardRemove())
    return LOCATION

async def ask_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        age = int(update.message.text)
        context.user_data['age'] = age
    except ValueError:
        await update.message.reply_text("ကျေးဇူးပြု၍ အသက်ကို ဂဏန်းသီးသန့် ရိုက်ထည့်ပေးပါ (ဥပမာ- 22):")
        return LOCATION

    await update.message.reply_text("သင့်မြို့ သို့မဟုတ် နေထိုင်သည့် ဒေသကို ရိုက်ထည့်ပေးပါ (ဥပမာ- Yangon, Mandalay):")
    return PROFILE_NAME

async def ask_profile_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['city'] = update.message.text
    await update.message.reply_text("Bot ထဲတွင် ပြသမည့် သင့် Profile နာမည် (Nickname) ကို ရိုက်ထည့်ပေးပါ:")
    return INTEREST

async def ask_interest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['profile_name'] = update.message.text
    reply_keyboard = [["Male", "Female", "Anyone"]]
    await update.message.reply_text(
        "သင် မည်သည့် Gender ကို စိတ်ဝင်စားပါသနည်း-",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True),
    )
    return PHOTO

async def ask_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['interest'] = update.message.text
    await update.message.reply_text(
        "📸 သင့် Profile အတွက် ဓာတ်ပုံတစ်ပုံ ပို့ပေးပါ (Match ရှာသည့်အခါ အခြားသူများ မြင်တွေ့ရမည်ဖြစ်ပါသည်):",
        reply_markup=ReplyKeyboardRemove()
    )
    return 6

async def complete_registration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo:
        await update.message.reply_text("ကျေးဇူးပြု၍ ဓာတ်ပုံ (Photo) တစ်ပုံ ပို့ပေးပါရန်:")
        return 6

    photo_file = update.message.photo[-1].file_id
    context.user_data['photo_id'] = photo_file
    
    user = update.effective_user
    save_user_profile(user.id, user.username, context.user_data)
    
    await update.message.reply_text(
        "🎉 Profile သတ်မှတ်ခြင်း အောင်မြင်ပါသည်။\n/find ကို နှိပ်၍ Match များ စတင်ရှာဖွေနိုင်ပါပြီ။"
    )
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("လုပ်ဆောင်ချက်ကို ပယ်ဖျက်လိုက်ပါပြီ။", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

# --- Find / Matching Handlers ---
async def find_match(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_prof = get_user_profile(user_id)
    
    if not user_prof:
        await update.message.reply_text("ကျေးဇူးပြု၍ /start နှိပ်ပြီး အရင် စာရင်းသွင်းပေးပါ။")
        return

    conn = sqlite3.connect("match_bot.db")
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT user_id, profile_name, gender, age, city, photo_id FROM users 
        WHERE user_id != ? AND user_id NOT IN (
            SELECT target_id FROM matches WHERE user_id = ?
        ) LIMIT 1
    ''', (user_id, user_id))
    
    target = cursor.fetchone()
    conn.close()

    if not target:
        await update.message.reply_text("ယခုအချိန်တွင် သင့်အတွက် Match အသစ်များ မရှိသေးပါ။ ခဏကြာမှ ပြန်ရှာကြည့်ပါ။")
        return

    context.user_data['current_target'] = target[0]
    reply_keyboard = [["❤️ Like", "❌ Pass"]]
    
    caption = (
        f"✨ Target Profile ✨\n\n"
        f"👤 Name: {target[1]}\n"
        f"🚻 Gender: {target[2]}\n"
        f"🎂 Age: {target[3]}\n"
        f"📍 City: {target[4]}"
    )

    if target[5]:
        await update.message.reply_photo(
            photo=target[5],
            caption=caption,
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)
        )
    else:
        await update.message.reply_text(
            caption,
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)
        )

async def handle_match_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id
    target_id = context.user_data.get('current_target')

    if not target_id or text not in ["❤️ Like", "❌ Pass"]:
        return

    action = "like" if text == "❤️ Like" else "pass"
    
    conn = sqlite3.connect("match_bot.db")
    cursor = conn.cursor()
    cursor.execute('INSERT OR REPLACE INTO matches (user_id, target_id, action) VALUES (?, ?, ?)', (user_id, target_id, action))
    
    if action == "like":
        cursor.execute('SELECT action FROM matches WHERE user_id = ? AND target_id = ?', (target_id, user_id))
        match_status = cursor.fetchone()
        
        if match_status and match_status[0] == "like":
            user_prof = get_user_profile(user_id)
            target_prof = get_user_profile(target_id)
            
            if user_prof.get('username'):
                user_link = f"https://t.me/{user_prof['username']}"
            else:
                user_link = f"tg://user?id={user_id}"
                
            if target_prof.get('username'):
                target_link = f"https://t.me/{target_prof['username']}"
            else:
                target_link = f"tg://user?id={target_id}"

            msg_for_me = (
                f"🎉 **အချစ်သစ်တွေ့ပါပြီ (Match Successful!)** 🎉\n\n"
                f"သင်နှင့် **{target_prof['profile_name']}** တို့ အပြန်အလှန် Like ပေးထားကြပါသည်။\n\n"
                f"💬 တိုက်ရိုက် စကားပြောရန် Link ကို နှိပ်ပါ - [{target_prof['profile_name']}]({target_link})"
            )
            await update.message.reply_text(msg_for_me, parse_mode='Markdown')
            
            msg_for_target = (
                f"🎉 **အချစ်သစ်တွေ့ပါပြီ (Match Successful!)** 🎉\n\n"
                f"သင်နှင့် **{user_prof['profile_name']}** တို့ အပြန်အလှန် Like ပေးထားကြပါသည်။\n\n"
                f"💬 တိုက်ရိုက် စကားပြောရန် Link ကို နှိပ်ပါ - [{user_prof['profile_name']}]({user_link})"
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
        entry_points=[CommandHandler("start", start)],
        states={
            ASK_AGE_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_age)],
            LOCATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_location)],
            PROFILE_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_profile_name)],
            INTEREST: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_interest)],
            PHOTO: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_photo)],
            6: [MessageHandler(filters.PHOTO, complete_registration)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("find", find_match))
    app.add_handler(MessageHandler(filters.Regex("^(❤️ Like|❌ Pass)$"), handle_match_action))

    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
    
