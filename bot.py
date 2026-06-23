import time
import random
from datetime import datetime

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

import os

BOT_TOKEN = os.getenv("BOT_TOKEN")

COOLDOWN = 180
DAILY_LIMIT = 150
ADMIN_ID = 958970107

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
    await update.message.reply_text("Bot is running. Use /next")

async def addlink(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("You are not authorized.")
        return

    if not context.args:
        await update.message.reply_text("Usage:\n/addlink https://your-link")
        return

    new_link = " ".join(context.args).strip()

    import os

    file_path = os.path.abspath("links.txt")
    print("Writing to:", file_path)

    with open(file_path, "a") as f:
        f.write("\n" + new_link)

    await update.message.reply_text("✅ Link added successfully.")

async def next_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    now = time.time()
    today = datetime.now().strftime("%Y-%m-%d")

    if user_id not in user_daily_count or user_daily_count[user_id]["date"] != today:
        user_daily_count[user_id] = {"date": today, "count": 0}
        user_sent_links[user_id] = set()

    if user_daily_count[user_id]["count"] >= DAILY_LIMIT:
        await update.message.reply_text("Daily limit reached.")
        return

    last = user_last_time.get(user_id, 0)
    if now - last < COOLDOWN:
        remaining = int((COOLDOWN - (now - last)) // 60) + 1
        remaining_today = DAILY_LIMIT - user_daily_count[user_id]["count"]

        await update.message.reply_text(
            f"⏳ Next link available in {remaining} minutes.\n"
            f"📊 Remaining today: {remaining_today}"
        )
        return
    

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
        f"⏳ Next link available in 3 minutes.\n"
        f"📊 Remaining today: {remaining_today}"
    )

def main():
    print("BOT STARTING...")
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("next", next_link))
    app.add_handler(CommandHandler("addlink", addlink))

    print("BOT RUNNING...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
