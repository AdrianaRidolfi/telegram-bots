import os
import sys
if sys.platform == "win32":
    os.system("chcp 65001")
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
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
import copy
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    JobQueue,
    MessageHandler, filters
)
from pdf_generator import generate_errors_pdf_sync
from get_gifs import yay, yikes
from wrong_answers import WrongAnswersManager
from user_stats import UserStatsManager
from firebase_admin import credentials, firestore
from aiohttp import web, web_runner
import aiofiles
import logging
import handlers
import asyncio
from typing import Dict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# per far partire il bot
bot_running = True

user_locks: Dict[int, asyncio.Lock] = {}

def get_user_lock(user_id: int) -> asyncio.Lock:
    """Restituisce o crea un lock per l'utente specifico"""
    if user_id not in user_locks:
        user_locks[user_id] = asyncio.Lock()
    return user_locks[user_id]

def clear_user_lock(user_id: int):
    """Rimuove il lock quando l'utente completa il quiz"""
    user_locks.pop(user_id, None)

from dotenv import load_dotenv
load_dotenv()  # questo legge automaticamente il file .env

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

print(f"Modalità: {'Webhook' if USE_WEBHOOK else 'Polling (locale)'}")
print(f"Server port: {PORT}")

application = ApplicationBuilder().token(TOKEN).build()

user_states = {}

QUIZ_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "quizzes")
JSON = ".json"
SCEGLI_MATERIA = "📚 Scegli materia"
RIPASSA_ERRORI = "📖 Ripassa errori"
AZZERA_STATISTICHE = "🧹 Azzera statistiche"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE, show_intro_text_only=False):
    print("[DEBUG] /start command received")
    user_id = update.effective_user.id
    # Inizializzo il manager per l'utente, pronto a raccogliere errori
    manager = get_manager(user_id)

    msg = (
        "*👋 Ciao!*\n"
        "Questo bot ti aiuta a esercitarti con domande d'esame.\n"
        "Accanto a ogni materia trovi la *data dell'ultimo aggiornamento del quiz*.\n"
        "Vuoi contribuire? Clicca su GitHub e segui la guida!\n\n"

        "*📚 Quiz disponibili:*\n"
        "• *Ingegneria del software* - _inedite + 60 da AI_  + inedite primi 27 capitoli- `13/10`\n"
        "• *Programmazione distribuita e cloud computing* - _inedite_ - `22/08`\n"
        "• *Diritto per le aziende digitali* - _inedite_ - `18/07`\n"
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
    keyboard.append([InlineKeyboardButton(text=SCEGLI_MATERIA, callback_data="_choose_subject_")])

    #se l'utente ha errori aggiungo il bottone
    if manager.has_wrong_answers():
        keyboard.append([InlineKeyboardButton(RIPASSA_ERRORI, callback_data="review_errors")])

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
         callback_data=f"download_pdf:{f}")]
        for f in files
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await context.bot.send_message(
        chat_id=user_id,
        text="📚 Scegli la materia per scaricare il PDF:",
        reply_markup=reply_markup
    )


