import os
import uuid
import json
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from .models import ProcessResponse, UploadResponse, HealthResponse, Coordinate
from .storage import upload_image, save_result
from .vision import process_image
from .speech import process_voice_command

load_dotenv()

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "proyectosm-494910")
VERSION = "0.1.0"

app = FastAPI(
    title="Dal-i API",
    description="Collaborative Robotic Drawing System — UAB Sistemes Multimedia 2025-2026",
    version=VERSION
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Check if the API is running."""
    return HealthResponse(
        status="ok",
        project_id=PROJECT_ID,
        version=VERSION
    )

@app.post("/upload", response_model=UploadResponse)
async def upload(file: UploadFile = File(...)):
    """
    Upload an image to Cloud Storage.
    Returns the public URL of the uploaded image.
    """
    try:
        file_bytes = await file.read()
        filename = f"{uuid.uuid4()}_{file.filename}"
        image_url = upload_image(
            file_bytes=file_bytes,
            filename=filename,
            content_type=file.content_type
        )
        return UploadResponse(
            status="ok",
            image_url=image_url,
            filename=filename
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/process", response_model=ProcessResponse)
async def process(
    file: UploadFile = File(...),
    style: str = Form(default="default")
):
    """
    Main endpoint: receive image + style, return plotter coordinates.
    Simulates robot input for testing without physical hardware.
    """
    try:
        image_bytes = await file.read()
        filename = f"{uuid.uuid4()}_{file.filename}"
        image_url = upload_image(
            file_bytes=image_bytes,
            filename=filename,
            content_type=file.content_type
        )
        result = process_image(image_bytes, style)
        result_filename = f"{uuid.uuid4()}_result.json"
        save_result(
            result_data=json.dumps(result),
            filename=result_filename
        )
        coordinates = [
            Coordinate(x=c["x"], y=c["y"])
            for c in result["coordinates"]
        ]
        return ProcessResponse(
            status="ok",
            style=style,
            coordinates=coordinates,
            image_url=image_url,
            message=result["style_description"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/process/voice")
async def process_with_voice(
    image: UploadFile = File(...),
    audio: UploadFile = File(...)
):
    """
    Extended endpoint: receive image + voice command, return coordinates.
    Voice command is transcribed to extract artistic style.
    """
    try:
        image_bytes = await image.read()
        audio_bytes = await audio.read()
        voice_result = process_voice_command(audio_bytes)
        style = voice_result["style"]
        filename = f"{uuid.uuid4()}_{image.filename}"
        image_url = upload_image(
            file_bytes=image_bytes,
            filename=filename,
            content_type=image.content_type
        )
        result = process_image(image_bytes, style)
        coordinates = [
            Coordinate(x=c["x"], y=c["y"])
            for c in result["coordinates"]
        ]
        return ProcessResponse(
            status="ok",
            style=style,
            coordinates=coordinates,
            image_url=image_url,
            message=f"Voice: '{voice_result['transcript']}' → Style: {style}"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))