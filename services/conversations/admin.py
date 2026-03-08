from django.contrib import admin
from .models import CallRecording, NotificationDelivery


@admin.register(CallRecording)
class CallRecordingAdmin(admin.ModelAdmin):
    list_display = ("id", "org", "uploaded_by", "status", "created_at", "transcription_job_id")
    readonly_fields = ("transcription_job_id", "transcript_json", "created_at")


@admin.register(NotificationDelivery)
class NotificationDeliveryAdmin(admin.ModelAdmin):
    list_display = (
        "id", "recording", "kind", "channel", "salesperson_email",
        "status", "attempts", "subject", "truncated_body", "truncated_last_error",
        "created_at", "last_attempt_at", "sent_at",
    )
    readonly_fields = ("created_at",)
    list_filter = ("kind", "channel", "status")

    @admin.display(description="body")
    def truncated_body(self, obj):
        if not obj.body:
            return ""
        return obj.body[:80] + ("…" if len(obj.body) > 80 else "")

    @admin.display(description="last error")
    def truncated_last_error(self, obj):
        if not obj.last_error:
            return ""
        return obj.last_error[:80] + ("…" if len(obj.last_error) > 80 else "")
