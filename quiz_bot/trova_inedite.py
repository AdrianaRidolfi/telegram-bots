import json
import unicodedata
import re
import os
import fitz  # PyMuPDF

def normalizza_confronto(testo):
    """Normalizza il testo per il confronto rimuovendo accenti, spazi e caratteri speciali"""
    testo = testo.lower()
    testo = unicodedata.normalize('NFD', testo)
    testo = ''.join(c for c in testo if unicodedata.category(c) != 'Mn')
    # Rimuovi tutti i segni di punteggiatura e caratteri speciali
    testo = re.sub(r'[^\w\s]', '', testo)
    # Rimuovi tutti gli spazi per confronto
    testo = re.sub(r'\s+', '', testo)
    testo = testo.strip()
    return testo

def normalizza_leggibile(testo):
    """Normalizzazione leggera per mantenere il testo leggibile"""
    testo = testo.strip()
    return testo

def carica_domande_txt(percorso_txt):
    """Carica le domande dal file TXT"""
    domande = []
    with open(percorso_txt, encoding='utf-8') as f:
        blocco = {}
        for riga in f:
            riga = riga.strip()
            if riga.startswith("Domanda:"):
                blocco['question'] = riga.replace("Domanda:", "").strip()
            elif riga.startswith("Risposta corretta:"):
                blocco['correct'] = riga.replace("Risposta corretta:", "").strip()
            elif riga == "-----------------------------" and blocco:
                domande.append(blocco)
                blocco = {}
        # Aggiungi l'ultimo blocco se presente
        if blocco:
            domande.append(blocco)
    return domande

def carica_domande_json(percorso_json):
    """Carica le domande dal file JSON e crea un dizionario normalizzato per confronto"""
    with open(percorso_json, encoding='utf-8') as f:
        data = json.load(f)
    
    # Creo un dizionario: domanda_normalizzata -> risposta_normalizzata
    domande_risposte = {}
    for item in data:
        domanda_norm = normalizza_confronto(item['question'])
        risposta_norm = normalizza_confronto(item['correct_answer'])
        domande_risposte[domanda_norm] = risposta_norm
    
    return domande_risposte

def estrai_solo_domanda(testo_completo):
    """Estrae solo la parte della domanda, escludendo le opzioni di risposta"""
    # Divide il testo quando trova la prima opzione (A., B., C., D.)
    parti = re.split(r'\s+[A-D]\.', testo_completo)
    if len(parti) > 1:
        return parti[0].strip()
    return testo_completo.strip()

def carica_domande_da_pdf(percorso_pdf):
    """Carica le domande dal PDF nel formato specificato"""
    domande_pdf = set()
    
    with fitz.open(percorso_pdf) as doc:
        testo_completo = ""
        for pagina in doc:
            testo_completo += pagina.get_text("text")
    
    # Dividi il testo in righe
    righe = testo_completo.split('\n')
    
    domanda_corrente = ""
    raccogliendo_domanda = False
    
    for riga in righe:
        riga = riga.strip()
        
        # Cerca le righe che iniziano con un numero seguito da un punto
        if re.match(r'^\d+\.', riga):
            # Se stavamo raccogliendo una domanda precedente, la salviamo
            if domanda_corrente:
                # Estrai solo la parte della domanda (senza opzioni)
                solo_domanda = estrai_solo_domanda(domanda_corrente)
                domanda_norm = normalizza_confronto(solo_domanda)
                if domanda_norm:  # Solo se non è vuota
                    domande_pdf.add(domanda_norm)
            
            # Inizia nuova domanda
            domanda_corrente = riga
            raccogliendo_domanda = True
            # Rimuovi il numero e il punto dall'inizio
            domanda_corrente = re.sub(r'^\d+\.\s*', '', domanda_corrente)
            
        elif raccogliendo_domanda and (riga.startswith('A.') or riga.startswith('B.') or riga.startswith('C.') or riga.startswith('D.')):
            # Questa è una risposta, continua ad accumularla alla domanda
            domanda_corrente += " " + riga
            
        elif riga.startswith('Answer:'):
            # Fine della domanda, la aggiungo al set
            if domanda_corrente:
                # Estrai solo la parte della domanda (senza opzioni)
                solo_domanda = estrai_solo_domanda(domanda_corrente)
                domanda_norm = normalizza_confronto(solo_domanda)
                if domanda_norm:  # Solo se non è vuota
                    domande_pdf.add(domanda_norm)
                domanda_corrente = ""
                raccogliendo_domanda = False
    
    # Gestisci l'ultima domanda se il file non finisce con Answer:
    if domanda_corrente:
        solo_domanda = estrai_solo_domanda(domanda_corrente)
        domanda_norm = normalizza_confronto(solo_domanda)
        if domanda_norm:
            domande_pdf.add(domanda_norm)
    
    return domande_pdf

