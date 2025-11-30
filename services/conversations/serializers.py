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
            "created_at",
        ]
        read_only_fields = ["id", "status", "created_at"]

    def create(self, validated_data):
        request = self.context["request"]
        user = request.user if request.user.is_authenticated else None
        org = getattr(user, "org", None) if user else None

        # For now we require a user with org – later we can support service accounts etc.
        if org is None:
            raise serializers.ValidationError("User must belong to an organization.")

        recording = CallRecording.objects.create(
            org=org,
            uploaded_by=user,
            status=CallRecording.Status.WAITING_TRANSCRIPTION,
            **validated_data,
        )
        return recording
