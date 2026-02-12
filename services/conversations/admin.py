from django.contrib import admin
from .models import CallRecording


@admin.register(CallRecording)
class CallRecordingAdmin(admin.ModelAdmin):
    list_display = ("id", "org", "uploaded_by", "status", "created_at", "transcription_job_id")
    readonly_fields = ("transcription_job_id", "transcript_json", "created_at")
