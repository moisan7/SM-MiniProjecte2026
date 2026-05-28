import cv2
import numpy as np
from unittest.mock import patch, MagicMock
from src.vision import detect_edges, edges_to_coordinates, apply_style_transfer, process_image


# ---------------------------------------------------------------------------
# detect_edges — pure OpenCV, no GCP
# ---------------------------------------------------------------------------

def test_detect_edges_shape(sample_image_bytes):
    edges, width, height = detect_edges(sample_image_bytes)
    assert edges is not None
    assert edges.shape == (100, 100)

def test_detect_edges_is_binary(sample_image_bytes):
    edges, width, height = detect_edges(sample_image_bytes)
    unique_values = set(np.unique(edges))
    assert unique_values.issubset({0, 255})

def test_detect_edges_has_edges(sample_image_bytes):
    edges, width, height = detect_edges(sample_image_bytes)
    assert edges.sum() > 0


# ---------------------------------------------------------------------------
# edges_to_coordinates — pure OpenCV, no GCP
# ---------------------------------------------------------------------------

def test_edges_to_coordinates_returns_list():
    edges = np.zeros((100, 100), dtype=np.uint8)
    coords = edges_to_coordinates(edges)
    assert isinstance(coords, list)

def test_edges_to_coordinates_empty_on_blank():
    edges = np.zeros((100, 100), dtype=np.uint8)
    coords = edges_to_coordinates(edges)
    assert coords == []

def test_edges_to_coordinates_finds_rectangle():
    img = np.zeros((100, 100, 3), dtype=np.uint8)
    cv2.rectangle(img, (20, 20), (80, 80), (255, 255, 255), 2)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    coords = edges_to_coordinates(gray)
    assert len(coords) > 0
    for c in coords:
        assert "x" in c and "y" in c

def test_edges_to_coordinates_scale():
    img = np.zeros((100, 100, 3), dtype=np.uint8)
    cv2.rectangle(img, (20, 20), (80, 80), (255, 255, 255), 2)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    coords_1x = edges_to_coordinates(gray, scale_x=1.0, scale_y=1.0)
    coords_2x = edges_to_coordinates(gray, scale_x=2.0, scale_y=2.0)
    if coords_1x and coords_2x:
        assert coords_2x[0]["x"] == coords_1x[0]["x"] * 2
        assert coords_2x[0]["y"] == coords_1x[0]["y"] * 2


# ---------------------------------------------------------------------------
# apply_style_transfer — mock Vertex AI
# ---------------------------------------------------------------------------

@patch("src.vision.vertexai.init")
@patch("src.vision.GenerativeModel")
def test_apply_style_transfer_returns_description(MockModel, mock_init, sample_image_bytes):
    mock_response = MagicMock()
    mock_response.text = "Bold fragmented shapes with sharp angles."
    mock_instance = MagicMock()
    mock_instance.generate_content.return_value = mock_response
    MockModel.return_value = mock_instance

    result = apply_style_transfer(sample_image_bytes, "picasso")

    assert result == "Bold fragmented shapes with sharp angles."
    mock_init.assert_called_once()
    mock_instance.generate_content.assert_called_once()


@patch("src.vision.vertexai.init")
@patch("src.vision.GenerativeModel")
def test_apply_style_transfer_includes_style_in_prompt(MockModel, mock_init, sample_image_bytes):
    mock_response = MagicMock()
    mock_response.text = "Swirling brushstrokes."
    mock_instance = MagicMock()
    mock_instance.generate_content.return_value = mock_response
    MockModel.return_value = mock_instance

    apply_style_transfer(sample_image_bytes, "van gogh")

    call_args = mock_instance.generate_content.call_args[0][0]
    prompt_text = call_args[1]
    assert "van gogh" in prompt_text.lower()


# ---------------------------------------------------------------------------
# process_image — full pipeline with mocked Vertex AI
# ---------------------------------------------------------------------------

@patch("src.vision.vertexai.init")
@patch("src.vision.GenerativeModel")
def test_process_image_returns_expected_keys(MockModel, mock_init, sample_image_bytes):
    mock_response = MagicMock()
    mock_response.text = "Geometric lines in cubist style."
    mock_instance = MagicMock()
    mock_instance.generate_content.return_value = mock_response
    MockModel.return_value = mock_instance

    result = process_image(sample_image_bytes, "picasso")

    assert "style_description" in result
    assert "coordinates" in result
    assert "total_points" in result
    # Without advanced_mode, Gemini is not called; description comes from template
    assert "picasso" in result["style_description"].lower()
    assert isinstance(result["coordinates"], list)
    assert result["total_points"] == len(result["coordinates"])


@patch("src.vision.vertexai.init")
@patch("src.vision.GenerativeModel")
def test_process_image_coordinates_have_xy(MockModel, mock_init, sample_image_bytes):
    mock_response = MagicMock()
    mock_response.text = "Lines."
    mock_instance = MagicMock()
    mock_instance.generate_content.return_value = mock_response
    MockModel.return_value = mock_instance

    result = process_image(sample_image_bytes, "default")

    for coord in result["coordinates"]:
        assert "x" in coord and "y" in coord
        assert isinstance(coord["x"], float)
        assert isinstance(coord["y"], float)
