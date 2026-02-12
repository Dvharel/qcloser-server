import os
import time
import requests
from django.conf import settings

BASE_URL = getattr(settings, "ASSEMBLYAI_BASE_URL", "https://api.assemblyai.com").rstrip("/")
HEADERS = {"Authorization": settings.ASSEMBLYAI_API_KEY}


class AssemblyAIError(RuntimeError):
    pass


def _upload_local_file(file_path: str) -> str:
    """
    Uploads a local file to AssemblyAI and returns an upload_url.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Audio file not found at: {file_path}")

    with open(file_path, "rb") as f:
        resp = requests.post(
            f"{BASE_URL}/v2/upload",
            headers={**HEADERS, "Content-Type": "application/octet-stream"},
            data=f,
            timeout=120,
        )
    resp.raise_for_status()
    data = resp.json()
    upload_url = data.get("upload_url")
    if not upload_url:
        raise AssemblyAIError(f"Upload succeeded but no upload_url returned: {data}")
    return upload_url


def submit_transcription(recording, language=None) -> dict:
    """
    Async step 1: submit a transcription job.
    - Local disk today: upload to AssemblyAI, then submit using upload_url
    - MVP later: pass S3 public URL directly and skip upload
    Returns: {"id": "...", "status": "..."}
    """
    # TODAY: local file path
    audio_source = recording.audio_file.path

    # Later in the MVP if we have a public URL (S3), I can do:
    # audio_url = recording.audio_file.url
    # and skip upload.

    upload_url = _upload_local_file(audio_source)

    payload = {
        "audio_url": upload_url,
        "speaker_labels": True,           # enables speaker diarization :contentReference[oaicite:1]{index=1}
        "language_detection": True,       # default-ish; keep it on for POC :contentReference[oaicite:2]{index=2}
        "speech_models": ["universal-3-pro", "universal-2"],  # example from docs :contentReference[oaicite:3]{index=3}
    }

    # Optional: if you *really* want to force language instead of detection:
    # AssemblyAI supports language config; for POC you said auto is fine.

    resp = requests.post(f"{BASE_URL}/v2/transcript", headers=HEADERS, json=payload, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    if "id" not in data:
        raise AssemblyAIError(f"Unexpected submit response: {data}")

    return {"id": data["id"], "status": data.get("status", "queued")}


def poll_transcription(transcript_id: str) -> dict:
    """
    Async step 2: poll transcript status.
    Returns full transcript JSON when completed, or status if still processing.
    """
    resp = requests.get(f"{BASE_URL}/v2/transcript/{transcript_id}", headers=HEADERS, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    status = data.get("status")
    if status == "error":
        # docs: status=error includes an error message :contentReference[oaicite:4]{index=4}
        raise AssemblyAIError(f"Transcription failed: {data.get('error')}")

    return data


def format_speaker_transcript(transcript_json: dict) -> str:
    """
    Converts AssemblyAI utterances to readable text like:
    Speaker A: ...
    Speaker B: ...
    """
    utterances = transcript_json.get("utterances") or []
    lines = []
    for u in utterances:
        speaker = u.get("speaker")
        text = (u.get("text") or "").strip()
        if text:
            lines.append(f"{speaker}: {text}")
    return "\n".join(lines).strip()
