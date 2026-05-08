from unittest.mock import patch
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

FAKE_URL = "https://storage.googleapis.com/dal-i-bucket/images/fake.jpg"
FAKE_COORDS = [{"x": 10.0, "y": 20.0}, {"x": 30.0, "y": 40.0}]
FAKE_PROCESS_RESULT = {
    "style_description": "Bold lines, fragmented shapes in Picasso style.",
    "coordinates": FAKE_COORDS,
    "total_points": 2,
}


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["project_id"] == "proyectosm-494910"
    assert "version" in body


# ---------------------------------------------------------------------------
# Upload
# ---------------------------------------------------------------------------

@patch("src.main.upload_image", return_value=FAKE_URL)
def test_upload_success(mock_upload, sample_image_bytes):
    response = client.post(
        "/upload",
        files={"file": ("test.jpg", sample_image_bytes, "image/jpeg")},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["image_url"] == FAKE_URL
    assert "filename" in body
    mock_upload.assert_called_once()


@patch("src.main.upload_image", side_effect=Exception("GCS unavailable"))
def test_upload_error(mock_upload, sample_image_bytes):
    response = client.post(
        "/upload",
        files={"file": ("test.jpg", sample_image_bytes, "image/jpeg")},
    )
    assert response.status_code == 500
    assert "GCS unavailable" in response.json()["detail"]


# ---------------------------------------------------------------------------
# Process (text style)
# ---------------------------------------------------------------------------

@patch("src.main.save_result", return_value="https://storage.googleapis.com/dal-i-bucket/results/fake.json")
@patch("src.main.process_image", return_value=FAKE_PROCESS_RESULT)
@patch("src.main.upload_image", return_value=FAKE_URL)
def test_process_success(mock_upload, mock_process, mock_save, sample_image_bytes):
    response = client.post(
        "/process",
        files={"file": ("test.jpg", sample_image_bytes, "image/jpeg")},
        data={"style": "picasso"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["style"] == "picasso"
    assert len(body["coordinates"]) == 2
    assert body["coordinates"][0] == {"x": 10.0, "y": 20.0}
    assert body["image_url"] == FAKE_URL
    mock_process.assert_called_once()


@patch("src.main.save_result", return_value=FAKE_URL)
@patch("src.main.process_image", return_value=FAKE_PROCESS_RESULT)
@patch("src.main.upload_image", return_value=FAKE_URL)
def test_process_default_style(mock_upload, mock_process, mock_save, sample_image_bytes):
    response = client.post(
        "/process",
        files={"file": ("test.jpg", sample_image_bytes, "image/jpeg")},
    )
    assert response.status_code == 200
    _, call_style = mock_process.call_args[0]
    assert call_style == "default"


@patch("src.main.upload_image", side_effect=Exception("Storage error"))
def test_process_error(mock_upload, sample_image_bytes):
    response = client.post(
        "/process",
        files={"file": ("test.jpg", sample_image_bytes, "image/jpeg")},
        data={"style": "picasso"},
    )
    assert response.status_code == 500


# ---------------------------------------------------------------------------
# Process/voice
# ---------------------------------------------------------------------------

FAKE_VOICE_RESULT = {"transcript": "draw it in van gogh style", "style": "van gogh"}


@patch("src.main.process_image", return_value=FAKE_PROCESS_RESULT)
@patch("src.main.upload_image", return_value=FAKE_URL)
@patch("src.main.process_voice_command", return_value=FAKE_VOICE_RESULT)
def test_process_voice_success(mock_voice, mock_upload, mock_process, sample_image_bytes, sample_audio_bytes):
    response = client.post(
        "/process/voice",
        files={
            "image": ("test.jpg", sample_image_bytes, "image/jpeg"),
            "audio": ("voice.wav", sample_audio_bytes, "audio/wav"),
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["style"] == "van gogh"
    assert "van gogh" in body["message"]
    assert len(body["coordinates"]) == 2


@patch("src.main.process_voice_command", side_effect=Exception("STT error"))
def test_process_voice_error(mock_voice, sample_image_bytes, sample_audio_bytes):
    response = client.post(
        "/process/voice",
        files={
            "image": ("test.jpg", sample_image_bytes, "image/jpeg"),
            "audio": ("voice.wav", sample_audio_bytes, "audio/wav"),
        },
    )
    assert response.status_code == 500
