import os
import functions_framework
import firebase_admin
from firebase_admin import auth as firebase_auth
from google.cloud import firestore, storage
from flask import make_response, jsonify

BUCKET_NAME = os.getenv("BUCKET_NAME", "dal-i-bucket")
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "proyectosm-494910")

try:
    firebase_admin.initialize_app()
except ValueError:
    pass  # already initialized

_db = None
_storage_client = None

_CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, DELETE, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, Authorization",
}


def _get_db():
    global _db
    if _db is None:
        _db = firestore.Client(project=PROJECT_ID)
    return _db


def _get_storage():
    global _storage_client
    if _storage_client is None:
        _storage_client = storage.Client(project=PROJECT_ID)
    return _storage_client


def _cors(response):
    for k, v in _CORS_HEADERS.items():
        response.headers[k] = v
    return response


def _verify_token(req):
    header = req.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        return None, _cors(make_response(jsonify({"error": "Unauthorized"}), 401))
    token = header.split(" ", 1)[1]
    try:
        decoded = firebase_auth.verify_id_token(token)
        return decoded["uid"], None
    except Exception:
        return None, _cors(make_response(jsonify({"error": "Invalid token"}), 401))


def _get_col(uid):
    return _get_db().collection("generation_history").document(uid).collection("items")


def _delete_gcs_blobs(*urls):
    bucket = _get_storage().bucket(BUCKET_NAME)
    prefix = f"https://storage.googleapis.com/{BUCKET_NAME}/"
    for url in urls:
        if not url:
            continue
        try:
            if url.startswith(prefix):
                blob_name = url[len(prefix):]
                bucket.blob(blob_name).delete()
        except Exception:
            pass  # blob already gone or not found


@functions_framework.http
def history_handler(request):
    if request.method == "OPTIONS":
        return _cors(make_response("", 204))

    uid, err = _verify_token(request)
    if err:
        return err

    col = _get_col(uid)

    if request.method == "GET":
        page_size = min(int(request.args.get("page_size", 12)), 50)
        page_token = request.args.get("page_token")

        query = col.order_by("created_at", direction=firestore.Query.DESCENDING).limit(page_size + 1)
        if page_token:
            cursor_doc = col.document(page_token).get()
            if cursor_doc.exists:
                query = query.start_after(cursor_doc)

        docs = list(query.stream())
        has_more = len(docs) > page_size
        if has_more:
            docs = docs[:page_size]

        items = []
        for doc in docs:
            item = doc.to_dict()
            item["id"] = doc.id
            if "created_at" in item and hasattr(item["created_at"], "isoformat"):
                item["created_at"] = item["created_at"].isoformat()
            items.append(item)

        next_page_token = docs[-1].id if has_more else None
        return _cors(make_response(jsonify({"items": items, "next_page_token": next_page_token}), 200))

    if request.method == "DELETE":
        delete_all = request.args.get("deleteAll") == "true"
        doc_id = request.args.get("id")

        if delete_all:
            all_docs = list(col.stream())
            db = _get_db()
            batch = db.batch()
            batch_count = 0
            deleted = 0
            for doc in all_docs:
                data = doc.to_dict()
                _delete_gcs_blobs(data.get("image_url"), data.get("styled_image_url"))
                batch.delete(col.document(doc.id))
                batch_count += 1
                deleted += 1
                if batch_count >= 500:
                    batch.commit()
                    batch = db.batch()
                    batch_count = 0
            if batch_count > 0:
                batch.commit()
            return _cors(make_response(jsonify({"status": "ok", "deleted_count": deleted}), 200))

        if not doc_id:
            return _cors(make_response(jsonify({"error": "Missing 'id' or 'deleteAll' param"}), 400))

        doc_ref = col.document(doc_id)
        doc = doc_ref.get()
        if doc.exists:
            data = doc.to_dict()
            _delete_gcs_blobs(data.get("image_url"), data.get("styled_image_url"))
            doc_ref.delete()
        return _cors(make_response(jsonify({"status": "ok", "deleted": doc_id}), 200))

    return _cors(make_response(jsonify({"error": "Method not allowed"}), 405))
