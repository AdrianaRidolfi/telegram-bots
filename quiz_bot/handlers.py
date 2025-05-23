from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from utils import load_quiz_list
from quiz_logic import start_quiz, handle_answer, show_final_stats
from state import get_user_state, reset_user_state, reset_stats
from constants import *

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    files = load_quiz_list()

    if not files:
        await context.bot.send_message(chat_id=user_id, text="⚠️ Nessun quiz disponibile.")
        return

    keyboard = [[InlineKeyboardButton(f.replace(".json", ""), callback_data=f)] for f in files]
    await context.bot.send_message(chat_id=user_id, text="Scegli la materia del quiz:", reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    if data == CALLBACK_STOP:
        reset_user_state(user_id)
        await context.bot.send_message(chat_id=user_id, text="⛔ Quiz interrotto.")
    elif data == CALLBACK_CHANGE_COURSE:
        await start(update, context)
    elif data == CALLBACK_RESET_STATS:
        reset_stats(user_id)
        await context.bot.send_message(chat_id=user_id, text="✅ Statistiche azzerate.")
    elif data == CALLBACK_REPEAT_QUIZ:
        state = get_user_state(user_id)
        if state:
            await start_quiz(update, context, state["quiz_file"])
    elif data.endswith(".json"):
        await start_quiz(update, context, data)
    elif data.startswith("answer:"):
        index = int(data.split(":")[1])
        await handle_answer(user_id, index, context)
