from rest_framework import viewsets, permissions, status, parsers
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError

from .models import CallRecording
from .serializers import CallRecordingSerializer
from .transcription_service import (
    submit_transcription,
    poll_transcription,
    format_speaker_transcript,
    compact_utterances,
)
from .analysis_service import analyze_call_recording
from .followup_service import generate_followup

from services.conversations.ai_client import analyze_via_ai_service


class CallRecordingViewSet(viewsets.ModelViewSet):
    serializer_class = CallRecordingSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [
        parsers.JSONParser,
        parsers.MultiPartParser,
        parsers.FormParser,
    ]

    def get_queryset(self):
        """
        Returns only recordings that belong to the request user's organization.
        """
        user = self.request.user
        org = getattr(user, "org", None)
        if not org:
            return CallRecording.objects.none()
        return CallRecording.objects.filter(org=org).order_by("-created_at")

    def perform_create(self, serializer):
        user = self.request.user
        org = getattr(user, "org", None)

        if not org:
            raise ValidationError(
                {
                    "org": "User must belong to an organization before uploading recordings."
                }
            )

        recording = serializer.save(
            org=org,
            uploaded_by=user,
            status=CallRecording.Status.WAITING_TRANSCRIPTION,
        )

        language_code = recording.language
        if language_code == CallRecording.Language.AUTO:
            language_code = None

        # Auto-submit async transcription job (POC behavior)
        try:
            result = submit_transcription(recording, language_code=language_code)
            recording.transcription_job_id = result["id"]
            recording.save(update_fields=["transcription_job_id"])
        except Exception as e:
            print("AssemblyAI submit failed:", e)

    # ---------- TRANSCRIBE ACTION (POST submit, GET poll) ----------
    @action(detail=True, methods=["get"], url_path="transcript")
    def transcribe(self, request, pk=None):
        """
        GET /api/recordings/<id>/transcript/

        - If already transcribed -> return saved transcript
        - Else -> poll AssemblyAI
            - processing -> return awaiting
            - completed -> save + return transcript
        """
        recording = self.get_object()

        # If already ready, return from DB (fast, no provider call)
        if recording.status == CallRecording.Status.TRANSCRIBED:
            return Response(
                {
                    "state": "completed",
                    "transcript": recording.transcript,
                    "utterances": compact_utterances(recording.transcript_json or {}),
                },
                status=status.HTTP_200_OK,
            )

        # Not submitted / missing job id (shouldn't happen if upload auto-submits)
        if not recording.transcription_job_id:
            return Response(
                {
                    "state": "not_submitted",
                    "detail": "No transcription job id found for this recording.",
                },
                status=status.HTTP_409_CONFLICT,
            )

        # Poll provider
        try:
            data = poll_transcription(recording.transcription_job_id)
        except Exception as e:
            return Response(
                {"detail": f"Poll failed: {e}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        provider_status = data.get("status")

        if provider_status in ("queued", "processing"):
            return Response(
                {"state": "awaiting_transcription", "provider_status": provider_status},
                status=status.HTTP_200_OK,
            )

        if provider_status == "completed":
            recording.transcript_json = data
            recording.transcript = (
                format_speaker_transcript(data) or (data.get("text") or "").strip()
            )
            recording.status = CallRecording.Status.TRANSCRIBED
            recording.save(update_fields=["transcript_json", "transcript", "status"])

            clean_utterances = []
            for u in data.get("utterances") or []:
                clean_utterances.append(
                    {
                        "speaker": u.get("speaker"),
                        "text": u.get("text"),
                    }
                )

            return Response(
                {
                    "state": "completed",
                    "transcript": recording.transcript,
                    "utterances": clean_utterances,
                },
                status=status.HTTP_200_OK,
            )

        return Response(
            {"detail": f"Unexpected provider status: {provider_status}", "raw": data},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    @action(detail=True, methods=["get", "post"])
    def analyze(self, request, pk=None):
        """
        GET  /api/recordings/<id>/analyze/   -> tells user to press POST
        POST /api/recordings/<id>/analyze/   -> calls FastAPI /analyze and saves result
        """

        if request.method == "GET":
            return Response(
                {"detail": "Click POST to start analysis."}, status=status.HTTP_200_OK
            )

        recording = self.get_object()

        if recording.status != CallRecording.Status.TRANSCRIBED:
            return Response(
                {
                    "detail": "Recording must be in 'transcribed' status before analysis."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not recording.transcript:
            return Response(
                {"detail": "No transcript found. Run transcript first."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            result = analyze_via_ai_service(
                transcript=recording.transcript,
                language=getattr(recording, "language", None),
            )
        except Exception as e:
            return Response(
                {"detail": f"AI service analysis failed: {e}"},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        # You currently store golden_nuggets as TextField.
        # So for now we serialize the structured response into a readable string.
        # Later: store JSON in a JSONField.
        analysis_text = (
            "## Golden Nuggets\n"
            + "\n".join(f"- {x}" for x in result.get("nuggets", []))
            + "\n\n## Patterns\n"
            + "\n".join(f"- {x}" for x in result.get("patterns", []))
            + "\n\n## Risks\n"
            + "\n".join(f"- {x}" for x in result.get("risks", []))
            + "\n\n## Next Questions\n"
            + "\n".join(f"- {x}" for x in result.get("next_questions", []))
            + "\n\n## Closing Outlook\n"
            + f"Score: {result.get('closing_outlook', {}).get('score')}\n"
            + f"Reason: {result.get('closing_outlook', {}).get('reason')}"
        ).strip()

        recording.golden_nuggets = analysis_text
        recording.status = CallRecording.Status.ANALYZED
        recording.save(update_fields=["golden_nuggets", "status"])

        return Response(
            CallRecordingSerializer(recording, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["get", "post"])
    def followup(self, request, pk=None):
        """
        POST /api/recordings/<id>/followup/

        Generates:
        - A WhatsApp/email-style follow-up message to client
        - A brief for the salesperson
        - A closing continuation plan
        """

        if request.method == "GET":
            return Response(
                {"detail": "Send POST to this endpoint to start followup."},
                status=status.HTTP_200_OK,
            )

        recording = self.get_object()

        if recording.status != CallRecording.Status.ANALYZED:
            return Response(
                {
                    "detail": "Recording must be in 'analyzed' status before generating follow-up."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            followup_text = generate_followup(
                transcript=recording.transcript, analysis=recording.golden_nuggets
            )
        except Exception as e:
            return Response(
                {"detail": f"Follow-up generation failed: {e}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # Save followup text into a new field later (MVP will add fields)
        # For the POC, return it directly
        return Response({"followup": followup_text}, status=status.HTTP_200_OK)
