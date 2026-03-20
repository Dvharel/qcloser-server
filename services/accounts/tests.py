from django.test import TestCase
from django.urls import reverse

from .models import Organization, User


class AuthTestCase(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(name="Test Org")
        self.user = User.objects.create_user(
            email="test@example.com",
            password="strongpassword123",
            org=self.org,
        )
        self.token_url = reverse("token_obtain_pair")
        self.refresh_url = reverse("token_refresh")
        self.logout_url = reverse("token_blacklist")
        self.me_url = reverse("user_me")

    def _get_tokens(self):
        response = self.client.post(
            self.token_url,
            {"email": "test@example.com", "password": "strongpassword123"},
            content_type="application/json",
        )
        return response.data

    # ------------------------------------------------------------------
    # POST /api/auth/token/
    # ------------------------------------------------------------------

    def test_login_valid_credentials_returns_tokens_and_user_data(self):
        response = self.client.post(
            self.token_url,
            {"email": "test@example.com", "password": "strongpassword123"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        self.assertEqual(response.data["email"], "test@example.com")
        self.assertEqual(response.data["org_id"], self.org.id)

    def test_login_wrong_password_returns_401(self):
        response = self.client.post(
            self.token_url,
            {"email": "test@example.com", "password": "wrongpassword"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 401)

    def test_login_nonexistent_email_returns_401(self):
        response = self.client.post(
            self.token_url,
            {"email": "nobody@example.com", "password": "strongpassword123"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 401)

    # ------------------------------------------------------------------
    # GET /api/auth/me/
    # ------------------------------------------------------------------

    def test_me_with_valid_token_returns_user_data(self):
        tokens = self._get_tokens()
        response = self.client.get(
            self.me_url,
            HTTP_AUTHORIZATION=f"Bearer {tokens['access']}",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], self.user.id)
        self.assertEqual(response.data["email"], "test@example.com")
        self.assertEqual(response.data["org_id"], self.org.id)

    def test_me_with_no_token_returns_401(self):
        response = self.client.get(self.me_url)
        self.assertEqual(response.status_code, 401)

    # ------------------------------------------------------------------
    # POST /api/auth/token/refresh/
    # ------------------------------------------------------------------

    def test_refresh_with_valid_token_returns_new_access_and_refresh(self):
        tokens = self._get_tokens()
        response = self.client.post(
            self.refresh_url,
            {"refresh": tokens["refresh"]},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        self.assertNotEqual(response.data["refresh"], tokens["refresh"])

    # ------------------------------------------------------------------
    # POST /api/auth/logout/
    # ------------------------------------------------------------------

    def test_logout_blacklists_refresh_token(self):
        tokens = self._get_tokens()
        # Logout succeeds
        response = self.client.post(
            self.logout_url,
            {"refresh": tokens["refresh"]},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        # Same token is now blacklisted — refresh must fail
        response = self.client.post(
            self.refresh_url,
            {"refresh": tokens["refresh"]},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 401)
