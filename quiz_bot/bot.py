import os
import re
import json
import time
import random
import signal
import firebase_admin
import base64
from typing import Dict
from collections import defaultdict, deque
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes
)
from pdf_generator import generate_pdf, generate_errors_pdf_sync
from get_gifs import yay, yikes
from wrong_answers import WrongAnswersManager
from user_stats import UserStatsManager
from firebase_admin import credentials, firestore
from aiohttp import web, web_runner
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# per far partire il bot
bot_running = True

# Prendi la variabile d'ambiente con le credenziali in base64
firebase_base64 = os.getenv("FIREBASE_CREDENTIALS_BASE64")

if not firebase_base64:
    raise RuntimeError("Variabile d'ambiente FIREBASE_CREDENTIALS_BASE64 non trovata.")

# Decodifica e salva temporaneamente il file
firebase_json = base64.b64decode(firebase_base64).decode("utf-8")
with open("firebase-credentials.json", "w") as f:
    f.write(firebase_json)

# Carica le credenziali da file e inizializza Firebase (solo una volta)
cred = credentials.Certificate("firebase-credentials.json")

# Crea le credenziali e inizializza Firebase
# cred = credentials.Certificate(cred_dict)
if not firebase_admin._apps:
    firebase_admin.initialize_app(cred)

# Inizializza Firestore
db = firestore.client()
user_managers: Dict[int, WrongAnswersManager] = {}

# --- DDOS protection: simple rate limit per utente ---
RATE_LIMIT = 10  # max richieste
RATE_PERIOD = 5  # secondi
user_requests = defaultdict(lambda: deque(maxlen=RATE_LIMIT))

def is_rate_limited(user_id):
    now = time.time()
    dq = user_requests[user_id]
    dq.append(now)
    if len(dq) == RATE_LIMIT and now - dq[0] < RATE_PERIOD:
        return True
    return False

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

# URL del webhook che fornirà Koyeb (opzionale per test locali)
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
USE_WEBHOOK = WEBHOOK_URL is not None

PORT = int(os.environ.get("PORT", 8000))

print(f"🔧 Modalità: {'Webhook' if USE_WEBHOOK else 'Polling (locale)'}")
print(f"🌐 Server port: {PORT}")

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
        "Questo bot ti aiuta a esercitarti con domande d'esame.\n"
        "Accanto a ogni materia trovi la *data dell'ultimo aggiornamento del quiz*.\n"
        "Vuoi contribuire? Clicca su GitHub e segui la guida!\n\n"

        "*📚 Quiz disponibili:*\n"
        "• *Diritto per le aziende digitali* - _inedite_ - `18/07`\n"
        "• *Ingegneria del software* - _inedite_ - `03/07`\n"
        "• *Corporate planning* - _paniere + inedite + 78 da AI_ - `01/07`\n"
        "• *Programmazione 2* - _inedite_ - `23/06`\n"
        "• *Tecnologie web* - _esamsync + inedite_ - `15/06`\n"
        "• *Statistica* - _paniere_ - `13/06`\n"
        "• *Strategia, organizzazione e marketing* - _paniere + inedite_ - `08/06`\n"
        "• *Comunicazione digitale* - _inedite_ - `28/05`\n"
        "• *Reti di calcolatori e cybersecurity* - _paniere_ - `28/05`\n"
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

    # --- DDOS protection ---
    if is_rate_limited(user_id):
        await context.bot.send_message(chat_id=user_id, text="⏳ Stai andando troppo veloce! Riprova tra qualche secondo.")
        return

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
        "subject": filename.replace(JSON, ""),
        "start_time": time.time()  # <-- TIMER QUIZ
    }

    await send_next_question(user_id, context)


async def error_handler(update, context):
    err = str(context.error)
    # Gestione specifica errore query scaduta
    if "Query is too old and response timeout expired or query id is invalid" in err:
        print("[INFO] Query scaduta, ignorata.")
        return
    print(f"[ERROR] Exception while handling an update: {context.error}")

