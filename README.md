# telegram-bots

Questo repository contiene bot Telegram per somministrare quiz agli utenti in chat private.

---

## Struttura del repository


```bash
```bash
telegram-bots/
├── quiz_bot/
│   ├── bot.py               # codice Python del bot
│   ├── requirements.txt     # dipendenze Python
│   ├── Procfile             # comando per il deploy su Render o simili
│   └──quizzes/
│     ├── convert.py           # codice di utility per convertire file .qwz e .txt nei json
│     ├── diritto.json         # file JSON con domande e risposte
│     └── altro_quiz.json      # altri quiz in JSON

```

## Formato del file `quiz.json`

Il file `quiz.json` contiene una lista di domande e risposte nel seguente formato:

```json
[
  {
    "question": "Testo della domanda",
    "answers": [
      "Risposta 1",
      "Risposta 2",
      "Risposta 3",
      "Risposta 4"
    ],
    "correct_answer": "Risposta corretta"
  }
]
```

- **question**: testo della domanda
- **options**: lista delle possibili risposte (in ordine)
- **answer**: indice (zero-based) della risposta corr

## Conversione e preparazione dei file JSON

I file di partenza potrebbero avere formati diversi, per uniformare il formato al JSON sopra, è presente uno script di conversione che per ora gestisce file .qwz e .txt, per utilizzarlo basta salvare il file di partenza nella cartella quiz e modificare i nomi dei file nel codice prima di lanciarlo. Il nome del file json sara' quello che viene visualizzato fra la scelta degli esami sul bot

```code
# Nome del file da convertire
input_file = "diritto.qwz"  # Cambia questo con il file da elaborare
output_json = "diritto.json"
```


## Comandi del bot

```code
    /start
```
Avvia la sessione quiz in chat privata con l'utente che ha inviato il comando.
Il bot inizia a fare le domande una ad una.

```code
    /stats
```
Mostra le statistiche dell'utente.

```code
    /stop
```
Termina la sessione quiz in corso per quell’utente.


## Deploy e sviluppo
Ogni bot è contenuto in una cartella separata per facilitare la manutenzione e l’aggiunta di nuovi bot. Per aggiungere un nuovo bot, crea una nuova cartella con i file base (bot.py, quiz.json, requirements.txt, Procfile). Configura il deploy su Render o altra piattaforma cloud, impostando la root directory del bot.

