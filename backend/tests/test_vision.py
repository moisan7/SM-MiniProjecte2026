import numpy as np
from src.vision import detect_edges, edges_to_coordinates

def test_detect_edges():
    # Create a simple test image (black square on white)
    import cv2
    img = np.ones((100, 100, 3), dtype=np.uint8) * 255
    cv2.rectangle(img, (25, 25), (75, 75), (0, 0, 0), 2)
    _, img_bytes = cv2.imencode('.jpg', img)
    
    edges = detect_edges(img_bytes.tobytes())
    assert edges is not None
    assert edges.shape == (100, 100)

def test_edges_to_coordinates():
    # Create simple edge map
    edges = np.zeros((100, 100), dtype=np.uint8)
    edges[50, 50] = 255
    edges[60, 60] = 255
    
    coords = edges_to_coordinates(edges)
    assert isinstance(coords, list)