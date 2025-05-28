from firebase_admin import firestore
from typing import List, Dict

class WrongAnswersManager:
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.db = firestore.client()
        self.to_increment: Dict[str, List[str]] = {}
        self.to_decrement: Dict[str, List[str]] = {}

    def queue_wrong_answer(self, subject: str, question_data: Dict):
        qid = question_data.get("id")
        if qid:
            self.to_increment.setdefault(subject, []).append(qid)

    def queue_decrement(self, subject: str, question_id: str):
        self.to_decrement.setdefault(subject, []).append(question_id)

    def _update_subject_data(self, current: List[Dict], inc_ids: List[str], dec_ids: List[str]) -> List[Dict]:
        """Aggiorna la lista di domande di una materia applicando incrementi e decrementi."""
        counters = {q["id"]: q["counter"] for q in current}

        for qid in inc_ids:
            counters[qid] = counters.get(qid, 0) + 3

        for qid in dec_ids:
            if qid in counters:
                counters[qid] -= 1
                if counters[qid] <= 0:
                    del counters[qid]

        return [{"id": qid, "counter": count} for qid, count in counters.items()]

    def commit_changes(self):
        doc_ref = self.db.collection("wrong_answers").document(self.user_id)
        transaction = self.db.transaction()

        @firestore.transactional
        def update(transaction, doc_ref):
            snapshot = doc_ref.get(transaction=transaction)
            data = snapshot.to_dict() if snapshot.exists else {}

            subjects = set(self.to_increment) | set(self.to_decrement)
            for subject in subjects:
                current = data.get(subject, [])
                inc_ids = self.to_increment.get(subject, [])
                dec_ids = self.to_decrement.get(subject, [])
                updated = self._update_subject_data(current, inc_ids, dec_ids)
                if updated:
                    data[subject] = updated
                else:
                    data.pop(subject, None)

            if data:
                transaction.set(doc_ref, data)
            else:
                transaction.delete(doc_ref)

        update(transaction, doc_ref)
        self.to_increment.clear()
        self.to_decrement.clear()

    def get_all(self) -> Dict[str, List[Dict]]:
        doc = self.db.collection("wrong_answers").document(self.user_id).get()
        return doc.to_dict() if doc.exists else {}

    def get_for_subject(self, subject: str) -> List[Dict]:
        doc = self.db.collection("wrong_answers").document(self.user_id).get()
        return doc.to_dict().get(subject, []) if doc.exists else []

    def decrement_counter(self, subject: str, question_id: str):
        doc_ref = self.db.collection("wrong_answers").document(self.user_id)
        transaction = self.db.transaction()

        @firestore.transactional
        def update(transaction, doc_ref):
            snapshot = doc_ref.get(transaction=transaction)
            if not snapshot.exists:
                return
            data = snapshot.to_dict()

            current = data.get(subject, [])
            updated = self._update_subject_data(current, [], [question_id])

            if updated:
                data[subject] = updated
                transaction.set(doc_ref, data)
            else:
                data.pop(subject, None)
                if data:
                    transaction.set(doc_ref, data)
                else:
                    transaction.delete(doc_ref)

        update(transaction, doc_ref)

    def remove_subject(self, subject: str):
        doc_ref = self.db.collection("wrong_answers").document(self.user_id)
        transaction = self.db.transaction()

        @firestore.transactional
        def update(transaction, doc_ref):
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

        update(transaction, doc_ref)

    def has_wrong_answers(self) -> bool:
        return any(self.get_all().values())

    def print_all(self):
        data = self.get_all()
        print(f"Wrong answers for {self.user_id}:")
        for subject, questions in data.items():
            print(f"  {subject} ({len(questions)}):")
            for q in questions:
                print(f"    - {q['id']} (counter={q['counter']})")
