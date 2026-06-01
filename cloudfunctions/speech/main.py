import os
import base64
import functions_framework
import firebase_admin
from firebase_admin import auth as firebase_auth
from google.cloud import speech, texttospeech
from flask import make_response, jsonify

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "proyectosm-494910")

try:
    firebase_admin.initialize_app()
except ValueError:
    pass  # already initialized

_speech_client = None
_tts_client = None

SUPPORTED_STYLES = [
    "picasso", "van gogh", "monet", "dali", "dalí",
    "warhol", "rembrandt", "matisse", "kandinsky",
    "manga", "boceto", "graffiti", "minimalista",
    "disney", "cyberpunk", "tribal", "caricatura",
    "gótico", "gotico", "puntillismo", "expresionismo",
    "realista", "low poly", "steampunk", "ukiyo-e",
]

_TTS_VOICES = {
    "es-ES": "es-ES-Journey-F",
    "en-US": "en-US-Journey-F",
}

_ES_MARKERS = set("áéíóúüñ¿¡")
_ES_WORDS = {"estilo", "como", "haz", "dibuja", "quiero", "una", "imagen", "con", "para", "que"}

_CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, Authorization",
}


def _get_speech_client():
    global _speech_client
    if _speech_client is None:
        _speech_client = speech.SpeechClient()
    return _speech_client


def _get_tts_client():
    global _tts_client
    if _tts_client is None:
        _tts_client = texttospeech.TextToSpeechClient()
    return _tts_client


def _cors(response):
    for k, v in _CORS_HEADERS.items():
        response.headers[k] = v
    return response


def _verify_token(req):
    header = req.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        return None, _cors(make_response(jsonify({"error": "Unauthorized"}), 401))
    token = header.split(" ", 1)[1]
    try:
        decoded = firebase_auth.verify_id_token(token)
        return decoded["uid"], None
    except Exception:
        return None, _cors(make_response(jsonify({"error": "Invalid token"}), 401))


def _detect_language(text: str) -> str:
    lower = text.lower()
    if any(c in _ES_MARKERS for c in lower):
        return "es-ES"
    if any(w in lower.split() for w in _ES_WORDS):
        return "es-ES"
    return "en-US"


def _extract_style(text: str) -> str:
    lower = text.lower()
    for style in SUPPORTED_STYLES:
        if style in lower:
            return style
    return "default"


@functions_framework.http
def speech_handler(request):
    if request.method == "OPTIONS":
        return _cors(make_response("", 204))

    uid, err = _verify_token(request)
    if err:
        return err

    if request.method != "POST":
        return _cors(make_response(jsonify({"error": "Method not allowed"}), 405))

    action = request.args.get("action", "")

    if action == "transcribe":
        file = request.files.get("audio")
        if not file:
            return _cors(make_response(jsonify({"error": "No audio file provided"}), 400))

        audio_bytes = file.read()
        try:
            audio = speech.RecognitionAudio(content=audio_bytes)
            config = speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.WEBM_OPUS,
                language_code="es-ES",
                alternative_language_codes=["en-US"],
            )
            response = _get_speech_client().recognize(config=config, audio=audio)
            transcript = response.results[0].alternatives[0].transcript if response.results else ""
        except Exception as e:
            return _cors(make_response(jsonify({"error": f"Transcription failed: {e}"}), 500))

        style = _extract_style(transcript)
        return _cors(make_response(jsonify({"transcript": transcript, "style": style}), 200))

    if action == "tts":
        data = request.get_json(silent=True) or {}
        text = data.get("text", "").strip()
        if not text:
            return _cors(make_response(jsonify({"error": "No text provided"}), 400))

        language_code = data.get("language_code") or _detect_language(text)
        voice_name = _TTS_VOICES.get(language_code, _TTS_VOICES["es-ES"])

        try:
            response = _get_tts_client().synthesize_speech(
                input=texttospeech.SynthesisInput(text=text),
                voice=texttospeech.VoiceSelectionParams(
                    language_code=language_code,
                    name=voice_name,
                ),
                audio_config=texttospeech.AudioConfig(
                    audio_encoding=texttospeech.AudioEncoding.MP3
                ),
            )
            audio_b64 = base64.b64encode(response.audio_content).decode("utf-8")
        except Exception as e:
            return _cors(make_response(jsonify({"error": f"TTS failed: {e}"}), 500))

        return _cors(make_response(jsonify({"audio_base64": audio_b64}), 200))

    return _cors(make_response(jsonify({"error": "Unknown action. Use ?action=transcribe or ?action=tts"}), 400))