async def select_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id=None, filename=None):
    # Permetti chiamata sia da callback che diretta
    if update and update.callback_query:
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        filename = query.data
    elif hasattr(context, 'user_id') and hasattr(context, 'filename'):
        # Se context ha user_id e filename (non standard, ma fallback)
        user_id = context.user_id
        filename = context.filename
    elif hasattr(context, 'chat_data') and 'user_id' in context.chat_data and 'filename' in context.chat_data:
        user_id = context.chat_data['user_id']
        filename = context.chat_data['filename']
    # Permetti anche chiamata esplicita con parametri
    if user_id is None or filename is None:
        # Prova a recuperare da user_states (fallback)
        if update and update.effective_user:
            user_id = update.effective_user.id
        if update and hasattr(update, 'data'):
            filename = update.data
        await context.bot.send_message(chat_id=update.effective_user.id if update and update.effective_user else None, text="Errore: dati mancanti per il quiz.")
        return
    
    # PULIZIA MANAGER ERRORI 
    manager = get_manager(user_id)
    manager.commit_changes()
    clear_manager(user_id)

    # --- DDOS protection ---
    if is_rate_limited(user_id):
        await context.bot.send_message(chat_id=user_id, text="⏳ Stai andando troppo veloce! Riprova tra qualche secondo.")
        return

    quiz_path = os.path.join(QUIZ_FOLDER, filename)

    try:
        async with aiofiles.open(quiz_path, mode="r", encoding="utf-8") as f:
            content = await f.read()
            quiz_data = json.loads(content)
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
    
    # Gestione specifica per callback invalidi
    if "Button_data_invalid" in err:
        print(f"[INFO] Button data invalid per update: {update}")
        if update and update.effective_user:
            try:
                await context.bot.send_message(
                    chat_id=update.effective_user.id,
                    text="⚠️ Pulsante scaduto. Usa /start per ricominciare"
                )
            except Exception as send_error:
                print(f"[ERROR] Impossibile inviare messaggio errore: {send_error}")
        return
    
    # Gestione specifica errore query scaduta
    if "Query is too old and response timeout expired or query id is invalid" in err:
        print("[INFO] Query scaduta, ignorata.")
        return
        
    # Altri errori di callback
    if "CallbackQuery" in err and ("invalid" in err.lower() or "expired" in err.lower()):
        print(f"[INFO] Callback error ignorato: {err}")
        return
    
    print(f"[ERROR] Exception while handling an update: {context.error}")

def escape_markdown(text: str) -> str:
    if not text:
        return ""
    escape_chars = r"_*`[]"
    return re.sub(rf"([{re.escape(escape_chars)}])", r"\\\1", text)

async def send_next_question(user_id, context):
    # Acquisisce il lock per questo utente
    lock = get_user_lock(user_id)
    
    async with lock:
        print(f"[TRACE] send_next_question LOCKED per user {user_id}")
        
        try:
            state = user_states.get(user_id)
            if not state:
                print(f"[TRACE] Sessione non trovata per user {user_id}")
                await context.bot.send_message(chat_id=user_id, text="Sessione non trovata. Scrivi /start per iniziare.")
                return

            current_index = state["index"]
            total = state["total"]
            
            print(f"[TRACE] user {user_id} - index={current_index}, total={total}")

            # Verifica se il quiz è completato
            if current_index >= total:
                print(f"[TRACE] Quiz completato per user {user_id}")
                await show_final_stats(user_id, context, state, is_review_mode=state.get("is_review", False))
                manager = get_manager(user_id)
                manager.commit_changes()
                clear_user_lock(user_id)  # Rimuove il lock
                return

            q_index = state["order"][current_index]
            print(f"[TRACE] user {user_id} - caricamento domanda q_index={q_index}")
            
            question_data = await _validate_and_get_question(state, q_index, user_id, context)
            if question_data is None:
                print(f"[TRACE] user {user_id} - domanda {q_index} non valida, incremento index")
                # IMPORTANTE: qui NON richiamiamo send_next_question ricorsivamente
                # incrementiamo solo l'index e riproveremo nel prossimo ciclo
                return

            correct_index, new_answers = _get_shuffled_answers_and_correct_index(question_data)
            if correct_index is None or new_answers is None:
                print(f"[TRACE] user {user_id} - risposte non valide per domanda {q_index}, skip")
                state["index"] += 1
                state["total"] -= 1  # Decrementa il totale
                return

            state["quiz"][q_index]["_shuffled_answers"] = new_answers
            state["quiz"][q_index]["_correct_index"] = correct_index

            question_text = _build_question_text(state, question_data, new_answers)
            reply_markup = _build_question_keyboard(new_answers)

            if await _try_send_image(question_data, user_id, context, question_text, reply_markup):
                print(f"[TRACE] user {user_id} - domanda {q_index} inviata con immagine")
                return

            await _send_question_text(user_id, context, question_text, reply_markup)
            print(f"[TRACE] user {user_id} - domanda {q_index} inviata come testo")

        except Exception as e:
            print(f"❌ Errore critico in send_next_question per user {user_id}: {e}")
            import traceback
            traceback.print_exc()
            user_states.pop(user_id, None)
            clear_user_lock(user_id)
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text="❌ Si è verificato un errore. Riprova con /start"
                )
            except Exception:
                pass


