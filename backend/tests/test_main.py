from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

FAKE_URL = "https://storage.googleapis.com/dal-i-bucket/images/fake.jpg"
FAKE_COORDS = [{"x": 10.0, "y": 20.0}, {"x": 30.0, "y": 40.0}]
FAKE_PROCESS_RESULT = {
    "style_description": "Bold lines, fragmented shapes in Picasso style.",
    "coordinates": FAKE_COORDS,
    "total_points": 2,
    "style_transfer_ok": True,
}
FAKE_HISTORY = [
    {
        "id": "abc123",
        "style": "picasso",
        "image_url": FAKE_URL,
        "styled_image_url": None,
        "message": "Drawing in picasso style.",
        "coordinates": FAKE_COORDS,
        "status": "ok",
    }
]


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["project_id"] == "proyectosm-494910"

def test_process_text_no_image():
    # Missing required 'image' file should return 422 Unprocessable Entity
    response = client.post("/process/text", data={"text": "estilo Picasso"})
    assert response.status_code == 422
    assert "detail" in response.json()


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
    assert response.json()["detail"]  # generic message; internal details not exposed


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


# ---------------------------------------------------------------------------
# Process/text
# ---------------------------------------------------------------------------

@patch("src.main.generate_speech_base64", return_value="ZmFrZWF1ZGlv")
@patch("src.main.process_image", return_value=FAKE_PROCESS_RESULT)
@patch("src.main.upload_image", return_value=FAKE_URL)
def test_process_text_success(mock_upload, mock_process, mock_tts, sample_image_bytes):
    response = client.post(
        "/process/text",
        files={"image": ("test.jpg", sample_image_bytes, "image/jpeg")},
        data={"text": "dibuja al estilo picasso"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["style"] == "picasso"
    assert len(body["coordinates"]) == 2
    assert body["audio_base64"] == "ZmFrZWF1ZGlv"
    assert "picasso" in body["message"].lower()
    mock_tts.assert_called_once()


@patch("src.main.generate_speech_base64", return_value="ZmFrZWF1ZGlv")
@patch("src.main.process_image", return_value=FAKE_PROCESS_RESULT)
@patch("src.main.upload_image", return_value=FAKE_URL)
def test_process_text_spanish_detected(mock_upload, mock_process, mock_tts, sample_image_bytes):
    """Spanish text must call TTS with es-ES language code."""
    client.post(
        "/process/text",
        files={"image": ("test.jpg", sample_image_bytes, "image/jpeg")},
        data={"text": "dibuja al estilo picasso"},
    )
    _, kwargs = mock_tts.call_args
    assert kwargs.get("language_code") == "es-ES"


@patch("src.main.generate_speech_base64", return_value="ZmFrZWF1ZGlv")
@patch("src.main.process_image", return_value=FAKE_PROCESS_RESULT)
@patch("src.main.upload_image", return_value=FAKE_URL)
def test_process_text_english_detected(mock_upload, mock_process, mock_tts, sample_image_bytes):
    """English text must call TTS with en-US language code."""
    client.post(
        "/process/text",
        files={"image": ("test.jpg", sample_image_bytes, "image/jpeg")},
        data={"text": "draw in picasso style"},
    )
    _, kwargs = mock_tts.call_args
    assert kwargs.get("language_code") == "en-US"


@patch("src.main.generate_speech_base64", return_value=None)
@patch("src.main.process_image", return_value=FAKE_PROCESS_RESULT)
@patch("src.main.upload_image", return_value=FAKE_URL)
def test_process_text_tts_failure_still_succeeds(mock_upload, mock_process, mock_tts, sample_image_bytes):
    """TTS failure (returns None) must not break the endpoint."""
    response = client.post(
        "/process/text",
        files={"image": ("test.jpg", sample_image_bytes, "image/jpeg")},
        data={"text": "estilo van gogh"},
    )
    assert response.status_code == 200
    assert response.json()["audio_base64"] is None


@patch("src.main.process_image", side_effect=Exception("vision error"))
@patch("src.main.upload_image", return_value=FAKE_URL)
def test_process_text_error(mock_upload, mock_process, sample_image_bytes):
    response = client.post(
        "/process/text",
        files={"image": ("test.jpg", sample_image_bytes, "image/jpeg")},
        data={"text": "estilo monet"},
    )
    assert response.status_code == 500


def test_process_text_invalid_mime(sample_image_bytes):
    """Non-image MIME type must be rejected with 415."""
    response = client.post(
        "/process/text",
        files={"image": ("doc.pdf", sample_image_bytes, "application/pdf")},
        data={"text": "estilo picasso"},
    )
    assert response.status_code == 415


def test_upload_invalid_mime(sample_image_bytes):
    """Non-image upload must be rejected with 415."""
    response = client.post(
        "/upload",
        files={"file": ("data.csv", sample_image_bytes, "text/csv")},
    )
    assert response.status_code == 415


def test_upload_oversized_file():
    """Files larger than 10 MB must be rejected with 413."""
    big_file = b"x" * (10 * 1024 * 1024 + 1)
    response = client.post(
        "/upload",
        files={"file": ("big.jpg", big_file, "image/jpeg")},
    )
    assert response.status_code == 413


# ---------------------------------------------------------------------------
# History
# ---------------------------------------------------------------------------

@patch("src.main.get_history", return_value=FAKE_HISTORY)
def test_fetch_history_returns_list(mock_get):
    response = client.get("/history")
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    assert len(body) == 1
    assert body[0]["style"] == "picasso"
    mock_get.assert_called_once_with(limit=12)


@patch("src.main.get_history", return_value=FAKE_HISTORY)
def test_fetch_history_limit_param(mock_get):
    response = client.get("/history?limit=5")
    assert response.status_code == 200
    mock_get.assert_called_once_with(limit=5)


@patch("src.main.get_history", side_effect=Exception("Firestore down"))
def test_fetch_history_error(mock_get):
    response = client.get("/history")
    assert response.status_code == 500


@patch("src.main.delete_from_history", return_value=None)
def test_delete_history_item_success(mock_delete):
    response = client.delete("/history/abc123")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    mock_delete.assert_called_once_with("abc123")


@patch("src.main.delete_from_history", side_effect=Exception("Firestore down"))
def test_delete_history_item_error(mock_delete):
    response = client.delete("/history/nonexistent")
    assert response.status_code == 500
