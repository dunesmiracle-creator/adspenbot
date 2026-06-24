import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# Get token from Railway environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN")


# /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bot is alive ✅ AspenBot is running.")


# simple test command
async def next_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Next command received ✅")


def main():
    print("BOT STARTING...")

    # safety check
    if not BOT_TOKEN:
        print("ERROR: BOT_TOKEN not found")
        return

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("next", next_cmd))

    print("BOT RUNNING...")
    app.run_polling()


if __name__ == "__main__":
    main()
