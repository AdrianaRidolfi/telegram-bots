from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from exams_sync import ExamSync, ExamSyncError
from pdf_generator import generate_exam_pdf
import time
import re


EXAMS = ["Matematica Discreta", "Analisi matematica", "Calcolo delle probabilità e statistica", "Programmazione 1",
         "Algoritmi e strutture dati", "Architettura dei calcolatori", "Diritto per le aziende digitali", 
         "Reti di calcolatori e Cybersecurity", "Programmazione 2", "Ingegneria del software", 
         "Tecnologie Web", "Programmazione distribuita e cloud computing", 
         "Strategia, organizzazione e marketing", "Corporate planning e valore d'impresa"]

TOKEN_VALIDITY = 3600  # 1 ora in secondi


def escape_markdown(text):
    """Escape dei caratteri speciali per MarkdownV2"""
    if not text:
        return ""
    special_chars = r'([_*\[\]()~`>#+=|{}.!\\])'
    return re.sub(special_chars, r'\\\1', str(text))


def is_token_valid(token_info):
    """Verifica se il token è ancora valido"""
    if not token_info:
        return False
    
    token = token_info.get("token")
    token_timestamp = token_info.get("timestamp", 0)
    
    if not token:
        return False
    
    current_time = time.time()
    token_age = current_time - token_timestamp
    return token_age < TOKEN_VALIDITY


async def analyze_exam_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Avvia il processo di analisi dell'esame"""
    user_id = update.effective_user.id
    context.user_data["analyze_exam"] = {}
    context.user_data["exam_sync"] = ExamSync()
    
    # Controlla se abbiamo un token valido
    token_info = context.user_data.get("auth_token", {})
    
    if is_token_valid(token_info):
        # Token ancora valido, vai direttamente alla selezione
        await show_exam_selection(update, context)
    else:
        # Token scaduto o inesistente, richiedi credenziali
        if token_info:
            await context.bot.send_message(
                chat_id=user_id, 
                text="🔄 Token scaduto, inserisci nuovamente le credenziali."
            )
        
        await context.bot.send_message(chat_id=user_id, text="🔐 Inserisci il tuo username:")
        context.user_data["analyze_state"] = "awaiting_username"


async def show_exam_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra la selezione degli esami disponibili"""
    user_id = update.effective_user.id
    keyboard = [
        [InlineKeyboardButton(name, callback_data=f"select_exam_{name}")]
        for name in EXAMS
    ]
    
    # Aggiungi pulsante per rinnovare il token
    keyboard.append([InlineKeyboardButton("🔄 Rinnova token", callback_data="renew_token")])
    
    await context.bot.send_message(
        chat_id=user_id,
        text="📚 Seleziona l'esame da analizzare:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def get_valid_token(context: ContextTypes.DEFAULT_TYPE):
    """Ottiene un token valido, rinnovandolo se necessario"""
    token_info = context.user_data.get("auth_token", {})
    
    if is_token_valid(token_info):
        return token_info["token"]
    
    # Token scaduto, prova a rinnovarlo con le credenziali salvate
    saved_credentials = context.user_data.get("saved_credentials", {})
    username = saved_credentials.get("username")
    password = saved_credentials.get("password")
    
    if not (username and password):
        return None
    
    syncer = context.user_data.get("exam_sync", ExamSync())
    try:
        new_token = syncer.login(username, password)
        # Salva il nuovo token
        context.user_data["auth_token"] = {
            "token": new_token,
            "timestamp": time.time()
        }
        return new_token
    except ExamSyncError:
        # Login fallito, cancella credenziali e token
        context.user_data.pop("saved_credentials", None)
        context.user_data.pop("auth_token", None)
        return None


async def handle_exam_analyze_flow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gestisce il flusso di inserimento credenziali"""
    if "analyze_state" not in context.user_data:
        return  # Non fare nulla se non siamo nel flusso
    
    user_id = update.effective_user.id
    state = context.user_data.get("analyze_state")
    text = update.message.text

    if state == "awaiting_username":
        context.user_data["analyze_exam"]["username"] = text
        context.user_data["analyze_state"] = "awaiting_password"
        await context.bot.send_message(chat_id=user_id, text="🔐 Ora inserisci la password:")
        
    elif state == "awaiting_password":
        username = context.user_data["analyze_exam"]["username"]
        password = text
        
        # Prova il login per ottenere il token
        syncer = context.user_data.get("exam_sync", ExamSync())
        try:
            token = syncer.login(username, password)
            
            # Salva il token e le credenziali per rinnovi futuri
            context.user_data["auth_token"] = {
                "token": token,
                "timestamp": time.time()
            }
            context.user_data["saved_credentials"] = {
                "username": username,
                "password": password
            }
            
            # Rimuovi lo stato di attesa
            context.user_data.pop("analyze_state", None)
            
            await context.bot.send_message(chat_id=user_id, text="✅ Login effettuato con successo!")
            await show_exam_selection(update, context)
            
        except ExamSyncError as e:
            await context.bot.send_message(
                chat_id=user_id, 
                text=f"❌ Errore di login: {str(e)}\n\n🔐 Inserisci nuovamente il tuo username:"
            )
            context.user_data["analyze_state"] = "awaiting_username"


