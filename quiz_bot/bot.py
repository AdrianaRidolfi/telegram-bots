import os
import json
import random
from fastapi import FastAPI, Request, HTTPException
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
from contextlib import asynccontextmanager
from pdf_generator import generate_pdf


# Inizializzazione bot Telegram
TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TOKEN:
    raise RuntimeError("Variabile d'ambiente TELEGRAM_TOKEN non trovata.")

application = ApplicationBuilder().token(TOKEN).build()
user_states = {}
QUIZ_FOLDER = "quizzes"
user_stats = {}  # Statistiche per utente e per materia


# --- Funzione per inviare la custom keyboard con comandi rapidi ---
async def send_custom_keyboard(user_id, context):
    keyboard = [
        ["Start", "Stop", "Help"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)
    await context.bot.send_message(chat_id=user_id, text="Comandi rapidi:", reply_markup=reply_markup)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE, show_intro_text_only=False):
    user_id = update.effective_user.id
    try:
        files = [f for f in os.listdir(QUIZ_FOLDER) if f.endswith(".json")]
    except Exception as e:
        await context.bot.send_message(chat_id=user_id, text=f"Errore nel leggere la cartella quiz: {e}")
        return

    if not files:
        await context.bot.send_message(chat_id=user_id, text="Nessun quiz disponibile.")
        return

    keyboard = [
        [InlineKeyboardButton(f.replace("_", " ").replace(".json", ""), callback_data=f)]
        for f in files
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if not show_intro_text_only:
        # Invia la custom keyboard rapida ai comandi
        await send_custom_keyboard(user_id, context)

    await context.bot.send_message(
        chat_id=user_id,
        text="Scegli la materia del quiz:",
        reply_markup=reply_markup,
    )


async def select_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    filename = query.data
    quiz_path = os.path.join(QUIZ_FOLDER, filename)

    try:
        with open(quiz_path, encoding="utf-8") as f:
            quiz_data = json.load(f)
    except Exception as e:
        await context.bot.send_message(chat_id=user_id, text=f"Errore nel caricamento del quiz: {e}")
        return

    question_order = list(range(len(quiz_data)))
    random.shuffle(question_order)
    question_order = question_order[:30]  # Prende solo 30 domande

    user_states[user_id] = {
        "quiz": quiz_data,
        "quiz_file": filename,  # AGGIUNTO
        "order": question_order,
        "index": 0,
        "score": 0,
        "total": len(question_order),
        "subject": filename.replace(".json", "")
    }

    await send_next_question(user_id, context)


async def send_next_question(user_id, context):
    state = user_states.get(user_id)
    if not state:
        await context.bot.send_message(chat_id=user_id, text="Sessione non trovata. Scrivi /start per iniziare.")
        return

    if state["index"] >= state["total"]:
        await show_final_stats(user_id, context, state)
        user_states.pop(user_id, None)
        return

    q_index = state["order"][state["index"]]
    question_data = state["quiz"][q_index]

    original_answers = question_data.get("answers", [])
    correct_index = question_data.get("correct_answer_index")

    if correct_index is None:
        try:
            correct_answer = question_data["correct_answer"]
            correct_index = original_answers.index(correct_answer)
        except Exception:
            correct_index = -1

    shuffled = list(enumerate(original_answers))
    random.shuffle(shuffled)
    new_answers = [ans for _, ans in shuffled]
    new_correct_index = next((i for i, (orig_i, _) in enumerate(shuffled) if orig_i == correct_index), -1)

    state["quiz"][q_index]["_shuffled_answers"] = new_answers
    state["quiz"][q_index]["_correct_index"] = new_correct_index

    question_text = f"{state['index'] + 1}. {question_data.get('question', 'Domanda mancante')}\n\n"
    for i, opt in enumerate(new_answers):
        question_text += f"{chr(65+i)}. {opt}\n"

    keyboard = [
        [InlineKeyboardButton(chr(65 + i), callback_data=f"answer:{i}") for i in range(len(new_answers))]
    ]
    keyboard.append([
        InlineKeyboardButton("🛑 Stop", callback_data="stop"),
        InlineKeyboardButton("🔄 Cambia corso", callback_data="change_course")
    ])
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Se c'è un'immagine, la inviamo prima del messaggio
    image_filename = question_data.get("image")
    if image_filename:
        image_path = os.path.join(QUIZ_FOLDER, "images", image_filename)
        if os.path.isfile(image_path):
            try:
                with open(image_path, "rb") as image_file:
                    await context.bot.send_photo(
                        chat_id=user_id,
                        photo=image_file,
                        caption=question_text,
                        reply_markup=reply_markup
                    )
                return  # Non inviare anche il testo dopo la foto
            except Exception as e:
                await context.bot.send_message(chat_id=user_id, text=f"❗ Errore nell'invio dell'immagine: {e}")

    # Se non c'è immagine o qualcosa va storto, mandiamo solo il testo
    await context.bot.send_message(
        chat_id=user_id,
        text=question_text,
        reply_markup=reply_markup
    )


async def repeat_quiz(user_id: int, context: ContextTypes.DEFAULT_TYPE):
    old_state = user_states.get(user_id)
    if not old_state or "quiz_file" not in old_state:
        await context.bot.send_message(chat_id=user_id, text="Sessione non valida. Scrivi /start per iniziare.")
        return

    quiz_file = old_state["quiz_file"]
    quiz_path = os.path.join(QUIZ_FOLDER, quiz_file)

    try:
        with open(quiz_path, encoding="utf-8") as f:
            quiz_data = json.load(f)
    except Exception as e:
        await context.bot.send_message(chat_id=user_id, text=f"Errore nel ricaricare il quiz: {e}")
        return

    question_order = list(range(len(quiz_data)))
    random.shuffle(question_order)

    user_states[user_id] = {
        "quiz": quiz_data,
        "quiz_file": quiz_file,
        "order": question_order,
        "index": 0,
        "score": 0,
        "total": min(30, len(quiz_data)),
        "subject": old_state["subject"]
    }

    await send_next_question(user_id, context)


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    try:
        callback = json.loads(data)
        if callback.get("cmd") == "scarica_inedite":
            quiz_file = callback.get("file")
            await generate_pdf(quiz_file, context.bot, user_id)
            return
    except Exception:
        pass

    if data == "stop":
        await stop(update, context)
        user_states.pop(user_id, None)

    elif data == "change_course":
        state = user_states.get(user_id)
        await show_final_stats(user_id, context, state, from_change_course=True)
        await start(update, context, show_intro_text_only=True)

    elif data.endswith(".json"):
        await select_quiz(update, context)

    elif data == "reset_stats":
        await reset_stats(update, context)

    elif data == "__choose_subject__":
        await start(update, context)  # mostra direttamente le materie

    elif data == "repeat_quiz":
        await repeat_quiz(user_id, context)

    elif data.startswith("answer:"):
        selected = int(data.split(":")[1])
        await handle_answer_callback(user_id, selected, context)

    elif data == "git":
        await context.bot.send_message(chat_id=user_id, text="📂 Puoi visualizzare il codice su GitHub:\nhttps://github.com/AdrianaRidolfi/telegram-bots/blob/main/README.md")


async def handle_answer_callback(user_id: int, answer_index: int, context: ContextTypes.DEFAULT_TYPE):
    state = user_states.get(user_id)

    if not state:
        await context.bot.send_message(chat_id=user_id, text="Sessione scaduta. Riavvia il quiz con /start.")
        return

    q_index = state["order"][state["index"]]
    question_data = state["quiz"][q_index]

    correct_index = question_data.get("_correct_index", -1)
    answers = question_data.get("_shuffled_answers", question_data.get("answers", []))

    if answer_index == correct_index:
        state["score"] += 1
        await context.bot.send_message(chat_id=user_id, text="✅ Corretto!")
    else:
        correct_letter = chr(65 + correct_index) if correct_index >= 0 else "?"
        correct_text = answers[correct_index] if 0 <= correct_index < len(answers) else "N/A"
        await context.bot.send_message(
            chat_id=user_id,
            text=f"❌ Sbagliato! La risposta corretta era: {correct_letter}. {correct_text}"
        )

    state["index"] += 1
    await send_next_question(user_id, context)


async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    state = user_states.get(user_id)
    await show_final_stats(user_id, context, state, from_stop=True)
    user_states.pop(user_id, None)
    # Invia la custom keyboard dopo stop
    await send_custom_keyboard(user_id, context)


async def show_final_stats(user_id, context, state, from_stop=False, from_change_course=False):

    if not state:
        return

    subject = state["subject"]
    score = state["score"]
    total = max(state["index"], 1)
    percentage = round((score / total) * 100, 2)

    if user_id not in user_stats:
        user_stats[user_id] = {}
    stats = user_stats[user_id]
    if subject not in stats:
        stats[subject] = {"correct": 0, "total": 0}

    stats[subject]["correct"] += score
    stats[subject]["total"] += total

    summary = f"Quiz completato! Punteggio: {score} su {total} ({percentage}%)"
    summary += "\n\n📊 Statistiche:\n"
    for sub, data in stats.items():
        perc = round((data["correct"] / data["total"]) * 100, 2)
        summary += f"📘 {sub}: {perc}% ({data['correct']} su {data['total']})\n"

    keyboard = []

    if from_change_course:
        pass  # Nessun bottone “ripeti quiz” o “scegli materia”
    elif from_stop:
        keyboard.append([
            InlineKeyboardButton("📚 Scegli materia", callback_data="change_course")
        ])
    else:
        keyboard.append([
            InlineKeyboardButton("🔁 Ripeti quiz", callback_data="repeat_quiz"),
            InlineKeyboardButton("📚 Cambia materia", callback_data="change_course")
        ])

    keyboard.append([
        InlineKeyboardButton("🧹 Azzera statistiche", callback_data="reset_stats")
    ])

    keyboard.append([
        InlineKeyboardButton("📥 Scarica inedite", callback_data=json.dumps({"cmd": "scarica_inedite", "file": state['quiz_file']})),
        InlineKeyboardButton("🌐 Git", url="https://github.com/AdrianaRidolfi/telegram-bots/blob/main/README.md")
    ])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(chat_id=user_id, text=summary, reply_markup=reply_markup)


async def reset_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_stats[user_id] = {}
    await context.bot.send_message(chat_id=user_id, text="📊 Statistiche azzerate.")


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    stats = user_stats.get(user_id, {})
    if not stats:
        await context.bot.send_message(chat_id=user_id, text="Nessuna statistica disponibile.")
        return

    summary = "📊 Le tue statistiche:\n"
    for sub, data in stats.items():
        perc = round((data["correct"] / data["total"]) * 100, 2)
        summary += f"📘 {sub}: {perc}% ({data['correct']} su {data['total']})\n"

    await context.bot.send_message(chat_id=user_id, text=summary)


# --- Nuovo handler per messaggi testuali: gestione comandi e risposte lettere ---
async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip().lower()

    if text == "start":
        await start(update, context)
    elif text == "stop":
        await stop(update, context)
    elif text == "help":
        help_text = (
            "Usa i comandi:\n"
            "- Start: per iniziare o scegliere quiz\n"
            "- Stop: per fermare quiz e vedere statistiche\n"
            "- Help: per mostrare questo messaggio\n"
            "Durante il quiz puoi rispondere con lettere (A, B, C, D) oppure usare i bottoni inline."
        )
        await context.bot.send_message(chat_id=user_id, text=help_text)
    elif text in ["a", "b", "c", "d"]:
        state = user_states.get(user_id)
        if not state:
            await context.bot.send_message(chat_id=user_id, text="Nessun quiz attivo. Usa /start per iniziare.")
            return
        answer_index = ord(text.upper()) - 65
        await handle_answer_callback(user_id, answer_index, context)
    else:
        await context.bot.send_message(user_id, text="Comando non riconosciuto. Usa /help per assistenza.")


# FastAPI app
app = FastAPI()


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app.router.lifespan_context = lifespan


@app.post("/webhook")
async def webhook(request: Request):
    json_update = await request.json()
    update = Update.de_json(json_update, application.bot)
    await application.process_update(update)
    return {"ok": True}


# Registra handler
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("stats", stats))
application.add_handler(CommandHandler("help", handle_text_message))  # Help come comando testuale
application.add_handler(CallbackQueryHandler(handle_callback))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
