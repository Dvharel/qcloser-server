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
            "golden_nuggets",
            "created_at",

            # new / helpful
            "transcription_job_id",
            "transcript_ready",
            "transcript_url",
        ]
        read_only_fields = [
            "status",
            "transcript",
            "golden_nuggets",
            "created_at",
            "transcription_job_id",
            "transcript_ready",
            "transcript_url",
        ]

    def get_transcript_ready(self, obj):
            return obj.status == CallRecording.Status.TRANSCRIBED

    def get_transcript_url(self, obj):
            request = self.context.get("request")
            if not request:
                return None
            return request.build_absolute_uri(f"/api/recordings/{obj.id}/transcript/")

class TranscriptionRequestSerializer(serializers.Serializer):
    """
    Serializer just for the /transcript/ action.
    Shows dropdown in DRF browsable API.
    """

    LANGUAGE_CHOICES = [
        ("auto", "Auto-detect"),
        ("he", "Hebrew"),
        ("en", "English"),
    ]

    language = serializers.ChoiceField(
        choices=LANGUAGE_CHOICES,
        required=False,
        default="auto",
        help_text="Choose 'Auto-detect', 'Hebrew', or 'English'.",
    )