async def show_post_analyze_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra il menu dopo l'analisi dell'esame"""
    user_id = update.effective_user.id if update.effective_user else update.callback_query.from_user.id
    
    keyboard = [
        [InlineKeyboardButton("📚 Analizza altro esame", callback_data="analyze_another_exam")],
        [InlineKeyboardButton("🎯 Torna alle esercitazioni", callback_data="_choose_subject_")]
    ]
    
    await context.bot.send_message(
        chat_id=user_id,
        text="Cosa vuoi fare ora?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def handle_post_analyze_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gestisce il menu post-analisi"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "analyze_another_exam":
        await analyze_exam_start(update, context)
    elif query.data == "_choose_subject_":
        pass  # Torna al menu principale


async def handle_exam_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gestisce la selezione e l'analisi dell'esame"""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    # Gestisci il rinnovo del token
    if query.data == "renew_token":
        await handle_token_renewal(query, context)
        return
    
    # Gestisci la selezione dell'esame
    if query.data.startswith("select_exam_"):
        subject = query.data.replace("select_exam_", "")
        await process_exam_analysis(query, context, subject, user_id)


async def handle_token_renewal(query, context: ContextTypes.DEFAULT_TYPE):
    """Gestisce il rinnovo del token"""
    # Cancella token e credenziali
    context.user_data.pop("auth_token", None)
    context.user_data.pop("saved_credentials", None)
    context.user_data["analyze_exam"] = {}
    
    await query.edit_message_text("🔐 Inserisci il nuovo username:")
    context.user_data["analyze_state"] = "awaiting_username"


async def process_exam_analysis(query, context: ContextTypes.DEFAULT_TYPE, subject: str, user_id: int):
    """Processa l'analisi dell'esame selezionato"""
    context.user_data["analyze_exam"]["subject"] = subject
    
    await query.edit_message_text(
        f"📊 Sto caricando l'esame *{escape_markdown(subject)}*...", 
        parse_mode="MarkdownV2"
    )
    
    syncer = context.user_data.get("exam_sync", ExamSync())
    
    try:
        # Ottieni un token valido
        token = await get_valid_token(context)
        
        if not token:
            await context.bot.send_message(
                chat_id=user_id, 
                text="❌ Token non valido. Riavvia con /analyze_exam per inserire nuovamente le credenziali."
            )
            return
        
        # Ottieni gli esami disponibili
        exams = syncer.get_exams(token)
        
        if not exams:
            await context.bot.send_message(chat_id=user_id, text="❌ Nessun esame disponibile.")
            return
        
        # Trova l'esame specifico per la materia selezionata
        target_exam = syncer.get_exam_by_subject(subject, exams)
        
        if not target_exam:
            # Mostra gli esami disponibili per debug
            available_exams = [exam.get("name_exam", "N/A") for exam in exams[:5]]
            await context.bot.send_message(
                chat_id=user_id, 
                text=f"❌ Esame '{subject}' non trovato.\n\nEsami disponibili: {', '.join(available_exams)}"
            )
            return
        
        # Ottieni i risultati dell'esame
        exam_id = target_exam["id"]
        result = syncer.get_exam_result(token, exam_id)
        
        test_info = result.get("test", {})
        responses = result.get("responses", [])
        
        if not responses:
            await context.bot.send_message(chat_id=user_id, text="❌ Nessuna risposta trovata per questo esame.")
            return
        
        # Processa e mostra i risultati
        await display_exam_results(context, user_id, test_info, responses, subject, syncer)
        
        # Genera PDF
        await generate_exam_pdf(responses, subject, context.bot, user_id)
        
        # Mostra il menu post-analisi
        await show_post_analyze_menu(query, context)
        
    except ExamSyncError as e:
        await handle_exam_sync_error(context, user_id, e)
    except Exception as e:
        print(f"Errore imprevisto: {e}")
        await context.bot.send_message(
            chat_id=user_id, 
            text=f"❌ Errore durante l'analisi:\n{str(e)}"
        )


