from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from exams_sync import ExamSync, ExamSyncError
from pdf_generator import generate_exam_pdf
import time
import re


TOKEN_VALIDITY = 3600  # 1 ora in secondi


def escape_markdown(text):
    """Escape dei caratteri speciali per MarkdownV2"""
    if not text:
        return ""
    special_chars = r'([_*\[\]()~`>#+=|{}.!\\-])'  
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
        # Token ancora valido, va direttamente alla selezione
        await show_exam_selection(update, context)
    else:
        # Token scaduto o inesistente, richiede credenziali
        if token_info:
            await context.bot.send_message(
                chat_id=user_id, 
                text="🔄 Token scaduto, inserisci nuovamente le credenziali."
            )
        
        await context.bot.send_message(chat_id=user_id, text="🔐 Inserisci il tuo username:")
        context.user_data["analyze_state"] = "awaiting_username"


async def show_exam_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra la selezione degli esami disponibili dinamicamente"""
    user_id = update.effective_user.id
    
    # Ottiene il token valido
    token = await get_valid_token(context)
    
    if not token:
        await context.bot.send_message(
            chat_id=user_id, 
            text="❌ Token non valido. Riavvia con /analyze_exam per inserire nuovamente le credenziali."
        )
        return
    
    try:
        syncer = context.user_data.get("exam_sync", ExamSync())
        
        # Mostra messaggio di caricamento
        loading_msg = await context.bot.send_message(
            chat_id=user_id, 
            text="🔍 Caricamento esami disponibili..."
        )
        
        # Ottiene gli esami disponibili
        exams = syncer.get_exams(token)
        
        if not exams:
            await context.bot.edit_message_text(
                chat_id=user_id,
                message_id=loading_msg.message_id,
                text="❌ Nessun esame disponibile."
            )
            return
        
        # Crea i pulsanti dinamicamente dagli esami effettivamente disponibili
        keyboard = []
        
        for exam in exams:
            exam_name = exam.get("name_exam", "Esame sconosciuto")
            # Usa l'ID dell'esame come callback_data per evitare problemi di encoding
            callback_data = f"select_exam_id_{exam['id']}"
            keyboard.append([InlineKeyboardButton(exam_name, callback_data=callback_data)])
        
        # Aggiunge pulsante per rinnovare il token
        keyboard.append([InlineKeyboardButton("🔄 Rinnova token", callback_data="renew_token")])
        
        # Salva gli esami per riferimento futuro
        context.user_data["available_exams"] = exams
        
        await context.bot.edit_message_text(
            chat_id=user_id,
            message_id=loading_msg.message_id,
            text=f"📚 Seleziona l'esame da analizzare:\n\n📊 <i>Trovati {len(exams)} esami disponibili</i>",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )
        
    except ExamSyncError as e:
        await context.bot.send_message(
            chat_id=user_id, 
            text=f"❌ Errore nel caricamento degli esami: {str(e)}"
        )


async def get_valid_token(context: ContextTypes.DEFAULT_TYPE):
    """Ottiene un token valido (senza salvare credenziali)"""
    token_info = context.user_data.get("auth_token", {})
    
    if is_token_valid(token_info):
        return token_info["token"]
    
    # Token scaduto e non salva le credenziali
    return None


async def handle_exam_analyze_flow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gestisce il flusso di inserimento credenziali"""
    if "analyze_state" not in context.user_data:
        return  # Non fa nulla se non siamo nel flusso
    
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
            
            # Salva SOLO il token (non le credenziali)
            context.user_data["auth_token"] = {
                "token": token,
                "timestamp": time.time()
            }
            
            # Rimuove lo stato di attesa e le credenziali temporanee
            context.user_data.pop("analyze_state", None)
            context.user_data["analyze_exam"].pop("username", None)
            
            await context.bot.send_message(chat_id=user_id, text="✅ Login effettuato con successo!")
            await show_exam_selection(update, context)
            
        except ExamSyncError as e:
            await context.bot.send_message(
                chat_id=user_id, 
                text=f"❌ Errore di login: {str(e)}\n\n🔐 Inserisci nuovamente il tuo username:"
            )
            context.user_data["analyze_state"] = "awaiting_username"


