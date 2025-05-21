# telegram-bots

Questo repository contiene bot Telegram per somministrare quiz agli utenti in chat private.

---

## Struttura del repository

Ogni bot ha una propria cartella separata, ad esempio:

```bash
telegram-bots/
└── quiz_soem_bot/
    ├── bot.py          # codice Python del bot
    ├── quiz.json       # domande e risposte del quiz in formato JSON
    ├── requirements.txt # dipendenze Python
    └── Procfile        # comando per avviare il bot su Render
```

## Formato del file `quiz.json`

Il file `quiz.json` contiene una lista di domande e risposte nel seguente formato:

```json
[
  {
    "question": "Tra i seguenti autori chi è noto per aver sviluppato teorie sull’organizzazione scientifica del lavoro?",
    "options": [
      "Karl Marx",
      "Frederick W. Taylor",
      "Max Weber",
      "Henry Ford"
    ],
    "answer": 1
  }
]
```

- **question**: testo della domanda
- **options**: lista delle possibili risposte (in ordine)
- **answer**: indice (zero-based) della risposta corr


## Creare un bot Telegram con BotFather

Apri Telegram e cerca il bot @BotFather.
Digita /newbot e segui la procedura guidata per creare un nuovo bot.
Copia il token API che ti viene fornito, servirà per collegare il codice al bot Telegram.

## Comandi del bot

```code
    /start
```
Avvia la sessione quiz in chat privata con l'utente che ha inviato il comando.
Il bot inizia a fare le domande una ad una.

```code
    /stop
```
Termina la sessione quiz in corso per quell’utente.


## Deploy e sviluppo
Ogni bot è contenuto in una cartella separata per facilitare la manutenzione e l’aggiunta di nuovi bot. Per aggiungere un nuovo bot, crea una nuova cartella con i file base (bot.py, quiz.json, requirements.txt, Procfile). Configura il deploy su Render o altra piattaforma cloud, impostando la root directory del bot.

