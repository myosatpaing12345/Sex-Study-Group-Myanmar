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

# ADMIN ID (Broadcast လုပ်ရန် Admin ၏ Telegram User ID ထည့်ရန်)
ADMIN_ID = 123456789  # <--- သင်၏ Telegram User ID

# Channel Username (သို့မဟုတ် ID) - Bot ကို ဤ Channel တွင် Admin ခန့်ထားရမည်
CHANNEL_USERNAME = "@Sexstudygroupoffical_bot" # 

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
            age INTEGER,
            city TEXT,
            bio TEXT,
            media_id TEXT,
            media_type TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    # Matches Table (Like / Pass တွေ မှတ်သားရန်)
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

# Main Menu Keyboard
def get_main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔍 Match ရှာမည်", callback_data="find_match")],
        [InlineKeyboardButton("👤 My Profile", callback_data="my_profile"),
         InlineKeyboardButton("⚙️ Edit Profile", callback_data="edit_profile")]
    ])

# --- Channel Membership Check Helper ---
async def check_user_channel(bot, user_id):
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        # member.status က creator, administrator, member ဖြစ်မှ Join ပြီးသားဟု သတ်မှတ်မည်
        if member.status in ['creator', 'administrator', 'member']:
            return True
    except Exception as e:
        logger.error(f"Error checking channel membership: {e}")
    return False

