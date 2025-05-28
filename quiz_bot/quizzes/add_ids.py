import os
import json
import uuid

QUIZ_DIR = os.path.dirname(__file__)  # cartella corrente (quizzes)

def add_ids_to_quiz_file(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        try:
            quiz_data = json.load(f)
        except json.JSONDecodeError as e:
            print(f"Errore nel file {file_path}: {e}")
            return

    if not isinstance(quiz_data, list):
        print(f"❌ Il file {file_path} non contiene una lista.")
        return

    updated = False
    for question in quiz_data:
        if "id" not in question:
            question["id"] = str(uuid.uuid4())
            updated = True

    if updated:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(quiz_data, f, indent=2, ensure_ascii=False)
        print(f"Aggiunti ID a {file_path}")
    else:
        print(f"ℹNessun aggiornamento necessario per {file_path}")

def process_all_quizzes():
    for file_name in os.listdir(QUIZ_DIR):
        if file_name.endswith(".json"):
            full_path = os.path.join(QUIZ_DIR, file_name)
            add_ids_to_quiz_file(full_path)

if __name__ == "__main__":
    process_all_quizzes()
