import os
import json
from config import QUIZ_FOLDER

def load_quiz_list():
    try:
        files = [f for f in os.listdir(QUIZ_FOLDER) if f.endswith(".json")]
        return files
    except Exception as e:
        print(f"Errore caricamento lista quiz: {e}")
        return []

def load_quiz_file(filename):
    try:
        with open(os.path.join(QUIZ_FOLDER, filename), "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Errore caricamento quiz {filename}: {e}")
        return []

def get_image_path(img_name):
    path = os.path.join(QUIZ_FOLDER, "images", img_name)
    if os.path.isfile(path):
        return path
    return None
