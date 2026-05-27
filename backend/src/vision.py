import os
import cv2
import numpy as np
import vertexai
from vertexai.generative_models import GenerativeModel, Part
from vertexai.preview.vision_models import ImageGenerationModel, Image
from dotenv import load_dotenv
from typing import List, Tuple
import io
from PIL import Image as PILImage

load_dotenv()

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "proyectosm-494910")
LOCATION = os.getenv("VERTEX_LOCATION", "us-central1")

def init_vertex():
    vertexai.init(project=PROJECT_ID, location=LOCATION)

def resize_image(image_bytes: bytes, max_size: int = 768) -> bytes:
    """
    Resize image keeping aspect ratio, limiting the maximum side.
    """
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    height, width = img.shape[:2]
    if max(height, width) <= max_size:
        return image_bytes
        
    if width > height:
        new_width = max_size
        new_height = int(height * (max_size / width))
    else:
        new_height = max_size
        new_width = int(width * (max_size / height))
        
    resized = cv2.resize(img, (new_width, new_height), interpolation=cv2.INTER_AREA)
    _, buffer = cv2.imencode(".jpg", resized)
    return buffer.tobytes()

def generate_styled_image(image_bytes: bytes, style: str) -> bytes:
    """
    Use Vertex AI Gemini 2.5 Flash Image to apply a style transfer.
    This model supports multimodal image output.
    """
    try:
        init_vertex()
        # Using the specific image-output variant of Gemini 2.5 Flash
        model = GenerativeModel("gemini-2.5-flash-image")
        
        image_part = Part.from_data(image_bytes, mime_type="image/jpeg")
        prompt = f"Perform an artistic style transfer. Transform this image into the style of {style}. Return only the stylized image as a response."
        
        # Requesting content generation which should include an image part
        response = model.generate_content([image_part, prompt])
        
        if not response.candidates:
            print("Gemini 2.5 Flash Image: No candidates in response.")
            return image_bytes

        # Extract the image part from the response
        for part in response.candidates[0].content.parts:
            if part.inline_data and part.inline_data.mime_type.startswith("image/"):
                print(f"Gemini 2.5 Flash Image: Successfully generated image ({part.inline_data.mime_type})")
                return part.inline_data.data
            # Some versions might return a file_data reference if uploaded to a bucket
            if part.file_data:
                print("Gemini 2.5 Flash Image: Generated image as file_data (not handled directly).")
        
        print("Gemini 2.5 Flash Image: No image part found in response parts.")
        # Fallback to text part logging if available for debugging
        if response.text:
            print(f"Gemini 2.5 Flash Image response text: {response.text[:100]}...")
            
        return image_bytes
    except Exception as e:
        print(f"CRITICAL: Gemini 2.5 Flash Image styling failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return image_bytes

def apply_style_transfer(image_bytes: bytes, style: str) -> str:
    """
    Use Vertex AI Gemini 2.5 Flash to get style instructions for the image.
    """
    init_vertex()
    # Using the model suggested by the user
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

def detect_edges(image_bytes: bytes) -> Tuple[np.ndarray, int, int]:
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

def process_image(image_bytes: bytes, style: str, advanced_mode: bool = False) -> dict:
    """
    Full pipeline: image + style -> coordinates + SVG.
    advanced_mode=True applies Image-to-Image style transfer first.
    """
    # 1. Resize for optimization
    image_bytes = resize_image(image_bytes, max_size=768)
    
    styled_image_bytes = None
    if advanced_mode:
        # 2. Apply visual style transfer via Vertex AI Imagen
        try:
            styled_image_bytes = generate_styled_image(image_bytes, style)
            process_bytes = styled_image_bytes
        except Exception as e:
            print(f"Error in Image-to-Image: {e}")
            process_bytes = image_bytes # Fallback
    else:
        process_bytes = image_bytes

    # 3. Get text description — only call Gemini in advanced mode to avoid unnecessary charges
    if advanced_mode:
        style_description = apply_style_transfer(process_bytes, style)
    else:
        style_description = f"Drawing in {style} style using edge-detected contours."
    
    # 4. Detect edges via OpenCV
    # Pre-process to reduce noise: slightly more blur
    nparr = np.frombuffer(process_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    height, width = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (7, 7), 0) # Increased blur from 5,5 to 7,7
    edges = cv2.Canny(blurred, threshold1=70, threshold2=200) # Higher thresholds to ignore faint lines
    
    contours, _ = cv2.findContours(
        edges,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE
    )
    
    # Simplify and filter contours more aggressively
    simplified_contours = []
    for contour in contours:
        # Filter by area: ignore tiny spots that a plotter shouldn't waste time on
        if cv2.contourArea(contour) < 20: 
            continue
            
        # More aggressive simplification: increased epsilon from 0.01 to 0.02
        epsilon = 0.02 * cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, epsilon, True)
        
        # Only keep contours that have enough substance
        if len(approx) > 2:
            simplified_contours.append(approx)
            
    # Optimize path with TSP
    optimized_contours = tsp_sort_contours(simplified_contours)
    
    # Generate SVG
    svg_content = generate_svg(optimized_contours, width, height)
    
    # Flatten coordinates
    coordinates = []
    for contour in optimized_contours:
        for point in contour:
            coordinates.append({"x": float(point[0][0]), "y": float(point[0][1])})
            
    return {
        "style_description": style_description,
        "coordinates": coordinates,
        "svg": svg_content,
        "total_points": len(coordinates),
        "dimensions": {"width": width, "height": height},
        "styled_image_bytes": styled_image_bytes
    }