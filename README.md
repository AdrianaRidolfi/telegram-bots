# telegram-bots

Questo repository contiene bot Telegram per somministrare quiz agli utenti in chat private.

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
│   ├── bot.py                 # codice Python del bot
│   ├── pdf_generator.py       # script per generare PDF
│   ├── Procfile               # comando per il deploy su Render o simili
│   ├── quizzes
│   │   ├── diritto.json               # quiz in formato JSON
│   │   ├── convert.py                 # utility per convertire in JSON
│   │   ├── add_ids.py                 # utility per aggiungere gli id a un json
│   │   ├── fonts                      # cartella per i font usati nei PDF
│   │   │   └── [file di font vari]
│   │   ├── images                     # cartella per le immagini usate nei quiz
│   │   │   └── [immagini .jpg]
│   │   └── tecnologie.json            # altro quiz in formato JSON
│   ├── requirements.txt               # dipendenze Python
│   ├── test_firestore.py              # script di test per Firestore
│   └── wrong_answers.py               # gestione risposte errate
└── README.md                         # file di documentazione principale
```

## Dipendenze e installazione

Le dipendenze Python del bot sono elencate nel file [`requirements.txt`](/quiz_bot/requirements.txt). Per installarle localmente puoi usare:

```bash
pip install -r requirements.txt
```

## Deploy su Render

Il bot è attualmente deployato gratuitamente su [Render](https://render.com/). Questo significa che, se non viene utilizzato da un po' di tempo, il server può andare in modalità "sleep" per risparmiare risorse. In tal caso, la prima risposta al comando /start può richiedere fino a 50 secondi. Una volta riattivato, le risposte torneranno rapide.

## Come contribuire con nuovi test

Puoi contribuire aggiungendo nuovi quiz in formato `.json`.

### 1. Fai un fork del progetto

Clicca su **Fork** in alto a destra per creare una copia nel tuo account.

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
    "correct_answer": "Risposta 2",
    "image": "image.jpg",
    "id": "86c42b34-d157-4eef-981b-8d7ee94c929f"
  }
]
```

- **question**: testo della domanda
- **xanswers**: lista delle possibili risposte
- **correct_answer**: la risposta corretta
- **image**: eventuale immagine jpg, deve in quel caso essere aggiunta nella cartella images
- **id**: identificativo univoco


- Assicurati che:
    - il file sia un json valido.
    - correct_answer corrisponda esattamente a una delle risposte elencate in answers.

**NB.** se vuoi aggiungere un'immagine relativa alla domanda puoi aggiungere il campo image con il nome dell'immagine e salvarla dentro la cartella images. L'immagine DEVE essere in formato jpg.

- Salva il file nella cartella quiz_bot/quizzes/ e dagli un nome descrittivo, ad esempio storia.json.

Puoi utilizzare [add_ids.py](/quiz_bot/quizzes/add_ids.py) per aggiungere gli **id**

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

  - **.qwz** Quiz Writer XML 

  - **.pdf** 

Come dev'essere strutturato un PDF per la conversione:

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

Le domande sbagliate vengono salvate automaticamente su Firestore, all’interno di un database non relazionale chiamato:

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

Logica del ripasso:

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
Avvia la sessione quiz in chat privata con l'utente che ha inviato il comando.
Il bot inizia a fare le domande una ad una.

```code
    /stats
```
Mostra le statistiche dell'utente.
