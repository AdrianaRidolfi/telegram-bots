# exam_sync.py

import requests
from firebase_admin import firestore

db = firestore.client()

class ExamSync:
    BASE_URL = "https://app-api.pegaso.multiversity.click"

    def login(self, username: str, password: str) -> str:
        response = requests.post(
            f"{self.BASE_URL}/oauth/token",
            data={
                "username": username,
                "password": password,
                "grant_type": "password",
                "client_id": "pegaso_app"
            }
        )
        response.raise_for_status()
        return response.json()["access_token"]

    def get_exams(self, token: str):
        res = requests.get(
            f"{self.BASE_URL}/api/exam-online/sost",
            headers={"Authorization": f"Bearer {token}"}
        )
        res.raise_for_status()
        return res.json()

    def get_exam_result(self, token: str, exam_id: str):
        res = requests.get(
            f"{self.BASE_URL}/api/exam-online/test/result/{exam_id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        res.raise_for_status()
        return res.json()

    def save_exam_to_db(self, subject: str, questions: list):
        subject_ref = db.collection("exams").document(subject)
        doc = subject_ref.get()
        existing_data = doc.to_dict() if doc.exists else {}

        for q in questions:
            question = q["text"]
            answer_data = {"answer": q["user_answer"], "correct": q["correct"]}
            existing_answers = existing_data.get(question, [])

            # evita duplicati
            if answer_data not in existing_answers and len(existing_answers) < 4:
                existing_answers.append(answer_data)
                existing_data[question] = existing_answers

        subject_ref.set(existing_data)
