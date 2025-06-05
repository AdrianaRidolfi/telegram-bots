import json
import unicodedata
import re
import fitz  # PyMuPDF
import os

def normalizza_confronto(testo):
    testo = testo.lower()
    testo = unicodedata.normalize('NFD', testo)
    testo = ''.join(c for c in testo if unicodedata.category(c) != 'Mn')
    testo = testo.replace("'", "").replace('"', "")  # rimuovi virgolette
    testo = testo.replace("=", "").replace(":", "")  # rimuovi simboli specifici
    testo = re.sub(r'\s+', '', testo)  # Rimuovi tutti gli spazi per confronto
    testo = testo.strip()
    return testo

def normalizza_leggibile(testo):
    testo = testo.strip()
    # qui puoi mettere ulteriori normalizzazioni leggere se vuoi
    return testo

def carica_domande_txt(percorso_txt):
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
        if blocco:
            domande.append(blocco)
    return domande

def carica_risposte_json(percorso_json):
    with open(percorso_json, encoding='utf-8') as f:
        data = json.load(f)
    # mappa normalizzata (per confronto) : domanda originale
    return {normalizza_confronto(item['correct_answer']): item['question'] for item in data}

def leggi_testo_pdf(pdf_path):
    testo = ""
    with fitz.open(pdf_path) as doc:
        for pagina in doc:
            testo += pagina.get_text()
    return normalizza_confronto(testo)

def confronto_completo(txt_path, json_path, pdf_path, output_txt_path):
    domande_txt = carica_domande_txt(txt_path)
    risposte_json = carica_risposte_json(json_path)
    testo_pdf = leggi_testo_pdf(pdf_path)

    finali = []

    for d in domande_txt:
        risposta_norm = normalizza_confronto(d['correct'])
        domanda_norm = normalizza_confronto(d['question'])

        nel_json = risposta_norm in risposte_json
        if nel_json:
            domanda_json_norm = normalizza_confronto(risposte_json[risposta_norm])
            if domanda_json_norm != domanda_norm:
                # Risposta trovata, ma domanda diversa
                finali.append({
                    "question": d['question'] + "  # DOMANDA DIVERSA",
                    "correct": d['correct']
                })
            else:
                # Risposta e domanda uguali: non metto nulla
                pass
        else:
            # Risposta non trovata nel json: la salvo così com’è
            finali.append(d)

    # Rimuovo dal risultato finale le risposte trovate anche nel PDF
    finali_filtrate = [d for d in finali if normalizza_confronto(d['correct']) not in testo_pdf]

    with open(output_txt_path, 'w', encoding='utf-8') as f:
        for d in finali_filtrate:
            f.write(f"Domanda: {normalizza_leggibile(d['question'])}\n")
            f.write(f"Risposta corretta: {normalizza_leggibile(d['correct'])}\n")
            f.write("-----------------------------\n")

    print(f"File finale salvato in '{output_txt_path}' con {len(finali_filtrate)} domande residue.")


# -----------------------
# MAIN
# -----------------------
if __name__ == "__main__":
    # 🔧 Inserisci qui i nomi dei file
    nome_file_txt = "str.txt"
    nome_file_json = "strategia.json"       # Deve essere in ./quizzes/
    nome_file_pdf = "soem.pdf"
    nome_file_output = "finale_filtrato.txt" # Output finale

    percorso_json = os.path.join("quizzes", nome_file_json)

    confronto_completo(nome_file_txt, percorso_json, nome_file_pdf, nome_file_output)
