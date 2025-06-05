from firebase_admin import firestore

class UserStatsManager:
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.db = firestore.client()
        self.doc_ref = self.db.collection("user_stats").document(user_id)
        self.stats = self._load_stats()

    def _load_stats(self):
        doc = self.doc_ref.get()
        return doc.to_dict() if doc.exists else {}

    def update_stats(self, subject: str, correct: int, total: int):
        if subject not in self.stats:
            self.stats[subject] = {"correct": 0, "total": 0}
        self.stats[subject]["correct"] += correct
        self.stats[subject]["total"] += total
        self.save()

    def reset_stats(self):
        self.stats = {}
        self.doc_ref.set({})

    def get_summary(self):
        return self.stats

    def save(self):
        self.doc_ref.set(self.stats)
