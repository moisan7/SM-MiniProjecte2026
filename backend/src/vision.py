import os
import cv2
import numpy as np
import vertexai
from vertexai.generative_models import GenerativeModel, Part
from dotenv import load_dotenv
from typing import List

load_dotenv()

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "proyectosm-494910")
LOCATION = os.getenv("VERTEX_LOCATION", "us-central1")

def init_vertex():
    vertexai.init(project=PROJECT_ID, location=LOCATION)

def apply_style_transfer(image_bytes: bytes, style: str) -> str:
    """
    Use Vertex AI Gemini to get style instructions for the image.
    Returns a description of how to draw the image in the given style.
    """
    init_vertex()
    model = GenerativeModel("gemini-1.5-flash")
    image_part = Part.from_data(image_bytes, mime_type="image/jpeg")
    prompt = f"""
    Analyze this image and describe how to recreate it as a simple line drawing
    in the style of {style}. Focus on:
    1. The main shapes and outlines
    2. Key features to emphasize in {style} style
    3. Which details to simplify or exaggerate
    Keep the description focused on lines and strokes a robot plotter could draw.
    """
    response = model.generate_content([image_part, prompt])
    return response.text

def detect_edges(image_bytes: bytes) -> np.ndarray:
    """
    Apply Canny Edge Detection to simplify image to drawable lines.
    Returns edge map as numpy array.
    """
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blurred, threshold1=50, threshold2=150)
    return edges

def edges_to_coordinates(edges: np.ndarray, scale_x: float = 1.0, scale_y: float = 1.0) -> List[dict]:
    """
    Convert edge map to plotter coordinates.
    Returns list of {x, y} coordinates for the robot to follow.
    """
    coordinates = []
    contours, _ = cv2.findContours(
        edges,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE
    )
    for contour in contours:
        epsilon = 0.02 * cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, epsilon, True)
        for point in approx:
            x = float(point[0][0]) * scale_x
            y = float(point[0][1]) * scale_y
            coordinates.append({"x": x, "y": y})
    return coordinates

def process_image(image_bytes: bytes, style: str) -> dict:
    """
    Full pipeline: image + style -> coordinates.
    1. Apply style transfer via Vertex AI
    2. Detect edges via OpenCV
    3. Convert edges to plotter coordinates
    """
    style_description = apply_style_transfer(image_bytes, style)
    edges = detect_edges(image_bytes)
    coordinates = edges_to_coordinates(edges)
    return {
        "style_description": style_description,
        "coordinates": coordinates,
        "total_points": len(coordinates)
    }