def _get_shuffled_answers_and_correct_index(question_data):
    original_answers = question_data.get("answers", [])
    correct_index = question_data.get("correct_answer_index")
    if correct_index is None:
        correct_answer = question_data.get("correct_answer")
        if correct_answer and correct_answer in original_answers:
            correct_index = original_answers.index(correct_answer)
        else:
            return None, None
    shuffled = list(enumerate(original_answers))
    random.shuffle(shuffled)
    new_answers = [ans for _, ans in shuffled]
    new_correct_index = next((i for i, (orig_i, _) in enumerate(shuffled) if orig_i == correct_index), -1)
    return new_correct_index, new_answers

def _build_question_text(state, question_data, new_answers):
    question_index = f"{state['index'] + 1}."
    question_raw = question_data.get('question', 'Domanda mancante')
    escaped_question = escape_markdown(question_raw)
    if '*' in question_raw:
        question_text = f"{question_index} {escaped_question}\n\n"
    else:
        question_text = f"*{question_index} {escaped_question}*\n\n"
    for i, opt in enumerate(new_answers):
        question_text += f"*{chr(65+i)}.* {escape_markdown(opt)}\n"
    return question_text

def _build_question_keyboard(new_answers):
    keyboard = [
        [InlineKeyboardButton(chr(65 + i), callback_data=f"answer:{i}") for i in range(len(new_answers))]
    ]
    keyboard.append([
        InlineKeyboardButton("🛑 Stop", callback_data="stop"),
        InlineKeyboardButton("🔄 Cambia corso", callback_data="change_course")
    ])
    return InlineKeyboardMarkup(keyboard)

async def _try_send_image(question_data, user_id, context, question_text, reply_markup):
    image_filename = question_data.get("image")
    if image_filename:
        image_path = os.path.join(QUIZ_FOLDER, "images", image_filename)
        if os.path.isfile(image_path):
            try:
                async with aiofiles.open(image_path, "rb") as image_file:
                    photo_bytes = await image_file.read()
                    await asyncio.wait_for(
                        context.bot.send_photo(
                            chat_id=user_id,
                            photo=photo_bytes,
                            caption=question_text,
                            reply_markup=reply_markup,
                            parse_mode='Markdown'
                        ),
                        timeout=10.0
                    )
                return True
            except asyncio.TimeoutError:
                print(f"⏰ Timeout nell'invio immagine per user {user_id}")
            except Exception as e:
                print(f"❌ Errore nell'invio dell'immagine per user {user_id}: {e}")
    return False

async def _send_question_text(user_id, context, question_text, reply_markup):
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

async def _validate_and_get_question(state, q_index, user_id, context):
    question_id = None
    try:
        if q_index >= len(state["quiz"]):
            print(f"[ERROR] q_index {q_index} fuori range per user {user_id}")
            await context.bot.send_message(chat_id=user_id, text="❌ Errore nell'indice della domanda. Riprova con /start")
            user_states.pop(user_id, None)
            clear_user_lock(user_id)
            return None
            
        question_data = state["quiz"][q_index]
        question_id = question_data.get("id")
        
        print(f"[TRACE] Validazione domanda ID: {question_id} per user {user_id}")
        
        if not question_data.get("question") or not question_data.get("answers"):
            print(f"[ERROR] Domanda malformata per user {user_id}: {question_id}")
            state["index"] += 1
            state["total"] -= 1  # Decrementa il totale quando skippiamo
            # NON richiamare send_next_question qui!
            return None
            
        original_answers = question_data.get("answers", [])
        if len(original_answers) < 2:
            print(f"[ERROR] Domanda senza risposte sufficienti per user {user_id}: {question_id}")
            state["index"] += 1
            state["total"] -= 1  # Decrementa il totale quando skippiamo
            # NON richiamare send_next_question qui!
            return None
            
        print(f"[TRACE] Domanda validata correttamente per user {user_id}: {question_id}")
        return question_data
        
    except Exception as e:
        print(f"[ERROR] Eccezione in _validate_and_get_question per user {user_id}, question_id={question_id}: {e}")
        import traceback
        traceback.print_exc()
        return None