def escape_markdown(text: str) -> str:
    if not text:
        return ""
    escape_chars = r"_*`[]"
    return re.sub(rf"([{re.escape(escape_chars)}])", r"\\\1", text)

async def send_next_question(user_id, context):
    try:
        state = user_states.get(user_id)
        if not state:
            await context.bot.send_message(chat_id=user_id, text="Sessione non trovata. Scrivi /start per iniziare.")
            return

        if state["index"] >= state["total"]:
            await show_final_stats(user_id, context, state, is_review_mode=state.get("is_review", False))
            manager = get_manager(user_id)
            manager.commit_changes()
            return

        q_index = state["order"][state["index"]]
        
        # Verifica che l'indice sia valido
        if q_index >= len(state["quiz"]):
            await context.bot.send_message(chat_id=user_id, text="❌ Errore nell'indice della domanda. Riprova con /start")
            user_states.pop(user_id, None)
            return
            
        question_data = state["quiz"][q_index]
        
        # Verifica che la domanda abbia i campi necessari
        if not question_data.get("question") or not question_data.get("answers"):
            print(f"❌ Domanda malformata per user {user_id}: {question_data}")
            state["index"] += 1  # Salta questa domanda
            return await send_next_question(user_id, context)

        original_answers = question_data.get("answers", [])
        if len(original_answers) < 2:
            print(f"❌ Domanda senza risposte sufficienti per user {user_id}")
            state["index"] += 1  # Salta questa domanda
            return await send_next_question(user_id, context)
            
        correct_index = question_data.get("correct_answer_index")

        if correct_index is None:
            try:
                correct_answer = question_data.get("correct_answer")
                if correct_answer and correct_answer in original_answers:
                    correct_index = original_answers.index(correct_answer)
                else:
                    print(f"❌ Risposta corretta non trovata per user {user_id}: {correct_answer}")
                    state["index"] += 1  # Salta questa domanda
                    return await send_next_question(user_id, context)
            except Exception as e:
                print(f"❌ Errore nel trovare risposta corretta per user {user_id}: {e}")
                state["index"] += 1  # Salta questa domanda
                return await send_next_question(user_id, context)

        # Continua con il resto della logica originale...
        shuffled = list(enumerate(original_answers))
        random.shuffle(shuffled)
        new_answers = [ans for _, ans in shuffled]
        new_correct_index = next((i for i, (orig_i, _) in enumerate(shuffled) if orig_i == correct_index), -1)

        state["quiz"][q_index]["_shuffled_answers"] = new_answers
        state["quiz"][q_index]["_correct_index"] = new_correct_index

        question_index = f"{state['index'] + 1}."
        question_raw = question_data.get('question', 'Domanda mancante')
        escaped_question = escape_markdown(question_raw)

        if '*' in question_raw:
            question_text = f"{question_index} {escaped_question}\n\n"
        else:
            question_text = f"*{question_index} {escaped_question}*\n\n"

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

        # Gestione immagini con timeout
        image_filename = question_data.get("image")
        if image_filename:
            image_path = os.path.join(QUIZ_FOLDER, "images", image_filename)
            if os.path.isfile(image_path):
                try:
                    with open(image_path, "rb") as image_file:
                        await asyncio.wait_for(
                            context.bot.send_photo(
                                chat_id=user_id,
                                photo=image_file,
                                caption=question_text,
                                reply_markup=reply_markup,
                                parse_mode='Markdown'
                            ),
                            timeout=10.0
                        )
                    return 
                except asyncio.TimeoutError:
                    print(f"⏰ Timeout nell'invio immagine per user {user_id}")
                except Exception as e:
                    print(f"❌ Errore nell'invio dell'immagine per user {user_id}: {e}")

        # Se non c'è immagine o qualcosa va storto, manda solo il testo
        try:
            await asyncio.wait_for(
                context.bot.send_message(
                    chat_id=user_id,
                    text=question_text,
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                ),
                timeout=10.0
            )
        except asyncio.TimeoutError:
            print(f"⏰ Timeout nell'invio messaggio per user {user_id}")
            raise
        except Exception as e:
            print(f"❌ Errore nell'invio messaggio per user {user_id}: {e}")
            raise
            
    except Exception as e:
        print(f"❌ Errore critico in send_next_question per user {user_id}: {e}")
        # Pulisci lo stato dell'utente e invia messaggio di errore
        user_states.pop(user_id, None)
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text="❌ Si è verificato un errore. Riprova con /start"
            )
        except:
            pass


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
        "subject": old_state["subject"],
        "start_time": time.time()  
    }

    await send_next_question(user_id, context)

