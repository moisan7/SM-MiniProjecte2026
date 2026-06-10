"""
vision.py — Pipeline de processament d'imatges de Dal-i
========================================================
Transforma una imatge d'entrada en una llista de coordenades {x, y}
que el braç robòtic pot seguir per reproduir el dibuix sobre paper.

Etapes principals:
  1. resize_image()           — Redimensiona l'entrada a max 768 px
  2. generate_styled_image()  — (Mode Avançat) Transferència d'estil via Gemini
  3. detect_edges()           — Detecció de contorns amb OpenCV Canny
  4. tsp_sort_contours()      — Ordena contorns (Greedy Nearest Neighbour)
  5. optimize_contour_directions() — Tria direcció de recorregut per contorn
  6. tsp_two_opt()            — Millora local 2-opt sobre l'ordre de contorns
  7. generate_svg()           — Genera previsualització SVG
  8. process_image()          — Orquestra totes les etapes anteriors
"""

import os
import logging
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

logger = logging.getLogger(__name__)

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "proyectosm-494910")
LOCATION = os.getenv("VERTEX_LOCATION", "us-central1")


def init_vertex():
    """Inicialitza el client de Vertex AI amb el projecte i la regió configurats."""
    vertexai.init(project=PROJECT_ID, location=LOCATION)


def resize_image(image_bytes: bytes, max_size: int = 768) -> bytes:
    """
    Redimensiona la imatge mantenint la proporció, limitant el costat màxim a max_size px.
    Redueix el temps de processament de Canny i el nombre de punts generats.
    """
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    height, width = img.shape[:2]
    if max(height, width) <= max_size:
        return image_bytes  # ja és prou petita, no cal reescalar

    if width > height:
        new_width = max_size
        new_height = int(height * (max_size / width))
    else:
        new_height = max_size
        new_width = int(width * (max_size / height))

    resized = cv2.resize(img, (new_width, new_height), interpolation=cv2.INTER_AREA)
    _, buffer = cv2.imencode(".jpg", resized)
    return buffer.tobytes()


def generate_styled_image(image_bytes: bytes, style: str) -> Tuple[bytes, bool]:
    """
    Aplica transferència d'estil visual usant Vertex AI Gemini 2.5 Flash (mode imatge).
    Retorna (image_bytes, success). Si falla, retorna la imatge original i success=False
    perquè l'endpoint pugui avisar l'usuari sense aturar el processament.
    """
    try:
        init_vertex()
        model = GenerativeModel("gemini-2.5-flash-image")

        image_part = Part.from_data(image_bytes, mime_type="image/jpeg")
        prompt = (
            f"Perform an artistic style transfer. Transform this image into the style of {style}. "
            "Return only the stylized image as a response."
        )

        response = model.generate_content([image_part, prompt])

        if not response.candidates:
            logger.warning("Gemini 2.5 Flash Image: no candidates in response.")
            return image_bytes, False

        # Busca la primera part de la resposta que contingui una imatge inline
        for part in response.candidates[0].content.parts:
            if part.inline_data and part.inline_data.mime_type.startswith("image/"):
                logger.info("Gemini 2.5 Flash Image: styled image generated (%s)", part.inline_data.mime_type)
                return part.inline_data.data, True
            if part.file_data:
                logger.warning("Gemini 2.5 Flash Image: response contained file_data (not handled).")

        logger.warning("Gemini 2.5 Flash Image: no image part in response.")
        if response.text:
            logger.debug("Gemini 2.5 Flash Image response text: %s", response.text[:100])

        return image_bytes, False
    except Exception as e:
        logger.error("Gemini 2.5 Flash Image styling failed: %s", e, exc_info=True)
        return image_bytes, False


