from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from services.accounts.views import CustomTokenObtainPairView
from services.conversations.views import CallRecordingViewSet


@api_view(["GET"])
@permission_classes([AllowAny])
def ping(request):
    return Response({"status": "ok", "message": "qcloser backend is alive"})

router = DefaultRouter()
router.register("recordings", CallRecordingViewSet, basename="recording")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/ping/", ping), # simple endpoint to check if the backend is responding (for deployment in AWS / Docker / Render / Railway)
    path("api/auth/token/", CustomTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/", include(router.urls)), # DRF generates GET,POST,PATCH... routes for recordings. bc of router
]

if settings.DEBUG and not settings.USE_S3:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
