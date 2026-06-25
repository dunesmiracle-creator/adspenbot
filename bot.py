import os
import time
import random
from datetime import datetime

import sqlite3

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

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

def load_links():
    try:
        with open("links.txt", "r") as f:
            return [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        return []

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("AspenBot is active and running ✅")

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

    await update.message.reply_text("✅ Link saved to database")
    
async def next_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cursor.execute("SELECT id, url FROM links")
    rows = cursor.fetchall()

    if not rows:
        await update.message.reply_text("No links available.")
        return

    selected = random.choice(rows)

    link = selected[1]

    await update.message.reply_text(f"🔗 {link}")

    last = user_last_time.get(user_id, 0)
    if now - last < COOLDOWN:
        remaining = int((COOLDOWN - (now - last)) // 60) + 1
        remaining_today = DAILY_LIMIT - user_daily_count[user_id]["count"]

        await update.message.reply_text(
            f"⏳ Wait {remaining} min\n📊 Remaining today: {remaining_today}"
        )
        return

    async def checkdb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    cursor.execute("SELECT COUNT(*) FROM links")
    count = cursor.fetchone()[0]

    await update.message.reply_text(f"Database has {count} links.")

    # DATABASE LOGIC STARTS HERE
    cursor.execute("SELECT id, url FROM links")
    rows = cursor.fetchall()

    if not rows:
        await update.message.reply_text("No links available.")
        return

    selected = random.choice(rows)
    link = selected[1]

    user_last_time[user_id] = now
    user_daily_count[user_id]["count"] += 1

    await update.message.reply_text(f"🔗 {link}")

    links = load_links()
    available = [l for l in links if l not in user_sent_links[user_id]]

    if not available:
        await update.message.reply_text("No links left.")
        return

    link = random.choice(available)

    user_sent_links[user_id].add(link)
    user_last_time[user_id] = now
    user_daily_count[user_id]["count"] += 1

    remaining_today = DAILY_LIMIT - user_daily_count[user_id]["count"]

    await update.message.reply_text(
        f"✅ Your link:\n{link}\n\n"
        f"⏳ Next link in 3 min\n"
        f"📊 Remaining today: {remaining_today}"
    )

def main():
    print("BOT STARTING...")

    if not BOT_TOKEN:
        print("ERROR: BOT_TOKEN not found")
        return

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("next", next_link))
    app.add_handler(CommandHandler("addlink", addlink))
    app.add_handler(CommandHandler("checkdb", checkdb))

    print("BOT RUNNING...")
    app.run_polling()


if __name__ == "__main__":
    main()