def apply_style_transfer(image_bytes: bytes, style: str) -> str:
    """
    Usa Gemini 2.5 Flash (mode text) per generar una descripció artística
    de com reproduir la imatge en l'estil indicat. Retorna text per mostrar a l'usuari.
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


# ── TSP: Optimització de l'ordre de dibuix ─────────────────────────────────
# El repte del robot no és dibuixar els contorns, sinó en quin ordre fer-ho
# per minimitzar el desplaçament "en l'aire" (bolígraf aixecat). S'aplica
# una aproximació al Travelling Salesman Problem en tres passes successives.

def tsp_sort_contours(contours: List[np.ndarray]) -> List[np.ndarray]:
    """
    Pas 1 TSP: Nearest Neighbour greedy.
    Ordena els contorns escollint sempre el més proper al punt final del contorn anterior.
    Complexitat O(n²), adequat fins a centenars de contorns.
    """
    if not contours:
        return []

    sorted_contours = []
    remaining_contours = list(contours)

    # Partim de l'origen (0,0) — posició de repòs del robot
    current_pos = np.array([0, 0])

    while remaining_contours:
        best_idx = 0
        min_dist = float('inf')

        for i, contour in enumerate(remaining_contours):
            # Distància euclidiana des de la posició actual fins al primer punt del contorn
            start_point = contour[0][0]
            dist = np.linalg.norm(current_pos - start_point)

            if dist < min_dist:
                min_dist = dist
                best_idx = i

        # Afegim el millor contorn i actualitzem la posició al seu punt final
        next_contour = remaining_contours.pop(best_idx)
        sorted_contours.append(next_contour)
        current_pos = next_contour[-1][0]

    return sorted_contours


def optimize_contour_directions(contours: List[np.ndarray]) -> List[np.ndarray]:
    """
    Pas 2 TSP: Optimització de direccions.
    Per a cada contorn, decideix si recórrer-lo en l'ordre original o al revés,
    triant la direcció que minimitza la distància des del punt final del contorn anterior.
    Complexitat O(n), s'aplica després del Nearest Neighbour.
    """
    if not contours:
        return contours

    result = []
    current_pos = np.zeros(2, dtype=float)

    for c in contours:
        start = c[0][0].astype(float)
        end = c[-1][0].astype(float)
        # Si l'extrem final és més proper que l'inicial, invertim el contorn
        if np.linalg.norm(current_pos - end) < np.linalg.norm(current_pos - start):
            c = c[::-1]
        result.append(c)
        current_pos = c[-1][0].astype(float)

    return result


_TWO_OPT_MAX_CONTOURS = 150  # s'omet per a imatges molt complexes (evita bloqueig)
_TWO_OPT_MAX_PASSES = 3      # màxim de passades per limitar el temps de còmput


def tsp_two_opt(contours: List[np.ndarray]) -> List[np.ndarray]:
    """
    Pas 3 TSP: Cerca local 2-opt.
    Intenta millorar la solució greedy intercanviant parells de segments de la ruta.
    S'omet si hi ha més de _TWO_OPT_MAX_CONTOURS contorns.
    Típicament redueix el desplaçament en buit un 20–40% addicional.
    """
    n = len(contours)
    if n < 4 or n > _TWO_OPT_MAX_CONTOURS:
        return contours

    route = list(contours)
    passes = 0

    while passes < _TWO_OPT_MAX_PASSES:
        improved = False
        passes += 1

        for a in range(1, n - 1):
            for b in range(a + 2, n + 1):
                # Cost actual: distància entre contorn[a-1]→contorn[a] i contorn[b-1]→contorn[b]
                cost_before = np.linalg.norm(
                    route[a - 1][-1][0].astype(float) - route[a][0][0].astype(float)
                )
                if b < n:
                    cost_before += np.linalg.norm(
                        route[b - 1][-1][0].astype(float) - route[b][0][0].astype(float)
                    )

                # Cost si invertim el segment [a..b-1]: unió diferent dels extrems
                cost_after = np.linalg.norm(
                    route[a - 1][-1][0].astype(float) - route[b - 1][0][0].astype(float)
                )
                if b < n:
                    cost_after += np.linalg.norm(
                        route[a][-1][0].astype(float) - route[b][0][0].astype(float)
                    )

                if cost_after < cost_before - 1e-6:
                    route[a:b] = route[a:b][::-1]
                    improved = True

        if not improved:
            break  # cap millora en aquesta passada → convergit

    logger.debug("tsp_two_opt: %d contours, %d pass(es)", n, passes)
    return route


def generate_svg(contours: List[np.ndarray], width: int, height: int) -> str:
    """
    Genera una cadena SVG a partir dels contorns optimitzats.
    Cada contorn es converteix en un element <path> amb traços negres sobre fons transparent.
    Usada per mostrar la previsualització al frontend.
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

    return f"{svg_header}{''.join(paths)}</svg>"


