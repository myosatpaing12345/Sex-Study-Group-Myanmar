import os
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove,
)

from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

import psycopg2
from psycopg2.extras import RealDictCursor


# ---------------- LOG ---------------- #

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)


# ---------------- DATABASE ---------------- #

DATABASE_URL = os.environ.get("DATABASE_URL")


def get_db_connection():
    if not DATABASE_URL:
        logger.error("DATABASE_URL not found!")
        return None

    return psycopg2.connect(
        DATABASE_URL,
        cursor_factory=RealDictCursor,
    )


def init_db():
    conn = get_db_connection()

    if not conn:
        return

    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users(
            user_id BIGINT PRIMARY KEY,
            profile_name TEXT,
            age TEXT,
            gender TEXT,
            target_gender TEXT,
            bio TEXT,
            media_id TEXT,
            media_type TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS matches(
            user_id BIGINT,
            target_id BIGINT,
            action TEXT,
            message_text TEXT,
            PRIMARY KEY(user_id,target_id)
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

    cur.execute(
        "SELECT * FROM users WHERE user_id=%s",
        (user_id,)
    )

    user = cur.fetchone()

    cur.close()
    conn.close()

    return user


def get_main_menu():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "🔍 Find Match",
                callback_data="find_match"
            )
        ],
        [
            InlineKeyboardButton(
                "👤 My Profile",
                callback_data="my_profile"
            ),
            InlineKeyboardButton(
                "⚙️ Edit Profile",
                callback_data="edit_profile"
            ),
        ],
    ])


# ---------------- START ---------------- #

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user
    user_profile = get_user_profile(user.id)

    if user_profile and user_profile.get("profile_name"):

        age = user_profile.get("age", "18")

        keyboard = ReplyKeyboardMarkup(
            [[KeyboardButton(str(age))]],
            resize_keyboard=True,
            one_time_keyboard=True,
        )

        await update.message.reply_text(
            "Welcome back Sex Study Group Myanmar 🎉\n\n"
            "How old are you?\n\n"
            "⚠️ Profiles with an inaccurate age may be restricted.",
            reply_markup=keyboard,
        )

    else:

        await update.message.reply_text(
            "Welcome to Sex Study Group Myanmar 🎉\n\n"
            "How old are you?\n\n"
            "⚠️ Profiles with an inaccurate age may be restricted.",
            reply_markup=ReplyKeyboardRemove(),
        )

    context.user_data["step"] = "waiting_age"


# ---------------- AGE ---------------- #

