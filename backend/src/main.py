import os
import uuid
import json
import logging
import time
from collections import defaultdict
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

import firebase_admin
from firebase_admin import auth as firebase_auth

from fastapi.staticfiles import StaticFiles
from .models import ProcessResponse, HealthResponse, Coordinate
from .storage import upload_image, save_result
from .vision import process_image
from .speech import process_voice_command, extract_style, generate_speech_base64
from .db import save_to_history

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "proyectosm-494910")

MAX_IMAGE_BYTES = 10 * 1024 * 1024  # 10 MB

try:
    firebase_admin.initialize_app()
except ValueError:
    pass  # already initialized (e.g. during test reloads)

# ---------------------------------------------------------------------------
# Language detection
# ---------------------------------------------------------------------------
_ES_MARKERS = set("áéíóúüñ¿¡")
_ES_WORDS = {"estilo", "como", "haz", "dibuja", "quiero", "una", "imagen", "con", "para", "que"}

def _detect_language(text: str) -> str:
    lower = text.lower()
    if any(c in _ES_MARKERS for c in lower):
        return "es-ES"
    if any(w in lower.split() for w in _ES_WORDS):
        return "es-ES"
    return "en-US"

# ---------------------------------------------------------------------------
# Firebase auth dependencies
# ---------------------------------------------------------------------------

async def _verify_firebase_token(request: Request) -> str:
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header.")
    token = header.split(" ", 1)[1]
    try:
        decoded = firebase_auth.verify_id_token(token)
        return decoded["uid"]
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired Firebase token.")

async def _optional_firebase_token(request: Request) -> str:
    """Like _verify_firebase_token but falls back to 'device' uid for Pi/hardware clients."""
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        return "device"
    try:
        decoded = firebase_auth.verify_id_token(header.split(" ", 1)[1])
        return decoded["uid"]
    except Exception:
        return "device"

# ---------------------------------------------------------------------------
# Rate limiting (in-memory sliding window, per IP)
# ---------------------------------------------------------------------------
RATE_LIMIT = int(os.getenv("RATE_LIMIT_PER_MINUTE", "20"))
_rate_store: dict[str, list[float]] = defaultdict(list)

async def _check_rate_limit(request: Request) -> None:
    ip = request.client.host if request.client else "unknown"
    now = time.monotonic()
    window_start = now - 60.0
    timestamps = [t for t in _rate_store[ip] if t > window_start]
    if len(timestamps) >= RATE_LIMIT:
        raise HTTPException(
            status_code=429,
            detail="Demasiadas solicitudes. Espera un momento antes de volver a intentarlo."
        )
    timestamps.append(now)
    _rate_store[ip] = timestamps

_rate_limit = Depends(_check_rate_limit)

# ---------------------------------------------------------------------------
# Image validation
# ---------------------------------------------------------------------------
def _validate_image(file: UploadFile, file_bytes: bytes) -> None:
    if len(file_bytes) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="Imagen demasiado grande. Máximo 10 MB.")
    content_type = file.content_type or ""
    if not content_type.startswith("image/"):
        raise HTTPException(
            status_code=415,
            detail=f"Tipo de archivo no válido ({content_type or 'desconocido'}). Se requiere una imagen."
        )

VERSION = "0.1.0"

app = FastAPI(
    title="Dal-i API",
    description="Collaborative Robotic Drawing System — UAB Sistemes Multimedia 2025-2026",
    version=VERSION
)

_raw_origins = os.getenv("ALLOWED_ORIGINS", "*")
ALLOWED_ORIGINS = [o.strip() for o in _raw_origins.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)


