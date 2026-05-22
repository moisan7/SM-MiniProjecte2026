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
    model = GenerativeModel("gemini-2.5-flash")
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

def tsp_sort_contours(contours: List[np.ndarray]) -> List[np.ndarray]:
    """
    Sort contours using a greedy Nearest Neighbor approach to minimize
    the distance the robot arm travels "in the air".
    """
    if not contours:
        return []
    
    sorted_contours = []
    remaining_contours = list(contours)
    
    # Start with the contour closest to the origin (0,0)
    current_pos = np.array([0, 0])
    
    while remaining_contours:
        best_idx = 0
        min_dist = float('inf')
        
        for i, contour in enumerate(remaining_contours):
            # Distance from current position to the start of this contour
            start_point = contour[0][0]
            dist = np.linalg.norm(current_pos - start_point)
            
            if dist < min_dist:
                min_dist = dist
                best_idx = i
        
        # Add the best contour and update current position to its end point
        next_contour = remaining_contours.pop(best_idx)
        sorted_contours.append(next_contour)
        current_pos = next_contour[-1][0]
        
    return sorted_contours

def generate_svg(contours: List[np.ndarray], width: int, height: int) -> str:
    """
    Generate an SVG string from the given contours.
    """
    svg_header = f'<svg viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">'
    paths = []
    
    for contour in contours:
        if len(contour) < 2:
            continue
        
        points = []
        for i, point in enumerate(contour):
            x, y = point[0]
            prefix = "M" if i == 0 else "L"
            points.append(f"{prefix}{x:.1f},{y:.1f}")
        
        path_data = " ".join(points)
        paths.append(f'<path d="{path_data}" fill="none" stroke="black" stroke-width="1" />')
    
    svg_footer = '</svg>'
    return f"{svg_header}{''.join(paths)}{svg_footer}"

def detect_edges(image_bytes: bytes) -> tuple[np.ndarray, int, int]:
    """
    Apply Canny Edge Detection to simplify image to drawable lines.
    Returns (edge map, width, height).
    """
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    height, width = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blurred, threshold1=50, threshold2=150)
    return edges, width, height

def process_image(image_bytes: bytes, style: str) -> dict:
    """
    Full pipeline: image + style -> coordinates + SVG.
    1. Apply style transfer via Vertex AI
    2. Detect edges via OpenCV
    3. Sort contours via TSP
    4. Generate SVG and flat coordinates
    """
    style_description = apply_style_transfer(image_bytes, style)
    edges, width, height = detect_edges(image_bytes)
    
    contours, _ = cv2.findContours(
        edges,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE
    )
    
    # Simplify and filter small contours
    simplified_contours = []
    for contour in contours:
        epsilon = 0.01 * cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, epsilon, True)
        if len(approx) > 1:
            simplified_contours.append(approx)
            
    # Optimize path with TSP
    optimized_contours = tsp_sort_contours(simplified_contours)
    
    # Generate SVG
    svg_content = generate_svg(optimized_contours, width, height)
    
    # Flatten coordinates for backward compatibility / simple plotter use
    coordinates = []
    for contour in optimized_contours:
        for point in contour:
            coordinates.append({"x": float(point[0][0]), "y": float(point[0][1])})
            
    return {
        "style_description": style_description,
        "coordinates": coordinates,
        "svg": svg_content,
        "total_points": len(coordinates),
        "dimensions": {"width": width, "height": height}
    }