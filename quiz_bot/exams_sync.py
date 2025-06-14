# exam_sync.py

import requests
import os
from firebase_admin import firestore
from typing import Optional, Dict, List
import logging

logger = logging.getLogger(__name__)

class ExamSyncError(Exception):
    """Eccezione personalizzata per errori di ExamSync"""
    pass

class ExamSync:
    BASE_URL = "https://app-api.pegaso.multiversity.click"
    
    def __init__(self):
        self.db = firestore.client()
        self.client_secret = os.environ.get("CLIENT_SECRET")
        
        if not self.client_secret:
            raise ExamSyncError("CLIENT_SECRET non trovato nelle variabili d'ambiente")
    
    def login(self, username: str, password: str) -> str:
        try:
            response = requests.post(
                f"{self.BASE_URL}/oauth/token",
                data={
                    "username": username,
                    "password": password,
                    "grant_type": "password",
                    "client_id": "2",
                    "client_secret": self.client_secret,
                    "scope": "*"
                },
                timeout=30  # Timeout di 30 secondi
            )
            response.raise_for_status()
            
            data = response.json()
            if "access_token" not in data:
                raise ExamSyncError("Token di accesso non trovato nella risposta")
                
            return data["access_token"]
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Errore durante il login: {e}")
            raise ExamSyncError(f"Errore di connessione durante il login: {str(e)}")
        except KeyError as e:
            logger.error(f"Formato risposta login non valido: {e}")
            raise ExamSyncError("Formato risposta non valido dal server")
    
    def get_exams(self, token: str) -> List[Dict]:
        try:
            response = requests.get(
                f"{self.BASE_URL}/api/exam-online/sost",
                headers={"Authorization": f"Bearer {token}"},
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            
            # Verifica che la risposta sia una lista
            if not isinstance(data, list):
                logger.warning(f"Formato esami non atteso: {type(data)}")
                return []
                
            return data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Errore durante il recupero esami: {e}")
            raise ExamSyncError(f"Errore di connessione durante il recupero esami: {str(e)}")
        except ValueError as e:
            logger.error(f"Errore parsing JSON esami: {e}")
            raise ExamSyncError("Formato risposta non valido dal server")
    
    def get_exam_result(self, token: str, exam_id: str) -> Dict:
        try:
            response = requests.get(
                f"{self.BASE_URL}/api/exam-online/test/result/{exam_id}",
                headers={"Authorization": f"Bearer {token}"},
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            
            # Verifica che ci siano le chiavi attese
            if "questions" not in data:
                logger.warning("Campo 'questions' non trovato nella risposta")
                data["questions"] = []
                
            return data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Errore durante il recupero risultati: {e}")
            raise ExamSyncError(f"Errore di connessione durante il recupero risultati: {str(e)}")
        except ValueError as e:
            logger.error(f"Errore parsing JSON risultati: {e}")
            raise ExamSyncError("Formato risposta non valido dal server")
    
    def save_exam_to_db(self, subject: str, questions: List[Dict], max_answers: int = 4):

        try:
            subject_ref = self.db.collection("exams").document(subject) 
            doc = subject_ref.get()
            existing_data = doc.to_dict() if doc.exists else {}
            
            questions_added = 0
            answers_added = 0
            
            for q in questions:
                question_text = q.get("text", "").strip()
                user_answer = q.get("user_answer", "").strip()
                is_correct = q.get("correct", False)
                
                # Salta domande vuote
                if not question_text or not user_answer:
                    continue
                
                answer_data = {
                    "answer": user_answer,
                    "correct": is_correct
                }
                
                # Inizializza la lista se la domanda non esiste
                if question_text not in existing_data:
                    existing_data[question_text] = []
                    questions_added += 1
                
                existing_answers = existing_data[question_text]
                
                # Evita duplicati e limita il numero di risposte
                if (answer_data not in existing_answers and 
                    len(existing_answers) < max_answers):
                    existing_answers.append(answer_data)
                    answers_added += 1
                
                existing_data[question_text] = existing_answers
            
            # Salva solo se ci sono stati cambiamenti
            if questions_added > 0 or answers_added > 0:
                subject_ref.set(existing_data)
                logger.info(f"Salvato {questions_added} nuove domande e {answers_added} nuove risposte per {subject}")
            else:
                logger.info(f"Nessun nuovo dato da salvare per {subject}")
                
        except Exception as e:
            logger.error(f"Errore durante il salvataggio: {e}")
            raise ExamSyncError(f"Errore durante il salvataggio nel database: {str(e)}")
    
    def get_exam_by_subject(self, subject: str, exams: List[Dict]) -> Optional[Dict]:
        for exam in exams:
            # Confronto case-insensitive e gestione di possibili variazioni del nome
            exam_name = exam.get("name", "").strip().lower()
            subject_lower = subject.strip().lower()
            
            if exam_name == subject_lower or subject_lower in exam_name:
                return exam
                
        return None