async def generate_errors_pdf(user_id, subject, context):
    manager = get_manager(user_id)
    manager.commit_changes()
    wrong_qs = manager.get_for_subject(subject)
    base = json.load(open(os.path.join(QUIZ_FOLDER, subject + JSON), encoding="utf-8"))
    base_by_id = {q["id"]: q for q in base}
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
        await context.bot.send_message(chat_id=user_id, text="Nessun errore da esportare.")
        return

    # Genera PDF tramite pdf_generator
    pdf_path = generate_errors_pdf_sync(wrong_answers_detailed, subject, user_id)
    with open(pdf_path, "rb") as pdf_file:
        await context.bot.send_document(chat_id=user_id, document=pdf_file, filename=pdf_path)
    os.remove(pdf_path)

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    data = query.data

    print(f"[DEBUG] handle_callback chiamata per user {user_id}, data: {data}")

    # Risposta al callback query (necessaria per evitare spinner infinito su Telegram)
    try:
        await query.answer()
        print(f"[DEBUG] Query answered per user {user_id}")
    except Exception as e:
        print(f"[DEBUG] Errore nell'answer query: {e}")

    # Tenta di interpretare il dato come JSON, ma solo se plausibile
    callback = None
    if data and data.strip().startswith("{") and data.strip().endswith("}"):
        try:
            callback = json.loads(data)
        except json.JSONDecodeError as e:
            print(f"[DEBUG] Errore parsing JSON: {e}")

    # Se è JSON e contiene comandi speciali, gestiscili subito
    if isinstance(callback, dict):
        if callback.get("cmd") in ("scarica_inedite", "download_pdf"):
            print(f"[DEBUG] Comando PDF per user {user_id}")
            quiz_file = callback.get("file")
            if quiz_file:
                await generate_pdf(quiz_file, context.bot, user_id)
            return

    manager = get_manager(user_id)

    if data == "review_errors":
        print(f"[DEBUG] Review errors per user {user_id}")
        subjects = list(manager.get_all().keys())
        print(f"[DEBUG] Materie disponibili: {subjects}")

        if not subjects:
            print(f"[DEBUG] Nessuna materia trovata per user {user_id}")
            return await query.answer("Non ci sono errori da ripassare!", show_alert=True)
        elif len(subjects) == 1:
            print(f"[DEBUG] Una sola materia, avvio diretto: {subjects[0]}")
            return await start_review_quiz(update, context, subjects[0])

        keyboard = [
            [InlineKeyboardButton(subj.replace("_", " "), callback_data=f"review_subject_{subj}")]
            for subj in subjects
        ]
        keyboard.append([InlineKeyboardButton("🔙 Indietro", callback_data="change_course")])

        try:
            await query.edit_message_text("Scegli la materia da ripassare:", reply_markup=InlineKeyboardMarkup(keyboard))
            print(f"[DEBUG] Messaggio scelta materia inviato per user {user_id}")
        except Exception as e:
            print(f"[ERROR] Errore nell'inviare messaggio scelta materia: {e}")
        return

    if data.startswith("review_subject_"):
        subject = data.split("review_subject_")[1]
        print(f"[DEBUG] Review subject selezionato: {subject} per user {user_id}")
        return await start_review_quiz(update, context, subject)

    if data.startswith("download_errors_pdf:"):
        subject = data.split("download_errors_pdf:")[1]
        await generate_errors_pdf(user_id, subject, context)
        return
    elif data == "no_download_errors_pdf":
        subjects = list(manager.get_all().keys())
        if len(subjects) == 1:
            return await start_review_quiz(update, context, subjects[0])
        keyboard = [
            [InlineKeyboardButton(subj.replace("_", " "), callback_data=f"review_subject_{subj}")]
            for subj in subjects
        ]
        keyboard.append([InlineKeyboardButton("🔙 Indietro", callback_data="change_course")])
        return await query.edit_message_text("Scegli la materia da ripassare:", reply_markup=InlineKeyboardMarkup(keyboard))

    if data == "stop":
        return await stop(update, context)

    elif data.startswith("clear_errors:"):
        subject = data.split(":")[1]
        manager.remove_subject(subject)
        return await context.bot.send_message(
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
        user_states.pop(user_id, None)
        return await choose_subject(update, context)

    elif data.endswith(JSON): 
        user_states.pop(user_id, None)
        return await select_quiz(update, context)

    elif data == "reset_stats":
        return await reset_stats(update, context)

    elif data == "_choose_subject_":
        return await choose_subject(update, context)

    elif data == "repeat_quiz":
        return await repeat_quiz(user_id, context)

    elif data.startswith("answer:"):
        selected = int(data.split(":")[1])
        return await handle_answer_callback(user_id, selected, context)

    elif data.startswith("show_mistakes_"):
        subject = data.split("show_mistakes_")[1]
        return await show_mistakes(user_id, subject, context)

    elif data == "git":
        return await context.bot.send_message(
            chat_id=user_id,
            text="📂 Puoi visualizzare il codice su GitHub:\nhttps://github.com/AdrianaRidolfi/telegram-bots"
        )


async def start_review_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE, subject: str):
    user_id = update.effective_user.id
    print(f"[DEBUG] start_review_quiz chiamata per user {user_id}, subject: {subject}")
    
    try:
        manager = get_manager(user_id)
        print(f"[DEBUG] Manager ottenuto per user {user_id}")
        
        wrong_qs = manager.get_for_subject(subject)
        print(f"[DEBUG] Domande sbagliate trovate: {len(wrong_qs)} per subject {subject}")

        # Verifica che il file del quiz esista
        quiz_path = os.path.join(QUIZ_FOLDER, subject + JSON)
        print(f"[DEBUG] Percorso quiz: {quiz_path}")
        
        if not os.path.exists(quiz_path):
            print(f"[DEBUG] File non trovato: {quiz_path}")
            await context.bot.send_message(
                chat_id=user_id, 
                text=f"❌ File quiz non trovato per {subject}. Riprova con /start"
            )
            return

        # Carica domande di base con gestione errori
        try:
            print(f"[DEBUG] Caricamento file: {quiz_path}")
            with open(quiz_path, encoding="utf-8") as f:
                base = json.load(f)
            print(f"[DEBUG] File caricato, {len(base)} domande trovate")
        except Exception as e:
            print(f"[DEBUG] Errore caricamento file: {e}")
            await context.bot.send_message(
                chat_id=user_id,
                text=f"❌ Errore nel caricamento del quiz: {e}. Riprova con /start"
            )
            return

        if not base:
            print(f"[DEBUG] Quiz vuoto")
            await context.bot.send_message(
                chat_id=user_id,
                text="❌ Quiz vuoto. Riprova con /start"
            )
            return

        print(f"[DEBUG] Creazione dizionario base_by_id...")
        base_by_id = {}
        for i, q in enumerate(base):
            q_id = q.get("id")
            if q_id is not None:
                base_by_id[q_id] = q
            else:
                print(f"[DEBUG] Domanda {i} senza ID: {q.get('question', 'N/A')[:50]}...")
        
        print(f"[DEBUG] base_by_id creato con {len(base_by_id)} domande")

        print(f"[DEBUG] Creazione lista weighted...")
        weighted = []
        for entry in wrong_qs:
            q_id = entry.get("id")
            if not q_id:
                print(f"[DEBUG] Entry senza ID: {entry}")
                continue
                
            counter = entry.get("counter", 1)
            if q_id in base_by_id:
                repeat_times = min((counter + 1) // 2, 5)
                weighted += [base_by_id[q_id]] * repeat_times
                print(f"[DEBUG] Aggiunta domanda ID {q_id}, {repeat_times} volte")
            else:
                print(f"[DEBUG] ID {q_id} non trovato in base_by_id")

        print(f"[DEBUG] Lista weighted creata con {len(weighted)} elementi")

        selected = []
        if weighted:
            to_select = min(len(weighted), 30)
            print(f"[DEBUG] Selezione di {to_select} domande da {len(weighted)}")
            selected = random.sample(weighted, to_select)

        # Aggiunta di domande extra se < 30
        if len(selected) < 30:
            print(f"[DEBUG] Aggiunta domande extra, attuali: {len(selected)}")
            used_ids = {q.get("id") for q in selected if q.get("id")}
            extras = [q for q in base if q.get("id") and q.get("id") not in used_ids]
            needed = 30 - len(selected)
            print(f"[DEBUG] Domande extra disponibili: {len(extras)}, necessarie: {needed}")
            if extras:
                to_add = min(len(extras), needed)
                selected += random.sample(extras, to_add)
                print(f"[DEBUG] Aggiunte {to_add} domande extra")

        if not selected:
            print(f"[DEBUG] Nessuna domanda selezionata")
            await context.bot.send_message(
                chat_id=user_id,
                text="❌ Nessuna domanda disponibile per il ripasso. Riprova con /start"
            )
            return

        print(f"[DEBUG] Creazione stato utente con {len(selected)} domande")
        # Salva quiz in stato utente
        user_states[user_id] = {
            "quiz": selected,
            "quiz_file": subject + JSON,
            "order": list(range(len(selected))),
            "index": 0,
            "score": 0,
            "total": len(selected),
            "is_review": True,
            "subject": subject,
            "start_time": time.time()
        }

        random.shuffle(user_states[user_id]["order"])
        print(f"[DEBUG] Stato utente creato, chiamata send_next_question")
        
        await send_next_question(user_id, context)
        print(f"[DEBUG] send_next_question completata")
        
    except Exception as e:
        print(f"[ERROR] Errore in start_review_quiz per user {user_id}: {e}")
        import traceback
        traceback.print_exc()
        await context.bot.send_message(
            chat_id=user_id,
            text="❌ Si è verificato un errore. Riprova con /start"
        )
        # Pulisci lo stato dell'utente in caso di errore
        user_states.pop(user_id, None)

    

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
    manager.commit_changes()
    wrong_qs = manager.get_for_subject(subject)
    base = json.load(open(os.path.join(QUIZ_FOLDER, subject + JSON), encoding="utf-8"))
    base_by_id = {q["id"]: q for q in base}
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
            f"📊 *Sbagliata*: {times} {label}\n\n"
            )

    if len(full_text) > 4000:
        await context.bot.send_message(chat_id=user_id, text="⚠️ Troppe domande da mostrare in un messaggio.")
        # Chiedi se vuole scaricare il PDF
        keyboard = [
            [
                InlineKeyboardButton("✅ Sì", callback_data=f"download_errors_pdf:{subject}"),
                InlineKeyboardButton("❌ No", callback_data="no_download_errors_pdf")
            ]
        ]
        await context.bot.send_message(
            chat_id=user_id,
            text="Vuoi scaricare un PDF con i tuoi errori?",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
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

    # --- TIMER: calcola durata quiz ---
    duration = ""
    if "start_time" in state:
        elapsed = int(time.time() - state["start_time"])
        mins = elapsed // 60
        secs = elapsed % 60
        duration = f"\n🕒 Tempo impiegato: {mins} min {secs} sec\n"

    if score == 30 and total == 30:
        await context.bot.send_animation(chat_id=user_id, animation=yay())
    if score < 18 and total == 30:
        await context.bot.send_animation(chat_id=user_id, animation=yikes())

    summary = f"🎯Quiz completato!\nPunteggio: {score} su {total} ({percentage}%)\n"
    summary += duration
    summary += "\n📊 Statistiche:\n"

    for sub, data in all_stats.items():
        perc = round((data['correct'] / data['total']) * 100, 2)
        summary += f"- {sub}: {perc}% ({data['correct']} su {data['total']})\n"

    keyboard = []

    manager = get_manager(user_id)
    manager.commit_changes() 
    has_errors = manager.has_wrong_answers()

    if from_change_course:
        pass
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

    # Mostra bottoni errori SOLO se ci sono errori
    if has_errors:
        keyboard.append([
            InlineKeyboardButton("📖 Ripassa errori", callback_data="review_errors"),
            InlineKeyboardButton("📝 Mostra errori", callback_data=f"show_mistakes_{subject}")
        ])

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

async def setup_bot():
    print("🔧 Configurazione bot...")

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("stats", stats))
    application.add_handler(CommandHandler("download", download))
    application.add_handler(CommandHandler("choose_subject", choose_subject))
    application.add_handler(CallbackQueryHandler(handle_callback))
    application.add_error_handler(error_handler)

    print("✅ Bot configurato con successo.")

