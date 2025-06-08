import json
import urllib.parse
import re
import os
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path

import fitz  # PyMuPDF

# Percorso della cartella dove si trova questo script
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Nome del file da convertire
input_file = "SOEM.pdf"  # Cambia questo con il file da elaborare
output_json = "green_economy.json"

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
            "id": str(uuid.uuid4()),
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
            "id": str(uuid.uuid4()),
            "question": question_text,
            "answers": answers,
            "correct_answer": correct_answer
        })

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(questions, f, indent=2, ensure_ascii=False)

    print(f"File JSON salvato in: {json_path}")

def parse_questions_from_text(text):
    question_pattern = re.compile(
        r"(\d+)\.\s+(.*?)\n(?:A\.\s+(.*?)\nB\.\s+(.*?)\nC\.\s+(.*?)\nD\.\s+(.*?))\n\n?Answer:\s*([A-D])",
        re.DOTALL
    )

    questions = []

    for match in question_pattern.finditer(text):
        number, qtext, a, b, c, d, answer_letter = match.groups()
        options = [a.strip(), b.strip(), c.strip(), d.strip()]
        correct_index = ord(answer_letter.upper()) - ord("A")

        questions.append({
            "id": str(uuid.uuid4()),
            "question": qtext.strip(),
            "answers": options,
            "correct_answer": options[correct_index],
            "number": int(number),
            "image": None
        })

    return questions

def convert_pdf_to_json(pdf_path, json_path):
    doc = fitz.open(pdf_path)
    image_dir = os.path.join(BASE_DIR, "images")
    os.makedirs(image_dir, exist_ok=True)

    json_basename = Path(json_path).stem[:3].lower()
    image_counter = 1

    full_text = ""
    page_question_map = []

    for page_index, page in enumerate(doc):
        text = page.get_text()
        full_text += text

        questions = parse_questions_from_text(text)
        for q in questions:
            q["page"] = page_index
            q["image"] = None
        page_question_map.extend(questions)

        image_list = page.get_images(full=True)
        for img_index, img in enumerate(image_list):
            xref = img[0]
            base_image = doc.extract_image(xref)
            image_bytes = base_image["image"]
            image_ext = ".jpg"
            image_filename = f"{json_basename}{image_counter}.jpg"
            image_path = os.path.join(image_dir, image_filename)

            with open(image_path, "wb") as img_out:
                img_out.write(image_bytes)

            # Assegna immagine all'ultima domanda della pagina
            last_question = [q for q in page_question_map if q["page"] == page_index]
            if last_question:
                last_question[-1]["image"] = image_filename

            image_counter += 1

    final_questions = []
    for q in page_question_map:
        q.pop("page", None)
        q.pop("number", None)
        if q.get("image") is None:
            q.pop("image", None)
        final_questions.append(q)

    if os.path.exists(json_path):
        with open(json_path, "r", encoding="utf-8") as f:
            existing = json.load(f)
    else:
        existing = []

    existing_qtexts = {q["question"] for q in existing}
    merged = existing + [q for q in final_questions if q["question"] not in existing_qtexts]

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(merged, f, indent=2, ensure_ascii=False)

    print(f"{len(final_questions)} nuove domande aggiunte. Totale: {len(merged)}.")

def convert_pdf_with_green_answers_to_json(pdf_path, json_path):
    doc = fitz.open(pdf_path)
    questions = []
    image_dir = os.path.join(BASE_DIR, "images")
    os.makedirs(image_dir, exist_ok=True)
    json_basename = Path(json_path).stem[:3].lower()
    image_counter = 1

    current_question = None

    for page in enumerate(doc):
        blocks = page.get_text("dict")["blocks"]

        for block in blocks:
            for line in block.get("lines", []):
                line_text = ""
                line_spans = []

                for span in line.get("spans", []):
                    text = span["text"].strip()
                    if not text:
                        continue

                    line_text += text + " "
                    line_spans.append(span)

                line_text = line_text.strip()

                # Nuova domanda
                if re.match(r"^\d+\.\s+", line_text):
                    if current_question:
                        questions.append(current_question)
                    question_text = re.sub(r"^\d+\.\s+", "", line_text)
                    current_question = {
                        "id": str(uuid.uuid4()),
                        "question": question_text,
                        "answers": [],
                        "correct_answer": None,
                        "image": None
                    }

                # Opzioni A-D
                elif re.match(r"^[A-Da-d]\.\s+", line_text) and current_question:
                    match = re.match(r"^([A-Da-d])\.\s+(.*)", line_text)
                    if match:
                        letter = match.group(1).upper()
                        option_text = match.group(2).strip()
                        is_correct = any(is_green(span) for span in line_spans)
                        current_question["answers"].append(option_text)
                        if is_correct:
                            current_question["correct_answer"] = option_text

    if current_question:
        questions.append(current_question)

    for q in questions:
        if q.get("correct_answer") is None and q["answers"]:
            q["correct_answer"] = q["answers"][0]  # fallback
        if not q.get("image"):
            q.pop("image", None)

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(questions, f, indent=2, ensure_ascii=False)

    print(f"{len(questions)} domande salvate in: {json_path}")

def is_green(span):
    color_int = span["color"]
    r = (color_int >> 16) & 255
    g = (color_int >> 8) & 255
    b = color_int & 255
    # Normalizza tra 0 e 1
    r /= 255
    g /= 255
    b /= 255
    return g > 0.5 and r < 0.3 and b < 0.3


def convert_quiz(input_file, json_file):
    input_path = os.path.join(BASE_DIR, input_file)
    json_path = os.path.join(BASE_DIR, json_file)

    ext = os.path.splitext(input_file)[1].lower()

    if ext == ".txt":
        convert_txt_to_json(input_path, json_path)
    elif ext == ".qwz":
        convert_qwz_to_json(input_path, json_path)
    elif ext == ".pdf":
        convert_pdf_to_json(input_path, json_path)
    else:
        print(f"Estensione '{ext}' non supportata.")

if __name__ == "__main__":
    convert_quiz(input_file, output_json)
    # input_path = os.path.join(BASE_DIR, input_file)  
    # json_path = os.path.join(BASE_DIR, output_json)

    # convert_pdf_with_green_answers_to_json(input_path, json_path) #se il pdf ha segnalate solo con il verde le risposte giuste
