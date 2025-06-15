# exams_sync.py
import requests
import os
from firebase_admin import firestore
from typing import Optional, Dict, List
import logging

logger = logging.getLogger(__name__)


class ExamSyncError(Exception):
    """Eccezione personalizzata per errori di sincronizzazione esami"""
    pass


class ExamSync:
    """Classe per la sincronizzazione e gestione degli esami"""
    
    BASE_URL = "https://app-api.pegaso.multiversity.click"
    
    def __init__(self):
        self.db = firestore.client()
        self.client_secret = os.environ.get("CLIENT_SECRET")
        
        if not self.client_secret:
            raise ExamSyncError("CLIENT_SECRET non trovato nelle variabili d'ambiente")
    
    def login(self, username: str, password: str) -> str:
        """Effettua il login e restituisce il token di accesso"""
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
                timeout=30
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
        """Recupera la lista degli esami disponibili"""
        try:
            response = requests.get(
                f"{self.BASE_URL}/api/exam-online/sost",
                headers={"Authorization": f"Bearer {token}"},
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            
            # La struttura è: { "data": [ { "id": "123", "name_exam": "Nome" } ] }
            if isinstance(data, dict) and "data" in data:
                return data["data"]
            else:
                logger.warning(f"Struttura risposta esami inaspettata: {data}")
                return []
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Errore durante il recupero esami: {e}")
            raise ExamSyncError(f"Errore di connessione durante il recupero esami: {str(e)}")
        except ValueError as e:
            logger.error(f"Errore parsing JSON esami: {e}")
            raise ExamSyncError("Formato risposta non valido dal server")
    
    def get_exam_result(self, token: str, exam_id: str) -> Dict:
        """Recupera i risultati di un esame specifico"""
        try:
            response = requests.get(
                f"{self.BASE_URL}/api/exam-online/test/result/{exam_id}",
                headers={"Authorization": f"Bearer {token}"},
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            
            # La struttura è: { "data": { "test": {...}, "responses": [...] } }
            if isinstance(data, dict) and "data" in data:
                return data["data"]
            else:
                logger.warning(f"Struttura risposta risultati inaspettata: {data}")
                return {"responses": [], "test": {}}
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Errore durante il recupero risultati: {e}")
            raise ExamSyncError(f"Errore di connessione durante il recupero risultati: {str(e)}")
        except ValueError as e:
            logger.error(f"Errore parsing JSON risultati: {e}")
            raise ExamSyncError("Formato risposta non valido dal server")
    
    def save_exam_to_db(self, subject: str, questions: List[Dict], max_answers: int = 10):
        """Salva le domande e risposte dell'esame nel database Firebase"""
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
        """Trova un esame specifico nella lista degli esami disponibili"""
        for exam in exams:
            # La struttura è: { "id": "123", "name_exam": "Nome dell'esame" }
            exam_name = exam.get("name_exam", "").strip().lower()
            subject_lower = subject.strip().lower()
            
            if exam_name == subject_lower or subject_lower in exam_name:
                return exam
                
        return None
    
    def debug_print_subject_questions(self, subject: str):
        """
        Metodo di debug per stampare tutte le domande e risposte di una materia.
        Non viene mai chiamato dal bot, solo per uso manuale/debug.
        
        Args:
            subject (str): Nome della materia da stampare
        """
        try:
            subject_doc = self.db.collection("exams").document(subject).get()
            
            if not subject_doc.exists:
                print(f"❌ Materia '{subject}' non trovata nel database")
                return
            
            subject_data = subject_doc.to_dict()
            
            if not subject_data:
                print(f"❌ Nessun dato trovato per la materia '{subject}'")
                return
            
            print(f"\n{'='*80}")
            print(f"📚 MATERIA: {subject.upper()}")
            print(f"{'='*80}")
            print(f"📊 Totale domande: {len(subject_data)}")
            print(f"{'='*80}\n")
            
            question_number = 1
            
            for question_text, answers_list in subject_data.items():
                if not isinstance(answers_list, list):
                    continue
                
                print(f"🔸 DOMANDA {question_number}:")
                print(f"   {question_text}")
                print(f"   📝 Risposte salvate: {len(answers_list)}")
                print()
                
                for i, answer_info in enumerate(answers_list, 1):
                    answer = answer_info.get("answer", "N/A")
                    is_correct = answer_info.get("correct", False)
                    status_icon = "✅" if is_correct else "❌"
                    
                    print(f"      {i}. {answer} {status_icon}")
                
                print(f"   {'-'*60}")
                print()
                question_number += 1
            
            # Statistiche finali
            total_answers = sum(len(answers) for answers in subject_data.values() if isinstance(answers, list))
            correct_answers = sum(
                sum(1 for answer in answers if answer.get("correct", False))
                for answers in subject_data.values() 
                if isinstance(answers, list)
            )
            
            print(f"{'='*80}")
            print(f"📈 STATISTICHE FINALI:")
            print(f"   • Domande totali: {len(subject_data)}")
            print(f"   • Risposte totali: {total_answers}")
            print(f"   • Risposte corrette: {correct_answers}")
            print(f"   • Risposte sbagliate: {total_answers - correct_answers}")
            if total_answers > 0:
                accuracy = (correct_answers / total_answers) * 100
                print(f"   • Percentuale successo: {accuracy:.1f}%")
            print(f"{'='*80}\n")
            
        except Exception as e:
            print(f"❌ Errore durante il recupero dei dati: {e}")
            logger.error(f"Errore in debug_print_subject_questions: {e}")