async def webhook_handler(request):
    """Fixed webhook handler"""
    start_time = time.time()
    user_id = "N/A"
    
    try:
        logger.info(f"Webhook received at {start_time}")
        
        # Get JSON data from request
        try:
            data = await asyncio.wait_for(request.json(), timeout=5.0)
            logger.debug(f"JSON data received: {len(str(data))} characters")
        except asyncio.TimeoutError:
            logger.error("Timeout reading request JSON")
            return web.Response(status=400, text="Request timeout")
        except Exception as e:
            logger.error(f"Error reading JSON: {e}")
            return web.Response(status=400, text="Invalid JSON")
        
        # Create Telegram Update object
        try:
            update = Update.de_json(data, application.bot)
            if not update:
                logger.warning("Invalid update received")
                return web.Response(status=200, text="OK")
        except Exception as e:
            logger.error(f"Error creating Update object: {e}")
            return web.Response(status=400, text="Invalid update format")
        
        if update.effective_user:
            user_id = update.effective_user.id
            logger.info(f"Processing update for user {user_id}")
        
        # Process update with timeout
        try:
            await asyncio.wait_for(application.process_update(update), timeout=15.0)
            elapsed = time.time() - start_time
            logger.info(f"Update processed successfully for user {user_id} in {elapsed:.2f}s")
            
        except asyncio.TimeoutError:
            elapsed = time.time() - start_time
            logger.error(f"Timeout processing update for user {user_id} after {elapsed:.2f}s")
            
            if update.effective_user:
                user_states.pop(update.effective_user.id, None)
                
            return web.Response(status=200, text="Timeout - cleaned up")
                    
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"Error processing update for user {user_id} after {elapsed:.2f}s: {e}")
            
            if update.effective_user:
                user_states.pop(update.effective_user.id, None)
            
            return web.Response(status=200, text="Error handled")
        
        return web.Response(status=200, text="OK")
        
    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"Critical error in webhook handler for user {user_id} after {elapsed:.2f}s: {e}")
        return web.Response(status=500, text="Internal error")



