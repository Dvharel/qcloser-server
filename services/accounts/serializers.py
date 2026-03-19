from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import User


class UserSerializer(serializers.ModelSerializer):
    org_id = serializers.IntegerField(source="org_id", read_only=True)

    class Meta:
        model = User
        fields = ["id", "email", "org_id"]


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        data["email"] = self.user.email
        data["org_id"] = self.user.org_id
        return data
