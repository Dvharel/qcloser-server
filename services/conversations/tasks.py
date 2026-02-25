from celery import shared_task
from django.utils import timezone
from rest_framework.response import Response
from rest_framework import status

from .models import CallRecording
from .transcription_service import poll_transcription, format_speaker_transcript
from .ai_client import (
    analyze_via_ai_service,
    feedback_via_ai_service,
    generate_followup_via_ai_service,
)


@shared_task(bind=True, max_retries=20, default_retry_delay=10)
def poll_transcription_until_done(self, recording_id: int):
    rec = CallRecording.objects.get(id=recording_id)

    if not rec.transcription_job_id:
        return Response(
            {
                "detail": "Error in poll_transcription_until_done -> No transcript found. Run transcript first."
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    data = poll_transcription(rec.transcription_job_id)
    st = data.get("status")

    if st in ("queued", "processing"):
        raise self.retry()

    if st == "completed":
        rec.transcript_json = data
        rec.transcript = (
            format_speaker_transcript(data) or (data.get("text") or "").strip()
        )
        rec.status = CallRecording.Status.TRANSCRIBED
        rec.save(update_fields=["transcript_json", "transcript", "status"])

        run_langgraph_pipeline.delay(rec.id)
        return

    # error case
    rec.status = CallRecording.Status.FAILED
    rec.error_stage = "transcription"
    rec.error_message = str(data)
    rec.save(update_fields=["status", "error_stage", "error_message"])


@shared_task
def run_langgraph_pipeline(recording_id: int):
    rec = CallRecording.objects.get(id=recording_id)

    # -------- ANALYZE (idempotent) --------
    if not rec.analysis_json:
        try:
            rec.status = CallRecording.Status.ANALYZING
            rec.save(update_fields=["status"])

            out = analyze_via_ai_service(
                transcript=rec.transcript,
                language=rec.language,
                deal_title=rec.deal_title,
                recording_id=rec.id,
            )

            rec.analysis_json = out["analysis_json"]
            rec.status = CallRecording.Status.ANALYZED
            rec.save(update_fields=["analysis_json", "status"])

        except Exception as e:
            rec.status = CallRecording.Status.FAILED
            rec.error_stage = "analyze"
            rec.error_message = str(e)
            rec.save(update_fields=["status", "error_stage", "error_message"])
            return

    # -------- FEEDBACK (idempotent, failure doesn't stop followup) --------
    if not rec.feedback_json:
        try:
            rec.status = CallRecording.Status.GENERATING_FEEDBACK
            rec.save(update_fields=["status"])

            out = feedback_via_ai_service(
                transcript=rec.transcript,
                analysis_json=rec.analysis_json,
                language=rec.language,
                recording_id=rec.id,
            )

            rec.feedback_json = out["feedback_json"]
            rec.status = CallRecording.Status.FEEDBACK_READY
            rec.save(update_fields=["feedback_json", "status"])

        except Exception as e:
            # log error but continue
            rec.error_stage = "feedback"
            rec.error_message = str(e)
            rec.save(update_fields=["error_stage", "error_message"])

    # -------- FOLLOWUP (idempotent) --------
    if not rec.followup_json:
        try:
            rec.status = CallRecording.Status.GENERATING_FOLLOWUP
            rec.save(update_fields=["status"])

            out = generate_followup_via_ai_service(
                rec.org_id,
                recording_id=rec.id,
                transcript=rec.transcript,
                analysis_json=rec.analysis_json,
                feedback_json=rec.feedback_json,
                language=rec.language,
                recording_id=rec.id,
            )

            rec.followup_json = out
            rec.status = CallRecording.Status.FOLLOWUP_READY
            rec.save(update_fields=["followup_json"])

        except Exception as e:
            rec.status = CallRecording.Status.FAILED
            rec.error_stage = "followup"
            rec.error_message = str(e)
            rec.save(update_fields=["status", "error_stage", "error_message"])
            return

    rec.status = CallRecording.Status.DONE
    rec.save(update_fields=["status"])
