import os

TOKEN = os.getenv("TELEGRAM_TOKEN", "Y7861155385:AAEhLcBpmcGvkq_rlxbnwcNSMHNAFWKgb8s")
QUIZ_FOLDER = os.path.join(os.path.dirname(__file__), "quizzes")
IMG_FOLDER = os.path.join(QUIZ_FOLDER, "images")
