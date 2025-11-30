from django.contrib import admin
from .models import CallRecording


@admin.register(CallRecording)
class CallRecordingAdmin(admin.ModelAdmin):
    list_display = ("id", "org", "uploaded_by", "deal_title", "status", "created_at")
    list_filter = ("org", "status", "created_at")
    search_fields = ("deal_title", "uploaded_by__username", "uploaded_by__email")