@app.get("/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse(status="ok", project_id=PROJECT_ID, version=VERSION)


@app.post("/process", response_model=ProcessResponse, dependencies=[_rate_limit])
async def process(
    file: UploadFile = File(...),
    style: str = Form(default="default"),
    advanced_mode: bool = Form(default=False),
    uid: str = Depends(_verify_firebase_token),
):
    try:
        image_bytes = await file.read()
        _validate_image(file, image_bytes)
        filename = f"{uuid.uuid4()}_{file.filename}"
        image_url = upload_image(
            file_bytes=image_bytes,
            filename=filename,
            content_type=(file.content_type or "application/octet-stream")
        )
        result = process_image(image_bytes, style, advanced_mode=advanced_mode)

        styled_image_url = None
        if result.get("styled_image_bytes"):
            styled_filename = f"styled_{uuid.uuid4()}.jpg"
            styled_image_url = upload_image(
                file_bytes=result["styled_image_bytes"],
                filename=styled_filename,
                content_type="image/jpeg"
            )

        result_filename = f"{uuid.uuid4()}_result.json"
        save_result(result_data=json.dumps(result, default=str), filename=result_filename)

        coordinates = [Coordinate(x=c["x"], y=c["y"]) for c in result["coordinates"]]

        warning = None
        if advanced_mode and not result.get("style_transfer_ok", True):
            warning = "La transformación de estilo visual no pudo completarse; se procesó la imagen original."

        doc_id = None
        try:
            doc_id = save_to_history({
                "style": style,
                "image_url": image_url,
                "styled_image_url": styled_image_url,
                "message": result["style_description"],
                "coordinates": [{"x": c.x, "y": c.y} for c in coordinates],
                "svg": result.get("svg"),
                "dimensions": result.get("dimensions"),
            }, uid=uid)
        except Exception as db_err:
            logger.error(f"Error saving to Firestore: {db_err}")

        return ProcessResponse(
            status="ok",
            style=style,
            coordinates=coordinates,
            image_url=image_url,
            styled_image_url=styled_image_url,
            message=result["style_description"],
            svg=result.get("svg"),
            dimensions=result.get("dimensions"),
            id=doc_id,
            warning=warning,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in process: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error al procesar la imagen.")


@app.post("/process/voice", dependencies=[_rate_limit])
async def process_with_voice(
    image: UploadFile = File(...),
    audio: UploadFile = File(...),
    advanced_mode: bool = Form(default=False),
    uid: str = Depends(_optional_firebase_token),
):
    try:
        image_bytes = await image.read()
        _validate_image(image, image_bytes)
        audio_bytes = await audio.read()
        voice_result = process_voice_command(audio_bytes)
        style = voice_result["style"]
        filename = f"{uuid.uuid4()}_{image.filename}"
        image_url = upload_image(
            file_bytes=image_bytes,
            filename=filename,
            content_type=(image.content_type or "application/octet-stream")
        )
        result = process_image(image_bytes, style, advanced_mode=advanced_mode)

        styled_image_url = None
        if result.get("styled_image_bytes"):
            styled_filename = f"styled_{uuid.uuid4()}.jpg"
            styled_image_url = upload_image(
                file_bytes=result["styled_image_bytes"],
                filename=styled_filename,
                content_type="image/jpeg"
            )

        coordinates = [Coordinate(x=c["x"], y=c["y"]) for c in result["coordinates"]]

        warning = None
        if advanced_mode and not result.get("style_transfer_ok", True):
            warning = "La transformación de estilo visual no pudo completarse; se procesó la imagen original."

        doc_id = None
        try:
            doc_id = save_to_history({
                "style": style,
                "image_url": image_url,
                "styled_image_url": styled_image_url,
                "transcript": voice_result["transcript"],
                "message": f"Voice: '{voice_result['transcript']}' → Style: {style}",
                "coordinates": [{"x": c.x, "y": c.y} for c in coordinates],
                "svg": result.get("svg"),
                "dimensions": result.get("dimensions"),
            }, uid=uid)
        except Exception as db_err:
            logger.error(f"Error saving to Firestore: {db_err}")

        return ProcessResponse(
            status="ok",
            style=style,
            coordinates=coordinates,
            image_url=image_url,
            styled_image_url=styled_image_url,
            transcript=voice_result["transcript"],
            message=f"Voice: '{voice_result['transcript']}' → Style: {style}",
            svg=result.get("svg"),
            dimensions=result.get("dimensions"),
            id=doc_id,
            warning=warning,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in process_with_voice: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error al procesar la imagen con voz.")


@app.post("/process/text", response_model=ProcessResponse, dependencies=[_rate_limit])
async def process_with_text(
    image: UploadFile = File(...),
    text: str = Form(...),
    advanced_mode: bool = Form(default=False),
    uid: str = Depends(_optional_firebase_token),
):
    try:
        image_bytes = await image.read()
        _validate_image(image, image_bytes)
        style = extract_style(text)

        filename = f"{uuid.uuid4()}_{image.filename}"
        image_url = upload_image(
            file_bytes=image_bytes,
            filename=filename,
            content_type=(image.content_type or "application/octet-stream")
        )

        result = process_image(image_bytes, style, advanced_mode=advanced_mode)

        tts_lang = _detect_language(text)
        tts_text = (
            f"¡Entendido! Preparando los motores para dibujar al estilo {style}."
            if tts_lang == "es-ES"
            else f"Got it! Preparing the motors to draw in {style} style."
        )
        audio_b64 = generate_speech_base64(tts_text, language_code=tts_lang)

        styled_image_url = None
        if result.get("styled_image_bytes"):
            styled_filename = f"styled_{uuid.uuid4()}.jpg"
            styled_image_url = upload_image(
                file_bytes=result["styled_image_bytes"],
                filename=styled_filename,
                content_type="image/jpeg"
            )

        coordinates = [Coordinate(x=c["x"], y=c["y"]) for c in result["coordinates"]]

        warning = None
        if advanced_mode and not result.get("style_transfer_ok", True):
            warning = "La transformación de estilo visual no pudo completarse; se procesó la imagen original."

        doc_id = None
        try:
            doc_id = save_to_history({
                "style": style,
                "image_url": image_url,
                "styled_image_url": styled_image_url,
                "message": f"Text: '{text}' → Style: {style}",
                "coordinates": [{"x": c.x, "y": c.y} for c in coordinates],
                "svg": result.get("svg"),
                "dimensions": result.get("dimensions"),
            }, uid=uid)
        except Exception as db_err:
            logger.error(f"Error saving to Firestore: {db_err}")

        return ProcessResponse(
            status="ok",
            style=style,
            coordinates=coordinates,
            image_url=image_url,
            styled_image_url=styled_image_url,
            message=f"Text: '{text}' → Style: {style}",
            audio_base64=audio_b64,
            svg=result.get("svg"),
            dimensions=result.get("dimensions"),
            id=doc_id,
            warning=warning,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in process_with_text: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error al procesar la imagen con texto.")


# Serve the static frontend if the 'out' directory exists
base_dir = os.path.dirname(__file__)
frontend_path_docker = os.path.join(base_dir, "../frontend/out")
frontend_path_local = os.path.join(base_dir, "../../frontend/out")
if os.path.exists(frontend_path_docker):
    app.mount("/", StaticFiles(directory=frontend_path_docker, html=True), name="frontend")
elif os.path.exists(frontend_path_local):
    app.mount("/", StaticFiles(directory=frontend_path_local, html=True), name="frontend")
