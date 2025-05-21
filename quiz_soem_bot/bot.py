import json
import random
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext

# Carica il quiz una volta sola
with open("quiz.json", encoding="utf-8") as f:
    QUIZ = json.load(f)

# Dizionario per tenere traccia dello stato utente
# Ogni utente ha: index corrente, score, ordine casuale delle domande (lista di indici)
user_states = {}

def start(update: Update, context: CallbackContext):
    user = update.effective_user
    chat = update.effective_chat

    # Se siamo in gruppo o topic, rispondi in privato
    if chat.type in ['group', 'supergroup']:
        context.bot.send_message(chat_id=user.id, text="Ciao! Ti mando il quiz in chat privata.")
        # Facciamo partire il quiz in privato simulando un messaggio da solo
        # oppure mandiamo il messaggio di benvenuto
        context.bot.send_message(chat_id=user.id, text="Benvenuto! Iniziamo il quiz. Scrivi /stop per fermarti.")
    else:
        # Siamo già in chat privata
        context.bot.send_message(chat_id=user.id, text="Benvenuto! Iniziamo il quiz. Scrivi /stop per fermarti.")

    # Inizializza stato: ordina casualmente gli indici delle domande
    question_order = list(range(len(QUIZ)))
    random.shuffle(question_order)
    user_states[user.id] = {"index": 0, "score": 0, "order": question_order}

    # Invia prima domanda in privato
    send_next_question_private(user.id, context)

def send_next_question_private(user_id, context: CallbackContext):
    state = user_states.get(user_id)

    if not state:
        context.bot.send_message(chat_id=user_id, text="Scrivi /start per iniziare il quiz.")
        return

    if state["index"] >= len(QUIZ):
        context.bot.send_message(chat_id=user_id, text=f"Quiz completato! Punteggio: {state['score']} su {len(QUIZ)}")
        user_states.pop(user_id, None)
        return

    q_idx = state["order"][state["index"]]
    question_data = QUIZ[q_idx]

    question_text = f"{state['index'] + 1}. {question_data['question']}\n"
    for i, answer in enumerate(question_data["answers"]):
        question_text += f"{chr(65 + i)}. {answer}\n"

    context.bot.send_message(chat_id=user_id, text=question_text)

def handle_message(update: Update, context: CallbackContext):
    user = update.effective_user
    chat = update.effective_chat

    # Il quiz funziona solo in chat privata
    if chat.type != 'private':
        # Ignora messaggi nei gruppi e topic
        return

    state = user_states.get(user.id)

    if not state:
        context.bot.send_message(chat_id=user.id, text="Scrivi /start per iniziare il quiz.")
        return

    user_answer = update.message.text.strip().upper()
    q_idx = state["order"][state["index"]]
    question_data = QUIZ[q_idx]
    correct = question_data["correct_answer"].strip().lower()
    all_answers = [a.strip().lower() for a in question_data["answers"]]

    try:
        # Gestione A, B, C, D oppure risposta completa
        if user_answer in ["A", "B", "C", "D"]:
            index = ord(user_answer) - ord("A")
            answer = all_answers[index]
        else:
            answer = user_answer.lower()

        if answer == correct:
            context.bot.send_message(chat_id=user.id, text="✅ Corretto!")
            state["score"] += 1
        else:
            context.bot.send_message(chat_id=user.id, text=f"❌ Sbagliato! Risposta corretta: {question_data['correct_answer']}")
    except:
        context.bot.send_message(chat_id=user.id, text="Risposta non valida. Riprova.")
        return

    state["index"] += 1
    send_next_question_private(user.id, context)

def stop(update: Update, context: CallbackContext):
    user = update.effective_user
    if user.id in user_states:
        context.bot.send_message(chat_id=user.id, text="Quiz interrotto.")
        user_states.pop(user.id, None)
    else:
        context.bot.send_message(chat_id=user.id, text="Nessun quiz attivo. Scrivi /start per iniziare.")

def main():
    TOKEN = "7781432394:AAEftn4wvo1gXnJ4pekdwY0vnd7NonvR3NQ"
    updater = Updater(token=TOKEN, use_context=True)
    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("stop", stop))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))

    updater.start_polling()
    print("Bot avviato. Premi CTRL+C per fermarlo.")
    updater.idle()

if __name__ == '__main__':
    main()