def detect_edges(image_bytes: bytes) -> Tuple[np.ndarray, int, int]:
    """
    Aplica l'algoritme de Canny d'OpenCV per detectar les vores d'una imatge.
    Retorna (mapa de vores, amplada, alçada).
    Llindars (50, 150) ajustats empíricament per capturar detalls sense excés de soroll.
    """
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    height, width = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blurred, threshold1=50, threshold2=150)
    return edges, width, height


def edges_to_coordinates(edges: np.ndarray, scale_x: float = 1.0, scale_y: float = 1.0) -> list:
    """Converteix un mapa de vores (ndarray) a una llista de dicts {x, y}."""
    points = np.argwhere(edges > 0)  # retorna (fila, columna) == (y, x)
    return [{"x": float(col) * scale_x, "y": float(row) * scale_y} for row, col in points]


def process_image(image_bytes: bytes, style: str, advanced_mode: bool = False) -> dict:
    """
    Pipeline complet: imatge + estil → coordenades + SVG.
    Si advanced_mode=True, aplica primer la transferència d'estil visual amb Gemini.

    Retorna un diccionari amb:
      - style_description: text descriptiu de l'estil aplicat
      - coordinates: llista de {x, y} per al robot
      - svg: string SVG per a la previsualització
      - total_points: nombre total de punts
      - dimensions: {width, height} de la imatge processada
      - styled_image_bytes: bytes de la imatge estilitzada (o None)
      - style_transfer_ok: True si Gemini va respondre correctament
    """
    # Pas 1: Redimensionar per optimitzar temps de processament
    image_bytes = resize_image(image_bytes, max_size=768)

    styled_image_bytes = None
    style_transfer_ok = True

    if advanced_mode:
        # Pas 2: Transferència d'estil visual via Vertex AI Gemini
        styled_image_bytes, style_transfer_ok = generate_styled_image(image_bytes, style)
        process_bytes = styled_image_bytes
        if not style_transfer_ok:
            logger.warning("Style transfer failed; processing original image instead.")
    else:
        process_bytes = image_bytes

    # Pas 3: Descripció artística (només en mode avançat per evitar costos innecessaris)
    if advanced_mode:
        style_description = apply_style_transfer(process_bytes, style)
    else:
        style_description = f"Drawing in {style} style using edge-detected contours."

    # Pas 4: Detecció de contorns amb Canny
    # S'aplica més difuminat (7,7) i llindars més alts (70/200) que la funció
    # detect_edges() bàsica per ignorar línies febles i reduir soroll
    nparr = np.frombuffer(process_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    height, width = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (7, 7), 0)
    edges = cv2.Canny(blurred, threshold1=70, threshold2=200)

    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Simplificació i filtratge de contorns
    simplified_contours = []
    for contour in contours:
        # Descartem contorns massa petits (taques de soroll < 20 px²)
        if cv2.contourArea(contour) < 20:
            continue
        # approxPolyDP redueix punts redundants (epsilon = 2% del perímetre)
        epsilon = 0.02 * cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, epsilon, True)
        if len(approx) > 2:
            simplified_contours.append(approx)

    # Pas 5–7: Optimització de la trajectòria del robot (TSP en tres passes)
    optimized_contours = tsp_sort_contours(simplified_contours)       # Nearest Neighbour
    optimized_contours = optimize_contour_directions(optimized_contours)  # Flip de direcció
    optimized_contours = tsp_two_opt(optimized_contours)              # Millora local 2-opt

    # Pas 8: Generar SVG per a la previsualització al frontend
    svg_content = generate_svg(optimized_contours, width, height)

    # Aplanar a llista de coordenades {x, y} per enviar al robot
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
        "styled_image_bytes": styled_image_bytes,
        "style_transfer_ok": style_transfer_ok,
    }
