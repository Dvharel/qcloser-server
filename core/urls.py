from django.contrib import admin
from django.urls import path, include
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.routers import DefaultRouter

from services.conversations.views import CallRecordingViewSet


@api_view(["GET"])
@permission_classes([AllowAny])
def ping(request):
    return Response({"status": "ok", "message": "qcloser backend is alive"})

router = DefaultRouter()
router.register("recordings", CallRecordingViewSet, basename="recording")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/ping/", ping),
    path("api/", include(router.urls)),

]
