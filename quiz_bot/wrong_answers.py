from firebase_admin import firestore
from typing import List, Dict

class WrongAnswersManager:
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.db = firestore.client()
        self.to_increment = {}  # subject -> [question dict]
        self.to_decrement = {}  # subject -> [question_text]

    def queue_wrong_answer(self, subject: str, question_data: Dict):
        self.to_increment.setdefault(subject, []).append(question_data)

    def queue_decrement(self, subject: str, question_text: str):
        self.to_decrement.setdefault(subject, []).append(question_text)

    def commit_changes(self):
        doc_ref = self.db.collection("wrong_answers").document(self.user_id)
        transaction = self.db.transaction()

        @firestore.transactional
        def update_firestore(transaction, doc_ref):
            snapshot = doc_ref.get(transaction=transaction)
            data = snapshot.to_dict() if snapshot.exists else {}

            # Processa incrementi
            for subject, questions in self.to_increment.items():
                subject_list = data.get(subject, [])
                for new_q in questions:
                    for existing_q in subject_list:
                        if existing_q["question"] == new_q["question"]:
                            existing_q["counter"] = existing_q.get("counter", 0) + 3
                            break
                    else:
                        q_copy = new_q.copy()
                        q_copy["counter"] = 3
                        subject_list.append(q_copy)
                data[subject] = subject_list

            # Processa decrementi
            for subject, question_texts in self.to_decrement.items():
                if subject not in data:
                    continue
                subject_list = data[subject]
                new_list = []
                for q in subject_list:
                    if q["question"] in question_texts:
                        new_counter = q.get("counter", 1) - 1
                        if new_counter > 0:
                            q["counter"] = new_counter
                            new_list.append(q)
                        # else: lo rimuoviamo
                    else:
                        new_list.append(q)
                if new_list:
                    data[subject] = new_list
                else:
                    data.pop(subject)

            # Aggiorna o elimina documento
            if data:
                transaction.set(doc_ref, data)
            else:
                transaction.delete(doc_ref)

        update_firestore(transaction, doc_ref)
        self.to_increment.clear()
        self.to_decrement.clear()

    def get_all(self) -> Dict[str, List[Dict]]:
        """Ritorna tutte le domande sbagliate dell'utente, per materia."""
        user_doc = self.db.collection("wrong_answers").document(self.user_id).get()
        if not user_doc.exists:
            return {}
        data = user_doc.to_dict()
        # Garantisce che ogni materia abbia una lista
        for materia, domande in data.items():
            if not isinstance(domande, list):
                data[materia] = []
        return data

    def get_for_subject(self, subject: str) -> List[Dict]:
        """Ritorna le domande sbagliate per una materia specifica."""
        all_wrong = self.get_all()
        return all_wrong.get(subject, [])

    def save_wrong_answer(self, subject: str, question_data: Dict):
        """Aggiunge o aggiorna una domanda sbagliata con counter +3."""
        doc_ref = self.db.collection("wrong_answers").document(self.user_id)
        transaction = self.db.transaction()

        @firestore.transactional
        def transaction_update(transaction, doc_ref):
            snapshot = doc_ref.get(transaction=transaction)
            data = snapshot.to_dict() if snapshot.exists else {}

            subject_list = data.get(subject, [])

            for q in subject_list:
                if q["question"] == question_data["question"]:
                    q["counter"] = q.get("counter", 0) + 3
                    break
            else:
                new_q = question_data.copy()
                new_q["counter"] = 3
                subject_list.append(new_q)

            data[subject] = subject_list
            transaction.set(doc_ref, data)

        transaction_update(transaction, doc_ref)

    def decrement_counter(self, subject: str, question_text: str):
        """
        Decrementa il counter di una domanda di 1.
        Rimuove domanda se counter arriva a 0.
        Rimuove materia se lista vuota.
        Rimuove documento utente se tutto vuoto.
        """
        doc_ref = self.db.collection("wrong_answers").document(self.user_id)
        transaction = self.db.transaction()

        @firestore.transactional
        def transaction_update(transaction, doc_ref):
            snapshot = doc_ref.get(transaction=transaction)
            if not snapshot.exists:
                return
            data = snapshot.to_dict()
            if subject not in data:
                return

            subject_list = data[subject]
            new_list = []
            for q in subject_list:
                if q["question"] == question_text:
                    new_counter = q.get("counter", 1) - 1
                    if new_counter > 0:
                        q["counter"] = new_counter
                        new_list.append(q)
                    # else rimuove domanda (non aggiunge)
                else:
                    new_list.append(q)

            if new_list:
                data[subject] = new_list
            else:
                data.pop(subject)

            if data:
                transaction.set(doc_ref, data)
            else:
                transaction.delete(doc_ref)

        transaction_update(transaction, doc_ref)

    def remove_subject(self, subject: str):
        """Rimuove completamente una materia dal DB dell'utente."""
        doc_ref = self.db.collection("wrong_answers").document(self.user_id)
        transaction = self.db.transaction()

        @firestore.transactional
        def transaction_update(transaction, doc_ref):
            snapshot = doc_ref.get(transaction=transaction)
            if not snapshot.exists:
                return
            data = snapshot.to_dict()
            if subject in data:
                data.pop(subject)
                if data:
                    transaction.set(doc_ref, data)
                else:
                    transaction.delete(doc_ref)

        transaction_update(transaction, doc_ref)

    def has_wrong_answers(self) -> bool:
        """True se l'utente ha almeno una domanda sbagliata."""
        wrong = self.get_all()
        return any(wrong.get(materia) for materia in wrong)

    # Metodo opzionale di debug
    def print_all(self):
        wa = self.get_all()
        print(f"Wrong answers for {self.user_id}:")
        for subject, questions in wa.items():
            print(f"  {subject}: {len(questions)} questions")
            for q in questions:
                print(f"    - {q['question']} (counter={q.get('counter', 'N/A')})")
