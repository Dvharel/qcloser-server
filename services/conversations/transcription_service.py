import os
import time
import requests
import boto3
from botocore.config import Config
from django.conf import settings

BASE_URL = getattr(
    settings, "ASSEMBLYAI_BASE_URL", "https://api.assemblyai.com"
).rstrip("/")
HEADERS = {"Authorization": settings.ASSEMBLYAI_API_KEY}
if not settings.ASSEMBLYAI_API_KEY:
    raise RuntimeError("ASSEMBLYAI_API_KEY is missing from environment")


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


def _generate_s3_presigned_url(s3_key: str, expiry: int) -> str:
    """
    Generate a pre-signed GET URL for a private S3 object.
    AssemblyAI will use this URL to fetch the audio directly from S3.
    """
    client = boto3.client(
        "s3",
        region_name=settings.AWS_S3_REGION_NAME,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        config=Config(signature_version="s3v4"),
    )
    return client.generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.AWS_STORAGE_BUCKET_NAME, "Key": s3_key},
        ExpiresIn=expiry,
    )


def submit_transcription(recording, language_code=None) -> dict:
    """
    Async step 1: submit a transcription job.
    - S3 mode: generate a pre-signed URL and pass it directly to AssemblyAI.
    - Local mode: upload file bytes to AssemblyAI, then submit with the upload_url.
    Returns: {"id": "...", "status": "..."}
    """
    if getattr(settings, "USE_S3", False):
        expiry = getattr(settings, "AWS_S3_PRESIGNED_EXPIRY", 3600)
        audio_url = _generate_s3_presigned_url(recording.audio_file.name, expiry)
    else:
        audio_url = _upload_local_file(recording.audio_file.path)

    payload = {
        "audio_url": audio_url,
        "speaker_labels": True,
    }

    # Optional: if you *really* want to force language instead of detection:
    # AssemblyAI supports language config; for POC you said auto is fine.

    if language_code:
        payload["language_code"] = language_code
    else:
        payload["language_detection"] = True

    resp = requests.post(
        f"{BASE_URL}/v2/transcript",
        headers=HEADERS,
        json=payload,
        timeout=30,
    )
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
    resp = requests.get(
        f"{BASE_URL}/v2/transcript/{transcript_id}", headers=HEADERS, timeout=30
    )
    resp.raise_for_status()
    data = resp.json()

    status = data.get("status")
    if status == "error":
        # docs: status=error includes an error message :contentReference[oaicite:4]{index=4}
        raise AssemblyAIError(f"Transcription failed: {data.get('error')}")

    return data


def format_speaker_transcript(transcript_json: dict) -> str:
    utterances = transcript_json.get("utterances") or []
    if not utterances:
        # fallback: return plain transcript text if no diarization
        return (transcript_json.get("text") or "").strip()

    lines = []
    for u in utterances:
        speaker = u.get("speaker")
        text = (u.get("text") or "").strip()
        if text:
            lines.append(f"Speaker {speaker}: {text}")
    return "\n".join(lines).strip()


def compact_utterances(transcript_json: dict) -> list:
    """
    Return utterances without word-level details (keeps response small).
    """
    utterances = transcript_json.get("utterances") or []
    compact = []
    for u in utterances:
        compact.append(
            {
                "speaker": u.get("speaker"),
                "text": u.get("text"),
                "start": u.get("start"),
                "end": u.get("end"),
                "confidence": u.get("confidence"),
            }
        )
    return compact
