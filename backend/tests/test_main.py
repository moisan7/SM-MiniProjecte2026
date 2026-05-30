from unittest.mock import patch
from fastapi.testclient import TestClient
from src.main import app, _verify_firebase_token

# Override Firebase auth so tests don't need a real token
app.dependency_overrides[_verify_firebase_token] = lambda: "test-uid"

client = TestClient(app)

FAKE_URL = "https://storage.googleapis.com/dal-i-bucket/images/fake.jpg"
FAKE_COORDS = [{"x": 10.0, "y": 20.0}, {"x": 30.0, "y": 40.0}]
FAKE_PROCESS_RESULT = {
    "style_description": "Bold lines, fragmented shapes in Picasso style.",
    "coordinates": FAKE_COORDS,
    "total_points": 2,
    "style_transfer_ok": True,
}


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["project_id"] == "proyectosm-494910"

def test_process_text_no_image():
    response = client.post("/process/text", data={"text": "estilo Picasso"})
    assert response.status_code == 422
    assert "detail" in response.json()


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
    response = client.post(
        "/process/text",
        files={"image": ("doc.pdf", sample_image_bytes, "application/pdf")},
        data={"text": "estilo picasso"},
    )
    assert response.status_code == 415
