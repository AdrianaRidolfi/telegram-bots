from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from exams_sync import ExamSync, ExamSyncError
from pdf_generator import generate_exam_pdf
import time
import re


EXAMS = ["Matematica Discreta", "Analisi matematica", "Calcolo delle probabilità e statistica", "Programmazione 1",
              "Algoritmi e strutture dati", "Architettura dei calcolatori", "Diritto per le aziende digitali", "Reti di calcolatori e Cybersecurity",
              "Programmazione 2", "Ingegneria del software", "Tecnologie Web", "Programmazione distribuita e cloud computing",
              "Strategia, organizzazione e marketing", "Corporate planning e valore d'impresa"]

def escape_markdown(text):
    if not text:
        return ""
    # Caratteri da escapare: _ * [ ] ( ) ~ ` > # + - = | { } . !
    special_chars = r'([_*\[\]()~`>#+=|{}.!\\])'
    return re.sub(special_chars, r'\\\1', str(text))

async def sync_exam_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    context.user_data["sync_exam"] = {}
    context.user_data["exam_sync"] = ExamSync()
    
    # Controlla se abbiamo un token valido
    token_info = context.user_data.get("auth_token", {})
    token = token_info.get("token")
    token_timestamp = token_info.get("timestamp", 0)
    
    # Verifica se il token è ancora valido (assumiamo scadenza di 1 ora)
    current_time = time.time()
    token_age = current_time - token_timestamp
    TOKEN_VALIDITY = 3600  # 1 ora in secondi
    
    if token and token_age < TOKEN_VALIDITY:
        # Token ancora valido, vai direttamente alla selezione
        await show_exam_selection(update, context)
    else:
        # Token scaduto o inesistente, richiedi credenziali
        if token:
            await context.bot.send_message(chat_id=user_id, text="🔄 Token scaduto, inserisci nuovamente le credenziali.")
        
        await context.bot.send_message(chat_id=user_id, text="🔐 Inserisci il tuo username:")
        context.user_data["sync_state"] = "awaiting_username"

