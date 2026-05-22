import os
import uuid
import json
import logging
import traceback
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from fastapi.staticfiles import StaticFiles
from .models import ProcessResponse, UploadResponse, HealthResponse, Coordinate
from .storage import upload_image, save_result
from .vision import process_image
from .speech import process_voice_command, extract_style
from .db import save_to_history, get_history, delete_from_history

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

@app.get("/history")
async def fetch_history(limit: int = 12):
    """Retrieve the recent generation history."""
    try:
        return get_history(limit=limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/history/{item_id}")
async def delete_history_item(item_id: str):
    """Delete an item from the history."""
    try:
        delete_from_history(item_id)
        return {"status": "ok", "message": "Item deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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
            content_type=(file.content_type or "application/octet-stream")
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
            content_type=(file.content_type or "application/octet-stream")
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
        
        # Save to history
        save_to_history({
            "style": style,
            "image_url": image_url,
            "message": result["style_description"],
            "coordinates": [{"x": c.x, "y": c.y} for c in coordinates],
            "svg": result.get("svg"),
            "dimensions": result.get("dimensions")
        })
        
        return ProcessResponse(
            status="ok",
            style=style,
            coordinates=coordinates,
            image_url=image_url,
            message=result["style_description"],
            svg=result.get("svg"),
            dimensions=result.get("dimensions")
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
            content_type=(image.content_type or "application/octet-stream")
        )
        result = process_image(image_bytes, style)
        coordinates = [
            Coordinate(x=c["x"], y=c["y"])
            for c in result["coordinates"]
        ]
        
        # Save to history
        save_to_history({
            "style": style,
            "image_url": image_url,
            "message": f"Voice: '{voice_result['transcript']}' → Style: {style}",
            "coordinates": [{"x": c.x, "y": c.y} for c in coordinates],
            "svg": result.get("svg"),
            "dimensions": result.get("dimensions")
        })
        
        return ProcessResponse(
            status="ok",
            style=style,
            coordinates=coordinates,
            image_url=image_url,
            message=f"Voice: '{voice_result['transcript']}' → Style: {style}",
            svg=result.get("svg"),
            dimensions=result.get("dimensions")
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/process/text", response_model=ProcessResponse)
async def process_with_text(
    image: UploadFile = File(...),
    text: str = Form(...)
):
    """
    Receive image + text prompt, extract style from text, return coordinates.
    """
    try:
        logger.info(f"Received request for /process/text with prompt: '{text}'")
        image_bytes = await image.read()
        style = extract_style(text)
        logger.info(f"Extracted style: {style}")

        filename = f"{uuid.uuid4()}_{image.filename}"
        logger.info(f"Uploading image to Storage as: {filename}")
        image_url = upload_image(
            file_bytes=image_bytes,
            filename=filename,
            content_type=(image.content_type or "application/octet-stream")
        )
        logger.info(f"Image uploaded successfully: {image_url}")

        logger.info("Starting image processing (Vertex AI + OpenCV)...")
        result = process_image(image_bytes, style)
        
        svg_content = result.get("svg")
        if not svg_content:
            logger.warning("Warning: No SVG content generated in result.")
        else:
            logger.info(f"SVG generated successfully (length: {len(svg_content)})")

        coordinates = [
            Coordinate(x=c["x"], y=c["y"])
            for c in result["coordinates"]
        ]
        
        # Save to history
        logger.info("Saving record to Firestore...")
        try:
            save_to_history({
                "style": style,
                "image_url": image_url,
                "message": f"Text: '{text}' → Style: {style}",
                "coordinates": [{"x": c.x, "y": c.y} for c in coordinates],
                "svg": svg_content,
                "dimensions": result.get("dimensions")
            })
            logger.info("History saved successfully.")
        except Exception as db_err:
            logger.error(f"Error saving to Firestore: {str(db_err)}")
            # We continue even if history fails to return the result to the user

        return ProcessResponse(
            status="ok",
            style=style,
            coordinates=coordinates,
            image_url=image_url,
            message=f"Text: '{text}' → Style: {style}",
            svg=svg_content,
            dimensions=result.get("dimensions")
        )
    except Exception as e:
        logger.error(f"Error in process_with_text: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

# Servir el frontend estático si existe la carpeta 'out'
frontend_path = os.path.join(os.path.dirname(__file__), "../../frontend/out")
base_dir = os.path.dirname(__file__)
frontend_path_local = os.path.join(base_dir, "../../frontend/out")
frontend_path_docker = os.path.join(base_dir, "../frontend/out")
if os.path.exists(frontend_path_docker):
    app.mount("/", StaticFiles(directory=frontend_path_docker, html=True), name="frontend")
elif os.path.exists(frontend_path_local):
    app.mount("/", StaticFiles(directory=frontend_path_local, html=True), name="frontend")