# /start Command (Channel Join စစ်ဆေးခြင်း)
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    
    # Channel Join ပြီးပြီလား စစ်မည်
    is_member = await check_user_channel(context.bot, user_id)
    
    if not is_member:
        keyboard = [
            [InlineKeyboardButton("📢 Join Official Channel", url="https://t.me/Sexstudygroupoffical_bot")],
            [InlineKeyboardButton("✅ Check Subscription", callback_data="check_sub")]
        ]
        await update.message.reply_text(
            "📢 Bot ကို အသုံးပြုရန် Official Channel ကို အရင် Join လုပ်ပေးပါ။\n\nJoin ပြီးလျှင် Check Subscription ကို နှိပ်ပါ၊၊",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    # Join ပြီးသားဆိုရင် ပုံမှန်အတိုင်း ရှေ့ဆက်မည်
    await proceed_after_subscription(update, context)

# Check Subscription Button Handler
async def check_subscription_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    is_member = await check_user_channel(context.bot, user_id)
    
    if not is_member:
        await query.message.answer_query if hasattr(query, 'answer_query') else None
        await query.message.edit_text(
            "⚠️ ကျေးဇူးပြု၍ Channel ကို မ join ရသေးပါက အရင် Join ပေးပါရန်။\n\nJoin ပြီးမှ Check Subscription ကို ထပ်နှိပ်ပါ။",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📢 Join Official Channel", url="https://t.me/Sexstudygroupoffical_bot")],
                [InlineKeyboardButton("✅ Check Subscription", callback_data="check_sub")]
            ])
        )
        return

    # Join ပြီးသွားပြီဆိုရင် Message အဟောင်းကို ဖျက်ပြီး start ပုံစံအတိုင်း ဆက်သွားမည်
    await query.message.delete()
    
    # ယာယီ update object ပုံစံဖြင့် start လုပ်ငန်းစဥ်ကို ဆက်လုပ်ရန်
    user_prof = get_user_profile(user_id)
    if user_prof and user_prof.get('profile_name'):
        await context.bot.send_message(
            chat_id=user_id,
            text=f"Welcome back, {user_prof['profile_name']}! 🎉\nသင်၏ Profile အဆင်သင့် ဖြစ်နေပါပြီ။",
            reply_markup=get_main_menu()
        )
        return

    keyboard = [
        [InlineKeyboardButton("👨 Male (ကျား)", callback_data="reg_male")],
        [InlineKeyboardButton("👩 Female (မ)", callback_data="reg_female")]
    ]
    await context.bot.send_message(
        chat_id=user_id,
        text="👋 မင်္ဂလာပါ LeoMatch မှ ကြိုဆိုပါတယ်။\nစတင်ရန် ကျေးဇူးပြု၍ သင်၏ ကျား/မ ကို ရွေးချယ်ပါ -",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def proceed_after_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_prof = get_user_profile(user_id)
    
    if user_prof and user_prof.get('profile_name'):
        await update.message.reply_text(
            f"Welcome back, {user_prof['profile_name']}! 🎉\nသင်၏ Profile အဆင်သင့် ဖြစ်နေပါပြီ။",
            reply_markup=get_main_menu()
        )
        return

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
    
    gender = query.data.split("_")[1]
    context.user_data['reg_gender'] = gender
    
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

# Target ရွေးချယ်ပြီးပါက Age (အသက်) မေးရန်
async def target_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    target = query.data.split("_")[1]
    context.user_data['reg_target'] = target
    
    await query.message.edit_text(
        "🎂 ကျေးဇူးပြု၍ သင်၏ **အသက် (Age)** ကို နံပါတ်ဖြင့် ရိုက်ထည့်ပေးပါ။ (ဥပမာ - 20)"
    )
    context.user_data['step'] = 'waiting_age'

# My Profile ပြသရန်
async def show_my_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    user_prof = get_user_profile(user_id)
    
    if not user_prof:
        await query.message.reply_text("⚠️ Profile မရှိသေးပါ။ /start ဖြင့် အစကနေ စတင်ပါ။")
        return

    caption = (
        f"👤 **Your Profile**\n\n"
        f"📝 Name: {user_prof['profile_name']}\n"
        f"🚻 Gender: {user_prof['gender']}\n"
        f"🎯 Target: {user_prof['target_gender']}\n"
        f"🎂 Age: {user_prof.get('age', 'မထည့်ရသေးပါ')}\n"
        f"📍 City: {user_prof.get('city', 'မထည့်ရသေးပါ')}\n"
        f"💬 Bio: {user_prof.get('bio', 'မရှိပါ')}"
    )
    
    if user_prof.get('media_id'):
        if user_prof.get('media_type') == 'video':
            await query.message.reply_video(video=user_prof['media_id'], caption=caption, parse_mode='Markdown', reply_markup=get_main_menu())
        else:
            await query.message.reply_photo(photo=user_prof['media_id'], caption=caption, parse_mode='Markdown', reply_markup=get_main_menu())
    else:
        await query.message.reply_text(caption, parse_mode='Markdown', reply_markup=get_main_menu())

# Edit Profile
async def edit_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("👨 Male (ကျား)", callback_data="reg_male")],
        [InlineKeyboardButton("👩 Female (မ)", callback_data="reg_female")]
    ]
    await query.message.edit_text(
        "⚙️ Profile အသစ်ပြန်ပြင်ရန် သင်၏ ကျား/မ ကို ရွေးချယ်ပါ -",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# --- Matching System ---
async def find_match(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    user_prof = get_user_profile(user_id)
    if not user_prof:
        await query.message.reply_text("⚠️ ကျေးဇူးပြု၍ ပထမဆုံး /start ဖြင့် Profile လုပ်ပါရန်။")
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
            "😔 လောလောဆယ် Profile အသစ်များ မရှိတော့ပါ။ နောက်မှ ထပ်စမ်းကြည့်ပါ။",
            reply_markup=get_main_menu()
        )
        return

    context.user_data['current_target'] = target['user_id']
    
    keyboard = [
        [InlineKeyboardButton("❤️ Like", callback_data="match_like"),
         InlineKeyboardButton("💌 Message ဖြင့် Like", callback_data="match_msg_like")],
        [InlineKeyboardButton("👎 Pass", callback_data="match_pass"),
         InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]
    ]
    
    caption = (
        f"👤 **{target['profile_name']}**\n"
        f"🚻 Gender: {target['gender']} | 🎂 Age: {target.get('age', 'N/A')}\n"
        f"📍 City: {target.get('city', 'N/A')}\n\n"
        f"💬 Bio: {target.get('bio', 'မရှိပါ')}"
    )
    
    if target.get('media_id'):
        if target.get('media_type') == 'video':
            await query.message.reply_video(video=target['media_id'], caption=caption, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await query.message.reply_photo(photo=target['media_id'], caption=caption, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await query.message.reply_text(caption, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

# Match Actions
async def match_action_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    action_type = query.data
    user_id = query.from_user.id
    target_id = context.user_data.get('current_target')

    if action_type == "main_menu":
        await query.message.edit_text("🏠 Main Menu သို့ ပြန်ရောက်ပါပြီ။", reply_markup=get_main_menu())
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
        await query.message.edit_text("💌 ဟိုဘက်လူဆီ ပို့မယ့် Message (သို့မဟုတ် Video/Photo) ကို ပို့ပေးပါ။")
        context.user_data['step'] = 'waiting_like_message'
        return

async def process_like(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id, target_id, action, custom_msg=None):
    conn = get_db_connection()
    if not conn:
        return
    cur = conn.cursor()
    
    cur.execute("INSERT INTO matches (user_id, target_id, action, message_text) VALUES (%s, %s, %s, %s) ON CONFLICT (user_id, target_id) DO UPDATE SET action = %s, message_text = %s", 
                (user_id, target_id, action, custom_msg, action, custom_msg))
    
    cur.execute("SELECT action FROM matches WHERE user_id = %s AND target_id = %s", (target_id, user_id))
    mutual = cur.fetchone()
    
    user_prof = get_user_profile(user_id)
    target_prof = get_user_profile(target_id)
    
    conn.commit()
    cur.close()
    conn.close()

    if custom_msg:
        notify_text = f"💌 **{user_prof['profile_name']} ထံမှ Like နှင့် မက်ဆေ့ချ် ရရှိထားပါသည်!**\n\n💬 Message: _{custom_msg}_"
    else:
        notify_text = f"❤️ **{user_prof['profile_name']} က သင့်ကို Like ပေးထားပါသည်။**"

    try:
        await context.bot.send_message(chat_id=target_id, text=notify_text, parse_mode='Markdown')
    except Exception:
        pass

    if mutual and mutual['action'] == 'like':
        match_msg = f"🎉 **Match Successful!** 🎉\n\nသင်နှင့် **{target_prof['profile_name']}** တို့ အပြန်အလှန် သဘောကျကြပါပြီ။"
        try:
            await update.effective_chat.send_message(match_msg)
            await context.bot.send_message(chat_id=target_id, text=match_msg)
        except Exception:
            pass

    await find_match(update, context)

# Admin Broadcast Command
async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("⚠️ ဤ Command သည် Admin အတွက်သာ ဖြစ်ပါသည်။")
        return

    context.user_data['step'] = 'waiting_broadcast_msg'
    await update.message.reply_text("📢 အများပြည်သူသို့ ပို့လိုသော ကြေညာချက် စာသား သို့မဟုတ် ပုံကို ပို့ပေးပါ။")

# Text / Media / Registration Step Handler
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # စာမပို့ခင် Channel Join ပြီးသားလား အမြဲစစ်မည်
    is_member = await check_user_channel(context.bot, user_id)
    if not is_member:
        keyboard = [
            [InlineKeyboardButton("📢 Join Official Channel", url="https://t.me/Sexstudygroupoffical_bot")],
            [InlineKeyboardButton("✅ Check Subscription", callback_data="check_sub")]
        ]
        await update.message.reply_text(
            "📢 Bot ကို အသုံးပြုရန် Official Channel ကို အရင် Join လုပ်ပေးပါ။\n\nJoin ပြီးလျှင် Check Subscription ကို နှိပ်ပါ၊၊",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    step = context.user_data.get('step')
    
    if step == 'waiting_age':
        try:
            age = int(update.message.text)
            context.user_data['reg_age'] = age
            context.user_data['step'] = 'waiting_city'
            await update.message.reply_text("📍 သင်နေထိုင်ရာ မြို့ (City) ကို ရိုက်ထည့်ပေးပါ။ (ဥပမာ - Yangon)")
        except ValueError:
            await update.message.reply_text("⚠️ ကျေးဇူးပြု၍ အသက်ကို နံပါတ်သီးသန့် (ဥပမာ - 20) ဖြင့်သာ ရိုက်ထည့်ပါ။")
        return

    elif step == 'waiting_city':
        context.user_data['reg_city'] = update.message.text
        context.user_data['step'] = 'waiting_name'
        await update.message.reply_text("✍️ ကျေးဇူးပြု၍ သင်၏ **နာမည် (Profile Name)** ကို ရိုက်ထည့်ပေးပါ။")
        return

    elif step == 'waiting_name':
        context.user_data['reg_name'] = update.message.text
        context.user_data['step'] = 'waiting_bio'
        await update.message.reply_text("💬 သင်အကြောင်း အတိုချုံး (Bio) တစ်ခုလောက် ရေးပြပေးပါ (သို့မဟုတ် ကျော်သွားချင်ရင် 'No' လို့ ရိုက်ပါ)။")
        return

    elif step == 'waiting_bio':
        bio_text = update.message.text
        context.user_data['reg_bio'] = "" if bio_text.lower() == 'no' else bio_text
        context.user_data['step'] = 'waiting_media'
        await update.message.reply_text("📸 ကျေးဇူးပြု၍ သင်၏ **ဓာတ်ပုံ သို့မဟုတ် ဗီဒီယို** တစ်ခု ပို့ပေးပါ။")
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
            
        gender = context.user_data.get('reg_gender')
        target = context.user_data.get('reg_target')
        age = context.user_data.get('reg_age')
        city = context.user_data.get('reg_city')
        name = context.user_data.get('reg_name')
        bio = context.user_data.get('reg_bio')
        
        conn = get_db_connection()
        if conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO users (user_id, profile_name, gender, target_gender, age, city, bio, media_id, media_type)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (user_id) DO UPDATE SET
                profile_name = EXCLUDED.profile_name,
                gender = EXCLUDED.gender,
                target_gender = EXCLUDED.target_gender,
                age = EXCLUDED.age,
                city = EXCLUDED.city,
                bio = EXCLUDED.bio,
                media_id = EXCLUDED.media_id,
                media_type = EXCLUDED.media_type
            """, (user_id, name, gender, target, age, city, bio, media_id, media_type))
            conn.commit()
            cur.close()
            conn.close()
            
        context.user_data.clear()
        
        await update.message.reply_text(
            "✅ သင်၏ Profile ကို အောင်မြင်စွာ သိမ်းဆည်းပြီးပါပြီ! 🎉",
            reply_markup=get_main_menu()
        )
        return

    elif step == 'waiting_like_message':
        target_id = context.user_data.get('current_target')
        msg_text = update.message.text if update.message.text else "Sent a media message"
        
        context.user_data.pop('step', None)
        await process_like(update, context, user_id, target_id, "like", custom_msg=msg_text)
        return

    elif step == 'waiting_broadcast_msg':
        context.user_data.pop('step', None)
        conn = get_db_connection()
        if not conn:
            return
        cur = conn.cursor()
        cur.execute("SELECT user_id FROM users")
        all_users = cur.fetchall()
        cur.close()
        conn.close()

        success_count = 0
        for u in all_users:
            try:
                if update.message.photo:
                    await context.bot.send_photo(chat_id=u['user_id'], photo=update.message.photo[-1].file_id, caption=update.message.caption)
                elif update.message.video:
                    await context.bot.send_video(chat_id=u['user_id'], video=update.message.video.fil
