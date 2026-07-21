import os
import asyncio
import threading
from flask import Flask, render_template

app = Flask(__name__)

BOT_TOKEN  = os.environ.get("BOT_TOKEN")
PORT       = int(os.environ.get("PORT", 8000))
WEBAPP_URL = f"https://{os.environ.get('REPLIT_DEV_DOMAIN', 'localhost')}"


@app.route("/")
def index():
    return render_template("index.html")


# ── Bot (runs in a background thread with its own event loop) ──

async def _bot_main():
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo, MenuButtonWebApp
    from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
    from telegram import Update

    async def send_play(update: Update, context: ContextTypes.DEFAULT_TYPE):
        keyboard = [[InlineKeyboardButton(
            "🎲 ቢንጎ ጫወት!",
            web_app=WebAppInfo(url=WEBAPP_URL)
        )]]
        await update.message.reply_text(
            "🎲 *እንኳን ወደ አማርኛ ቢንጎ!*\n\n"
            "ከዚህ በታች ያለውን ቁልፍ ጫን ጨዋታውን ለመጀመር:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )

    bot_app = ApplicationBuilder().token(BOT_TOKEN).build()
    bot_app.add_handler(CommandHandler("start", send_play))
    bot_app.add_handler(CommandHandler("play",  send_play))

    await bot_app.initialize()

    # Set the menu button so Telegram shows a web-app launch button
    try:
        await bot_app.bot.set_chat_menu_button(
            menu_button=MenuButtonWebApp(
                text="🎲 ቢንጎ",
                web_app=WebAppInfo(url=WEBAPP_URL)
            )
        )
        print(f"Menu button set → {WEBAPP_URL}")
    except Exception as e:
        print(f"Menu button warning: {e}")

    await bot_app.start()
    await bot_app.updater.start_polling()
    print("Bot polling started.")

    # Keep the coroutine alive until the thread is cancelled
    await asyncio.Event().wait()


def run_bot():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(_bot_main())
    except Exception as e:
        print(f"Bot error: {e}")
    finally:
        loop.close()


if __name__ == "__main__":
    if BOT_TOKEN:
        t = threading.Thread(target=run_bot, daemon=True)
        t.start()
    else:
        print("Warning: BOT_TOKEN not set — bot not started.")

    print(f"Flask server starting on port {PORT}")
    app.run(host="0.0.0.0", port=PORT, debug=False)