async def show_post_analyze_menu(update_or_query, context: ContextTypes.DEFAULT_TYPE):
    # Gestisce Update e CallbackQuery
    if hasattr(update_or_query, 'effective_user'):
        # Update
        user_id = update_or_query.effective_user.id
    elif hasattr(update_or_query, 'from_user'):
        # CallbackQuery
        user_id = update_or_query.from_user.id
    else:
        # Fallback, prova a estrarre l'user_id in altro modo
        user_id = getattr(update_or_query, 'user_id', None)
        if not user_id:
            print(f"Errore: impossibile determinare user_id da {type(update_or_query)}")
            return
    
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
    
    # Gestisce il rinnovo del token
    if query.data == "renew_token":
        await handle_token_renewal(query, context)
        return
    
    # Gestisce la selezione dell'esame tramite ID
    if query.data.startswith("select_exam_id_"):
        exam_id = query.data.replace("select_exam_id_", "")
        await process_exam_analysis_by_id(query, context, exam_id, user_id)


async def handle_token_renewal(query, context: ContextTypes.DEFAULT_TYPE):
    """Gestisce il rinnovo del token"""
    # Cancella il token e gli esami salvati
    context.user_data.pop("auth_token", None)
    context.user_data.pop("available_exams", None)
    context.user_data["analyze_exam"] = {}
    
    await query.edit_message_text("🔐 Inserisci il nuovo username:")
    context.user_data["analyze_state"] = "awaiting_username"


async def process_exam_analysis_by_id(query, context: ContextTypes.DEFAULT_TYPE, exam_id: str, user_id: int):
    """Processa l'analisi dell'esame selezionato tramite ID"""
    try:
        exam_id = int(exam_id)
    except ValueError:
        await context.bot.send_message(chat_id=user_id, text="❌ ID esame non valido.")
        return
    
    # Trova l'esame negli esami disponibili
    available_exams = context.user_data.get("available_exams", [])
    target_exam = None
    
    for exam in available_exams:
        if exam.get("id") == exam_id:
            target_exam = exam
            break
    
    if not target_exam:
        await context.bot.send_message(chat_id=user_id, text="❌ Esame non trovato.")
        return
    
    exam_name = target_exam.get("name_exam", "Esame sconosciuto")
    context.user_data["analyze_exam"]["subject"] = exam_name
    
    await query.edit_message_text(
        f"👀 Sto caricando l'esame <b>{exam_name}</b>...",
        parse_mode="HTML"
    )
    
    syncer = context.user_data.get("exam_sync", ExamSync())
    
    try:
        # Ottiene un token valido
        token = await get_valid_token(context)
        
        if not token:
            await context.bot.send_message(
                chat_id=user_id, 
                text="❌ Token non valido. Riavvia con /analyze_exam per inserire nuovamente le credenziali."
            )
            return
        
        # Ottiene i risultati dell'esame
        result = syncer.get_exam_result(token, exam_id)
        
        test_info = result.get("test", {})
        responses = result.get("responses", [])
        
        if not responses:
            await context.bot.send_message(chat_id=user_id, text="❌ Nessuna risposta trovata per questo esame.")
            return
        
        # Processa e mostra i risultati
        await display_exam_results(context, user_id, test_info, responses, exam_name, syncer)
        
        # Genera PDF
        await generate_exam_pdf(responses, exam_name, context.bot, user_id)
        
        # Mostra menu post-analisi
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
    
    # Costruisce il messaggio con caratteri escapati
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
        msg += f"\\.\\.\\. e altre {escape_markdown(str(len(responses) - 3))} domande\n\n"
    
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
    
    # Se è un errore di token, non possiamo più rinnovarlo automaticamente
    if any(keyword in error_str for keyword in ["token", "unauthorized", "401"]):
        context.user_data.pop("auth_token", None)  # Cancella token scaduto
        context.user_data.pop("available_exams", None)  # Cancella anche gli esami salvati
        
        await context.bot.send_message(
            chat_id=user_id, 
            text=f"❌ Token scaduto: {str(error)}\nRiavvia con /analyze_exam per inserire nuovamente le credenziali."
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
    """Cancella token e dati dalla sessione"""
    context.user_data.pop("auth_token", None)
    context.user_data.pop("available_exams", None)
    context.user_data.pop("analyze_exam", None)
    context.user_data.pop("analyze_state", None)
    
    user_id = update.effective_user.id
    await context.bot.send_message(chat_id=user_id, text="🗑️ Sessione cancellata.")