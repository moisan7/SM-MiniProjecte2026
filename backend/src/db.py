import os
import datetime
from google.cloud import firestore
from dotenv import load_dotenv

load_dotenv()

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "proyectosm-494910")


def get_db():
    return firestore.Client(project=PROJECT_ID)


def _col(db, uid: str):
    return db.collection("generation_history").document(uid).collection("items")


def save_to_history(data: dict, uid: str) -> str:
    """Save a generation record to the user's Firestore sub-collection."""
    db = get_db()
    data["created_at"] = datetime.datetime.now(datetime.timezone.utc)
    _timestamp, doc_ref = _col(db, uid).add(data)
    return doc_ref.id


def get_history(uid: str, limit: int = 12) -> list:
    """Retrieve the most recent generation records for a user."""
    db = get_db()
    docs = _col(db, uid).order_by(
        "created_at", direction=firestore.Query.DESCENDING
    ).limit(limit).stream()

    history = []
    for doc in docs:
        item = doc.to_dict()
        item["id"] = doc.id
        if "created_at" in item:
            item["created_at"] = item["created_at"].isoformat()
        history.append(item)

    return history


def delete_from_history(doc_id: str, uid: str):
    """Delete a generation record from the user's Firestore sub-collection."""
    db = get_db()
    _col(db, uid).document(doc_id).delete()
