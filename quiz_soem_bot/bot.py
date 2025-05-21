import json
import random
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext

# Carica il quiz una volta sola
with open("quiz.json", encoding="utf-8") as f:
    QUIZ = json.load(f)

# Dizionario per tenere traccia dello stato utente
user_states = {}

def start(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    # Invia messaggio in privato all’utente, aprendo la chat privata se necessario
    context.bot.send_message(chat_id=user_id, text="Benvenuto! Iniziamo il quiz. Scrivi /stop per fermarti.")

    # crea lista indici mescolata e la metti nello stato
    question_order = list(range(len(QUIZ)))
    random.shuffle(question_order)

    user_states[user_id] = {
        "order": question_order,  # ordine random delle domande
        "index": 0,
        "score": 0
    }
    send_next_question(update, context)

def send_next_question(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    state = user_states.get(user_id)

    if not state or state["index"] >= len(QUIZ):
        context.bot.send_message(chat_id=user_id, text=f"Quiz completato! Punteggio: {state['score']} su {len(QUIZ)}")
        user_states.pop(user_id, None)
        return

    # prendi la domanda usando l'indice randomizzato
    question_index = state["order"][state["index"]]
    question_data = QUIZ[question_index]

    question_text = f"{state['index'] + 1}. {question_data['question']}\n"
    for i, answer in enumerate(question_data["answers"]):
        question_text += f"{chr(65 + i)}. {answer}\n"

    context.bot.send_message(chat_id=user_id, text=question_text)

def handle_message(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    state = user_states.get(user_id)

    if not state:
        context.bot.send_message(chat_id=user_id, text="Scrivi /start per iniziare il quiz.")
        return

    question_index = state["order"][state["index"]]
    question_data = QUIZ[question_index]

    user_answer = update.message.text.strip().upper()
    correct = question_data["correct_answer"].strip().lower()
    all_answers = [a.strip().lower() for a in question_data["answers"]]

    try:
        if user_answer in ["A", "B", "C", "D"]:
            index = ord(user_answer) - ord("A")
            answer = all_answers[index]
        else:
            answer = user_answer.lower()

        if answer == correct:
            context.bot.send_message(chat_id=user_id, text="Corretto!")
            state["score"] += 1
        else:
            context.bot.send_message(chat_id=user_id, text=f"Sbagliato! Risposta corretta: {question_data['correct_answer']}")
    except:
        context.bot.send_message(chat_id=user_id, text="Risposta non valida. Riprova.")
        return

    state["index"] += 1
    send_next_question(update, context)

def stop(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if user_id in user_states:
        context.bot.send_message(chat_id=user_id, text="Quiz interrotto.")
        user_states.pop(user_id, None)
    else:
        context.bot.send_message(chat_id=user_id, text="Nessun quiz attivo. Scrivi /start per iniziare.")

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
