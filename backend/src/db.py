import os
import datetime
from google.cloud import firestore
from dotenv import load_dotenv

load_dotenv()

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "proyectosm-494910")
COLLECTION_NAME = "generation_history"

def get_db():
    return firestore.Client(project=PROJECT_ID)

def save_to_history(data: dict) -> str:
    """
    Save a generation record to Firestore.
    'data' should contain: style, image_url, message, and coordinates (optional).
    Returns the Firestore document ID of the saved record.
    """
    db = get_db()
    data["created_at"] = datetime.datetime.now(datetime.timezone.utc)
    _timestamp, doc_ref = db.collection(COLLECTION_NAME).add(data)
    return doc_ref.id

def get_history(limit: int = 10):
    """
    Retrieve the most recent generation records from Firestore.
    """
    db = get_db()
    docs = db.collection(COLLECTION_NAME).order_by(
        "created_at", direction=firestore.Query.DESCENDING
    ).limit(limit).stream()
    
    history = []
    for doc in docs:
        item = doc.to_dict()
        item["id"] = doc.id
        # Convert datetime to string for JSON serialization
        if "created_at" in item:
            item["created_at"] = item["created_at"].isoformat()
        history.append(item)
    
    return history

def delete_from_history(doc_id: str):
    """
    Delete a generation record from Firestore by its document ID.
    """
    db = get_db()
    db.collection(COLLECTION_NAME).document(doc_id).delete()
