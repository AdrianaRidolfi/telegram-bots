from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from exams_sync import ExamSync, ExamSyncError


EXAMS = ["Matematica Discreta", "Analisi matematica", "Calcolo delle probabilità e statistica", "Programmazione 1",
              "Algoritmi e strutture dati", "Architettura dei calcolatori", "Diritto per le aziende digitali", "Reti di calcolatori e Cybersecurity",
              "Programmazione 2", "Ingegneria del software", "Tecnologie Web", "Programmazione distribuita e cloud computing",
              "Strategia, organizzazione e marketing", "Corporate planning e valore d'impresa"]

async def sync_exam_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    context.user_data["sync_exam"] = {}
    context.user_data["exam_sync"] = ExamSync()
    await context.bot.send_message(chat_id=user_id, text="🔐 Inserisci il tuo username:")
    context.user_data["sync_state"] = "awaiting_username"

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
        context.user_data["sync_exam"]["password"] = text
        context.user_data["sync_state"] = "awaiting_exam"
        keyboard = [
            [InlineKeyboardButton(name, callback_data=f"select_exam_{name}")]
            for name in EXAMS
        ]
        await context.bot.send_message(
            chat_id=user_id,
            text="📚 Seleziona l'esame:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

async def handle_exam_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    subject = query.data.replace("select_exam_", "")
    context.user_data["sync_exam"]["subject"] = subject
    
    await query.edit_message_text(f"🧠 Sto sincronizzando l'esame *{subject}*...", parse_mode="Markdown")
    
    data = context.user_data["sync_exam"]
    syncer = context.user_data["exam_sync"]
    
    try:
        token = syncer.login(data["username"], data["password"])
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
        msg = f"*📊 {test_info.get('name_exam', subject)}*\n"
        msg += f"*Stato:* {test_info.get('status_name', 'N/A')}\n"
        msg += f"*Punteggio:* {test_info.get('points', 'N/A')}/30\n\n"
        
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
                msg += f"*{i+1}.* {question_text[:80]}{'...' if len(question_text) > 80 else ''}\n"
                msg += f"*Risposta:* {user_answer} {'✅' if is_correct else '❌'}\n\n"
        
        if len(responses) > 3:
            msg += f"... e altre {len(responses) - 3} domande\n\n"
        
        # Salva nel database
        syncer.save_exam_to_db(subject, parsed)
        
        msg += f"*✅ Sincronizzazione completata!*\n"
        msg += f"*Totale domande salvate:* {len(parsed)}"
        
        await context.bot.send_message(
            chat_id=user_id,
            text=msg,
            parse_mode="Markdown"
        )
        
    except ExamSyncError as e:
        await context.bot.send_message(chat_id=user_id, text=f"❌ Errore: {str(e)}")
    except Exception as e:
        print(f"Errore imprevisto: {e}")
        await context.bot.send_message(chat_id=user_id, text=f"❌ Errore durante la sincronizzazione:\n{str(e)}")