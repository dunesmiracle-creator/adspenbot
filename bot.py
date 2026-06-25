import os
import time
import random
from datetime import datetime

import sqlite3

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler

def send_msg(update, text):
    if update.callback_query:
        return update.callback_query.message.reply_text(text)
    return update.message.reply_text(text)

BOT_TOKEN = os.getenv("BOT_TOKEN")

ADMIN_ID = 958970107

conn = sqlite3.connect("links.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS links (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT NOT NULL
)
""")

conn.commit()

COOLDOWN = 180  # 3 minutes
DAILY_LIMIT = 150

user_last_time = {}
user_daily_count = {}
user_sent_links = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "AspenBot is active and running ✅"
    )
    await show_menu(update)

async def addlink(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id != ADMIN_ID:
        await update.message.reply_text("❌ Not authorized.")
        return

    if not context.args:
        await update.message.reply_text("Usage: /addlink <url>")
        return

    new_link = " ".join(context.args).strip()

    if not new_link.startswith("http"):
        await update.message.reply_text("❌ Invalid link.")
        return

    cursor.execute("INSERT INTO links (url) VALUES (?)", (new_link,))
    conn.commit()

    await update.message.reply_text("✅ Link saved")
    
async def next_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("🔥 NEW TIMER CODE RUNNING")

    user_id = update.effective_user.id
    now = time.time()
    today = datetime.now().strftime("%Y-%m-%d")

    if user_id not in user_daily_count or user_daily_count[user_id]["date"] != today:
        user_daily_count[user_id] = {"date": today, "count": 0}
        user_sent_links[user_id] = {"date": today, "links": set()}

    if user_daily_count[user_id]["count"] >= DAILY_LIMIT:
        await update.message.reply_text("Daily limit reached.")
        return

    last = user_last_time.get(user_id, 0)

    # 🔴 COOLDOWN BLOCK (correctly indented)
    if now - last < COOLDOWN:
        remaining_seconds = int(COOLDOWN - (now - last)) // 60) + 1
        remaining_today = DAILY_LIMIT - user_daily_count[user_id]["count"]

        minutes = remaining_seconds // 60
        seconds = remaining_seconds % 60

        await update.message.reply_text(
            f"⏳ Wait {minutes}m {seconds}s\n"
            f"📊 Remaining today: {remaining_today}"
        )
        return

    # 🔵 NORMAL FLOW
    cursor.execute("SELECT url FROM links")
    links = [row[0] for row in cursor.fetchall()]

    if not links:
        await update.message.reply_text("No links available.")
        return

    sent_today = user_sent_links[user_id]["links"]

    available = [link for link in links if link not in sent_today]

    if not available:
        user_sent_links[user_id]["links"] = set()
        available = links

    link = random.choice(available)

    user_sent_links[user_id]["links"].add(link)

    user_last_time[user_id] = now
    user_daily_count[user_id]["count"] += 1

    await update.message.reply_text(f"🔗 {link}")
async def checkdb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    cursor.execute("SELECT COUNT(*) FROM links")
    count = cursor.fetchone()[0]

    await update.message.reply_text(f"Database has {count} links.")
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

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    print("BUTTON CLICKED:",query.data)
    await query.answer()

    if query.data == "next":

        cursor.execute("SELECT url FROM links")
        links = [row[0] for row in cursor.fetchall()]

        if not links:
            await query.message.reply_text("No links available.")
            return

        link = random.choice(links)

        await query.message.reply_text(f"🔗 {link}")

    elif query.data == "stats":

        cursor.execute("SELECT COUNT(*) FROM links")
        count = cursor.fetchone()[0]

        await query.message.reply_text(
            f"📊 Database has {count} links."
        )

    elif query.data == "help":

        await query.message.reply_text(
            "Use 📩 Get Link to receive an ad."
        )

async def migrate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    try:
        with open("links.txt", "r") as f:
            links = [line.strip() for line in f if line.strip()]

        count = 0
        for link in links:
            cursor.execute("INSERT INTO links (url) VALUES (?)", (link,))
            count += 1

        conn.commit()

        await update.message.reply_text(f"✅ Migrated {count} links into database.")

    except Exception as e:
        await update.message.reply_text(f"❌ Migration failed: {e}")
    
def main():
    print("BOT STARTING...")

    if not BOT_TOKEN:
        print("ERROR: BOT_TOKEN not found")
        return

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.bot.delete_webhook(drop_pending_updates=True)

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("next", next_link))
    app.add_handler(CommandHandler("addlink", addlink))
    app.add_handler(CommandHandler("checkdb", checkdb))
    app.add_handler(CommandHandler("migrate", migrate))
    app.add_handler(CallbackQueryHandler(button_handler))

    print("BOT RUNNING...")
    app.run_polling()


if __name__ == "__main__":
    main()