def filtra_domande_con_pdf(file_domande_txt, percorso_pdf, file_output):
    """Filtra le domande del TXT rimuovendo quelle presenti nel PDF"""
    
    print("Caricamento domande dal PDF...")
    domande_pdf = carica_domande_da_pdf(percorso_pdf)
    print(f"Caricate {len(domande_pdf)} domande dal PDF")
    
    print("Caricamento domande dal file creato...")
    domande_txt = carica_domande_txt(file_domande_txt)
    print(f"Caricate {len(domande_txt)} domande dal file TXT")
    
    print("Confronto con il PDF...")
    domande_finali = []
    
    for domanda in domande_txt:
        # Rimuovi eventuali segnalazioni precedenti per il confronto
        domanda_pulita = domanda['question'].replace("  # RISPOSTA DIVERSA", "")
        domanda_norm = normalizza_confronto(domanda_pulita)
        
        # Se la domanda NON è nel PDF, la mantieni
        if domanda_norm not in domande_pdf:
            domande_finali.append(domanda)
    
    print(f"Rimangono {len(domande_finali)} domande dopo il filtro PDF")
    
    # Salva le domande finali
    with open(file_output, 'w', encoding='utf-8') as f:
        for domanda in domande_finali:
            f.write(f"Domanda: {normalizza_leggibile(domanda['question'])}\n")
            f.write(f"Risposta corretta: {normalizza_leggibile(domanda['correct'])}\n")
            f.write("-----------------------------\n")
    
def trova_domande_inedite(txt_path, json_path, output_txt_path):
    """Trova le domande del TXT che non sono presenti nel JSON o hanno risposte diverse"""
    
    print("Caricamento domande dal file TXT...")
    domande_txt = carica_domande_txt(txt_path)
    print(f"Caricate {len(domande_txt)} domande dal file TXT")
    
    print("Caricamento domande dal file JSON...")
    domande_json = carica_domande_json(json_path)
    print(f"Caricate {len(domande_json)} domande dal file JSON")
    
    print("Confronto domande e risposte...")
    domande_inedite = []
    
    for domanda in domande_txt:
        domanda_norm = normalizza_confronto(domanda['question'])
        risposta_norm = normalizza_confronto(domanda['correct'])
        
        if domanda_norm not in domande_json:
            # Domanda non presente nel JSON - la aggiungo
            domande_inedite.append(domanda)
        else:
            # Domanda presente nel JSON, controllo la risposta
            risposta_json_norm = domande_json[domanda_norm]
            if risposta_norm != risposta_json_norm:
                # Stessa domanda ma risposta diversa - la aggiungo con segnalazione
                domanda_modificata = {
                    'question': domanda['question'] + "  # RISPOSTA DIVERSA",
                    'correct': domanda['correct']
                }
                domande_inedite.append(domanda_modificata)
    
    print(f"Trovate {len(domande_inedite)} domande inedite o con risposte diverse")
    
    # Salvo le domande inedite nel file di output
    with open(output_txt_path, 'w', encoding='utf-8') as f:
        for domanda in domande_inedite:
            f.write(f"Domanda: {normalizza_leggibile(domanda['question'])}\n")
            f.write(f"Risposta corretta: {normalizza_leggibile(domanda['correct'])}\n")
            f.write("-----------------------------\n")
    
    print(f"File delle domande inedite salvato in '{output_txt_path}'")
    return len(domande_inedite)

# -----------------------
# MAIN
# -----------------------

if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.abspath(__file__))

    nome_file_txt = os.path.join(base_dir, "ing.txt")
    nome_file_json = os.path.join(base_dir, "quizzes", "ingegneria.json")
    nome_file_pdf = os.path.join(base_dir, "paniere_ing.pdf")  # PDF alla stessa altezza di ing.txt
    nome_file_output = os.path.join(base_dir, "domande_inedite_ingegneria.txt")
    nome_file_finale = os.path.join(base_dir, "domande_finali_filtrate.txt")

    print("Inizio ricerca domande inedite e controllo risposte...")
    
    try:
        # Primo controllo: TXT vs JSON
        num_inedite = trova_domande_inedite(nome_file_txt, nome_file_json, nome_file_output)
        print(f"\nPrimo controllo completato! Trovate {num_inedite} domande inedite o con risposte diverse.")
        
        # Secondo controllo: risultato primo controllo vs PDF
        if os.path.exists(nome_file_pdf):
            print(f"\nInizio secondo controllo con PDF...")
            num_finali = filtra_domande_con_pdf(nome_file_output, nome_file_pdf, nome_file_finale)
            print(f"\nProcesso completato! Rimangono {num_finali} domande dopo tutti i controlli.")
        else:
            print(f"\nAttenzione: File PDF '{nome_file_pdf}' non trovato. Saltando il secondo controllo.")
            print(f"Processo completato solo con il primo controllo.")
        
    except FileNotFoundError as e:
        print(f"Errore: File non trovato - {e}")
    except json.JSONDecodeError as e:
        print(f"Errore nel parsing del JSON - {e}")
    except Exception as e:
        print(f"Errore imprevisto - {e}")
