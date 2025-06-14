from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from exams_sync import ExamSync


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
    syncer =context.user_data["exam_sync"]

    try:
        token = syncer.login(data["username"], data["password"])
        exams = syncer.get_exams(token)
        if not exams:
            await context.bot.send_message(chat_id=user_id, text="❌ Nessun esame disponibile.")
            return

        exam_id = exams[0]["id"]
        result = syncer.get_exam_result(token, exam_id)

        parsed = []
        msg = ""
        for q in result["questions"]:
            question_text = q["questionText"]
            user_ans = q["userAnswer"]
            correct = q["isCorrect"]
            parsed.append({
                "text": question_text,
                "user_answer": user_ans,
                "correct": correct
            })
            msg += f"• *{question_text}*\nRisposta: _{user_ans}_ {'✅' if correct else '❌'}\n\n"

        syncer.save_exam_to_db(subject, parsed)

        await context.bot.send_message(
            chat_id=user_id,
            text=f"*✅ Sincronizzazione completata!*\n\n{msg}",
            parse_mode="Markdown"
        )

    except Exception as e:
        await context.bot.send_message(chat_id=user_id, text=f"❌ Errore durante la sincronizzazione:\n{e}")
