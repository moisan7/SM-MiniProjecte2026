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
_translate_client = None

SUPPORTED_STYLES = [
    "picasso", "van gogh", "monet", "dali", "dalí",
    "warhol", "rembrandt", "matisse", "kandinsky",
    "manga", "boceto", "graffiti", "minimalista",
    "disney", "cyberpunk", "tribal", "caricatura",
    "gótico", "gotico", "puntillismo", "expresionismo",
    "realista", "low poly", "steampunk", "ukiyo-e",
]

SUPPORTED_LANGUAGES = {
    "es-ES": {"name": "Español",   "voice": "es-ES-Journey-F"},
    "en-US": {"name": "English",   "voice": "en-US-Journey-F"},
    "fr-FR": {"name": "Français",  "voice": "fr-FR-Journey-F"},
    "de-DE": {"name": "Deutsch",   "voice": "de-DE-Journey-F"},
    "it-IT": {"name": "Italiano",  "voice": "it-IT-Journey-F"},
    "pt-BR": {"name": "Português", "voice": "pt-BR-Journey-F"},
    "ca-ES": {"name": "Català",    "voice": "ca-ES-Standard-A"},
    "ja-JP": {"name": "日本語",     "voice": "ja-JP-Journey-F"},
    "zh-CN": {"name": "中文",       "voice": "cmn-CN-Wavenet-A"},
    "ar-XA": {"name": "العربية",   "voice": "ar-XA-Wavenet-A"},
}

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


def _get_translate_client():
    global _translate_client
    if _translate_client is None:
        from google.cloud import translate_v2
        _translate_client = translate_v2.Client()
    return _translate_client


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


def _translate_to_english(text: str, source_language: str) -> str:
    """Translate text from source_language to English. Returns original on failure."""
    if not text or source_language.startswith("en"):
        return text
    try:
        src = source_language.split("-")[0]
        result = _get_translate_client().translate(text, target_language="en", source_language=src)
        return result["translatedText"]
    except Exception:
        return text


def _translate_from_english(text: str, target_language: str) -> str:
    """Translate text from English to target_language. Returns original on failure."""
    if not text or target_language.startswith("en"):
        return text
    try:
        tgt = target_language.split("-")[0]
        result = _get_translate_client().translate(text, target_language=tgt, source_language="en")
        return result["translatedText"]
    except Exception:
        return text


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

    # ── Transcribe ──────────────────────────────────────────────────────────────
    if action == "transcribe":
        language = request.args.get("language", "es-ES")
        if language not in SUPPORTED_LANGUAGES:
            language = "es-ES"

        file = request.files.get("audio")
        if not file:
            return _cors(make_response(jsonify({"error": "No audio file provided"}), 400))

        audio_bytes = file.read()
        try:
            audio = speech.RecognitionAudio(content=audio_bytes)
            alt_langs = [] if language.startswith("en") else ["en-US"]
            config = speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.WEBM_OPUS,
                language_code=language,
                alternative_language_codes=alt_langs,
            )
            response = _get_speech_client().recognize(config=config, audio=audio)
            transcript = response.results[0].alternatives[0].transcript if response.results else ""
        except Exception as e:
            return _cors(make_response(jsonify({"error": f"Transcription failed: {e}"}), 500))

        # Translate transcript to English for style extraction
        transcript_en = _translate_to_english(transcript, language)
        style = _extract_style(transcript_en)

        return _cors(make_response(jsonify({
            "transcript": transcript,   # original language for display
            "style": style,
        }), 200))

    # ── Text-to-Speech ──────────────────────────────────────────────────────────
    if action == "tts":
        data = request.get_json(silent=True) or {}
        text = data.get("text", "").strip()
        if not text:
            return _cors(make_response(jsonify({"error": "No text provided"}), 400))

        language = data.get("language", "es-ES")
        if language not in SUPPORTED_LANGUAGES:
            language = "es-ES"

        # Translate English text to target language
        translated = _translate_from_english(text, language)

        lang_info = SUPPORTED_LANGUAGES[language]
        try:
            response = _get_tts_client().synthesize_speech(
                input=texttospeech.SynthesisInput(text=translated),
                voice=texttospeech.VoiceSelectionParams(
                    language_code=language,
                    name=lang_info["voice"],
                ),
                audio_config=texttospeech.AudioConfig(
                    audio_encoding=texttospeech.AudioEncoding.MP3
                ),
            )
            audio_b64 = base64.b64encode(response.audio_content).decode("utf-8")
        except Exception as e:
            return _cors(make_response(jsonify({"error": f"TTS failed: {e}"}), 500))

        return _cors(make_response(jsonify({
            "audio_base64": audio_b64,
            "translated_text": translated,
        }), 200))

    # ── Translate ───────────────────────────────────────────────────────────────
    if action == "translate":
        data = request.get_json(silent=True) or {}
        text = data.get("text", "").strip()
        source = data.get("source_language", "en-US")
        target = data.get("target_language", "en-US")

        if not text:
            return _cors(make_response(jsonify({"error": "No text provided"}), 400))

        if source == target or source.split("-")[0] == target.split("-")[0]:
            return _cors(make_response(jsonify({"translated_text": text}), 200))

        try:
            src = source.split("-")[0]
            tgt = target.split("-")[0]
            result = _get_translate_client().translate(text, target_language=tgt, source_language=src)
            translated = result["translatedText"]
        except Exception as e:
            translated = text  # graceful fallback

        return _cors(make_response(jsonify({"translated_text": translated}), 200))

    return _cors(make_response(jsonify({
        "error": "Unknown action. Use ?action=transcribe, ?action=tts, or ?action=translate"
    }), 400))
