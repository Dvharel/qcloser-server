from django.conf import settings
from openai import OpenAI
import os

client = OpenAI(api_key=settings.OPENAI_API_KEY)


def transcribe_call_recording(recording, language=None):
    """
    Transcribe a call recording using Whisper.
    language can be: "he", "en", or None for auto-detect.
    """
    file_path = recording.audio_file.path
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Audio file not found at: {file_path}")

    with open(file_path, "rb") as f:
        params = {
            "model": "whisper-1",
            "file": f,
        }

        if language in ("he", "en"):
            params["language"] = language

        response = client.audio.transcriptions.create(**params)

    return response.text.strip()
