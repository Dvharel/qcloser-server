from rest_framework.exceptions import ValidationError
from rest_framework.generics import ListCreateAPIView, RetrieveAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView

from .models import User
from .permissions import IsOrgAdmin
from .serializers import CustomTokenObtainPairSerializer, UserManagementSerializer, UserSerializer, UserUpdateSerializer


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
