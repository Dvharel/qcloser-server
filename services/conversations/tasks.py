import logging
from datetime import timedelta

from celery import shared_task
from celery.exceptions import MaxRetriesExceededError
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone
from rest_framework.response import Response
from rest_framework import status

from .models import CallRecording, NotificationDelivery
from .transcription_service import poll_transcription, format_speaker_transcript
from .ai_client import (
    analyze_via_ai_service,
    feedback_via_ai_service,
    generate_followup_via_ai_service,
)
from .email_builders import build_analysis_email, build_feedback_email, build_followup_email

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_delivery(self, delivery_id: int):
    with transaction.atomic():
        try:
            delivery = (
                NotificationDelivery.objects
                .select_for_update(skip_locked=True)
                .select_related("recording")
                .filter(
                    id=delivery_id,
                    status__in=[
                        NotificationDelivery.Status.PENDING,
                        NotificationDelivery.Status.RETRYING,
                    ],
                )
                .get()
            )
        except NotificationDelivery.DoesNotExist:
            # Row is locked by another worker, already SENT/FAILED, or doesn't exist.
            return

        delivery.status = NotificationDelivery.Status.RETRYING
        delivery.attempts += 1
        delivery.last_attempt_at = timezone.now()
        delivery.save(update_fields=["status", "attempts", "last_attempt_at", "updated_at"])

    try:
        kind = delivery.kind
        if kind == NotificationDelivery.Kind.ANALYSIS:
            subject, body = build_analysis_email(delivery.recording)
        elif kind == NotificationDelivery.Kind.FEEDBACK:
            subject, body = build_feedback_email(delivery.recording)
        elif kind == NotificationDelivery.Kind.FOLLOWUP:
            subject, body = build_followup_email(delivery.recording)
        else:
            raise ValueError(f"Unknown delivery kind: {kind}")
        delivery.subject = subject
        delivery.body = body
        delivery.save(update_fields=["subject", "body", "updated_at"])

        send_mail(
            subject=subject,
            message=body,
            from_email=None,  # uses DEFAULT_FROM_EMAIL
            recipient_list=[delivery.salesperson_email],
            fail_silently=False,
        )

        delivery.status = NotificationDelivery.Status.SENT
        delivery.sent_at = timezone.now()
        delivery.save(update_fields=["status", "sent_at", "updated_at"])

    except ValueError as exc:
        # Data problem — retrying won't fix it.
        logger.error("send_delivery [%s]: data error, will not retry — %s", delivery_id, exc)
        delivery.status = NotificationDelivery.Status.FAILED
        delivery.last_error = str(exc)
        delivery.save(update_fields=["status", "last_error", "updated_at"])

    except Exception as exc:
        # Transient error — keep RETRYING so the next attempt can pick it up.
        # Only mark FAILED once max retries are exhausted.
        logger.error("send_delivery [%s]: transient error, will retry — %s", delivery_id, exc)
        delivery.last_error = str(exc)
        delivery.save(update_fields=["last_error", "updated_at"])
        try:
            raise self.retry(exc=exc)
        except MaxRetriesExceededError:
            delivery.status = NotificationDelivery.Status.FAILED
            delivery.save(update_fields=["status", "updated_at"])


@shared_task
def sweep_stuck_deliveries():
    cutoff = timezone.now() - timedelta(minutes=10)
    stuck = NotificationDelivery.objects.filter(
        status__in=[
            NotificationDelivery.Status.PENDING,
            NotificationDelivery.Status.RETRYING,
        ],
        updated_at__lt=cutoff,
    )
    ids = list(stuck.values_list("id", flat=True))
    for delivery_id in ids:
        send_delivery.delay(delivery_id)
    if ids:
        logger.info("sweep_stuck_deliveries: re-queued %d stuck delivery(ies): %s", len(ids), ids)
    else:
        logger.debug("sweep_stuck_deliveries: no stuck deliveries found")


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

            if rec.salesperson_email:
                delivery = None
                try:
                    delivery, _ = NotificationDelivery.objects.get_or_create(
                        recording=rec,
                        kind=NotificationDelivery.Kind.FEEDBACK,
                        defaults={
                            "channel": NotificationDelivery.Channel.EMAIL,
                            "salesperson_email": rec.salesperson_email,
                            "status": NotificationDelivery.Status.PENDING,
                        },
                    )
                except Exception as e:
                    logger.error(
                        "Failed to create NotificationDelivery for recording %s: %s",
                        rec.id, e,
                    )
                if delivery is not None:
                    try:
                        send_delivery.delay(delivery.id)
                    except Exception as e:
                        logger.error(
                            "Failed to enqueue send_delivery for delivery %s (recording %s): %s",
                            delivery.id, rec.id, e,
                        )

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
                recording_id=rec.id,
                transcript=rec.transcript,
                deal_title=rec.deal_title,
                analysis_json=rec.analysis_json,
                language=rec.language,
            )

            rec.followup_json = out
            rec.status = CallRecording.Status.FOLLOWUP_READY
            rec.save(update_fields=["followup_json", "status"])

            if rec.salesperson_email:
                delivery = None
                try:
                    delivery, _ = NotificationDelivery.objects.get_or_create(
                        recording=rec,
                        kind=NotificationDelivery.Kind.FOLLOWUP,
                        defaults={
                            "channel": NotificationDelivery.Channel.EMAIL,
                            "salesperson_email": rec.salesperson_email,
                            "status": NotificationDelivery.Status.PENDING,
                        },
                    )
                except Exception as e:
                    logger.error(
                        "Failed to create NotificationDelivery for recording %s: %s",
                        rec.id, e,
                    )
                if delivery is not None:
                    try:
                        send_delivery.delay(delivery.id)
                    except Exception as e:
                        logger.error(
                            "Failed to enqueue send_delivery for delivery %s (recording %s): %s",
                            delivery.id, rec.id, e,
                        )

        except Exception as e:
            rec.status = CallRecording.Status.FAILED
            rec.error_stage = "followup"
            rec.error_message = str(e)
            rec.save(update_fields=["status", "error_stage", "error_message"])
            return

    rec.status = CallRecording.Status.DONE
    rec.save(update_fields=["status"])
