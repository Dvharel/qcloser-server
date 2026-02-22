from rest_framework import serializers
from .models import CallRecording


class CallRecordingSerializer(serializers.ModelSerializer):
    transcript_ready = serializers.SerializerMethodField()
    transcript_url = serializers.SerializerMethodField()

    class Meta:
        model = CallRecording
        fields = [
            "id",
            "deal_title",
            "audio_file",
            "language",
            "status",
            "transcript",
            "created_at",
            # pipeline / debug
            "transcription_job_id",
            "analysis_text",
            "feedback_text",
            "followup_json",
            "error_stage",
            "error_message",
            # helpers
            "transcript_ready",
            "transcript_url",
        ]
        read_only_fields = [
            "status",
            "transcript",
            "created_at",
            "transcription_job_id",
            "analysis_text",
            "feedback_text",
            "followup_json",
            "error_stage",
            "error_message",
            "transcript_ready",
            "transcript_url",
        ]

    def get_transcript_ready(self, obj):
        # אם מבחינתך "מוכן" כולל גם מעבר לשלבים מתקדמים:
        return obj.status in (
            CallRecording.Status.TRANSCRIBED,
            CallRecording.Status.ANALYZING,
            CallRecording.Status.ANALYZED,
            CallRecording.Status.GENERATING_FEEDBACK,
            CallRecording.Status.FEEDBACK_READY,
            CallRecording.Status.GENERATING_FOLLOWUP,
            CallRecording.Status.FOLLOWUP_READY,
            CallRecording.Status.DONE,
        )

    def get_transcript_url(self, obj):
        request = self.context.get("request")
        if not request:
            return None
        return request.build_absolute_uri(f"/api/recordings/{obj.id}/transcript/")
