import random
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from state import set_user_state, get_user_state, update_stats
from config import QUIZ_FOLDER
from utils import load_quiz_file, get_image_path
from constants import *

async def start_quiz(update, context, filename):
    user_id = update.effective_user.id
    quiz_data = load_quiz_file(filename)

    order = list(range(len(quiz_data)))
    random.shuffle(order)
    order = order[:30]

    state = {
        "quiz": quiz_data,
        "quiz_file": filename,
        "order": order,
        "index": 0,
        "score": 0,
        "total": len(order),
        "subject": filename.replace(".json", "")
    }

    set_user_state(user_id, state)
    await send_next_question(user_id, context)

async def send_next_question(user_id, context):
    state = get_user_state(user_id)
    if not state:
        await context.bot.send_message(chat_id=user_id, text="Sessione non trovata. Scrivi /start per iniziare.")
        return

    if state["index"] >= state["total"]:
        await show_final_stats(user_id, context, state)
        return

    q_index = state["order"][state["index"]]
    q_data = state["quiz"][q_index]
    answers = q_data["answers"]
    correct_index = q_data.get("correct_answer_index", -1)

    shuffled = list(enumerate(answers))
    random.shuffle(shuffled)
    new_answers = [a for _, a in shuffled]
    new_correct_index = next((i for i, (orig_i, _) in enumerate(shuffled) if orig_i == correct_index), -1)

    state["quiz"][q_index]["_shuffled_answers"] = new_answers
    state["quiz"][q_index]["_correct_index"] = new_correct_index

    img_path = q_data.get("image")
    if img_path:
        full_img_path = get_image_path(img_path)
        if full_img_path:
            with open(full_img_path, "rb") as f:
                await context.bot.send_photo(chat_id=user_id, photo=f)

    question_text = f"{state['index']+1}. {q_data.get('question')}\n\n"
    for i, opt in enumerate(new_answers):
        question_text += f"{chr(65+i)}. {opt}\n"

    keyboard = [[InlineKeyboardButton(chr(65+i), callback_data=f"answer:{i}") for i in range(len(new_answers))]]
    keyboard.append([
        InlineKeyboardButton("🛑 Stop", callback_data=CALLBACK_STOP),
        InlineKeyboardButton("🔄 Cambia corso", callback_data=CALLBACK_CHANGE_COURSE)
    ])

    await context.bot.send_message(chat_id=user_id, text=question_text, reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_answer(user_id, answer_index, context):
    state = get_user_state(user_id)
    if not state:
        await context.bot.send_message(chat_id=user_id, text="Sessione scaduta. Scrivi /start.")
        return

    q_index = state["order"][state["index"]]
    q_data = state["quiz"][q_index]
    correct_index = q_data["_correct_index"]
    answers = q_data["_shuffled_answers"]

    if answer_index == correct_index:
        state["score"] += 1
        await context.bot.send_message(chat_id=user_id, text="✅ Corretto!")
    else:
        await context.bot.send_message(
            chat_id=user_id,
            text=f"❌ Sbagliato! La risposta corretta era: {chr(65+correct_index)}. {answers[correct_index]}"
        )

    state["index"] += 1
    await send_next_question(user_id, context)

async def show_final_stats(user_id, context, state):
    score = state["score"]
    total = max(state["index"], 1)
    subject = state["subject"]
    percent = round(score / total * 100, 2)

    update_stats(user_id, subject, score, total)

    msg = f"Quiz completato! Punteggio: {score} su {total} ({percent}%)"
    keyboard = [[
        InlineKeyboardButton("🔁 Ripeti quiz", callback_data=CALLBACK_REPEAT_QUIZ),
        InlineKeyboardButton("📚 Cambia materia", callback_data=CALLBACK_CHANGE_COURSE)
    ], [
        InlineKeyboardButton("🧹 Azzera statistiche", callback_data=CALLBACK_RESET_STATS)
    ]]
    await context.bot.send_message(chat_id=user_id, text=msg, reply_markup=InlineKeyboardMarkup(keyboard))
