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

# --- Render Web Service Port Scan အတွက် Web Server ငယ်လေး ---
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
TOKEN = "8905518813:AAEEjMQh6AOHQ6aXAbhor0l_imltjvn2iP8"  # <--- သင့် Bot Token အသစ်ကို ဒီမှာ ထည့်ပါ

# Conversation States
ASK_AGE_INPUT, LOCATION, PROFILE_NAME, INTEREST = range(4)
EDIT_CHOICE, EDIT_VALUE = range(4, 6)

# --- SQLite Database Setup ---
def init_db():
    conn = sqlite3.connect("match_bot.db")
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            gender TEXT,
            age INTEGER,
            city TEXT,
            latitude REAL,
            longitude REAL,
            profile_name TEXT,
            interest TEXT
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

def save_user_profile(user_id, data):
    conn = sqlite3.connect("match_bot.db")
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO users (user_id, gender, age, city, latitude, longitude, profile_name, interest)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        user_id,
        data.get('gender'),
        data.get('age'),
        data.get('city'),
        data.get('latitude'),
        data.get('longitude'),
        data.get('profile_name'),
        data.get('interest')
    ))
    conn.commit()
    conn.close()

def get_user_profile(user_id):
    conn = sqlite3.connect("match_bot.db")
    cursor = conn.cursor()
    cursor.execute('SELECT gender, age, city, profile_name, interest FROM users WHERE user_id = ?', (user_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {
            'gender': row[0],
            'age': row[1],
            'city': row[2],
            'profile_name': row[3],
            'interest': row[4]
        }
    return None

# --- Registration Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    profile = get_user_profile(user_id)
    if profile:
        await update.message.reply_text(
            f"မင်္ဂလာပါ {profile['profile_name']}! သင့် Profile ရှိပြီးသားဖြစ်ပါသည်။\n\n"
            f"👤 Gender: {profile['gender']}\n"
            f"🎂 Age: {profile['age']}\n"
            f"📍 City: {profile['city']}\n"
            f"🎯 Interest: {profile['interest']}\n\n"
            f"Profile ပြင်ရန် /edit သို့မဟုတ် Match ရှာရန် /find ကို နှိပ်ပါ။"
        )
        return ConversationHandler.END

    reply_keyboard = [["ကျား (Male)", "မ (Female)", "အခြား (Other)"]]
    await update.message.reply_text(
        "မင်္ဂလာပါ! Dating & Match Bot မှ ကြိုဆိုပါတယ်။\nသင့်ရဲ့ Gender (လိင်) ကို ရွေးချယ်ပေးပါ-",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True),
    )
    return ASK_AGE_INPUT

async def ask_age(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['gender'] = update.message.text
    await update.message.reply_text("သင့်အသက်ကို ရိုက်ထည့်ပေးပါ (ဥပမာ- 22):", reply_markup=ReplyKeyboardRemove())
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

async def save_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['profile_name'] = update.message.text
    reply_keyboard = [["ကျား (Male)", "မ (Female)", "မည်သူမဆို (Anyone)"]]
    await update.message.reply_text(
        "သင် မည်သည့် Gender ကို စိတ်ဝင်စားပါသနည်း-",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True),
    )
    return 5  # Save complete state

async def complete_registration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['interest'] = update.message.text
    user_id = update.effective_user.id
    save_user_profile(user_id, context.user_data)
    
    await update.message.reply_text(
        "🎉 Profile သတ်မှတ်ခြင်း အောင်မြင်ပါသည်။\n/find ကို နှိပ်၍ Match များ စတင်ရှာဖွေနိုင်ပါပြီ။",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("လုပ်ဆောင်ချက်ကို ပယ်ဖျက်လိုက်ပါပြီ။", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

# --- Edit Profile Handlers ---
async def edit_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    profile = get_user_profile(user_id)
    if not profile:
        await update.message.reply_text("သင့်မှာ Profile မရှိသေးပါ။ /start ကို နှိပ်၍ အရင် စာရင်းသွင်းပါ။")
        return ConversationHandler.END

    reply_keyboard = [["Name", "Age"], ["City", "Interest"], ["Cancel"]]
    await update.message.reply_text(
        "မည်သည့် အချက်အလက်ကို ပြင်ဆင်လိုပါသနည်း-",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)
    )
    return EDIT_CHOICE

async def edit_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    choice = update.message.text
    if choice == "Cancel":
        await update.message.reply_text("ပြင်ဆင်ခြင်းကို ပယ်ဖျက်လိုက်ပါပြီ။", reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END
    
    context.user_data['edit_field'] = choice.lower()
    await update.message.reply_text(f"အသစ် ပြင်ဆင်လိုသော {choice} ကို ရိုက်ထည့်ပေးပါ-", reply_markup=ReplyKeyboardRemove())
    return EDIT_VALUE

async def edit_save(update: Update, context: ContextTypes.DEFAULT_TYPE):
    field = context.user_data.get('edit_field')
    new_val = update.message.text
    user_id = update.effective_user.id
    
    profile = get_user_profile(user_id)
    if field == "name":
        profile['profile_name'] = new_val
    elif field == "age":
        try:
            profile['age'] = int(new_val)
        except ValueError:
            await update.message.reply_text("အသက်ကို ဂဏန်းသီးသန့် ပြန်ရိုက်ပေးပါ:")
            return EDIT_VALUE
    elif field == "city":
        profile['city'] = new_val
    elif field == "interest":
        profile['interest'] = new_val

    save_user_profile(user_id, profile)
    await update.message.reply_text("✅ Profile အချက်အလက် အောင်မြင်စွာ ပြင်ဆင်ပြီးပါပြီ။")
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
    
    # မိမိ မကြည့်ရသေးသော profile များကို ရှာခြင်း
    cursor.execute('''
        SELECT user_id, profile_name, gender, age, city FROM users 
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
    await update.message.reply_text(
        f"✨ Target Profile ✨\n\n"
        f"👤 Name: {target[1]}\n"
        f"🚻 Gender: {target[2]}\n"
        f"🎂 Age: {target[3]}\n"
        f"📍 City: {target[4]}",
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
    
    # Match ဖြစ်မဖြစ် စစ်ဆေးခြင်း
    if action == "like":
        cursor.execute('SELECT action FROM matches WHERE user_id = ? AND target_id = ?', (target_id, user_id))
        match_status = cursor.fetchone()
        if match_status and match_status[0] == "like":
            await update.message.reply_text("🎉 အချစ်သစ်တွေ့ပြီ! ၎င်းလူပုဂ္ဂိုလ်လည်း သင့်ကို Like ပေးထားပါသည်။ (Match Successful!)")
            try:
                await context.bot.send_message(chat_id=target_id, text="🎉 သင်နှင့် လူတစ်ဦး Match ဖြစ်သွားပါပြီ!")
            except Exception:
                pass
    
    conn.commit()
    conn.close()
    
    await update.message.reply_text("မှတ်တမ်းတင်ပြီးပါပြီ။", reply_markup=ReplyKeyboardRemove())
    await find_match(update, context)

def main():
    init_db()

    # Web Server ကို Background Thread အဖြစ် Run ခြင်း
    web_thread = threading.Thread(target=run_web_server, daemon=True)
    web_thread.start()

    app = Application.builder().token(TOKEN).build()

    # Registration Conversation Handler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            ASK_AGE_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_age)],
            LOCATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_location)],
            PROFILE_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_profile_name)],
            INTEREST: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_profile)],
            5: [MessageHandler(filters.TEXT & ~filters.COMMAND, complete_registration)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    # Edit Profile Conversation Handler
    edit_handler = ConversationHandler(
        entry_points=[CommandHandler("edit", edit_start)],
        states={
            EDIT_CHOICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_choice)],
            EDIT_VALUE: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_save)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(conv_handler)
    app.add_handler(edit_handler)
    app.add_handler(CommandHandler("find", find_match))
    app.add_handler(MessageHandler(filters.Regex("^(❤️ Like|❌ Pass)$"), handle_match_action))

    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
    
