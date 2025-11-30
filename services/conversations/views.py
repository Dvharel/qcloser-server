from rest_framework import viewsets, permissions, parsers

from .models import CallRecording
from .serializers import CallRecordingSerializer


class CallRecordingViewSet(viewsets.ModelViewSet):
    serializer_class = CallRecordingSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [parsers.MultiPartParser, parsers.FormParser]

    def get_queryset(self):
        user = self.request.user
        org = getattr(user, "org", None)
        if not org:
            return CallRecording.objects.none()
        return CallRecording.objects.filter(org=org)

    def perform_create(self, serializer):
        serializer.save()
