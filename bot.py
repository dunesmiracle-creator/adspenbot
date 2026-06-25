import os
import time
import random
from datetime import datetime

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

BOT_TOKEN = os.getenv("BOT_TOKEN")

ADMIN_ID = 958970107

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

    with open("links.txt", "a") as f:
        f.write(new_link + "\n")

    await update.message.reply_text("✅ Link added")


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
            f"⏳ Wait {remaining} min\n📊 Remaining today: {remaining_today}"
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

    print("BOT RUNNING...")
    app.run_polling()


if __name__ == "__main__":
    main()