async def repeat_quiz(user_id: int, context: ContextTypes.DEFAULT_TYPE):
    
    # PULIZIA MANAGER ERRORI 
    manager = get_manager(user_id)
    manager.commit_changes()
    clear_manager(user_id)

    old_state = user_states.get(user_id)
    if not old_state or "quiz_file" not in old_state:
        await context.bot.send_message(chat_id=user_id, text="Sessione non valida. Scrivi /start per iniziare.")
        return

    quiz_file = old_state["quiz_file"]
    quiz_path = os.path.join(QUIZ_FOLDER, quiz_file)

    try:
        async with aiofiles.open(quiz_path, encoding="utf-8") as f:
            content = await f.read()
            quiz_data = json.loads(content)
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
    quiz_path = os.path.join(QUIZ_FOLDER, subject + JSON)
    async with aiofiles.open(quiz_path, encoding="utf-8") as f:
        content = await f.read()
        base = json.loads(content)
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
    async with aiofiles.open(pdf_path, "rb") as pdf_file:
        pdf_bytes = await pdf_file.read()
        await context.bot.send_document(chat_id=user_id, document=pdf_bytes, filename=pdf_path)
    os.remove(pdf_path)

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update or not update.callback_query:
        print("[ERROR] handle_callback: update o callback_query non valido")
        return

    query = update.callback_query
    user_id = query.from_user.id
    data = query.data

    # Validazione preventiva del callback data
    if not data or len(data) > 64:
        try:
            await query.answer("Pulsante non valido", show_alert=True)
        except:
            pass
        return

    print(f"[DEBUG] handle_callback chiamata per user {user_id}, data: {data}")

    # Always answer the callback query to avoid spinner
    try:
        await query.answer()
        print(f"[DEBUG] Query answered per user {user_id}")
    except Exception as e:
        error_msg = str(e).lower()
        print(f"[DEBUG] Errore nell'answer query: {e}")
        
        # Se il callback è invalido/scaduto, non continuare
        if any(keyword in error_msg for keyword in ["invalid", "expired", "too old"]):
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text="⚠️ Pulsante scaduto. Usa /start per ricominciare"
                )
            except:
                pass
            return

    # Rate limiting per callback
    if is_rate_limited(user_id):
        try:
            await context.bot.send_message(
                chat_id=user_id, 
                text="⏳ Stai andando troppo veloce! Riprova tra qualche secondo."
            )
        except:
            pass
        return

    # Try to parse JSON callback data
    callback = None
    if data and data.strip().startswith("{") and data.strip().endswith("}"):
        try:
            callback = json.loads(data)
        except json.JSONDecodeError as e:
            print(f"[DEBUG] Errore parsing JSON: {e}")

    manager = get_manager(user_id)

    # List of handler functions with their required arguments
    handler_functions = [
        lambda: handlers._handle_download_pdf(data, user_id, context),
        lambda: handlers._handle_review_errors(data, manager, query, update, context, user_id),
        lambda: handlers._handle_review_subject(data, update, context, user_id),
        lambda: handlers._handle_download_errors_pdf(data, manager, query, context, user_id),
        lambda: handlers._handle_stop(data, update, context),
        lambda: handlers._handle_clear_errors(data, manager, context, user_id),
        lambda: handlers._handle_change_course(data, manager, user_id, context),
        lambda: handlers._handle_select_quiz(data, user_id, context),
        lambda: handlers._handle_reset_stats(data, update, context),
        lambda: handlers._handle_choose_subject(data, update, context),
        lambda: handlers._handle_repeat_quiz(data, user_id, context),
        lambda: handlers._handle_answer(data, user_id, context),
        lambda: handlers._handle_show_mistakes(data, user_id, context),
        lambda: handlers._handle_git(data, context, user_id),
    ]

    for handler in handler_functions:
        if await handler():
            return



