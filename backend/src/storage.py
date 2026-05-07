import os
from google.cloud import storage
from dotenv import load_dotenv

load_dotenv()

BUCKET_NAME = os.getenv("BUCKET_NAME", "dal-i-bucket")
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "proyectosm-494910")

def get_client():
    return storage.Client(project=PROJECT_ID)

def upload_image(file_bytes: bytes, filename: str, content_type: str = "image/jpeg") -> str:
    """
    Upload an image to Cloud Storage.
    Returns the public URL of the uploaded image.
    """
    client = get_client()
    bucket = client.bucket(BUCKET_NAME)
    blob = bucket.blob(f"images/{filename}")
    blob.upload_from_string(file_bytes, content_type=content_type)
    blob.make_public()
    return blob.public_url

def download_image(filename: str) -> bytes:
    """
    Download an image from Cloud Storage.
    Returns the image as bytes.
    """
    client = get_client()
    bucket = client.bucket(BUCKET_NAME)
    blob = bucket.blob(f"images/{filename}")
    return blob.download_as_bytes()

def save_result(result_data: str, filename: str) -> str:
    """
    Save processing result (coordinates JSON) to Cloud Storage.
    Returns the public URL.
    """
    client = get_client()
    bucket = client.bucket(BUCKET_NAME)
    blob = bucket.blob(f"results/{filename}")
    blob.upload_from_string(result_data, content_type="application/json")
    blob.make_public()
    return blob.public_url