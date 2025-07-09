# telegram-bots

Questo repository contiene [bot Telegram](https://core.telegram.org/bots/api) per somministrare quiz agli utenti in chat private.

---

## INDICE

- [Struttura del repository](#struttura-del-repository)
- [Dipendenze e istallazione](#dipendenze-e-installazione)
- [Deploy su render](#deploy-su-render)
- [Come contribuire con nuovi test](#come-contribuire-con-nuovi-test)
- [Conversione e preparazione dei file json](#conversione-e-preparazione-dei-file-json)
- [Ripasso](#ripasso-degli-errori)
- [Comandi del bot](#comandi-del-bot)

## Struttura del repository

```bash

telegram-bots/
├── quiz_bot
│   ├── bot.py                         # codice Python del bot
│   ├── get_gifs.py
│   ├── pdf_generator.py               # script per generare PDF
│   ├── Procfile                       # comando per il deploy su Render o simili
│   ├── quizzes
│   │   ├── add_ids.py                 # utility per aggiungere gli id a un json
│   │   ├── comunicazione_digital.json # quiz in formato JSON
│   │   ├── convert.py                 # utility per convertire in JSON
│   │   ├── fonts                      # cartella per i font usati nei PDF
│   │   │   └── [file di font vari]
│   │   ├── images                     # cartella per le immagini usate nei quiz
│   │   │   └── [immagini .jpg]
│   │   └── [test .json]
│   ├── requirements.txt               # dipendenze Python
│   ├── test_firestore.py              # script di test per Firestore
│   ├── trova_inedite.py               # utility per trovare domande assenti nel json
│   ├── user_stats.py                  # gestione statistiche utente
│   └── wrong_answers.py               # gestione risposte errate
└── README.md                          # TU SEI QUI                     
```

## Dipendenze e installazione

Le dipendenze Python del bot sono elencate nel file [`requirements.txt`](/quiz_bot/requirements.txt). Per installarle localmente puoi usare:

```bash
pip install -r requirements.txt
```

## Deploy su Render

Il bot è attualmente deployato gratuitamente su [Render](https://render.com/). Questo significa che, se non viene utilizzato da un po' di tempo, il server può andare in modalità "sleep" per risparmiare risorse. In tal caso, la prima risposta al comando /start può richiedere più di 50 secondi. Una volta riattivato, le risposte torneranno rapide.

## Deploy come immagine Docker

costruisci immagine:
```bash 
docker build -t quiz-bot ./quiz_bot
```


## Come contribuire con nuovi test

Puoi contribuire aggiungendo nuovi quiz in formato `.json`.

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

- [ ] fix gestione visualizzazione errori (bisogna prima salvare quelli appena fatti e poi riprenderli)
- [ ] fix quando vengono mostrati bottoni errori
- [ ] fix come riprendere descrizione esami presente
- [ ] add metodo per inserire test
- [ ] add metodo per fare discrimine fra solo inedite e tutte
- [ ] ingegneria del software aggiungi inedite da examsync
- [ ] sposta su docker
- [ ] crea docker file
- [ ] crea docker compose
- [ ] aggiorna requirements
- [ ] crea file .env
- [ ] aggiungi .env a gitignore
- [x] Rimuovi endpoint webhook: Elimina o commenta @app.post("/webhook") in bot.py
- [ ] Aggiungi avvio polling in lifespan(): await application.start_polling()
- [ ] Costruisci immagine: docker compose up --build -d
- [ ] Controlla log: docker compose logs -f
- [ ] env di esempio
