# telegram-bots

Questo repository contiene [bot Telegram](https://core.telegram.org/bots/api) per somministrare quiz agli utenti in chat private.

---

## INDICE

- [Struttura del repository](#struttura-del-repository)
- [Dipendenze e installazione](#dipendenze-e-installazione)
- [Configurazione ambiente (`.env`)](#configurazione-ambiente-env)
- [Deploy su Render come Webhook](#deploy-su-render-come-webhook)
- [Deploy con Docker Compose](#deploy-con-docker-compose)
- [Come creare il tuo bot Telegram](#come-creare-il-tuo-bot-telegram)
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
├── Dockerfile                   # per build e run container
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
- `TELEGRAM_TOKEN`: il token del tuo bot Telegram (creato con [@BotFather](https://core.telegram.org/bots#botfather)).

---

## Deploy su Render come Webhook

Il bot viene deployato su [Render](https://render.com/) come **Web Service** usando Docker.  
Render costruisce automaticamente l'immagine Docker dal [`Dockerfile`](./Dockerfile) incluso nel repository.

**Passaggi principali:**
1. Crea un nuovo servizio su Render (Web Service) e collega questo repository.
2. Imposta le variabili d'ambiente (`TELEGRAM_TOKEN`, `FIREBASE_CREDENTIALS_FILE`, ecc.).
3. Render costruirà l'immagine Docker e avvierà il bot.
4. L'applicazione espone l'endpoint `/webhook` per ricevere gli aggiornamenti da Telegram.
5. **Imposta manualmente il webhook** del tuo bot Telegram puntando all'URL fornito da Render, usando la [API Telegram setWebhook](https://core.telegram.org/bots/api#setwebhook) oppure un comando come:
   ```bash
   curl -X POST "https://api.telegram.org/bot<TELEGRAM_TOKEN>/setWebhook?url=https://tuo-endpoint-su-render.com/webhook"
   ```

**Risorse utili:**
- [Guida ufficiale Render Docker](https://render.com/docs/deploy-docker)
- [Guida webhook Telegram](https://core.telegram.org/bots/api#setwebhook)

## Deploy con Docker Compose

Puoi anche eseguire il bot localmente o su altri server usando **Docker Compose**.

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

---

## Come creare il tuo bot Telegram

Puoi copiare questo codice per creare un tuo bot quiz personalizzato!

1. **Crea un bot su Telegram**  
   Vai su [@BotFather](https://core.telegram.org/bots#botfather), crea un nuovo bot e copia il token.

2. **Clona questo repository**  
   ```bash
   git clone https://github.com/AdrianaRidolfi/telegram-bots.git
   cd telegram-bots
   ```

3. **Prepara le variabili d'ambiente**  
   Copia `.env.example` in `.env` e inserisci il tuo token e le altre variabili.

4. **Prepara le credenziali Firebase**  
   Scarica il file `firebase-credentials.json` dal tuo progetto Firebase e posizionalo nella root.

5. **Deploy su Render o Docker**  
   - Su Render: collega il repo e imposta le variabili d'ambiente.
   - Con Docker: usa l'immagine generata dal [`Dockerfile`](./Dockerfile) e avvia con Docker Compose.

6. **Imposta manualmente il webhook**  
   Dopo il deploy, usa la [API Telegram setWebhook](https://core.telegram.org/bots/api#setwebhook) per collegare il tuo bot all'endpoint `/webhook` fornito da Render.

7. **Personalizza i quiz**  
   Modifica o aggiungi file nella cartella [`quiz_bot/quizzes/`](./quiz_bot/quizzes/) seguendo la struttura descritta sotto.

---

## Come contribuire con nuovi test

Puoi contribuire aggiungendo nuovi quiz in formato `.json` seguendo la struttura già presente nei file esistenti nella cartella [`quiz_bot/quizzes/`](./quiz_bot/quizzes/). 

### 1. Fai un fork del progetto

Per iniziare, crea una copia personale del progetto tramite il pulsante **Fork** su GitHub.

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
  }
]
```

- **question**: testo della domanda
- **answers**: lista delle possibili risposte
- **correct_answer**: la risposta corretta
- **image**: eventuale immagine jpg, da inserire in `quiz_bot/quizzes/images`
- **id**: identificativo univoco (puoi usare [add_ids.py](quiz_bot/quizzes/add_ids.py) per aggiungerli automaticamente)

- Assicurati che:
    - il file sia un json valido.
    - l'immagine, se presente, sia in formato jpg e inserita dentro quiz_bot/quizzes/images
    - correct_answer corrisponda esattamente a una delle risposte elencate in answers.

- Salva il file nella cartella quiz_bot/quizzes/ e dagli un nome descrittivo.

3. Fai una pull request per proporre il tuo quiz.

---

## Conversione e preparazione dei file JSON

Puoi convertire quiz da diversi formati a JSON usando lo script convert.py.
Formati supportati:

  - **.txt**: con blocchi DOMANDE e RISPOSTE, vedi [tecnologie.txt](quiz_bot/quizzes/tecnologie.txt) per un esempio
  - **.qwz**: file XML prodotto da [Question Writer](https://www.questionwriter.com/download.html)  
  - **.pdf**: struttura specifica, vedi README originale

### Come usare lo script:

Modifica dentro convert.py:

```python
input_file = "reti.pdf" #nome del file da convertire
output_json = "reti_di_calcolatori.json" #nome del json
```
e lancia lo script.

---

## Ripasso degli errori

Il bot implementa un sistema di ripasso mirato basato sugli errori commessi dagli utenti nei quiz.  
Le domande sbagliate vengono salvate su [Firestore](https://firebase.google.com/docs/firestore?hl=it) e riproposte in modo intelligente.

---

## Comandi del bot

```code
    /start
```
Avvia il bot mostrando il messaggio di benvenuto e i quiz disponibili.

```code
    /stats
```
Mostra le statistiche dell'utente.

```code
    /download
```
Scarica il quiz in formato PDF.

```code
    /choose_subject
```
Scegli la materia per iniziare lo studio.

---

## TO DO

- [x] fix gestione visualizzazione errori
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
- [ ] fix come riprendere descrizione esami presente
- [ ] add metodo per inserire test
- [ ] add metodo per fare discrimine fra solo inedite e tutte
- [ ] ingegneria del software aggiungi inedite da examsync
