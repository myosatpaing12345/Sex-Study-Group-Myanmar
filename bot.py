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
            [[KeyboardButton(user_profile["
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
            [[KeyboardButton(user_profile["
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
           
