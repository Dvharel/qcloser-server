from .models import CallRecording


def build_analysis_email(recording: CallRecording) -> tuple[str, str]:
    subject = f"Call Analysis Ready — {recording.deal_title or f'Recording #{recording.id}'}"
    body = (recording.analysis_json or {}).get("analysis_text", "")
    if not body:
        raise ValueError(
            f"analysis_text is empty or missing for recording {recording.id}"
        )
    return subject, body
