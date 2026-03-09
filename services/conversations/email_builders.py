import json

from .models import CallRecording


def build_analysis_email(recording: CallRecording) -> tuple[str, str]:
    subject = f"Call Analysis Ready — {recording.deal_title or f'Recording #{recording.id}'}"
    body = (recording.analysis_json or {}).get("analysis_text", "")
    if not body:
        raise ValueError(
            f"analysis_text is empty or missing for recording {recording.id}"
        )
    return subject, body


def build_feedback_email(recording: CallRecording) -> tuple[str, str]:
    if not recording.feedback_json:
        raise ValueError(f"feedback_json is empty or missing for recording {recording.id}")
    subject = f"{recording.deal_title} — Feedback"
    body = json.dumps(recording.feedback_json, ensure_ascii=False)
    return subject, body


def build_followup_email(recording: CallRecording) -> tuple[str, str]:
    if not recording.followup_json:
        raise ValueError(f"followup_json is empty or missing for recording {recording.id}")
    subject = f"{recording.deal_title} — Follow-up"
    body = json.dumps(recording.followup_json, ensure_ascii=False)
    return subject, body
