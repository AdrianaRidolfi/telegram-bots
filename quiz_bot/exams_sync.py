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
    
    def __init__(self):
        self.db = firestore.client()
    
    
    def print_subject_questions(self, subject: str):
        
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