# telegram-bots

Questo repository contiene [bot Telegram](https://core.telegram.org/bots/api) per somministrare quiz agli utenti in chat private.

---

## INDICE

- [Struttura del repository](#struttura-del-repository)
- [Dipendenze e installazione](#dipendenze-e-installazione)
- [Configurazione ambiente (`.env`)](#configurazione-ambiente-env)
- [Deploy con Docker Compose](#deploy-con-docker-compose)
- [Come contribuire con nuovi test](#come-contribuire-con-nuovi-test)
- [Conversione e preparazione dei file JSON](#conversione-e-preparazione-dei-file-json)
- [Ripasso degli errori](#ripasso-degli-errori)
- [Comandi del bot](#comandi-del-bot)
- [TO DO](#to-do)

## Struttura del repository

```bash
telegram-bots/
├── quiz_bot/
│   ├── bot.py                   # Codice principale del bot Telegram
│   ├── get_gifs.py              # Utility per GIF di feedback
│   ├── pdf_generator.py         # Generazione PDF dei quiz
│   ├── requirements.txt         # Dipendenze Python
│   ├── user_stats.py            # Gestione statistiche utente
│   ├── wrong_answers.py         # Gestione risposte errate
│   ├── test_firestore.py        # Script di test Firestore
│   ├── trova_inedite.py         # Utility per domande inedite
│   ├── quizzes/
│   │   ├── add_ids.py           # Utility per aggiungere ID ai quiz
│   │   ├── convert.py           # Utility per conversione quiz in JSON
│   │   ├── [quiz].json          # File quiz in formato JSON
│   │   ├── images/              # Immagini associate ai quiz
│   │   └── fonts/               # Font per PDF
│   └── Procfile                 # (Non più usato, era per Render)
├── firebase-credentials.json    # Credenziali Firebase (NON versionato, vedi sotto)
├── Dockerfile                   #  per build e run container
├── docker-compose.yml           # per gestione servizi
├── .env.example                 # Esempio di file .env
└── README.md                    # TU SEI QUI
```

## Dipendenze e installazione

Le dipendenze Python del bot sono elencate nel file [`requirements.txt`](/quiz_bot/requirements.txt). Per installarle localmente puoi usare:

```bash
pip install -r quiz_bot/requirements.txt
```

## Configurazione ambiente `.env`

Il bot utilizza alcune variabili d'ambiente per funzionare.  
**Non modificare direttamente il file** [`.env.example`](./.env.example): copialo e rinominalo in `.env`, poi inserisci i tuoi valori.

```bash
cp .env.example .env
```

**Esempio di `.env.example`:**
```bash
CLIENT_SECRET=client_secret_value_here
FIREBASE_CREDENTIALS_FILE=firebase-credentials.json
TELEGRAM_TOKEN=telegram_token_value_here
```

- `CLIENT_SECRET`: (opzionale) chiave segreta per eventuali integrazioni future.
- `FIREBASE_CREDENTIALS_FILE`: nome del file con le credenziali Firebase (deve essere presente nella root del progetto o nella directory specificata).
- `TELEGRAM_TOKEN`: il token del tuo bot Telegram (creato con @BotFather).

---

## Deploy con Docker Compose

Il modo consigliato per eseguire il bot è tramite **Docker Compose**, che semplifica la gestione di variabili d’ambiente e volumi.

### 1. Prepara i file necessari

- `.env` (vedi sopra)
- `firebase-credentials.json` (scaricalo da Firebase e posizionalo nella root del progetto)

### 2. Avvia il bot

```bash
docker compose up --build
```

Questo comando:
- Costruisce l’immagine Docker usando il [Dockerfile](./Dockerfile)
- Avvia il servizio `quiz-bot` come definito in [docker-compose.yml](./docker-compose.yml)
- Monta i volumi per quiz e credenziali, così puoi aggiornare quiz e credenziali senza rebuildare l’immagine

### 3. Personalizza la tua immagine

Se vuoi creare una tua versione personalizzata (ad esempio con quiz diversi):

- Modifica o aggiungi i file nella cartella [`quiz_bot/quizzes/`](./quiz_bot/quizzes/)
- Ricostruisci e riavvia con:

```bash
docker compose up --build
```


## Come contribuire con nuovi test

Puoi contribuire aggiungendo nuovi quiz in formato `.json` seguendo la struttura già presente nei file esistenti nella cartella [`quiz_bot/quizzes/`](./quiz_bot/quizzes/). 

### 1. Fai un fork del progetto

Per iniziare, devi creare una tua copia personale di questo progetto. Per farlo, clicca sul pulsante **Fork** che trovi in alto a destra su questa pagina GitHub. Questo creerà una copia del progetto nel tuo account, sulla quale potrai lavorare liberamente.

### 2. Aggiungi il tuo quiz

- Crea un file `.json` nel formato seguente:

```json
[
  {
    "question": "Testo della domanda 1?",
    "answers": [
      "Risposta A",
      "Risposta B",
      "Risposta C",
      "Risposta D"
    ],
    "correct_answer": "Risposta B",
    "image": "immagine_quiz1.jpg",
    "id": "86c42b34-d157-4eef-981b-8d7ee94c929f"
  },
  {
    "question": "Testo della domanda 2?",
    "answers": [
      "Opzione 1",
      "Opzione 2",
      "Opzione 3",
      "Opzione 4"
    ],
    "correct_answer": "Opzione 3",
    "id": "a1b2c3d4-e5f6-7890-1234-567890abcdef"
  }
]
```

- **question**: testo della domanda
- **answers**: lista delle possibili risposte
- **correct_answer**: la risposta corretta
- **image**: eventuale immagine jpg, deve in quel caso essere aggiunta nella cartella images
- **id**: identificativo univoco, puoi utilizzare [add_ids.py](/quiz_bot/quizzes/add_ids.py) per aggiungere gli **id** alle tue domande in maniera automatica.


- Assicurati che:
    - il file sia un json valido.
    - l'immagine, se presente, sia in formato jpg e inserita dentro quiz_bot/quizzes/images
    - correct_answer corrisponda esattamente a una delle risposte elencate in answers.


- Salva il file nella cartella quiz_bot/quizzes/ e dagli un nome descrittivo, ad esempio storia.json.


3. Fai una pull request. Una volta aggiunto il file e fatto il commit sul tuo fork:

  - Vai nella pagina del tuo fork.
  - Clicca su Pull request.
  - Seleziona il tuo branch con il quiz.
  - Clicca su Create pull request e inserisci un messaggio descrittivo.

Una volta approvato, il tuo quiz sarà incluso nel bot!

## Conversione e preparazione dei file JSON

Puoi convertire quiz da diversi formati a JSON usando lo script convert.py.
Formati supportati:

  - **.txt**: con blocchi DOMANDE e RISPOSTE, vedi [tecnologie.txt](/quiz_bot/quizzes/tecnologie.txt) per un esempio

  - **.qwz**: file XML prodotto da [Question Writer](https://www.questionwriter.com/download.html)  

  - **.pdf**: richiedono una struttura specifica per essere letti dallo script.

**Come dev'essere strutturato un PDF per la conversione:**

Il testo del PDF deve seguire questa struttura per ciascuna domanda:

```
1. Testo della domanda
A. Opzione A
B. Opzione B
C. Opzione C
D. Opzione D

Answer: B
```

Ogni domanda comincia con numero.
Le opzioni iniziano con A., B., ecc.
La risposta corretta è indicata dopo Answer:
Le eventuali immagini devono essere vere immagini, non solo testo o placeholder. Verranno associate automaticamente alla domanda più vicina nella pagina e salvate come .jpg nella cartella images/.

Il nome delle immagini sarà generato automaticamente a partire dal nome del file JSON (es. ret1.jpg, ret2.jpg, ecc. se il JSON si chiama reti_di_calcolatori.json).

### Come usare lo script:

Modifica dentro convert.py:

```python
input_file = "reti.pdf" #nome del file da convertire
output_json = "reti_di_calcolatori.json" #nome del json, sarà anche quello visualizzato nel bottone di scelta
```
e lancia lo script. Le domande saranno salvate nel file JSON.

## Ripasso degli errori

Il bot implementa un sistema di ripasso mirato basato sugli errori commessi dagli utenti nei quiz.

Come funziona:

Le domande sbagliate vengono salvate automaticamente su [Firestore](https://firebase.google.com/docs/firestore?hl=it), all’interno di un database non relazionale chiamato:

```code
  quiz-bot-errori
```

Per ogni utente Telegram, i dati sono salvati nel percorso:

```code
  wrong-answers/<telegram_user_id>/<materia>
```
Per ogni domanda sbagliata vengono salvati:

```code
  id: l'ID univoco della domanda sbagliata
  counter: un contatore che indica quante volte è stata sbagliata (x3)
```
![immagine](https://github.com/user-attachments/assets/286fcb0d-aa4a-46b0-ae67-650bda575e42)

### Logica del ripasso:

Quando un utente attiva una sessione di ripasso per una materia, il bot:
  - Recupera le domande sbagliate di quella materia
  - Per ciascuna, la inserisce in una lista ponderata in base al numero di errori:
      Una domanda sbagliata più volte appare più frequentemente
      Es.: una domanda con counter = 3 può essere riproposta fino a 2 volte
      Il numero massimo di ripetizioni per ogni domanda è 5
  - Se le domande sbagliate sono meno di 30, il bot aggiunge altre domande casuali non ancora sbagliate per arrivare a 30
  - La lista finale viene mescolata e inviata all’utente come nuovo quiz di ripasso

Questo approccio consente di:
  - Concentrarsi sulle domande più difficili per l’utente
  - Alternare ripasso mirato a domande nuove
  - Costruire una memoria a lungo termine attraverso la ripetizione distribuita
  - Ogni volta che una risposta è stata sbagliata l'utente dovrà rispondere correttamente 3 volte affinché sparisca dal ripasso

## Comandi del bot

```code
    /start
```
Avvia il bot mostrando un messaggio di benvenuto, le informazioni sui quiz presenti ed i bottoni per iniziare con i test.

```code
    /stats
```
Mostra le statistiche dell'utente.

```code
    /download
```
Mostra i bottoni con i quiz presenti per decidere quale scaricare in formato PDF, il bot crea il file sul momento quindi non c'è rischio non sia allineato con i quiz presenti.

```code
    /choose_subject
```
Mostra i bottoni con i quiz presenti per iniziare con lo studio


## TO DO

- [x] fix gestione visualizzazione errori (bisogna prima salvare quelli appena fatti e poi riprenderli)
- [x] fix quando vengono mostrati bottoni errori
- [ ] fix come riprendere descrizione esami presente
- [ ] add metodo per inserire test
- [ ] add metodo per fare discrimine fra solo inedite e tutte
- [ ] ingegneria del software aggiungi inedite da examsync
- [x] sposta su docker
- [x] crea docker file
- [x] crea docker compose
- [x] aggiorna requirements
- [x] crea file .env
- [x] aggiungi .env a gitignore
- [x] Rimuovi endpoint webhook: Elimina o commenta @app.post("/webhook") in bot.py
- [x] Aggiungi avvio polling in lifespan(): await application.start_polling()
- [x] Costruisci immagine: docker compose up --build -d
- [x] Controlla log: docker compose logs -f
- [x] env di esempio