async def start_review_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE, subject: str):
    user_id = update.effective_user.id
    print(f"[DEBUG] start_review_quiz chiamata per user {user_id}, subject: {subject}")

    def send_error(msg):
        print(f"[DEBUG] {msg}")
        return context.bot.send_message(chat_id=user_id, text=msg)

    def load_quiz_file(path):
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[DEBUG] Errore caricamento file: {e}")
            return None

    def build_base_by_id(base):
        base_by_id = {}
        for i, q in enumerate(base):
            q_id = q.get("id")
            if q_id is not None:
                base_by_id[q_id] = q
            else:
                print(f"[DEBUG] Domanda {i} senza ID: {q.get('question', 'N/A')[:50]}...")
        return base_by_id

    def build_weighted_list(wrong_qs, base_by_id):
        """Restituisce una lista con domande duplicate (feature voluta) ma ogni occorrenza è una copia
        indipendente, così da non sovrascrivere _shuffled_answers / _correct_index tra ripetizioni.
        Il numero di ripetizioni dipende dal counter (peso) come prima.
        """
        weighted = []
        for entry in wrong_qs:
            q_id = entry.get("id")
            if not q_id:
                print(f"[DEBUG] Entry senza ID: {entry}")
                continue
            counter = entry.get("counter", 1)
            if q_id in base_by_id:
                repeat_times = min((counter + 1) // 2, 5)
                for _ in range(repeat_times):
                    # copia profonda per evitare side-effects tra occorrenze ripetute
                    weighted.append(copy.deepcopy(base_by_id[q_id]))
                print(f"[DEBUG] Aggiunta domanda ID {q_id}, {repeat_times} copie indipendenti")
            else:
                print(f"[DEBUG] ID {q_id} non trovato in base_by_id")
        return weighted

    try:
        manager = get_manager(user_id)
        wrong_qs = manager.get_for_subject(subject)
        quiz_path = os.path.join(QUIZ_FOLDER, subject + JSON)

        if not os.path.exists(quiz_path):
            await send_error(f"❌ File quiz non trovato per {subject}. Riprova con /start")
            return

        base = load_quiz_file(quiz_path)
        if base is None:
            await send_error("❌ Errore nel caricamento del quiz. Riprova con /start")
            return

        if not base:
            await send_error("❌ Quiz vuoto. Riprova con /start")
            return

        base_by_id = build_base_by_id(base)
        weighted = build_weighted_list(wrong_qs, base_by_id)

        selected = []
        if weighted:
            to_select = min(len(weighted), 30)
            selected = random.sample(weighted, to_select)

        # Add extra questions if needed
        if len(selected) < 30:
            used_ids = {q.get("id") for q in selected if q.get("id")}
            extras = [q for q in base if q.get("id") and q.get("id") not in used_ids]
            needed = 30 - len(selected)
            if extras:
                to_add = min(len(extras), needed)
                selected += random.sample(extras, to_add)

        if not selected:
            await send_error("❌ Nessuna domanda disponibile per il ripasso. Riprova con /start")
            return

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
        await send_next_question(user_id, context)

    except Exception as e:
        print(f"[ERROR] Errore in start_review_quiz per user {user_id}: {e}")
        import traceback
        traceback.print_exc()
        await context.bot.send_message(
            chat_id=user_id,
            text="❌ Si è verificato un errore. Riprova con /start"
        )
        user_states.pop(user_id, None)

    

async def handle_answer_callback(user_id: int, answer_index: int, context: ContextTypes.DEFAULT_TYPE):
    print(f"[TRACE] handle_answer_callback per user {user_id}, risposta {answer_index}")
    
    state = user_states.get(user_id)
    if not state:
        print(f"[TRACE] Sessione scaduta per user {user_id}")
        await context.bot.send_message(chat_id=user_id, text="Sessione scaduta. Riavvia il quiz con /start.")
        return

    subject = state.get("subject", "")
    current_index = state["index"]
    q_index = state["order"][current_index]
    
    print(f"[TRACE] user {user_id} - risponde alla domanda index={current_index}, q_index={q_index}")
    
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

    # Incrementa l'index PRIMA di chiamare send_next_question
    state["index"] += 1
    print(f"[TRACE] user {user_id} - incremento index a {state['index']}, score={state['score']}, total={state['total']}")
    
    # Ora chiama send_next_question che userà l'index aggiornato
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
    clear_user_lock(user_id)  # Pulisce anche il lock
   
    await show_final_stats(user_id, context, state, from_stop=True)
    user_states.pop(user_id, None)


async def show_mistakes(user_id, subject, context: ContextTypes.DEFAULT_TYPE):
    manager = get_manager(user_id)
    manager.commit_changes()
    wrong_qs = manager.get_for_subject(subject)
    
    async with aiofiles.open(os.path.join(QUIZ_FOLDER, subject + JSON), encoding="utf-8") as f:
        content = await f.read()
        base = json.loads(content)
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
        reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton(RIPASSA_ERRORI, callback_data="review_errors")]])
        await context.bot.send_message(chat_id=user_id, text=full_text, parse_mode='Markdown', reply_markup=reply_markup)


