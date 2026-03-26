from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView, TokenBlacklistView

from .views import (
    CustomTokenObtainPairView,
    MeView,
    OrgUserListCreateView,
    OrgUserDetailView,
    PasswordResetRequestView,
    PasswordResetConfirmView,
)

urlpatterns = [
    path("token/", CustomTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("logout/", TokenBlacklistView.as_view(), name="token_blacklist"),
    path("me/", MeView.as_view(), name="user_me"),
    path("users/", OrgUserListCreateView.as_view(), name="org_user_list_create"),
    path("users/<int:pk>/", OrgUserDetailView.as_view(), name="org_user_detail"),
    path("password-reset/", PasswordResetRequestView.as_view(), name="password_reset_request"),
    path("password-reset/confirm/", PasswordResetConfirmView.as_view(), name="password_reset_confirm"),
]
