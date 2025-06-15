import os
import re
import json
import random
import firebase_admin
from handlers_exam_sync import (
    analyze_exam_start, handle_exam_selection,
    clear_session, handle_exam_analyze_flow,
    token_info, handle_post_analyze_menu)
from typing import Dict
from fastapi import FastAPI, Request, HTTPException
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters
)
from contextlib import asynccontextmanager
from pdf_generator import generate_pdf
from get_gifs import yay, yikes
from wrong_answers import WrongAnswersManager
from user_stats import UserStatsManager
from firebase_admin import credentials, firestore

# Carica la variabile d'ambiente
firebase_credentials = os.environ.get("FIREBASE_CREDENTIALS_JSON")

if not firebase_credentials:
    raise ValueError("La variabile d'ambiente FIREBASE_CREDENTIALS_JSON non è stata trovata.")

# Converte la stringa JSON in dizionario Python
cred_dict = json.loads(firebase_credentials)

# Crea le credenziali e inizializza Firebase
cred = credentials.Certificate(cred_dict)
if not firebase_admin._apps:
    firebase_admin.initialize_app(cred)

# Inizializza Firestore
db = firestore.client()

user_managers: Dict[int, WrongAnswersManager] = {}

def get_manager(user_id: int) -> WrongAnswersManager:
    # Restituisce (o crea) l'istanza condivisa di WrongAnswersManager per questo user_id
    if user_id not in user_managers:
        user_managers[user_id] = WrongAnswersManager(str(user_id))
    return user_managers[user_id]

def clear_manager(user_id: int):
    """Rimuove l'istanza manager dopo il commit."""
    user_managers.pop(user_id, None)

#per gestire le statistiche
stats_managers: Dict[int, UserStatsManager] = {}

def get_stats_manager(user_id: int) -> UserStatsManager:
    if user_id not in stats_managers:
        stats_managers[user_id] = UserStatsManager(str(user_id))
    return stats_managers[user_id]


# Inizializzazione bot Telegram
TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TOKEN:
    raise RuntimeError("Variabile d'ambiente TELEGRAM_TOKEN non trovata.")

application = ApplicationBuilder().token(TOKEN).build()
user_states = {}

