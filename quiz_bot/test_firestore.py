import os
import firebase_admin
from firebase_admin import credentials, firestore
from wrong_answers import WrongAnswersManager

def initialize_firestore():
    # Legge la variabile d'ambiente o usa file locale
    firebase_cred_path = os.getenv('FIREBASE_CREDENTIALS_PATH', 'firebase_credentials.json')
    if os.path.exists(firebase_cred_path):
        cred = credentials.Certificate(firebase_cred_path)
        print(f"Using local credentials file: {firebase_cred_path}")
    else:
        # Cerca la variabile FIREBASE_CREDENTIALS_JSON contenente il JSON della key
        firebase_cred_json = os.getenv('FIREBASE_CREDENTIALS_JSON')
        if not firebase_cred_json:
            raise Exception("No Firebase credentials found in env or file")
        import json
        cred = credentials.Certificate(json.loads(firebase_cred_json))
        print("Using credentials from environment variable FIREBASE_CREDENTIALS_JSON")

    if not firebase_admin._apps:
        firebase_admin.initialize_app(cred)
    return firestore.client()

def test_firestore_connection():
    db = initialize_firestore()
    # Prova a leggere una collezione di test "test_collection"
    try:
        docs = db.collection('test_collection').limit(1).stream()
        for doc in docs:
            print(f"Doc ID: {doc.id}, data: {doc.to_dict()}")
        print("Firestore connection test succeeded")
    except Exception as e:
        print("Firestore connection test failed:", e)


def test_manager():
    user_id = "test_user_123"
    mgr = WrongAnswersManager(user_id)

    # 1) Assicurati che non ci siano inizialmente errori
    assert mgr.get_all() == {}

    # 2) Aggiungi una domanda di prova
    q = {
        "question": "Domanda di prova?",
        "answers": ["A", "B", "C", "D"],
        "correct_answer": "A"
    }
    mgr.save_wrong_answer("prova_materia", q)
    all_data = mgr.get_all()
    assert "prova_materia" in all_data
    assert all_data["prova_materia"][0]["counter"] == 3

    # 3) Riapri il manager e verifica persistenza
    mgr2 = WrongAnswersManager(user_id)
    data2 = mgr2.get_for_subject("prova_materia")
    assert data2[0]["question"] == q["question"]

    # 4) Decrementa il counter fino a rimozione
    for _ in range(3):
        mgr2.decrement_counter("prova_materia", q["question"])
    assert mgr2.get_for_subject("prova_materia") == []

    # 5) Pulisci del tutto
    mgr2.remove_subject("prova_materia")
    assert mgr2.get_all() == {}

    print("✅ Test WrongAnswersManager passato!")


if __name__ == "__main__":
    test_firestore_connection()
    test_manager()