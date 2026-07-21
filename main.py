import os
import random
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

TOKEN = os.environ.get("BOT_TOKEN")

# የጨዋታው ግዛት (Game State)
game_data = {
    "is_active": False,
    "called_numbers": [],
    "players": {},  # user_id: {"name": str, "card": list, "marked": set}
    "caller_task": None
}

def get_letter(num):
    if 1 <= num <= 15: return "B (ቢ)"
    elif 16 <= num <= 30: return "I (አይ)"
    elif 31 <= num <= 45: return "N (ኤን)"
    elif 46 <= num <= 60: return "G (ጂ)"
    else: return "O (ኦ)"

def generate_card():
    col_b = random.sample(range(1, 16), 5)
    col_i = random.sample(range(16, 31), 5)
    col_n = random.sample(range(31, 46), 5)
    col_g = random.sample(range(46, 61), 5)
    col_o = random.sample(range(61, 76), 5)

    col_n[2] = "FREE"  # የመካከለኛው ነፃ ቦታ

    # Grid construction (5x5)
    card = []
    for r in range(5):
        row = [str(col_b[r]), str(col_i[r]), str(col_n[r]), str(col_g[r]), str(col_o[r])]
        card.append(row)
    return card

def build_keyboard(user_id):
    player = game_data["players"][user_id]
    card = player["card"]
    marked = player["marked"]

    keyboard = []
    # Header Row
    keyboard.append([InlineKeyboardButton(col, callback_data="none") for col in ["B", "I", "N", "G", "O"]])

    for r in range(5):
        row_buttons = []
        for c in range(5):
            val = card[r][c]
            cell_key = f"{r}_{c}"

            if val == "FREE" or cell_key in marked:
                display = f"❌ {val}" if val != "FREE" else "⭐ FREE"
            else:
                display = val

            row_buttons.append(InlineKeyboardButton(display, callback_data=f"mark_{r}_{c}"))
        keyboard.append(row_buttons)

    # Bingo Win Claim Button
    keyboard.append([InlineKeyboardButton("🏆 BINGO! (አሸንፌአለሁ ቼክ አድርግ)", callback_data="claim_win")])
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "🎲 **እንኳን ወደ አማርኛ ቢንጎ ጨዋታ በደህና መጡ!** 🎲\n\n"
        "ተጫዋቾች ለመግባት: /join ይበሉ\n"
        "ጨዋታውን ለማስጀመር: /startgame ይበሉ\n"
        "ጨዋታውን ለማቋረጥ: /stopgame ይበሉ"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

async def join_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id in game_data["players"]:
        await update.message.reply_text(f"አቶ/ወ/ሮ {user.first_name}፣ አስቀድመው ተመዝግበዋል!")
        return

    game_data["players"][user.id] = {
        "name": user.first_name,
        "card": generate_card(),
        "marked": {"2_2"}  # FREE space automatically marked
    }

    await update.message.reply_text(
        f"✅ {user.first_name} ወደ ጨዋታው ተቀላቅለዋል!\n"
        f"አጠቃላይ ተጫዋቾች፡ {len(game_data['players'])}።\n"
        "ካርድዎን ለማየት /mycard ይበሉ።"
    )

async def show_my_card(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in game_data["players"]:
        await update.message.reply_text("ገና አልተመዘገቡም! መጀመሪያ /join ይበሉ።")
        return

    reply_markup = build_keyboard(user_id)
    await update.message.reply_text("🎲 **የእርስዎ የቢንጎ ካርድ፦**", reply_markup=reply_markup, parse_mode="Markdown")

async def number_caller(context: ContextTypes.DEFAULT_TYPE, chat_id):
    all_numbers = list(range(1, 76))
    random.shuffle(all_numbers)

    for num in all_numbers:
        if not game_data["is_active"]:
            break

        letter = get_letter(num)
        game_data["called_numbers"].append(num)

        call_msg = f"📣 **የተጠራ ቁጥር፦** {letter} {num}"
        await context.bot.send_message(chat_id=chat_id, text=call_msg, parse_mode="Markdown")

        await asyncio.sleep(5)  # በየ 5 ሰከንዱ ቁጥር ይጠራል

async def start_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if game_data["is_active"]:
        await update.message.reply_text("ጨዋታው bereits ተጀምሯል!")
        return

    if len(game_data["players"]) == 0:
        await update.message.reply_text("ቢያንስ 1 ተጫዋች መመዝገብ አለበት! መጀመሪያ /join ይበሉ።")
        return

    game_data["is_active"] = True
    game_data["called_numbers"] = []

    await update.message.reply_text("🚀 **ጨዋታው ተጀምሯል! ቁጥሮች መጠራት ይጀምራሉ...**\nካርድዎን ለመመልከት /mycard ይበሉ።")

    # Start async number generator loop
    asyncio.create_task(number_caller(context, update.effective_chat.id))

async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    data = query.data

    await query.answer()

    if user_id not in game_data["players"]:
        return

    player = game_data["players"][user_id]

    if data.startswith("mark_"):
        _, r, c = data.split("_")
        r, c = int(r), int(c)
        val = player["card"][r][c]

        if val != "FREE" and int(val) not in game_data["called_numbers"]:
            await query.answer("⚠️ ይህ ቁጥር ገና አልተጠራም!", show_alert=True)
            return

        cell_key = f"{r}_{c}"
        if cell_key in player["marked"]:
            player["marked"].remove(cell_key)
        else:
            player["marked"].add(cell_key)

        reply_markup = build_keyboard(user_id)
        await query.edit_message_reply_markup(reply_markup=reply_markup)

    elif data == "claim_win":
        if check_win(player):
            game_data["is_active"] = False
            winner_name = player["name"]
            await query.message.reply_text(f"🎉🎉 **ቢንጎ! BINGO!** 🎉🎉\n\nአሸናፊ፦ **{winner_name}**!\nእንኳን ደስ አለዎት! ጨዋታው ተጠናቋል! 🏆")
        else:
            await query.answer("❌ ገና አልሞሉም! መስመሮቹን ደግመው ያረጋግጡ።", show_alert=True)

def check_win(player):
    marked = player["marked"]

    # Rows & Columns check
    for i in range(5):
        if all(f"{i}_{j}" in marked for j in range(5)): return True
        if all(f"{j}_{i}" in marked for j in range(5)): return True

    # Diagonals check
    if all(f"{i}_{i}" in marked for i in range(5)): return True
    if all(f"{i}_{4-i}" in marked for i in range(5)): return True

    return False

async def stop_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    game_data["is_active"] = False
    game_data["players"] = {}
    game_data["called_numbers"] = []
    await update.message.reply_text("🛑 ጨዋታው ቆሟል፤ ሁሉም ዳታዎች ጸድተዋል።")

if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("join", join_game))
    app.add_handler(CommandHandler("mycard", show_my_card))
    app.add_handler(CommandHandler("startgame", start_game))
    app.add_handler(CommandHandler("stopgame", stop_game))
    app.add_handler(CallbackQueryHandler(handle_button))

    print("ቦቱ ሥራ ጀምሯል...")
    app.run_polling()
