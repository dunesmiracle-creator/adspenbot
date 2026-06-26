import os
import time
import random
from datetime import datetime

import psycopg2
from psycopg2.extras import RealDictCursor

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler


# ---------------- CONFIG ----------------
BOT_TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")

ADMIN_ID = 958970107

COOLDOWN = 180  # seconds
DAILY_LIMIT = 150


# ---------------- DATABASE ----------------
conn = psycopg2.connect(DATABASE_URL)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS links (
    id SERIAL PRIMARY KEY,
    url TEXT NOT NULL
)
""")
conn.commit()


# ---------------- MEMORY STORAGE ----------------
user_last_time = {}
user_daily_count = {}
user_sent_links = {}


# ---------------- MENU ----------------
async def show_menu(update: Update):
    keyboard = [
        [InlineKeyboardButton("📩 Get Link", callback_data="next")],
        [InlineKeyboardButton("📊 Stats", callback_data="stats")],
        [InlineKeyboardButton("ℹ️ Help", callback_data="help")]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "🚀 AspenBot Menu",
        reply_markup=reply_markup
    )


# ---------------- START ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("AspenBot is active and running ✅")
    await show_menu(update)


# ---------------- CORE LOGIC ----------------
async def send_next_link(update, user_id):
    now = time.time()
    today = datetime.now().strftime("%Y-%m-%d")

    # reset daily tracking
    if user_id not in user_daily_count or user_daily_count[user_id]["date"] != today:
        user_daily_count[user_id] = {"date": today, "count": 0}
        user_sent_links[user_id] = {"date": today, "links": set()}

    # daily limit
    if user_daily_count[user_id]["count"] >= DAILY_LIMIT:
        await update.message.reply_text("Daily limit reached.")
        return

    last = user_last_time.get(user_id, 0)

    # cooldown check
if now - last < COOLDOWN:
    remaining_seconds = int(COOLDOWN - (now - last))
    remaining_today = DAILY_LIMIT - user_daily_count[user_id]["count"]

    minutes = remaining_seconds // 60
    seconds = remaining_seconds % 60

    await update.message.reply_text(
        f"⏳ Wait {minutes}m {seconds}s\n"
        f"📊 Remaining today: {remaining_today}"
    )
    return
    
    # fetch links
    cursor.execute("SELECT url FROM links")
    rows = cursor.fetchall()

    links = [r[0] for r in rows]

    if not links:
        await update.message.reply_text("No links available.")
        return

    sent = user_sent_links[user_id]["links"]
    available = [l for l in links if l not in sent]

    if not available:
        user_sent_links[user_id]["links"] = set()
        available = links

    link = random.choice(available)

    # update state
    user_sent_links[user_id]["links"].add(link)
    user_last_time[user_id] = now
    user_daily_count[user_id]["count"] += 1

    await update.message.reply_text(f"🔗 {link}")


# ---------------- COMMAND ----------------
async def next_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("🔥 next_link triggered")
    await send_next_link(update, update.effective_user.id)


# ---------------- BUTTONS ----------------
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "next":
        await send_next_link(query, query.from_user.id)

    elif query.data == "stats":
        cursor.execute("SELECT COUNT(*) FROM links")
        count = cursor.fetchone()[0]

        await query.message.reply_text(f"📊 Database has {count} links.")

    elif query.data == "help":
        await query.message.reply_text("Use 📩 Get Link to receive a link.")


# ---------------- ADD LINK ----------------
async def addlink(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id != ADMIN_ID:
        await update.message.reply_text("❌ Not authorized.")
        return

    if not context.args:
        await update.message.reply_text("Usage: /addlink <url>")
        return

    link = " ".join(context.args).strip()

    if not link.startswith("http"):
        await update.message.reply_text("❌ Invalid link.")
        return

    cursor.execute("INSERT INTO links (url) VALUES (%s)", (link,))
    conn.commit()

    await update.message.reply_text("✅ Link saved")


# ---------------- CHECK DB ----------------
async def checkdb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    cursor.execute("SELECT COUNT(*) FROM links")
    count = cursor.fetchone()[0]

    await update.message.reply_text(f"Database has {count} links.")


# ---------------- MAIN ----------------
def main():
    print("BOT STARTING...")

    if not BOT_TOKEN or not DATABASE_URL:
        print("Missing BOT_TOKEN or DATABASE_URL")
        return

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.bot.delete_webhook(drop_pending_updates=True)

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("next", next_link))
    app.add_handler(CommandHandler("addlink", addlink))
    app.add_handler(CommandHandler("checkdb", checkdb))
    app.add_handler(CallbackQueryHandler(button_handler))

    print("BOT RUNNING...")
    app.run_polling()


if __name__ == "__main__":
    main()