async def health_check(request):
    """Simple health check endpoint"""
    try:
        return web.Response(text="OK", status=200, headers={
            'Content-Type': 'text/plain',
            'Cache-Control': 'no-cache'
        })
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return web.Response(text="Health check failed", status=500)


async def health_check(request):
    """Simple health check endpoint"""
    try:
        return web.Response(text="OK", status=200, headers={
            'Content-Type': 'text/plain',
            'Cache-Control': 'no-cache'
        })
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return web.Response(text="Health check failed", status=500)


async def info_handler(request):
    """Info endpoint"""
    try:
        return web.Response(
            text=json.dumps({
                "status": "running",
                "service": "telegram-bot",
                "timestamp": int(time.time())
            }),
            status=200,
            content_type="application/json"
        )
    except Exception as e:
        logger.error(f"Info handler error: {e}")
        return web.Response(text="Info handler failed", status=500)


async def setup_webhook_server():
    """FIXED: Simplified webhook server setup WITHOUT problematic middleware"""
    app = web.Application()
    
    # REMOVED the problematic middleware entirely
    # If you need CORS, add it directly to response headers in each handler
    
    # Telegram webhook endpoint - TOKEN is defined globally
    app.router.add_post(f"/{TOKEN}", webhook_handler)
    
    # Health check endpoints
    app.router.add_get("/health", health_check)
    app.router.add_get("/", health_check)
    app.router.add_get("/ping", health_check)
    app.router.add_get("/status", health_check)
    
    # Info endpoint
    app.router.add_get("/info", info_handler)
    
    logger.info(f"✅ Webhook server configured with routes:")
    logger.info(f"  POST /{TOKEN} -> webhook_handler")
    logger.info(f"  GET /health -> health_check")
    logger.info(f"  GET / -> health_check")
    logger.info(f"  GET /ping -> health_check")
    logger.info(f"  GET /status -> health_check")
    logger.info(f"  GET /info -> info_handler")
    
    return app

