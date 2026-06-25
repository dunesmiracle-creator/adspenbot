import os
import time
import random
from datetime import datetime
import sqlite3

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    CallbackQueryHandler
)

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 958970107

# ================= DB =================
conn = sqlite3.connect("links.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS links (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT NOT NULL
)
""")
conn.commit()

# ================= SETTINGS =================
COOLDOWN = 180
DAILY_LIMIT = 150

user_last_time = {}
user_daily_count = {}
user_sent_links = {}

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🚀 AspenBot is active and running ✅")
    await show_menu(update)

# ================= ADD LINK =================
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

# ================= NEXT LINK =================
async def next_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    now = time.time()
    today = datetime.now().strftime("%Y-%m-%d")

    # reset daily tracking
    if user_id not in user_daily_count or user_daily_count[user_id].get("date") != today:
        user_daily_count[user_id] = {"date": today, "count": 0}
        user_sent_links[user_id] = set()

    # daily limit
    if user_daily_count[user_id]["count"] >= DAILY_LIMIT:
        await update.message.reply_text("Daily limit reached.")
        return

    # cooldown
    last = user_last_time.get(user_id, 0)
    if now - last < COOLDOWN:
        remaining = int((COOLDOWN - (now - last)) // 60) + 1
        remaining_today = DAILY_LIMIT - user_daily_count[user_id]["count"]

        await update.message.reply_text(
            f"⏳ Wait {remaining} min\n📊 Remaining today: {remaining_today}"
        )
        return

    # DB fetch
    cursor.execute("SELECT url FROM links")
    links = [row[0] for row in cursor.fetchall()]

    if not links:
        await update.message.reply_text("No links available.")
        return

    sent_today = user_sent_links[user_id]

    available = [l for l in links if l not in sent_today]

    if not available:
        user_sent_links[user_id] = set()
        available = links

    link = random.choice(available)

    user_sent_links[user_id].add(link)

    user_last_time[user_id] = now
    user_daily_count[user_id]["count"] += 1

    await update.message.reply_text(f"🔗 {link}")

# ================= STATS =================
async def checkdb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    cursor.execute("SELECT COUNT(*) FROM links")
    count = cursor.fetchone()[0]

    await update.message.reply_text(f"📊 Database has {count} links")

# ================= MENU =================
async def show_menu(update: Update):
    keyboard = [
        [InlineKeyboardButton("📩 Get Link", callback_data="next")],
        [InlineKeyboardButton("📊 Stats", callback_data="stats")],
        [InlineKeyboardButton("ℹ️ Help", callback_data="help")]
    ]

    await update.message.reply_text(
        "🚀 AspenBot Menu",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ================= BUTTON HANDLER =================
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "next":
        await next_link(update, context)

    elif query.data == "stats":
        cursor.execute("SELECT COUNT(*) FROM links")
        count = cursor.fetchone()[0]
        await query.message.reply_text(f"📊 Total links: {count}")

    elif query.data == "help":
        await query.message.reply_text("Use /addlink (admin) or press Get Link")

# ================= MAIN =================
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

    app.add_handler(CallbackQueryHandler(button_handler))

    print("BOT RUNNING...")
    app.run_polling()

if __name__ == "__main__":
    main()
