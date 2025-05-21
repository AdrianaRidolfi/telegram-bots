import os
import json
import random
from fastapi import FastAPI, Request, HTTPException
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)
from contextlib import asynccontextmanager

# Inizializzazione bot Telegram
TOKEN = os.getenv("TELEGRAM_TOKEN", "YOUR_DEFAULT_TOKEN_HERE")  # Sostituisci se necessario
if not TOKEN:
    raise RuntimeError("Variabile d'ambiente TELEGRAM_TOKEN non trovata.")

application = ApplicationBuilder().token(TOKEN).build()
user_states = {}
QUIZ_FOLDER = "quizzes"

# --- Funzioni handler ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

    user_states[user_id] = {
        "quiz": quiz_data,
        "order": question_order,
        "index": 0,
        "score": 0,
        "total": len(quiz_data),
    }

    await send_next_question(user_id, context)


async def send_next_question(user_id, context):
    state = user_states.get(user_id)
    if not state:
        await context.bot.send_message(chat_id=user_id, text="Sessione non trovata. Scrivi /start per iniziare.")
        return

    if state["index"] >= state["total"]:
        percentage = round((state["score"] / state["total"]) * 100, 2)
        await context.bot.send_message(
            chat_id=user_id,
            text=f"Quiz completato! Punteggio: {state['score']} su {state['total']} ({percentage}%)"
        )
        user_states.pop(user_id, None)
        return

    q_index = state["order"][state["index"]]
    question_data = state["quiz"][q_index]
    question_text = f"{state['index'] + 1}. {question_data.get('question', 'Domanda mancante')}"

    keyboard = [
        [InlineKeyboardButton(f"{chr(65 + i)}. {opt}", callback_data=f"answer:{i}")]
        for i, opt in enumerate(question_data.get("answers", []))
    ]
    keyboard.append([
        InlineKeyboardButton("🛑 Stop", callback_data="stop"),
        InlineKeyboardButton("🔄 Cambia corso", callback_data="change_course")
    ])
    reply_markup = InlineKeyboardMarkup(keyboard)

    await context.bot.send_message(
        chat_id=user_id,
        text=question_text,
        reply_markup=reply_markup
    )


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    if data == "stop":
        await stop(update, context)
        user_states.pop(user_id, None)
    elif data == "change_course":
        user_states.pop(user_id, None)
        await start(update, context)
    elif data.endswith(".json"):
        await select_quiz(update, context)
    elif data.startswith("answer:"):
        selected = int(data.split(":")[1])
        await handle_answer_callback(user_id, selected, context)


async def handle_answer_callback(user_id: int, selected: int, context: ContextTypes.DEFAULT_TYPE):
    state = user_states.get(user_id)
    if not state:
        await context.bot.send_message(chat_id=user_id, text="Sessione scaduta. Scrivi /start per ripartire.")
        return

    q_index = state["order"][state["index"]]
    question_data = state["quiz"][q_index]
    correct_index = question_data.get("correct_answer_index")

    if correct_index is None:
        try:
            correct_answer = question_data["correct_answer"]
            correct_index = question_data["answers"].index(correct_answer)
        except Exception:
            correct_index = -1

    if selected == correct_index:
        await context.bot.send_message(chat_id=user_id, text="✅ Corretto!")
        state["score"] += 1
    else:
        correct_letter = chr(65 + correct_index) if correct_index >= 0 else "?"
        correct_text = question_data["answers"][correct_index] if correct_index >= 0 else "N/A"
        await context.bot.send_message(
            chat_id=user_id,
            text=f"❌ Sbagliato! La risposta corretta era: {correct_letter}. {correct_text}"
        )

    state["index"] += 1
    await send_next_question(user_id, context)


async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    state = user_states.pop(user_id, None)

    if state:
        percentage = round((state["score"] / max(state["index"], 1)) * 100, 2)
        stats_msg = f"Statistiche finali: {state['score']} risposte corrette su {state['index']} ({percentage}%)"
        await context.bot.send_message(chat_id=user_id, text="Quiz interrotto.")
        await context.bot.send_message(chat_id=user_id, text=stats_msg)
    else:
        await context.bot.send_message(chat_id=user_id, text="Nessun quiz attivo. Scrivi /start per iniziare.")


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    state = user_states.get(user_id)
    if not state or state["index"] == 0:
        await context.bot.send_message(chat_id=user_id, text="Nessuna statistica disponibile.")
        return

    percentage = round((state["score"] / state["index"]) * 100, 2)
    await context.bot.send_message(
        chat_id=user_id,
        text=f"Statistiche attuali: {state['score']} risposte corrette su {state['index']} ({percentage}%)"
    )


# --- Gestione Lifespan FastAPI ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    await application.initialize()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("stats", stats))
    application.add_handler(CallbackQueryHandler(handle_callback))
    print("✅ Applicazione Telegram inizializzata con successo.")
    yield
    # Qui potresti aggiungere cleanup se necessario


app = FastAPI(lifespan=lifespan)


# --- Webhook endpoint ---
@app.post("/webhook")
async def telegram_webhook(request: Request):
    try:
        data = await request.json()
        update = Update.de_json(data, application.bot)
        await application.process_update(update)
    except Exception as e:
        print(f"Errore webhook: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    return {"ok": True}


# --- Avvio manuale locale ---
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("bot:app", host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
