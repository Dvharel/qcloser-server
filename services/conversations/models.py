from django.db import models

from services.accounts.models import Organization, User

class CallRecording(models.Model):
    class Status(models.TextChoices):
        WAITING_TRANSCRIPTION = "waiting_transcription", "Waiting for transcription"
        TRANSCRIBED = "transcribed", "Transcribed"
        ANALYZED = "analyzed", "Analyzed"

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
        help_text="Temporary placeholder until full CRM integration.",
    )

    # THIS will go to S3 once storage is configured
    audio_file = models.FileField(upload_to="call_recordings/")

    status = models.CharField(
        max_length=32,
        choices=Status.choices,
        default=Status.WAITING_TRANSCRIPTION,  # 👈 satisfies 'waiting for transcription'
    )

    transcript = models.TextField(blank=True)
    golden_nuggets = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Call #{self.id} ({self.get_status_display()})"
