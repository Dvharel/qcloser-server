from rest_framework import serializers
from .models import CallRecording


class CallRecordingSerializer(serializers.ModelSerializer):
    class Meta:
        model = CallRecording
        fields = [
            "id",
            "deal_title",
            "audio_file",
            "status",
            "transcript",
            "created_at",
        ]
        read_only_fields = ["id", "status", "transcript", "created_at"]


class TranscriptionRequestSerializer(serializers.Serializer):
    """
    Serializer just for the /transcribe/ action.
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
