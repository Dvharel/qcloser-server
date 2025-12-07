from rest_framework import viewsets, permissions, status, parsers
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import CallRecording
from .serializers import CallRecordingSerializer, TranscriptionRequestSerializer
from .transcription_service import transcribe_call_recording
from .analysis_service import analyze_call_recording
from .followup_service import generate_followup



class CallRecordingViewSet(viewsets.ModelViewSet):
    serializer_class = CallRecordingSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [
        parsers.JSONParser,
        parsers.MultiPartParser,
        parsers.FormParser,
    ]

    def get_queryset(self):
        user = self.request.user
        org = getattr(user, "org", None)
        if not org:
            return CallRecording.objects.none()
        return CallRecording.objects.filter(org=org).order_by("-created_at")

    def perform_create(self, serializer):
        user = self.request.user
        org = getattr(user, "org", None)

        if not org:
            raise ValueError("User must belong to an organization.")

        serializer.save(
            org=org,
            uploaded_by=user,
            status=CallRecording.Status.WAITING_TRANSCRIPTION,
        )

    # ---------- TRANSCRIBE ACTION ----------
    @action(
        detail=True,
        methods=["post"],
        serializer_class=TranscriptionRequestSerializer,
    )
    def transcribe(self, request, pk=None):
        """
        POST /api/recordings/<id>/transcribe/

        Uses TranscriptionRequestSerializer to render a dropdown for language
        in the browsable API.
        """
        recording = self.get_object()

        if recording.status != CallRecording.Status.WAITING_TRANSCRIPTION:
            return Response(
                {"detail": "Recording is not in 'waiting_transcription' state."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate input using the serializer (drives the dropdown UI)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        lang_choice = serializer.validated_data.get("language", "auto")

        # map choice to actual Whisper language param
        if lang_choice == "auto":
            language = None
        else:
            language = lang_choice  # "he" or "en"

        try:
            text = transcribe_call_recording(recording, language=language)
        except FileNotFoundError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        except Exception as e:
            return Response(
                {"detail": f"Transcription failed: {e}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        recording.transcript = text
        recording.status = CallRecording.Status.TRANSCRIBED
        recording.save()

        # return the updated recording using the main serializer
        output_serializer = CallRecordingSerializer(recording)
        return Response(output_serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def analyze(self, request, pk=None):
        """
        POST /api/recordings/<id>/analyze/

        Uses the existing transcript to generate:
        - Golden Nuggets
        - Key patterns
        - Next conversation recommendation
        - Closing outlook
        """
        recording = self.get_object()

        if recording.status != CallRecording.Status.TRANSCRIBED:
            return Response(
                {"detail": "Recording must be in 'transcribed' status before analysis."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            analysis_text = analyze_call_recording(recording)
        except Exception as e:
            return Response(
                {"detail": f"Analysis failed: {e}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        recording.golden_nuggets = analysis_text
        recording.status = CallRecording.Status.ANALYZED
        recording.save()

        serializer = CallRecordingSerializer(recording)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def followup(self, request, pk=None):
        """
        POST /api/recordings/<id>/followup/

        Generates:
        - A WhatsApp/email-style follow-up message to client
        - A brief for the salesperson
        - A closing continuation plan
        """
        recording = self.get_object()

        if recording.status != CallRecording.Status.ANALYZED:
            return Response(
                {"detail": "Recording must be in 'analyzed' status before generating follow-up."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            followup_text = generate_followup(
                transcript=recording.transcript,
                analysis=recording.golden_nuggets
            )
        except Exception as e:
            return Response(
                {"detail": f"Follow-up generation failed: {e}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # Save followup text into a new field later (MVP will add fields)
        # For the POC, return it directly
        return Response({"followup": followup_text}, status=status.HTTP_200_OK)

