import os
from google.cloud import speech
from dotenv import load_dotenv

load_dotenv()

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "proyectosm-494910")

SUPPORTED_STYLES = [
    "picasso", "van gogh", "monet", "dali",
    "warhol", "rembrandt", "matisse", "kandinsky"
]

def get_client():
    return speech.SpeechClient()

def transcribe_audio(audio_bytes: bytes, language_code: str = "es-ES") -> str:
    """
    Transcribe audio bytes to text using Cloud Speech-to-Text.
    Returns the transcribed text.
    """
    client = get_client()
    audio = speech.RecognitionAudio(content=audio_bytes)
    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=16000,
        language_code=language_code,
        alternative_language_codes=["en-US"],
    )
    response = client.recognize(config=config, audio=audio)
    if not response.results:
        return ""
    return response.results[0].alternatives[0].transcript

def extract_style(text: str) -> str:
    """
    Extract artistic style from transcribed text.
    Falls back to "default" if no style found.
    """
    text_lower = text.lower()
    for style in SUPPORTED_STYLES:
        if style in text_lower:
            return style
    return "default"

def process_voice_command(audio_bytes: bytes) -> dict:
    """
    Full pipeline: audio -> transcription -> style extraction.
    Returns dict with transcript and extracted style.
    """
    transcript = transcribe_audio(audio_bytes)
    style = extract_style(transcript)
    return {
        "transcript": transcript,
        "style": style
    }