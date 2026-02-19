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
    transcript: str, language: str = "auto", deal_title: str | None = None
):
    payload = {"transcript": transcript, "language": language, "deal_title": deal_title}
    r = requests.post(
        f"{AI_URL}/analyze", json=payload, headers=_headers(), timeout=120
    )
    r.raise_for_status()
    return r.json()


def ai_generate_followup(
    transcript: str, analysis: dict, channel="whatsapp", tone="neutral", language="auto"
):
    payload = {
        "transcript": transcript,
        "analysis": analysis,
        "channel": channel,
        "tone": tone,
        "language": language,
    }
    r = requests.post(
        f"{AI_URL}/generate_followup", json=payload, headers=_headers(), timeout=120
    )
    r.raise_for_status()
    return r.json()