async def main():
    """Enhanced main function with better error handling"""
    global bot_running
    
    try:
        logger.info("🚀 Starting bot...")
        
        # Setup handlers
        await setup_bot()
        
        # Initialize Telegram application
        await application.initialize()
        await application.start()
        
        if USE_WEBHOOK:
            logger.info("🔗 Webhook mode activated")
            
            # Construct webhook URL
            if WEBHOOK_URL.startswith('http'):
                webhook_url = f"{WEBHOOK_URL}/{TOKEN}"
            else:
                webhook_url = f"https://{WEBHOOK_URL}/{TOKEN}"
            
            logger.info(f"🎯 Setting webhook URL: {webhook_url}")
            
            # Set webhook
            try:
                result = await application.bot.set_webhook(
                    url=webhook_url,
                    drop_pending_updates=True,
                    max_connections=40
                )
                logger.info(f"✅ Webhook set successfully: {result}")
                
                # Verify webhook
                webhook_info = await application.bot.get_webhook_info()
                logger.info(f"📋 Webhook info: {webhook_info}")
                
            except Exception as e:
                logger.error(f"❌ Failed to set webhook: {e}")
                raise
            
            # Setup and start web server
            try:
                app = await setup_webhook_server()
                runner = web_runner.AppRunner(app)
                await runner.setup()
                
                site = web_runner.TCPSite(runner, "0.0.0.0", PORT)
                await site.start()
                
                logger.info(f"🌐 Webhook server started on 0.0.0.0:{PORT}")
                logger.info(f"🔍 Test endpoints:")
                logger.info(f"   https://{WEBHOOK_URL}/test")
                logger.info(f"   https://{WEBHOOK_URL}/health")
                logger.info(f"   https://{WEBHOOK_URL}/webhook-info")
                
                # Keep running
                while bot_running:
                    await asyncio.sleep(1)
                    
            except Exception as e:
                logger.error(f"❌ Server setup error: {e}")
                raise
            finally:
                try:
                    await runner.cleanup()
                except:
                    pass
            
        else:
            logger.info("📡 Polling mode activated")
            await application.bot.delete_webhook(drop_pending_updates=True)
            await application.run_polling(drop_pending_updates=True)
            
    except Exception as e:
        logger.error(f"❌ Critical error in main: {e}")
        raise
    finally:
        logger.info("🛑 Shutting down...")
        try:
            await application.stop()
            await application.shutdown()
        except:
            pass

def signal_handler(signum, frame):
    global bot_running
    logger.info(f"🛑 Received signal {signum}. Shutting down...")
    bot_running = False


if __name__ == "__main__":
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        # Start the application
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n🛑 Bot interrupted by user")
    except Exception as e:
        logger.error(f"❌ Critical error: {e}")
    finally:
        logger.info("👋 Bot terminated")