async def show_final_stats(user_id, context, state, from_stop=False, is_review_mode=False):
    if not state:
        return

    subject = state.get("subject")
    if subject is None:
        await context.bot.send_message(chat_id=user_id, text="Nessun corso selezionato.")
        return

    score = state["score"]
    total = state["total"]
    answered = state["index"]

    keyboard = []
    has_errors = False

    summary = ""

    if answered == 0:
        summary = "Nessuna risposta data. Quiz interrotto dall'utente."
    else:
        percentage = round((score / answered) * 100, 2) if answered else 0
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

        # GIF solo se quiz completato (tutte le domande risposte) e total == 30
        if answered == total == 30:
            if score == 30:
                await context.bot.send_animation(chat_id=user_id, animation=yay())
            elif score < 18:
                await context.bot.send_animation(chat_id=user_id, animation=yikes())

        summary = f"🎯Quiz completato!\nPunteggio: {score} su {answered} ({percentage}%)\n"
        summary += duration
      
        summary += "\n📊 Statistiche:\n"

        for sub, data in all_stats.items():
            perc = round((data['correct'] / data['total']) * 100, 2)
            summary += f"- {sub}: {perc}% ({data['correct']} su {data['total']})\n"

        manager = get_manager(user_id)
        manager.commit_changes() 
        has_errors = manager.has_wrong_answers()

    if from_stop:
        keyboard.append([
            InlineKeyboardButton(SCEGLI_MATERIA, callback_data="change_course")
        ])
    else:
        keyboard.append([
            InlineKeyboardButton("🔁 Ripeti quiz", callback_data="repeat_quiz"),
            InlineKeyboardButton("📚 Cambia materia", callback_data="change_course")
        ])
    if is_review_mode:
        keyboard.append(
            [
                InlineKeyboardButton(AZZERA_STATISTICHE, callback_data="reset_stats"),
                InlineKeyboardButton("🧽 Cancella Errori", callback_data=f"clear_errors:{state['subject']}")]
        )
    else: 
        keyboard.append([
            InlineKeyboardButton(AZZERA_STATISTICHE, callback_data="reset_stats")
        ])

    # Mostra bottoni errori SOLO se ci sono errori
    if has_errors:
        keyboard.append([
            InlineKeyboardButton(RIPASSA_ERRORI, callback_data="review_errors"),
            InlineKeyboardButton("📝 Mostra errori", callback_data=f"show_mistakes_{subject}")
        ])

    keyboard.append([
        InlineKeyboardButton("📥 Scarica pdf", callback_data=f"download_pdf:{state['quiz_file']}"),
        InlineKeyboardButton("🌐 Git", url="https://github.com/AdrianaRidolfi/telegram-bots")
    ])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(chat_id=user_id, text=summary, reply_markup=reply_markup)

async def stats(update: Update = None, context: ContextTypes.DEFAULT_TYPE = None, user_id: int = None):
    # Se user_id non passato, prendilo da update
    if user_id is None:
        if not update or not update.effective_user:
            print("[ERROR] stats: update e user_id non validi")
            return
        user_id = update.effective_user.id

    msg = ""

    keyboard = []
    keyboard.append([InlineKeyboardButton(SCEGLI_MATERIA, callback_data="_choose_subject_")])

    stats_manager = get_stats_manager(user_id)
    stats_data = stats_manager.get_summary()
    if not stats_data:
        msg = "Nessuna statistica disponibile."

    else:
        msg = "📊 Statistiche:\n"
        for sub, data in stats_data.items():
            perc = round((data["correct"] / data["total"]) * 100, 2)
            msg += f"📘 {sub}: {perc}% ({data['correct']} su {data['total']})\n"
        
        keyboard.append([InlineKeyboardButton(AZZERA_STATISTICHE, callback_data="reset_stats")])


    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(chat_id=user_id, text=msg, reply_markup=reply_markup)



