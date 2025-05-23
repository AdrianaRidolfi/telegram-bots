import os
import json
from config import QUIZ_FOLDER, IMG_FOLDER

def load_quiz_list():
    try:
        return [f for f in os.listdir(QUIZ_FOLDER) if f.endswith(".json")]
    except Exception as e:
        return []

def load_quiz_file(filename):
    path = os.path.join(QUIZ_FOLDER, filename)
    with open(path, encoding="utf-8") as f:
        return json.load(f)

def get_image_path(relative_path):
    path = os.path.join(QUIZ_FOLDER, relative_path)
    return path if os.path.exists(path) else None