async def display_exam_results(context: ContextTypes.DEFAULT_TYPE, user_id: int, 
                              test_info: dict, responses: list, subject: str, syncer: ExamSync):
    """Mostra i risultati dell'esame formattati"""
    # Processa le risposte per il salvataggio
    parsed_questions = []
    
    # Costruisci il messaggio con caratteri escapati
    exam_name = escape_markdown(test_info.get('name_exam', subject))
    status_name = escape_markdown(test_info.get('status_name', 'N/A'))
    points = escape_markdown(str(test_info.get('points', 'N/A')))
    
    msg = f"*📊 {exam_name}*\n"
    msg += f"*Stato:* {status_name}\n"
    msg += f"*Punteggio:* {points}/30\n\n"
    
    for i, response in enumerate(responses):
        question_text = response.get("question", "")
        user_answer = response.get("answer", "")
        is_correct = response.get("point") == 1
        
        parsed_questions.append({
            "text": question_text,
            "user_answer": user_answer,
            "correct": is_correct
        })
        
        # Mostra solo le prime 3 domande nel messaggio
        if i < 3:
            question_preview = escape_markdown(
                question_text[:80] + ('...' if len(question_text) > 80 else '')
            )
            answer_preview = escape_markdown(user_answer)
            
            msg += f"*{i+1}\\.* {question_preview}\n"
            msg += f"*Risposta:* {answer_preview} {'✅' if is_correct else '❌'}\n\n"
    
    if len(responses) > 3:
        msg += f"\\.\\.\\. e altre {len(responses) - 3} domande\n\n"
    
    # Salva nel database in background
    syncer.save_exam_to_db(subject, parsed_questions)
    
    msg += f"*✅ Analisi completata\\!*"
    
    await context.bot.send_message(
        chat_id=user_id,
        text=msg,
        parse_mode="MarkdownV2"
    )


async def handle_exam_sync_error(context: ContextTypes.DEFAULT_TYPE, user_id: int, error: ExamSyncError):
    """Gestisce gli errori di sincronizzazione, inclusi i problemi di token"""
    error_str = str(error).lower()
    
    # Se è un errore di token, prova a rinnovarlo
    if any(keyword in error_str for keyword in ["token", "unauthorized", "401"]):
        context.user_data.pop("auth_token", None)  # Cancella token scaduto
        
        # Prova a ottenere un nuovo token
        new_token = await get_valid_token(context)
        if new_token:
            await context.bot.send_message(
                chat_id=user_id, 
                text="🔄 Token rinnovato automaticamente. Riprova l'analisi."
            )
        else:
            await context.bot.send_message(
                chat_id=user_id, 
                text=f"❌ Token scaduto e rinnovo fallito: {str(error)}\nRiavvia con /analyze_exam"
            )
    else:
        await context.bot.send_message(chat_id=user_id, text=f"❌ Errore: {str(error)}")


# Funzioni di utilità per debug e gestione sessione
async def token_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra informazioni sul token salvato (per debug)"""
    user_id = update.effective_user.id
    token_info = context.user_data.get("auth_token", {})
    
    if not token_info:
        await context.bot.send_message(chat_id=user_id, text="❌ Nessun token salvato")
        return
    
    token_timestamp = token_info.get("timestamp", 0)
    current_time = time.time()
    token_age = current_time - token_timestamp
    remaining_time = TOKEN_VALIDITY - token_age
    
    if remaining_time > 0:
        minutes_remaining = int(remaining_time // 60)
        await context.bot.send_message(
            chat_id=user_id, 
            text=f"✅ Token valido\n⏰ Scade tra: {minutes_remaining} minuti"
        )
    else:
        await context.bot.send_message(chat_id=user_id, text="❌ Token scaduto")


async def clear_session(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancella token e credenziali dalla sessione"""
    context.user_data.pop("auth_token", None)
    context.user_data.pop("saved_credentials", None)
    context.user_data.pop("analyze_exam", None)
    context.user_data.pop("analyze_state", None)
    
    user_id = update.effective_user.id
    await context.bot.send_message(chat_id=user_id, text="🗑️ Sessione cancellata.")