async def reset_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    stats_manager = get_stats_manager(user_id)
    stats_manager.reset_stats()
    await context.bot.send_message(chat_id=user_id, text="✅ Statistiche azzerate!")

async def debug_message(update, context):
    print("[DEBUG] Messaggio ricevuto:", update.message.text)


def setup_bot():
    print("🔧 Configurazione bot...")
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("stats", stats))
    application.add_handler(CommandHandler("stop", stop))
    application.add_handler(CommandHandler("download", download))
    application.add_handler(CommandHandler("choose_subject", choose_subject))
    application.add_handler(CallbackQueryHandler(handle_callback))
    
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, debug_message))
    
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


def health_check(request):
    """Simple health check endpoint"""
    try:
        return web.Response(text="OK", status=200, headers={
            'Content-Type': 'text/plain',
            'Cache-Control': 'no-cache'
        })
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return web.Response(text="Health check failed", status=500)


def info_handler(request):
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


def setup_webhook_server():
    """FIXED: Simplified webhook server setup WITHOUT problematic middleware"""
    app = web.Application()
    
    # Telegram webhook endpoint - TOKEN is defined globally
    app.router.add_post(f"/{TOKEN}", webhook_handler)
    
    # Health check endpoints
    app.router.add_get("/health", health_check)
    app.router.add_get("/", health_check)
    app.router.add_get("/ping", health_check)
    app.router.add_get("/status", health_check)
    
    # Info endpoint
    app.router.add_get("/info", info_handler)
    
    logger.info("✅ Webhook server configured with routes:")
    logger.info(f"  POST /{TOKEN} -> webhook_handler")
    logger.info("  GET /health -> health_check")
    logger.info("  GET / -> health_check")
    logger.info("  GET /ping -> health_check")
    logger.info("  GET /status -> health_check")
    logger.info("  GET /info -> info_handler")
    
    return app

async def main():
    """Enhanced main function with better error handling"""
    global shutdown_event

    shutdown_event = asyncio.Event()
    logger.info("MAIN...")

    try:
        logger.info("Starting bot...")

        # Setup handlers
        setup_bot()

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
                app = setup_webhook_server()
                runner = web_runner.AppRunner(app)
                await runner.setup()

                site = web_runner.TCPSite(runner, "0.0.0.0", PORT)
                await site.start()

                logger.info(f"🌐 Webhook server started on 0.0.0.0:{PORT}")
                logger.info("🔍 Test endpoints:")
                logger.info(f"   https://{WEBHOOK_URL}/test")
                logger.info(f"   https://{WEBHOOK_URL}/health")
                logger.info(f"   https://{WEBHOOK_URL}/webhook-info")

                # Wait for shutdown event
                await shutdown_event.wait()

            except Exception as e:
                logger.error(f"❌ Server setup error: {e}")
                raise
            finally:
                try:
                    await runner.cleanup()
                except Exception:
                    pass

        else:
            logger.info("Polling mode activated")
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
        except Exception:
            pass

def signal_handler(signum, frame):
    global shutdown_event
    logger.info(f"🛑 Received signal {signum}. Shutting down...")
    if 'shutdown_event' in globals():
        shutdown_event.set()


if __name__ == "__main__":
    # Register signal handlers
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    try:
        if USE_WEBHOOK:
            asyncio.run(main())
        else:
            setup_bot()
            logger.info("Polling mode activated (outside main)")
            application.run_polling(drop_pending_updates=True)
    except KeyboardInterrupt:
        logger.info("\n🛑 Bot interrupted by user")
    except Exception as e:
        logger.error(f"❌ Critical error: {e}")
    finally:
        logger.info("👋 Bot terminated")