async def show_exam_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    keyboard = [
        [InlineKeyboardButton(name, callback_data=f"select_exam_{name}")]
        for name in EXAMS
    ]
    
    # Aggiungi pulsante per forzare il rinnovo del token
    keyboard.append([InlineKeyboardButton("🔄 Rinnova token", callback_data="renew_token")])
    
    await context.bot.send_message(
        chat_id=user_id,
        text="📚 Seleziona l'esame:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def get_valid_token(context: ContextTypes.DEFAULT_TYPE):
    token_info = context.user_data.get("auth_token", {})
    token = token_info.get("token")
    token_timestamp = token_info.get("timestamp", 0)
    
    # Verifica validità token
    current_time = time.time()
    token_age = current_time - token_timestamp
    TOKEN_VALIDITY = 3600  # 1 ora
    
    if token and token_age < TOKEN_VALIDITY:
        return token
    
    # Token scaduto, prova a rinnovarlo con le credenziali salvate
    saved_credentials = context.user_data.get("saved_credentials", {})
    if saved_credentials.get("username") and saved_credentials.get("password"):
        syncer = context.user_data.get("exam_sync", ExamSync())
        try:
            new_token = syncer.login(saved_credentials["username"], saved_credentials["password"])
            # Salva il nuovo token
            context.user_data["auth_token"] = {
                "token": new_token,
                "timestamp": current_time
            }
            return new_token
        except ExamSyncError:
            # Login fallito, cancella credenziali e token
            context.user_data.pop("saved_credentials", None)
            context.user_data.pop("auth_token", None)
            return None
    
    return None

async def handle_exam_sync_flow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "sync_state" not in context.user_data:
        return  # Non fare nulla se non siamo nel flusso
    
    user_id = update.effective_user.id
    state = context.user_data.get("sync_state")
    text = update.message.text

    if state == "awaiting_username":
        context.user_data["sync_exam"]["username"] = text
        context.user_data["sync_state"] = "awaiting_password"
        await context.bot.send_message(chat_id=user_id, text="🔐 Ora inserisci la password:")
    elif state == "awaiting_password":
        username = context.user_data["sync_exam"]["username"]
        password = text
        context.user_data["sync_exam"]["password"] = password
        
        # Prova il login per ottenere il token
        syncer = context.user_data.get("exam_sync", ExamSync())
        try:
            token = syncer.login(username, password)
            
            # Salva il token e le credenziali per rinnovi futuri
            current_time = time.time()
            context.user_data["auth_token"] = {
                "token": token,
                "timestamp": current_time
            }
            context.user_data["saved_credentials"] = {
                "username": username,
                "password": password
            }
            
            # Rimuovi lo stato di attesa
            context.user_data.pop("sync_state", None)
            
            await context.bot.send_message(chat_id=user_id, text="✅ Login effettuato con successo!")
            await show_exam_selection(update, context)
            
        except ExamSyncError as e:
            await context.bot.send_message(chat_id=user_id, text=f"❌ Errore di login: {str(e)}\n\n🔐 Inserisci nuovamente il tuo username:")
            context.user_data["sync_state"] = "awaiting_username"

async def show_post_sync_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, subject: str):
    user_id = update.effective_user.id if update.effective_user else update.callback_query.from_user.id
    
    keyboard = [
        [InlineKeyboardButton("📥 Carica altro esame", callback_data="load_another_exam")],
        [InlineKeyboardButton("🎯 Torna alle esercitazioni", callback_data="_choose_subject_")],
       # [InlineKeyboardButton("📁 Scarica tutto dal DB", callback_data="download_all_db")]
    ]
    
    await context.bot.send_message(
        chat_id=user_id,
        text="Cosa vuoi fare?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_post_sync_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "load_another_exam":
        # Richiama il comando sync_exam
        await sync_exam_start(update, context)
    elif query.data == "_choose_subject_":
        pass
    elif query.data == "download_all_db":
        await show_db_subjects_selection(update, context)

async def show_db_subjects_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.callback_query.from_user.id
    
    try:
        syncer = context.user_data.get("exam_sync", ExamSync())
        subjects = syncer.get_subjects_from_db()
        
        if not subjects:
            await context.bot.send_message(
                chat_id=user_id, 
                text="❌ Nessuna materia trovata nel database."
            )
            return
        
        keyboard = [
            [InlineKeyboardButton(subject, callback_data=f"download_db_{subject}")]
            for subject in subjects
        ]
        
        await update.callback_query.edit_message_text(
            text="📁 Seleziona la materia da scaricare:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
    except Exception as e:
        await context.bot.send_message(
            chat_id=user_id, 
            text=f"❌ Errore nel recupero delle materie: {str(e)}"
        )

async def handle_db_download(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    if query.data.startswith("download_db_"):
        subject = query.data.replace("download_db_", "")
        
        await query.edit_message_text(f"📁 Sto preparando il download per *{escape_markdown(subject)}*...", parse_mode="MarkdownV2")
        
        try:
            syncer = context.user_data.get("exam_sync", ExamSync())
            all_questions = syncer.download_all_from_db(subject)
            
            if not all_questions:
                await context.bot.send_message(
                    chat_id=user_id, 
                    text=f"❌ Nessuna domanda trovata per {subject}"
                )
                return
            
            # Genera PDF con tutte le domande
           # await generate_all_pdf(all_questions, f"{subject} - Completo", context.bot, user_id)
            
            await context.bot.send_message(
                chat_id=user_id,
                text=f"✅ Download completato per *{escape_markdown(subject)}*\n📊 Totale domande: {len(all_questions)}",
                parse_mode="MarkdownV2"
            )
            
        except Exception as e:
            await context.bot.send_message(
                chat_id=user_id, 
                text=f"❌ Errore durante il download: {str(e)}"
            )

async def handle_exam_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    # Gestisci il rinnovo del token
    if query.data == "renew_token":
        # Cancella token e credenziali
        context.user_data.pop("auth_token", None)
        context.user_data.pop("saved_credentials", None)
        context.user_data["sync_exam"] = {}
        
        await query.edit_message_text("🔐 Inserisci il nuovo username:")
        context.user_data["sync_state"] = "awaiting_username"
        return
    
    # Gestisci la selezione dell'esame
    if query.data.startswith("select_exam_"):
        subject = query.data.replace("select_exam_", "")
        context.user_data["sync_exam"]["subject"] = subject
        
        await query.edit_message_text(f"🧠 Sto sincronizzando l'esame *{escape_markdown(subject)}*...", parse_mode="MarkdownV2")
        
        syncer = context.user_data.get("exam_sync", ExamSync())
        
        try:
            # Ottieni un token valido
            token = await get_valid_token(context)
            
            if not token:
                await context.bot.send_message(
                    chat_id=user_id, 
                    text="❌ Token non valido. Riavvia con /sync_exam per inserire nuovamente le credenziali."
                )
                return
            
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
            
            exam_id = target_exam["id"]
            result = syncer.get_exam_result(token, exam_id)
            
            # Usa la struttura corretta
            test_info = result.get("test", {})
            responses = result.get("responses", [])
            
            if not responses:
                await context.bot.send_message(chat_id=user_id, text="❌ Nessuna risposta trovata per questo esame.")
                return
            
            # Processa le risposte
            parsed = []
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
                
                parsed.append({
                    "text": question_text,
                    "user_answer": user_answer,
                    "correct": is_correct
                })
                
                # Mostra solo le prime 3 domande nel messaggio
                if i < 3:
                    question_preview = escape_markdown(question_text[:80] + ('...' if len(question_text) > 80 else ''))
                    answer_preview = escape_markdown(user_answer)
                    
                    msg += f"*{i+1}\\.* {question_preview}\n"
                    msg += f"*Risposta:* {answer_preview} {'✅' if is_correct else '❌'}\n\n"
            
            if len(responses) > 3:
                msg += f"\\.\\.\\. e altre {len(responses) - 3} domande\n\n"
            
            # Salva nel database
            syncer.save_exam_to_db(subject, parsed)
            
            msg += f"*✅ Sincronizzazione completata\\!*\n"
            msg += f"*Totale domande salvate:* {len(parsed)}"
            
            await context.bot.send_message(
                chat_id=user_id,
                text=msg,
                parse_mode="MarkdownV2"
            )
            
            # Genera PDF
            await generate_exam_pdf(responses, subject, context.bot, user_id)
            
            # Mostra il menu post-sincronizzazione
            await show_post_sync_menu(update, context, subject)

            
        except ExamSyncError as e:
            # Se è un errore di token, prova a rinnovarlo
            if "token" in str(e).lower() or "unauthorized" in str(e).lower() or "401" in str(e):
                context.user_data.pop("auth_token", None)  # Cancella token scaduto
                
                # Prova a ottenere un nuovo token
                new_token = await get_valid_token(context)
                if new_token:
                    await context.bot.send_message(
                        chat_id=user_id, 
                        text="🔄 Token rinnovato automaticamente. Riprova la sincronizzazione."
                    )
                    # Potresti anche richiamare ricorsivamente la funzione qui
                else:
                    await context.bot.send_message(
                        chat_id=user_id, 
                        text=f"❌ Token scaduto e rinnovo fallito: {str(e)}\nRiavvia con /sync_exam"
                    )
            else:
                await context.bot.send_message(chat_id=user_id, text=f"❌ Errore: {str(e)}")
        except Exception as e:
            print(f"Errore imprevisto: {e}")
            await context.bot.send_message(chat_id=user_id, text=f"❌ Errore durante la sincronizzazione:\n{str(e)}")

# Funzione per mostrare info sul token (opzionale, per debug)
async def token_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra informazioni sul token salvato"""
    user_id = update.effective_user.id
    token_info = context.user_data.get("auth_token", {})
    
    if not token_info:
        await context.bot.send_message(chat_id=user_id, text="❌ Nessun token salvato")
        return
    
    token_timestamp = token_info.get("timestamp", 0)
    current_time = time.time()
    token_age = current_time - token_timestamp
    remaining_time = 3600 - token_age  # 1 ora di validità
    
    if remaining_time > 0:
        minutes_remaining = int(remaining_time // 60)
        await context.bot.send_message(
            chat_id=user_id, 
            text=f"✅ Token valido\n⏰ Scade tra: {minutes_remaining} minuti"
        )
    else:
        await context.bot.send_message(chat_id=user_id, text="❌ Token scaduto")

# Funzione per cancellare token e credenziali
async def clear_session(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancella token e credenziali dalla sessione"""
    context.user_data.pop("auth_token", None)
    context.user_data.pop("saved_credentials", None)
    user_id = update.effective_user.id
    await context.bot.send_message(chat_id=user_id, text="🗑️ Sessione cancellata.")