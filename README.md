# telegram-bots

Questo repository contiene bot Telegram per somministrare quiz agli utenti in chat private.

---

## Come contribuire con nuovi test

Puoi contribuire aggiungendo nuovi quiz in formato `.json`.

### 1. Fai un fork del progetto

Vai su [https://github.com/AdrianaRidolfi/telegram-bots](https://github.com/AdrianaRidolfi/telegram-bots)  
e clicca su **Fork** in alto a destra per creare una copia nel tuo account.

### 2. Aggiungi il tuo quiz

- Crea un file `.json` nel formato seguente:

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
    "correct_answer": "Risposta 2"
  }
]
```

- Assicurati che:
    - il file sia un json valido.
    - correct_answer corrisponda esattamente a una delle risposte elencate in answers.

- Salva il file nella cartella quiz_bot/quizzes/ e dagli un nome descrittivo, ad esempio storia.json.

3. Fai una pull request. Una volta aggiunto il file e fatto il commit sul tuo fork:

  - Vai nella pagina del tuo fork.
  - Clicca su Pull request.
  - Seleziona il tuo branch con il quiz.
  - Clicca su Create pull request e inserisci un messaggio descrittivo.

Una volta approvato, il tuo quiz sarà incluso nel bot!


## Struttura del repository

```bash
telegram-bots/
├── quiz_bot/
│   ├── bot.py               # codice Python del bot
│   ├── requirements.txt     # dipendenze Python
│   ├── Procfile             # comando per il deploy su Render o simili
│   └── quizzes/
│     ├── images/             # cartella per le imagini
│     │   └── tec1.jpg
│     ├── fonts/               # cartella per i font utilizzati nei pdf
│     ├── convert.py           # codice di utility per convertire file .qwz e .txt nei json
│     ├── diritto.json         # file JSON con domande e risposte
│     └── altro_quiz.json      # altri quiz in JSON

```

## Dipendenze e installazione

Le dipendenze Python del bot sono elencate nel file [`requirements.txt`](/quiz_bot/requirements.txt). Per installarle localmente puoi usare:

```bash
pip install -r requirements.txt
```

## Deploy gratuito su Render

Il bot è attualmente deployato gratuitamente su [Render](https://render.com/). Questo significa che, se non viene utilizzato da un po' di tempo, il server può andare in modalità "sleep" per risparmiare risorse. In tal caso, la prima risposta al comando /start può richiedere fino a 50 secondi. Una volta riattivato, le risposte torneranno rapide.

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
    "correct_answer": "Risposta 2"
  }
]
```

- **question**: testo della domanda
- **options**: lista delle possibili risposte (in ordine)
- **answer**: indice (zero-based) della risposta corr

## Conversione e preparazione dei file JSON

I file di partenza potrebbero avere formati diversi, per uniformare il formato al JSON sopra, è presente uno script di conversione che per ora gestisce file .qwz e .txt, per utilizzarlo basta salvare il file di partenza nella cartella quizzes e modificare i nomi dei file nel codice prima di lanciarlo. Il nome del file json sara' quello che viene visualizzato fra la scelta degli esami sul bot

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
