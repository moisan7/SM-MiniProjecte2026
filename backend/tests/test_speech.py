from unittest.mock import patch, MagicMock
from src.speech import extract_style, transcribe_audio, process_voice_command


# ---------------------------------------------------------------------------
# extract_style — pure logic, no GCP calls
# ---------------------------------------------------------------------------

def test_extract_style_picasso():
    assert extract_style("draw this in picasso style") == "picasso"

def test_extract_style_vangogh():
    assert extract_style("I want van gogh style please") == "van gogh"

def test_extract_style_monet():
    assert extract_style("make it like monet") == "monet"

def test_extract_style_default():
    assert extract_style("just draw something") == "default"

def test_extract_style_case_insensitive():
    assert extract_style("PICASSO style please") == "picasso"

def test_extract_style_empty():
    assert extract_style("") == "default"

def test_extract_style_first_match_wins():
    result = extract_style("picasso and monet together")
    assert result in ("picasso", "monet")


# ---------------------------------------------------------------------------
# transcribe_audio — mock SpeechClient
# ---------------------------------------------------------------------------

def _make_recognition_response(transcript: str):
    alternative = MagicMock()
    alternative.transcript = transcript
    result = MagicMock()
    result.alternatives = [alternative]
    response = MagicMock()
    response.results = [result]
    return response


@patch("src.speech.speech.SpeechClient")
def test_transcribe_audio_returns_transcript(MockClient, sample_audio_bytes):
    mock_client = MagicMock()
    MockClient.return_value = mock_client
    mock_client.recognize.return_value = _make_recognition_response("draw in picasso style")

    result = transcribe_audio(sample_audio_bytes)

    assert result == "draw in picasso style"
    mock_client.recognize.assert_called_once()


@patch("src.speech.speech.SpeechClient")
def test_transcribe_audio_empty_response(MockClient, sample_audio_bytes):
    mock_client = MagicMock()
    MockClient.return_value = mock_client
    response = MagicMock()
    response.results = []
    mock_client.recognize.return_value = response

    result = transcribe_audio(sample_audio_bytes)

    assert result == ""


# ---------------------------------------------------------------------------
# process_voice_command — full pipeline with mock
# ---------------------------------------------------------------------------

@patch("src.speech.speech.SpeechClient")
def test_process_voice_command_known_style(MockClient, sample_audio_bytes):
    mock_client = MagicMock()
    MockClient.return_value = mock_client
    mock_client.recognize.return_value = _make_recognition_response("I want van gogh style")

    result = process_voice_command(sample_audio_bytes)

    assert result["transcript"] == "I want van gogh style"
    assert result["style"] == "van gogh"


@patch("src.speech.speech.SpeechClient")
def test_process_voice_command_unknown_style(MockClient, sample_audio_bytes):
    mock_client = MagicMock()
    MockClient.return_value = mock_client
    mock_client.recognize.return_value = _make_recognition_response("draw something nice")

    result = process_voice_command(sample_audio_bytes)

    assert result["style"] == "default"
