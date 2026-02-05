from django.contrib import admin
from .models import CallRecording


@admin.register(CallRecording)
class CallRecordingAdmin(admin.ModelAdmin):
    list_display = ("id", "org", "uploaded_by", "deal_title", "status", "created_at") # what is the difference betweem the 1st admin and the second?
    list_filter = ("org", "status", "created_at")
    search_fields = ("deal_title", "uploaded_by__username", "uploaded_by__email")
