import json
import urllib.parse
import re
import os
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET

# Percorso della cartella dove si trova questo script
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Nome del file da convertire
input_file = "diritto.qwz"  # Cambia questo con il file da elaborare
output_json = "diritto.json"

def convert_txt_to_json(txt_path, json_path):
    with open(txt_path, "r", encoding="utf-8") as f:
        content = f.read()

    domande_block = re.search(r"DOMANDE:\s*(.*?)\s*RISPOSTE:", content, re.DOTALL)
    risposte_block = re.search(r"RISPOSTE:\s*(.*)", content, re.DOTALL)

    if not domande_block or not risposte_block:
        print("Formato del file .txt non riconosciuto.")
        return

    domande_raw = domande_block.group(1).strip()
    risposte_raw = risposte_block.group(1).strip()

    question_blocks = re.split(r"\n(?=\d+\.\s)", domande_raw)

    questions = []
    for block in question_blocks:
        lines = block.strip().split("\n")
        question_text = re.sub(r"^\d+\.\s*", "", lines[0]).strip()
        options = [re.sub(r"^[A-Da-d]\.\s*", "", line).strip() for line in lines[1:]]
        questions.append({
            "question": question_text,
            "answers": options
        })

    correct_answers_map = {}
    for line in risposte_raw.strip().split("\n"):
        match = re.match(r"(\d+)\.\s*([A-Da-d])", line.strip())
        if match:
            num = int(match.group(1))
            letter = match.group(2).upper()
            correct_answers_map[num] = letter

    for i, q in enumerate(questions):
        correct_letter = correct_answers_map.get(i + 1)
        if not correct_letter:
            q["correct_answer"] = None
        else:
            index = ord(correct_letter) - ord("A")
            q["correct_answer"] = q["answers"][index]

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(questions, f, indent=2, ensure_ascii=False)

    print(f"File JSON salvato in: {json_path}")


def decode(text):
    return urllib.parse.unquote_plus(text.strip())

def clean_prefixes(text):
    # Rimuove ricorsivamente tutti i prefissi True; o False; da una stringa
    while text.lower().startswith("true;") or text.lower().startswith("false;"):
        text = text[5:].strip()
    return text.replace(";","")

def parse_options(raw_string):
    """
    Parsifica stringhe tipo:
    "False;Testo1;;True;Testo2;;False;Testo3;;False;Testo4;;"
    restituendo:
    (lista_risposte, risposta_corretta)
    """
    entries = raw_string.strip(";").split(";;")
    options = []
    correct_answer = None

    for entry in entries:
        if not entry:
            continue
        try:
            flag, text = entry.split(";", 1)
        except ValueError:
            continue  # malformato, lo saltiamo
        decoded_text = decode(text)
        cleaned_text = clean_prefixes(decoded_text)
        options.append(cleaned_text)
        if flag.strip().lower() == "true":
            correct_answer = cleaned_text

    return options, correct_answer

def convert_qwz_to_json(qwz_path, json_path):
    tree = ET.parse(qwz_path)
    root = tree.getroot()

    questions = []

    for node in root.findall(".//Node[@Type='QEMultipleChoiceQuestion']"):
        props = node.find("Properties")
        question_text = ""
        raw_options = ""

        for prop in props.findall("Property"):
            if prop.attrib.get("Name") == "QEPropsQuestion":
                question_text = decode(prop.attrib["value"])
            elif prop.attrib.get("Name") == "QEPropsMultipleChoice":
                raw_options = prop.attrib["value"]

        if not question_text or not raw_options:
            continue

        answers, correct_answer = parse_options(raw_options)

        if not answers:
            continue
        if correct_answer is None:
            correct_answer = answers[0]  # fallback

        questions.append({
            "question": question_text,
            "answers": answers,
            "correct_answer": correct_answer
        })

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(questions, f, indent=2, ensure_ascii=False)

    print(f"File JSON salvato in: {json_path}")

def convert_quiz(input_file, json_file):
    input_path = os.path.join(BASE_DIR, input_file)
    json_path = os.path.join(BASE_DIR, json_file)

    ext = os.path.splitext(input_file)[1].lower()

    if ext == ".txt":
        convert_txt_to_json(input_path, json_path)
    elif ext == ".qwz":
        convert_qwz_to_json(input_path, json_path)
    else:
        print(f"Estensione '{ext}' non supportata.")

if __name__ == "__main__":
    convert_quiz(input_file, output_json)
