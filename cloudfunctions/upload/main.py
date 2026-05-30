import os
import uuid
import functions_framework
import firebase_admin
from firebase_admin import auth as firebase_auth
from google.cloud import storage
from flask import make_response, jsonify

BUCKET_NAME = os.getenv("BUCKET_NAME", "dal-i-bucket")
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "proyectosm-494910")
MAX_IMAGE_BYTES = 10 * 1024 * 1024

try:
    firebase_admin.initialize_app()
except ValueError:
    pass  # already initialized

_storage_client = None

_CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, Authorization",
}


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


@functions_framework.http
def upload_handler(request):
    if request.method == "OPTIONS":
        return _cors(make_response("", 204))

    uid, err = _verify_token(request)
    if err:
        return err

    if request.method != "POST":
        return _cors(make_response(jsonify({"error": "Method not allowed"}), 405))

    file = request.files.get("file")
    if not file:
        return _cors(make_response(jsonify({"error": "No file provided"}), 400))

    content_type = file.content_type or ""
    if not content_type.startswith("image/"):
        return _cors(make_response(jsonify({"error": f"Invalid file type: {content_type}"}), 415))

    file_bytes = file.read()
    if len(file_bytes) > MAX_IMAGE_BYTES:
        return _cors(make_response(jsonify({"error": "File too large. Max 10 MB."}), 413))

    filename = f"{uuid.uuid4()}_{file.filename}"
    bucket = _get_storage().bucket(BUCKET_NAME)
    blob = bucket.blob(f"images/{filename}")
    blob.upload_from_string(file_bytes, content_type=content_type)
    blob.make_public()

    return _cors(make_response(jsonify({
        "status": "ok",
        "image_url": blob.public_url,
        "filename": filename,
    }), 200))
