from django.db import models

from services.accounts.models import Organization, User


class CallRecording(models.Model):
    class Status(models.TextChoices):
        WAITING_TRANSCRIPTION = "waiting_transcription"
        TRANSCRIBING = "transcribing"
        TRANSCRIBED = "transcribed"
        ANALYZING = "analyzing"
        ANALYZED = "analyzed"
        GENERATING_FEEDBACK = "generating_feedback"
        FEEDBACK_READY = "feedback_ready"
        GENERATING_FOLLOWUP = "generating_followup"
        FOLLOWUP_READY = "followup_ready"
        DONE = "done"
        FAILED = "failed"

    org = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="call_recordings",
    )
    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        related_name="uploaded_recordings",
        null=True,
        blank=True,
    )

    # later we can switch this to ForeignKey(Deal) once CRM is finalized
    deal_title = models.CharField(
        max_length=255,
        blank=True,
        help_text="Enter deal name",
    )

    # THIS will go to S3 once storage is configured
    audio_file = models.FileField(upload_to="call_recordings/")

    status = models.CharField(
        max_length=64,
        choices=Status.choices,
        default=Status.WAITING_TRANSCRIPTION,
    )

    transcript = models.TextField(blank=True, default="")

    transcription_job_id = models.CharField(max_length=128, blank=True)
    transcript_json = models.JSONField(null=True, blank=True)
    analysis_json = models.JSONField(null=True, blank=True)
    feedback_json = models.JSONField(null=True, blank=True)
    followup_json = models.JSONField(null=True, blank=True)
    error_stage = models.CharField(max_length=64, null=True, blank=True)
    error_message = models.TextField(null=True, blank=True)
    salesperson_email = models.EmailField(blank=True, default="")
    client_email = models.EmailField(blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    class Language(models.TextChoices):
        AUTO = "auto", "Auto-detect"
        HE = "he", "Hebrew"
        EN = "en", "English"

    language = models.CharField(
        max_length=8,
        choices=Language.choices,
        default=Language.AUTO,
        blank=True,
    )

    def __str__(self) -> str:
        return f"Call #{self.id} ({self.get_status_display()})"


class NotificationDelivery(models.Model):
    class Kind(models.TextChoices):
        ANALYSIS = "analysis"
        FEEDBACK = "feedback"
        FOLLOWUP = "followup"

    class Channel(models.TextChoices):
        EMAIL = "email"

    class Status(models.TextChoices):
        PENDING = "pending"
        SENDING = "sending"
        SENT = "sent"
        FAILED = "failed"
        RETRYING = "retrying"
        SKIPPED = "skipped"

    recording = models.ForeignKey(
        CallRecording,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    kind = models.CharField(max_length=16, choices=Kind.choices)
    channel = models.CharField(max_length=16, choices=Channel.choices, default=Channel.EMAIL)
    salesperson_email = models.EmailField()
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    attempts = models.PositiveIntegerField(default=0)
    subject = models.CharField(max_length=255, blank=True, default="")
    body = models.TextField(blank=True, default="")
    last_error = models.TextField(null=True, blank=True)
    last_attempt_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        unique_together = [("recording", "kind")]

    def __str__(self) -> str:
        return f"Delivery #{self.id} [{self.kind}] → {self.salesperson_email} ({self.status})"
