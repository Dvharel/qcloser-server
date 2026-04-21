import binascii
import logging

from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.mail import send_mail
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework.exceptions import ValidationError
from rest_framework.generics import (
    ListCreateAPIView,
    RetrieveAPIView,
    RetrieveUpdateAPIView,
    RetrieveUpdateDestroyAPIView,
)
from rest_framework.permissions import AllowAny, BasePermission, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from .models import Organization, User
from .permissions import IsOrgAdmin
from .serializers import (
    CustomTokenObtainPairSerializer,
    OrganizationSerializer,
    UserManagementSerializer,
    UserSerializer,
    UserUpdateSerializer,
)


logger = logging.getLogger(__name__)


class IsSuperUser(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_superuser)


class OrganizationCreateView(ListCreateAPIView):
    queryset = Organization.objects.all().order_by("created_at")
    serializer_class = OrganizationSerializer
    permission_classes = [IsAuthenticated, IsSuperUser]


class OrganizationDetailView(RetrieveUpdateAPIView):
    queryset = Organization.objects.all()
    serializer_class = OrganizationSerializer
    permission_classes = [IsAuthenticated, IsSuperUser]
    http_method_names = ["get", "patch", "head", "options"]


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


class MeView(RetrieveAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


class OrgUserListCreateView(ListCreateAPIView):
    permission_classes = [IsOrgAdmin]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return UserManagementSerializer
        return UserUpdateSerializer

    def get_queryset(self):
        if not self.request.user or not self.request.user.is_authenticated:
            return User.objects.none()
        return User.objects.filter(org=self.request.user.org)

    def perform_create(self, serializer):
        serializer.save(org=self.request.user.org, is_staff=False)


class OrgUserDetailView(RetrieveUpdateDestroyAPIView):
    serializer_class = UserUpdateSerializer
    permission_classes = [IsOrgAdmin]
    http_method_names = ["get", "patch", "delete", "head", "options"]

    def get_queryset(self):
        if not self.request.user or not self.request.user.is_authenticated:
            return User.objects.none()
        return User.objects.filter(org=self.request.user.org)

    def perform_destroy(self, instance):
        if instance == self.request.user:
            raise ValidationError("You cannot deactivate your own account.")
        instance.is_active = False
        instance.save(update_fields=["is_active"])

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        serializer = self.get_serializer(instance)
        return Response(serializer.data)


class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email", "").strip()
        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            return Response({})

        if not user.is_active:
            return Response({})

        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        reset_link = f"{settings.FRONTEND_URL.rstrip('/')}/reset-password?token={token}&uid={uid}"

        try:
            send_mail(
                subject="Reset your Q-Closer password",
                message=(
                    f"Hi {user.first_name or user.email},\n\n"
                    f"Click the link below to reset your password. "
                    f"This link expires in 3 days.\n\n"
                    f"{reset_link}\n\n"
                    f"If you did not request a password reset, you can ignore this email."
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
            )
        except Exception:
            logger.error(
                "Failed to send password reset email to %s", user.email, exc_info=True
            )

        return Response({})


class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        uid = request.data.get("uid", "")
        token = request.data.get("token", "")
        new_password = request.data.get("new_password", "")

        if not new_password:
            return Response({"error": "new_password is required."}, status=400)

        try:
            pk = force_str(urlsafe_base64_decode(uid))
            user = User.objects.get(pk=pk)
        except (User.DoesNotExist, ValueError, TypeError, binascii.Error):
            return Response({"error": "Invalid or expired token."}, status=400)

        if not default_token_generator.check_token(user, token):
            return Response({"error": "Invalid or expired token."}, status=400)

        try:
            validate_password(new_password, user)
        except DjangoValidationError as exc:
            return Response({"error": exc.messages}, status=400)

        user.set_password(new_password)
        user.save(update_fields=["password"])
        return Response({})