async def handle_age(update: Update, context: ContextTypes.DEFAULT_TYPE):

    context.user_data["reg_age"] = update.message.text

    keyboard = ReplyKeyboardMarkup(
        [
            [
                KeyboardButton("👨 Male"),
                KeyboardButton("👩 Female"),
            ]
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )

    await update.message.reply_text(
        "To get started, please select your gender:",
        reply_markup=keyboard,
    )

    context.user_data["step"] = "waiting_gender"


# ---------------- GENDER ---------------- #

async def gender_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = update.message.text

    if "Male" in text:
        gender = "male"

    elif "Female" in text:
        gender = "female"

    else:
        return

    context.user_data["reg_gender"] = gender

    keyboard = ReplyKeyboardMarkup(
        [
            [
                KeyboardButton("👨 Male"),
                KeyboardButton("👩 Female"),
            ],
            [
                KeyboardButton("🌐 No matter")
            ]
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )

    await update.message.reply_text(
        "🎯 Who are you looking for?",
        reply_markup=keyboard,
    )

    context.user_data["step"] = "waiting_target"


# ---------------- TARGET ---------------- #

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

    context.user_data["reg_target"] = target

    user_profile = get_user_profile(update.effective_user.id)

    if user_profile and user_profile.get("profile_name"):

        keyboard = ReplyKeyboardMarkup(
            [[KeyboardButton(user_profile["profile_name"])]],
            resize_keyboard=True,
            one_time_keyboard=True,
        )

    else:

        keyboard = ReplyKeyboardRemove()

    await update.message.reply_text(
        "✍️ Please enter your Profile Name:",
        reply_markup=keyboard,
    )

    context.user_data["step"] = "waiting_name"


# ---------------- NAME HANDLER ---------------- #

async def name_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["reg_name"] = update.message.text
    context.user_data["step"] = "waiting_media"

    keyboard = ReplyKeyboardMarkup(
        [
            [KeyboardButton("Leave current")],
            [KeyboardButton("Take from my Telegram profile")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )

    await update.message.reply_text(
        "📸 Please send your photo or video for your profile, or choose an option below:",
        reply_markup=keyboard,
    )


# ---------------- MESSAGE ROUTER ---------------- #

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    step = context.user_data.get("step")

    if step == "waiting_age":
        await handle_age(update, context)
    elif step == "waiting_gender":
        await gender_text_handler(update, context)
    elif step == "waiting_target":
        await target_text_handler(update, context)
    elif step == "waiting_name":
        await name_text_handler(update, context)
    elif step == "waiting_media" or update.message.photo or update.message.video or update.message.text in ["Leave current", "Take from my Telegram profile"]:
        await handle_media_input(update, context)
    elif step == "waiting_like_message":
        target_id = context.user_data.get("current_target")
        user_id = update.effective_user.id
        custom_msg = update.message.text
        context.user_data["step"] = None
        await process_like(update, context, user_id, target_id, "like", custom_msg)
    else:
        await start(update, context)


# ---------------- MY PROFILE ---------------- #

async def show_my_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    user = get_user_profile(query.from_user.id)

    if not user:
        await query.message.reply_text(
            "⚠️ Profile not found.\nUse /start first."
        )
        return

    caption = (
        f"👤 **Your Profile**\n\n"
        f"📝 Name : {user['profile_name']}\n"
        f"🎂 Age : {user.get('age','N/A')}\n"
        f"🚻 Gender : {user['gender']}\n"
        f"🎯 Looking For : {user['target_gender']}"
    )

    if user.get("media_id"):

        if user.get("media_type") == "video":

            await query.message.reply_video(
                video=user["media_id"],
                caption=caption,
                parse_mode="Markdown",
                reply_markup=get_main_menu(),
            )

        else:

            await query.message.reply_photo(
                photo=user["media_id"],
                caption=caption,
                parse_mode="Markdown",
                reply_markup=get_main_menu(),
            )

    else:

        await query.message.reply_text(
            caption,
            parse_mode="Markdown",
            reply_markup=get_main_menu(),
        )


# ---------------- EDIT PROFILE ---------------- #

async def edit_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    user = get_user_profile(query.from_user.id)

    if user and user.get("age"):

        keyboard = ReplyKeyboardMarkup(
            [[KeyboardButton(str(user["age"]))]],
            resize_keyboard=True,
            one_time_keyboard=True,
        )

    else:

        keyboard = ReplyKeyboardRemove()

    await query.message.reply_text(
        "How old are you?\n\n"
        "⚠️ Profiles with an inaccurate age may be restricted.",
        reply_markup=keyboard,
    )

    context.user_data["step"] = "waiting_age"


# ---------------- FIND MATCH ---------------- #

async def find_match(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id

    my_profile = get_user_profile(user_id)

    if not my_profile:

        await query.message.reply_text(
            "⚠️ Please create your profile first.\nUse /start"
        )
        return

    conn = get_db_connection()

    if not conn:
        return

    cur = conn.cursor()

    cur.execute(
        """
        SELECT *
        FROM users
        WHERE user_id != %s
        AND user_id NOT IN(
            SELECT target_id
            FROM matches
            WHERE user_id=%s
        )
        LIMIT 1
        """,
        (user_id, user_id),
    )

    target = cur.fetchone()

    cur.close()
    conn.close()

    if not target:

        await query.message.reply_text(
            "😔 No more new profiles available.",
            reply_markup=get_main_menu(),
        )

        return

    context.user_data["current_target"] = target["user_id"]

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "❤️ Like",
                callback_data="match_like",
            ),
            InlineKeyboardButton(
                "💌 Message with Like",
                callback_data="match_msg_like",
            ),
        ],
        [
            InlineKeyboardButton(
                "👎 Pass",
                callback_data="match_pass",
            ),
            InlineKeyboardButton(
                "🏠 Main Menu",
                callback_data="main_menu",
            ),
        ],
    ])

    caption = (
        f"👤 **{target['profile_name']}**\n"
        f"🎂 Age : {target.get('age','N/A')}\n"
        f"🚻 Gender : {target['gender']}"
    )

    if target.get("media_id"):

        if target.get("media_type") == "video":

            await query.message.reply_video(
                video=target["media_id"],
                caption=caption,
                parse_mode="Markdown",
                reply_markup=keyboard,
            )

        else:

            await query.message.reply_photo(
                photo=target["media_id"],
                caption=caption,
                parse_mode="Markdown",
                reply_markup=keyboard,
            )

    else:

        await query.message.reply_text(
            caption,
            parse_mode="Markdown",
            reply_markup=keyboard,
        )


# ---------------- MATCH ACTION ---------------- #

async def match_action_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    action = query.data

    user_id = query.from_user.id
    target_id = context.user_data.get("current_target")

    if not target_id:
        await query.message.reply_text(
            "⚠️ Target profile not found."
        )
        return

    if action == "main_menu":

        await query.message.reply_text(
            "🏠 Main Menu",
            reply_markup=get_main_menu(),
        )
        return

    if action == "match_pass":

        conn = get_db_connection()

        if conn:

            cur = conn.cursor()

            cur.execute(
                """
                INSERT INTO matches(user_id,target_id,action)
                VALUES(%s,%s,'pass')
                ON CONFLICT(user_id,target_id)
                DO UPDATE SET action='pass'
                """,
                (user_id, target_id),
            )

            conn.commit()

            cur.close()
            conn.close()

        await find_match(update, context)
        return

    if action == "match_like":

        await process_like(
            update,
            context,
            user_id,
            target_id,
            "like",
        )

        return

    if action == "match_msg_like":

        context.user_data["step"] = "waiting_like_message"

        await query.message.reply_text(
            "💌 Send your message.\n\n"
            "You can also send a photo or video."
        )

        return


# ---------------- PROCESS LIKE ---------------- #

async def process_like(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    user_id,
    target_id,
    action,
    custom_msg=None,
):

    conn = get_db_connection()

    if not conn:
        return

    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO matches(
            user_id,
            target_id,
            action,
            message_text
        )
        VALUES(%s,%s,%s,%s)

        ON CONFLICT(user_id,target_id)

        DO UPDATE SET

        action=EXCLUDED.action,
        message_text=EXCLUDED.message_text
        """,
        (
            user_id,
            target_id,
            action,
            custom_msg,
        ),
    )

    cur.execute(
        """
        SELECT action
        FROM matches
        WHERE user_id=%s
        AND target_id=%s
        """,
        (
            target_id,
            user_id,
        ),
    )

    mutual = cur.fetchone()

    conn.commit()

    cur.close()
    conn.close()

    my_profile = get_user_profile(user_id)
    target_profile = get_user_profile(target_id)

    if custom_msg:

        text = (
            f"💌 {my_profile['profile_name']} "
            f"liked you.\n\n"
            f"Message:\n{custom_msg}"
        )

    else:

        text = (
            f"❤️ {my_profile['profile_name']} "
            f"liked your profile."
        )

    try:

        await context.bot.send_message(
            chat_id=target_id,
            text=text,
        )

    except Exception:
        pass

    if mutual and mutual["action"] == "like":

        match_text = (
            "🎉 Match Successful!\n\n"
            f"You and {target_profile['profile_name']} "
            "liked each other ❤️"
        )

        try:

            await context.bot.send_message(
                chat_id=user_id,
                text=match_text,
            )

            await context.bot.send_message(
                chat_id=target_id,
                text=match_text,
            )

        except Exception:
            pass

    await find_match(update, context)


# ---------------- MEDIA INPUT ---------------- #

async def handle_media_input(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = update.effective_user.id

    media_id = None
    media_type = "photo"

    text = update.message.text if update.message.text else ""

    # Leave current
    if text == "Leave current":

        user = get_user_profile(user_id)

        if user and user.get("media_id"):

            media_id = user["media_id"]
            media_type = user.get("media_type", "photo")

        else:

            await update.message.reply_text(
                "⚠️ Current photo not found."
            )
            return

    # Telegram Profile
    elif text == "Take from my Telegram profile":

        photos = await context.bot.get_user_profile_photos(
            user_id=user_id,
            limit=1,
        )

        if photos.total_count == 0:

            await update.message.reply_text(
                "⚠️ You don't have a Telegram profile photo."
            )
            return

        media_id = photos.photos[0][-1].file_id
        media_type = "photo"

    # User sent Photo
    elif update.message.photo:

        media_id = update.message.photo[-1].file_id
        media_type = "photo"

    # User sent Video
    elif update.message.video:

        media_id = update.message.video.file_id
        media_type = "video"

    else:

        await update.message.reply_text(
            "⚠️ Please send a photo or video."
        )
        return

    age = context.user_data.get("reg_age")
    gender = context.user_data.get("reg_gender")
    target = context.user_data.get("reg_target")
    name = context.user_data.get("reg_name")

    if not all([age, gender, target, name]):

        old = get_user_profile(user_id)

        if old:

            age = age or old["age"]
            gender = gender or old["gender"]
            target = target or old["target_gender"]
            name = name or old["profile_name"]

    conn = get_db_connection()

    if conn:

        cur = conn.cursor()

        cur.execute("""
            INSERT INTO users(
                user_id,
                profile_name,
                age,
                gender,
                target_gender,
                media_id,
                media_type
            )

            VALUES(%s,%s,%s,%s,%s,%s,%s)

            ON CONFLICT(user_id)

            DO UPDATE SET

            profile_name=EXCLUDED.profile_name,
            age=EXCLUDED.age,
            gender=EXCLUDED.gender,
            target_gender=EXCLUDED.target_gender,
            media_id=EXCLUDED.media_id,
            media_type=EXCLUDED.media_type
        """,
        (
            user_id,
            name,
            age,
            gender,
            target,
            media_id,
            media_type,
        ))

        conn.commit()

        cur.close()
        conn.close()

    context.user_data.clear()

    await update.message.reply_text(
        "✅ Your profile has been saved successfully.",
        reply_markup=ReplyKeyboardRemove(),
    )

    await update.message.reply_text(
        "🏠 Main Menu",
        reply_markup=get_main_menu(),
    )


# ---------------- RENDER KEEP-ALIVE HTTP SERVER ---------------- #

class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running successfully!")

    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()

def run_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), SimpleHandler)
    server.serve_forever()


# ---------------- MAIN FUNCTION (BOT START) ---------------- #

if __name__ == "__main__":
    # Start HTTP server in a background thread so Render detects an active port and avoids early exit error
    threading.Thread(target=run_server, daemon=True).start()

    TOKEN = "8905518813:AAGfks_BGJM_g3uj0qu8ElzI0K3b6vFVj7Q"

    application = Application.builder().token(TOKEN).build()

    # Register Handlers
    application.add_handler(CommandHand
