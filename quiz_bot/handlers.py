from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from bot import (
    clear_manager, stats, user_states, JSON, QUIZ_FOLDER, RIPASSA_ERRORI, SCEGLI_MATERIA,
    start_review_quiz, select_quiz, reset_stats, choose_subject, repeat_quiz, generate_errors_pdf,
    stop, show_mistakes, show_final_stats, handle_answer_callback, get_stats_manager
)
from pdf_generator import generate_pdf

# Helper functions for callback handling


async def _handle_download_pdf(data, user_id, context):
    # Gestione callback come stringa (nuovo formato)
    if data.startswith("download_pdf:"):
        print(f"[DEBUG] Comando PDF (string) per user {user_id}")
        subject = data.split("download_pdf:")[1]
        if subject:
            await generate_pdf(subject, context.bot, user_id)
        return True
    return False

async def _handle_review_errors(data, manager, query, update, context, user_id):
    if data == "review_errors":
        print(f"[DEBUG] Review errors per user {user_id}")
        subjects = list(manager.get_all().keys())
        print(f"[DEBUG] Materie disponibili: {subjects}")

        if not subjects:
            print(f"[DEBUG] Nessuna materia trovata per user {user_id}")
            await query.answer("Non ci sono errori da ripassare!", show_alert=True)
            return True
        elif len(subjects) == 1:
            print(f"[DEBUG] Una sola materia, avvio diretto: {subjects[0]}")
            await start_review_quiz(update, context, subjects[0])
            return True

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
        return True
    return False

async def _handle_review_subject(data, update, context, user_id):
    if data.startswith("review_subject_"):
        subject = data.split("review_subject_")[1]
        print(f"[DEBUG] Review subject selezionato: {subject} per user {user_id}")
        await start_review_quiz(update, context, subject)
        return True
    return False

async def _handle_download_errors_pdf(data, manager, query, context, user_id):
    if data.startswith("download_errors_pdf:"):
        subject = data.split("download_errors_pdf:")[1]
        await generate_errors_pdf(user_id, subject, context)
        return True
    elif data == "no_download_errors_pdf":
        subjects = list(manager.get_all().keys())
        if len(subjects) == 1:
            await start_review_quiz(query, context, subjects[0])
            return True
        keyboard = [
            [InlineKeyboardButton(subj.replace("_", " "), callback_data=f"review_subject_{subj}")]
            for subj in subjects
        ]
        keyboard.append([InlineKeyboardButton("🔙 Indietro", callback_data="change_course")])
        await query.edit_message_text("Scegli la materia da ripassare:", reply_markup=InlineKeyboardMarkup(keyboard))
        return True
    return False

async def _handle_stop(data, update, context):
    if data == "stop":
        await stop(update, context)
        return True
    return False

async def _handle_clear_errors(data, manager, context, user_id):
    if data.startswith("clear_errors:"):
        subject = data.split(":")[1]
        manager.remove_subject(subject)
        await context.bot.send_message(
            chat_id=user_id,
            text=f"✅ Errori per *{subject}* cancellati!",
            parse_mode="Markdown"
        )
        return True
    return False

async def _handle_change_course(data, manager, user_id, context):
    if data == "change_course":
        
        state = user_states.get(user_id)
        
        await stats(user_id=user_id, context=context)
        
        if state:
            manager.commit_changes()
            clear_manager(user_id)
            user_states.pop(user_id, None)

        return True
    return False

async def _handle_select_quiz(data, user_id, context):
    if data.endswith(JSON): 
        user_states.pop(user_id, None)
        await select_quiz(None, context, user_id=user_id, filename=data)
        return True
    return False

async def _handle_reset_stats(data, update, context):
    if data == "reset_stats":
        await reset_stats(update, context)
        return True
    return False

async def _handle_choose_subject(data, update, context):
    if data == "_choose_subject_":
        await choose_subject(update, context)
        return True
    return False

async def _handle_repeat_quiz(data, user_id, context):
    if data == "repeat_quiz":
        await repeat_quiz(user_id, context)
        return True
    return False

async def _handle_answer(data, user_id, context):
    if data.startswith("answer:"):
        selected = int(data.split(":")[1])
        await handle_answer_callback(user_id, selected, context)
        return True
    return False

async def _handle_show_mistakes(data, user_id, context):
    if data.startswith("show_mistakes_"):
        subject = data.split("show_mistakes_")[1]
        await show_mistakes(user_id, subject, context)
        return True
    return False

async def _handle_git(data, context, user_id):
    if data == "git":
        await context.bot.send_message(
            chat_id=user_id,
            text="📂 Puoi visualizzare il codice su GitHub:\nhttps://github.com/AdrianaRidolfi/telegram-bots"
        )
        return True
    return False