QUIZ_FOLDER = "quizzes"
JSON = ".json"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE, show_intro_text_only=False):
    user_id = update.effective_user.id
    # Inizializzo il manager per l'utente, pronto a raccogliere errori
    manager = get_manager(user_id)

    msg = (
        "*👋 Ciao!*\n"
        "Questo bot ti aiuta a esercitarti con domande d’esame.\n"
        "Accanto a ogni materia trovi la *data dell’ultimo aggiornamento del quiz*.\n"
        "Vuoi contribuire? Clicca su GitHub e segui la guida!\n\n"

        "*📚 Quiz disponibili:*\n"
        "• *Tecnologie web* - _esamsync + inedite_ - `13/06`\n"
        "• *Statistica* - _paniere_ - `13/06`\n"
        "• *Diritto per le aziende digitali* - _inedite_ - `11/06`\n"
        "• *Strategia, organizzazione e marketing* - _paniere + inedite_ - `08/06`\n"
        "• *Corporate planning* - _solo paniere_ - `04/06`\n"
        "• *Comunicazione digitale* - _inedite_ - `28/05`\n"
        "• *Ingegneria del software* - _inedite_ - `28/05`\n"
        "• *Reti di calcolatori e cybersecurity* - _paniere_ - `28/05`\n"
        "• *Programmazione 2* - _inedite_ - `28/05`\n"
    )

    keyboard = []
    keyboard.append([InlineKeyboardButton("🌐 GitHub", url="https://github.com/AdrianaRidolfi/telegram-bots")])
    keyboard.append([InlineKeyboardButton(text="📚 Scegli materia", callback_data="_choose_subject_")])

    #se l'utente ha errori aggiungo il bottone
    if manager.has_wrong_answers():
        keyboard.append([InlineKeyboardButton("📖 Ripassa errori", callback_data="review_errors")])

    reply_markup = InlineKeyboardMarkup(keyboard)

    await context.bot.send_message(
        chat_id=user_id,
        text=msg,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def choose_subject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    
    user_id = update.effective_user.id

    try:
        files = [f for f in os.listdir(QUIZ_FOLDER) if f.endswith(JSON)]
    except Exception as e:
        await context.bot.send_message(chat_id=user_id, text=f"Errore nel leggere la cartella quiz: {e}")
        return

    if not files:
        await context.bot.send_message(chat_id=user_id, text="Nessun quiz disponibile.")
        return

    keyboard = [
        [InlineKeyboardButton(f.replace("_", " ").replace(JSON, ""), callback_data=f)]
        for f in files
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await context.bot.send_message(
        chat_id=user_id,
        text="📚 Materie disponibili:",
        reply_markup=reply_markup,
    )


async def download(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    try:
        files = [f for f in os.listdir(QUIZ_FOLDER) if f.endswith(JSON)]
    except Exception as e:
        await context.bot.send_message(chat_id=user_id, text=f"Errore nel leggere la cartella quiz: {e}")
        return

    if not files:
        await context.bot.send_message(chat_id=user_id, text="Nessun quiz disponibile.")
        return

    keyboard = [
        [InlineKeyboardButton(f.replace("_", " ").replace(JSON, ""),
         callback_data=json.dumps({"cmd": "download_pdf", "file": f}))]
        for f in files
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await context.bot.send_message(
        chat_id=user_id,
        text="📚 Scegli la materia per scaricare il PDF:",
        reply_markup=reply_markup
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
        "quiz_file": filename, 
        "order": question_order,
        "index": 0,
        "score": 0,
        "total": len(question_order),
        "subject": filename.replace(JSON, "")
    }


    await send_next_question(user_id, context)


async def error_handler(update, context):
    print(f"[ERROR] Exception while handling an update: {context.error}")


def escape_markdown(text: str) -> str:
    if not text:
        return ""
    escape_chars = r"_*`[]"
    return re.sub(rf"([{re.escape(escape_chars)}])", r"\\\1", text)

async def send_next_question(user_id, context):
    state = user_states.get(user_id)
    if not state:
        await context.bot.send_message(chat_id=user_id, text="Sessione non trovata. Scrivi /start per iniziare.")
        return

    if state["index"] >= state["total"]:
        await show_final_stats(user_id, context, state, is_review_mode=state.get("is_review", False))
        manager = get_manager(user_id)
        manager.commit_changes()
        user_states.pop(user_id, None) 
        return


    q_index = state["order"][state["index"]]
    question_data = state["quiz"][q_index]

    original_answers = question_data.get("answers", [])
    correct_index = question_data.get("correct_answer_index")

    if correct_index is None:
        try:
            correct_answer = question_data.get("correct_answer")
            correct_index = original_answers.index(correct_answer)
        except Exception:
            correct_index = -1

    shuffled = list(enumerate(original_answers))
    random.shuffle(shuffled)
    new_answers = [ans for _, ans in shuffled]
    new_correct_index = next((i for i, (orig_i, _) in enumerate(shuffled) if orig_i == correct_index), -1)

    state["quiz"][q_index]["_shuffled_answers"] = new_answers
    state["quiz"][q_index]["_correct_index"] = new_correct_index

    question_index = f"{state['index'] + 1}."
    question_text = f"*{question_index} {question_data.get('question', 'Domanda mancante')}*\n\n"
    
    for i, opt in enumerate(new_answers):
        question_text += f"*{chr(65+i)}.* {escape_markdown(opt)}\n"



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
                        reply_markup=reply_markup,
                        parse_mode='Markdown'
                    )
                return 
            except Exception as e:
                await context.bot.send_message(chat_id=user_id, text=f"❗ Errore nell'invio dell'immagine: {e}")

    # Se non c'è immagine o qualcosa va storto, mandiamo solo il testo
    await context.bot.send_message(
        chat_id=user_id,
        text=question_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
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
        if callback.get("cmd") in ("scarica_inedite", "download_pdf"):
            quiz_file = callback.get("file")
            await generate_pdf(quiz_file, context.bot, user_id)
            return
    except Exception:
        pass

    manager = get_manager(user_id)
    if data == "review_errors":
        subjects = list(manager.get_all().keys())

        #se non ci sono materie
        if not subjects:
            return await query.answer("Non ci sono errori da ripassare!", show_alert=True)
        #se c'e' una materia sola
        elif  len(subjects) == 1:
            return await start_review_quiz(update, context, subjects[0])

        keyboard = [[
            InlineKeyboardButton(subj.replace("_", " "), callback_data=f"review_subject_{subj}")]
            for subj in subjects
        ]
        keyboard.append([InlineKeyboardButton("🔙 Indietro", callback_data="change_course")])
        return await query.edit_message_text("Scegli la materia da ripassare:", reply_markup=InlineKeyboardMarkup(keyboard))

    if data.startswith("review_subject_"):
        subject = data.split("review_subject_")[1]
        return await start_review_quiz(update, context, subject)
    
    if data == "stop":
        await stop(update, context)

    elif data.startswith("clear_errors:"):
        subject = data.split(":")[1]
        manager.remove_subject(subject)
        await context.bot.send_message(
            chat_id=user_id,
            text=f"✅ Errori per *{subject}* cancellati!",
            parse_mode="Markdown"
        )

    elif data == "change_course":
        state = user_states.get(user_id)
        if state:
            manager.commit_changes()
            clear_manager(user_id)

        await show_final_stats(user_id, context, state, from_change_course=True)
        await choose_subject(update, context)

    elif data.endswith(JSON):
        await select_quiz(update, context)

    elif data == "reset_stats":
        await reset_stats(update, context)

    elif data == "_choose_subject_":
        await choose_subject(update, context)  

    elif data == "repeat_quiz":
        await repeat_quiz(user_id, context)

    elif data.startswith("answer:"):
        selected = int(data.split(":")[1])
        await handle_answer_callback(user_id, selected, context)

    elif data.startswith("show_mistakes_"):
        subject = data.split("show_mistakes_")[1]
        await show_mistakes(user_id, subject, context)

    elif data == "git":
        await context.bot.send_message(chat_id=user_id, text="📂 Puoi visualizzare il codice su GitHub:\nhttps://github.com/AdrianaRidolfi/telegram-bots")

async def start_review_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE, subject: str):
    
    user_id = update.effective_user.id
    manager = get_manager(user_id)
    wrong_qs = manager.get_for_subject(subject)

    # Carica domande di base
    base = json.load(open(os.path.join(QUIZ_FOLDER, subject + JSON), encoding="utf-8"))
    base_by_id = {q["id"]: q for q in base}

    weighted = []
    for entry in wrong_qs:
        q_id = entry["id"]
        counter = entry.get("counter", 1)
        if q_id in base_by_id:
            # Inserisci la domanda (counter + 1) // 2 volte, max 5
            repeat_times = min((counter + 1) // 2, 5)
            weighted += [base_by_id[q_id]] * repeat_times

    selected = []
    if weighted:
        selected = random.sample(weighted, min(len(weighted), 30))

    # Aggiunta di domande extra se < 30
    if len(selected) < 30:
        used_ids = {q["id"] for q in selected}
        extras = [q for q in base if q["id"] not in used_ids]
        needed = 30 - len(selected)
        selected += random.sample(extras, min(len(extras), needed))

    # Salva quiz in stato utente
    user_states[user_id] = {
        "quiz": selected,
        "quiz_file": subject + JSON,
        "order": list(range(len(selected))),
        "index": 0,
        "score": 0,
        "total": len(selected),
        "is_review": True,
        "subject": subject
    }

    random.shuffle(user_states[user_id]["order"])
    await send_next_question(user_id, context)



async def handle_answer_callback(user_id: int, answer_index: int, context: ContextTypes.DEFAULT_TYPE):
    state = user_states.get(user_id)

    if not state:
        await context.bot.send_message(chat_id=user_id, text="Sessione scaduta. Riavvia il quiz con /start.")
        return

    subject = state.get("subject", "")
    q_index = state["order"][state["index"]]
    question_data = state["quiz"][q_index]

    correct_index = question_data.get("_correct_index")
    if correct_index is None:
        correct_index = question_data["answers"].index(question_data["correct_answer"])

    answers = question_data.get("_shuffled_answers", question_data.get("answers", []))
    manager = get_manager(user_id)
    
    if answer_index == correct_index:
        state["score"] += 1
        await context.bot.send_message(chat_id=user_id, text="✅ Corretto!")
        if state.get("is_review"):
            manager.queue_decrement(subject, question_data["id"])
    else:
        await context.bot.send_message(chat_id=user_id, text="❌ Sbagliato!")
        correct_letter = chr(65 + correct_index)
        correct_text = answers[correct_index]
        await context.bot.send_message(
            chat_id=user_id,
            text=f"La risposta corretta era: {correct_letter}. {correct_text}"
        )
        manager.queue_wrong_answer(subject, question_data)

    state["index"] += 1
    await send_next_question(user_id, context)



async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    state = user_states.get(user_id)

    if not state:
        await context.bot.send_message(chat_id=user_id, text="Nessuna sessione attiva.")
        return
   
    manager = get_manager(user_id)
    manager.commit_changes()
    clear_manager(user_id)
   
    await show_final_stats(user_id, context, state, from_stop=True)
    user_states.pop(user_id, None)


async def show_mistakes(user_id, subject, context: ContextTypes.DEFAULT_TYPE):

    manager = get_manager(user_id)
    wrong_qs = manager.get_for_subject(subject)
    base = json.load(open(os.path.join(QUIZ_FOLDER, subject + JSON), encoding="utf-8"))
    base_by_id = {q["id"]: q for q in base}
    # Nuovo array che conterrà le domande sbagliate con contatore e risposta giusta
    wrong_answers_detailed = []

    for entry in wrong_qs:
        q_id = entry["id"]
        counter = entry.get("counter", 1)

        if counter < 3:
            continue
    
        if q_id in base_by_id:
            question = base_by_id[q_id]
            detailed_entry = {
                "question": question.get("question"),
                "correct_answer": question.get("correct_answer"), 
                "times_wrong": counter // 3
            }
            wrong_answers_detailed.append(detailed_entry)

    if not wrong_answers_detailed:
        await context.bot.send_message(chat_id=user_id, text="✅ Nessun errore trovato! Ottimo lavoro!")
        return

    full_text = "📋 *Ecco le domande che hai sbagliato:*\n\n"
    for item in wrong_answers_detailed:
        times = item['times_wrong']
        label = "volta" if times == 1 else "volte"
        full_text += (
            f"❓ *Domanda*: {item['question']}\n"
            f"✅ *Risposta corretta*: {item['correct_answer']}\n"
            f"🔁 *Sbagliata*: {times} {label}\n\n"
            )

    # Attenzione: Telegram ha un limite di 4096 caratteri per messaggio
    if len(full_text) > 4000:
        await context.bot.send_message(chat_id=user_id, text="⚠️ Troppe domande da mostrare in un messaggio.")
    else:
        reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("📖 Ripassa errori", callback_data="review_errors")]])
        await context.bot.send_message(chat_id=user_id, text=full_text, parse_mode='Markdown', reply_markup=reply_markup)



async def show_final_stats(user_id, context, state, from_stop=False, from_change_course=False, is_review_mode=False):
    
    if not state:
        return

    subject = state.get("subject")
    if subject is None:
        await context.bot.send_message(chat_id=user_id, text="Nessun corso selezionato.")
        return

    score = state["score"]
    total = state["index"]
    
    if total == 0:
        await context.bot.send_message(chat_id=user_id, text="Nessuna risposta data. Quiz interrotto.")
        return


    percentage = round((score / total) * 100, 2)

    stats_manager = get_stats_manager(user_id)
    stats_manager.update_stats(subject, score, total)

    all_stats = stats_manager.get_summary()

    if score == 30 and total == 30:
        await context.bot.send_animation(chat_id=user_id, animation=yay())

    if score < 18 and total == 30:
        await context.bot.send_animation(chat_id=user_id, animation=yikes())
    
    summary = f"Quiz completato! Punteggio: {score} su {total} ({percentage}%)\n\n📊 Statistiche:\n"
    
    
    for sub, data in all_stats.items():
        perc = round((data['correct'] / data['total']) * 100, 2)
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
    if is_review_mode:
        keyboard.append(
            [
                InlineKeyboardButton("🧹 Azzera statistiche", callback_data="reset_stats"),
                InlineKeyboardButton("🧽 Cancella Errori", callback_data=f"clear_errors:{state['subject']}")]
        )
    else: 
        keyboard.append([
            InlineKeyboardButton("🧹 Azzera statistiche", callback_data="reset_stats")
        ])

    manager = get_manager(user_id)
    if manager.has_wrong_answers():
        keyboard.append([InlineKeyboardButton("📖 Ripassa errori", callback_data="review_errors"),
                              InlineKeyboardButton("🔍 Mostra errori", callback_data=f"show_mistakes_{subject}")])

    keyboard.append([
        InlineKeyboardButton("📥 Scarica pdf", callback_data=json.dumps({"cmd": "scarica_inedite", "file": state['quiz_file']})),
        InlineKeyboardButton("🌐 Git", url="https://github.com/AdrianaRidolfi/telegram-bots")
    ])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(chat_id=user_id, text=summary, reply_markup=reply_markup)


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    stats_manager = get_stats_manager(user_id)
    stats = stats_manager.get_summary()
    if not stats:
        await context.bot.send_message(chat_id=user_id, text="Nessuna statistica disponibile.")
        return

    msg = "📊 Statistiche:\n"
    for sub, data in stats.items():
        perc = round((data["correct"] / data["total"]) * 100, 2)
        msg += f"📘 {sub}: {perc}% ({data['correct']} su {data['total']})\n"

    keyboard = []

    keyboard.append([
        InlineKeyboardButton("📚 Scegli materia", callback_data="change_course"),
        InlineKeyboardButton("🧹 Azzera statistiche", callback_data="reset_stats")
        ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)

    await context.bot.send_message(chat_id=user_id, text=msg, reply_markup=reply_markup)



async def reset_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    stats_manager = get_stats_manager(user_id)
    stats_manager.reset_stats()
    await context.bot.send_message(chat_id=user_id, text="✅ Statistiche azzerate!")

@asynccontextmanager
async def lifespan(app: FastAPI):
    await application.initialize()
    
    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("stats", stats))
    application.add_handler(CommandHandler("download", download))
    application.add_handler(CommandHandler("choose_subject", choose_subject))
    application.add_handler(CommandHandler("analyze_exam", analyze_exam_start))
    application.add_handler(CommandHandler("token_info", token_info))
    application.add_handler(CommandHandler("clear_session", clear_session))
    
    # Add specific callback handlers
    application.add_handler(CallbackQueryHandler(handle_post_analyze_menu, pattern="^(analyze_another_exam|_choose_subject_)$"))
    application.add_handler(CallbackQueryHandler(handle_exam_selection, pattern="^select_exam_"))
    application.add_handler(CallbackQueryHandler(handle_exam_selection, pattern="^renew_token$"))
    
    # Add the generic callback handler LAST
    application.add_handler(CallbackQueryHandler(handle_callback))
    
    # Add message handler
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_exam_analyze_flow))
    
    # Add error handler
    application.add_error_handler(error_handler)
    
    print("✅ Applicazione Telegram inizializzata con successo.")
    yield


app = FastAPI(lifespan=lifespan)

@app.get("/")
def read_root():
    return {"status": "ok"}


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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("bot:app", host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
