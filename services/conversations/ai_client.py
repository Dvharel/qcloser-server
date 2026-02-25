import os
import requests
from django.conf import settings

AI_URL = getattr(settings, "AI_SERVICE_URL", "http://ai:8001").rstrip("/")
AI_TOKEN = getattr(settings, "AI_SERVICE_TOKEN", "")


def _headers():
    h = {"Content-Type": "application/json"}
    token = getattr(settings, "AI_SERVICE_TOKEN", None)
    if token:
        h["X-AI-Token"] = token.strip()
    return h


def analyze_via_ai_service(
    *, transcript: str, language: str, deal_title: str, recording_id: int
):
    payload = {
        "recording_id": recording_id,
        "transcript": transcript,
        "language": language or "auto",
        "deal_title": deal_title,
    }
    r = requests.post(
        f"{AI_URL}/analyze", json=payload, headers=_headers(), timeout=120
    )
    r.raise_for_status()
    return r.json()


def feedback_via_ai_service(
    *,
    transcript: str,
    language: str,
    deal_title: str,
    recording_id: int,
    analysis_json: dict | None = None,
):
    payload = {
        "transcript": transcript,
        "language": language or "auto",
        "deal_title": deal_title,
        "recording_id": recording_id,
        "analysis_json": analysis_json,
    }
    r = requests.post(
        f"{AI_URL}/feedback", json=payload, headers=_headers(), timeout=120
    )
    r.raise_for_status()
    return r.json()


def generate_followup_via_ai_service(
    *,
    recording_id: int,
    transcript: str,
    deal_title: str,
    analysis_json: dict | str,
    language: str = "auto",
    channel: str = "whatsapp",
    tone: str = "friendly",
) -> dict:
    """
    Calls FastAPI /followup and returns JSON.
    """
    payload = {
        "recording_id": recording_id,
        "transcript": transcript,
        "deal_title": deal_title,
        "analysis_json": analysis_json,
        "language": language,
        "channel": channel,
        "tone": tone,
    }

    r = requests.post(
        f"{AI_URL}/followup",
        json=payload,
        headers=_headers(),
        timeout=120,
    )
    r.raise_for_status()
    return r.json()
