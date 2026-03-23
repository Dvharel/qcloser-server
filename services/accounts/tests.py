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


class OrgAdminAccessTestCase(TestCase):
    def setUp(self):
        self.org_a = Organization.objects.create(name="Org A")
        self.org_b = Organization.objects.create(name="Org B")

        self.admin = User.objects.create_user(
            email="admin@orga.com",
            password="strongpassword123",
            org=self.org_a,
            is_staff=True,
        )
        self.rep = User.objects.create_user(
            email="rep@orga.com",
            password="strongpassword123",
            org=self.org_a,
        )
        User.objects.create_user(
            email="other@orgb.com",
            password="strongpassword123",
            org=self.org_b,
        )

        self.token_url = reverse("token_obtain_pair")
        self.users_url = reverse("org_user_list_create")

    def _get_access_token(self, email, password="strongpassword123"):
        response = self.client.post(
            self.token_url,
            {"email": email, "password": password},
            content_type="application/json",
        )
        return response.data["access"]

    # ------------------------------------------------------------------
    # Batch 1 — Access control
    # ------------------------------------------------------------------

    def test_unauthenticated_get_users_returns_401(self):
        response = self.client.get(self.users_url)
        self.assertEqual(response.status_code, 401)

    def test_regular_user_get_users_returns_403(self):
        token = self._get_access_token("rep@orga.com")
        response = self.client.get(
            self.users_url,
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, 403)

    def test_org_admin_get_users_returns_200(self):
        token = self._get_access_token("admin@orga.com")
        response = self.client.get(
            self.users_url,
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, 200)

    def test_org_admin_cannot_see_users_from_another_org(self):
        token = self._get_access_token("admin@orga.com")
        response = self.client.get(
            self.users_url,
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, 200)
        emails = [u["email"] for u in response.data]
        self.assertNotIn("other@orgb.com", emails)
        self.assertIn("admin@orga.com", emails)
        self.assertIn("rep@orga.com", emails)

    # ------------------------------------------------------------------
    # Batch 2 — User creation
    # ------------------------------------------------------------------

    def test_org_admin_can_create_user_in_their_org(self):
        token = self._get_access_token("admin@orga.com")
        response = self.client.post(
            self.users_url,
            {"email": "newrep@orga.com", "password": "strongpassword123"},
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["email"], "newrep@orga.com")
        self.assertTrue(User.objects.filter(email="newrep@orga.com", org=self.org_a).exists())

    def test_created_user_can_log_in(self):
        token = self._get_access_token("admin@orga.com")
        self.client.post(
            self.users_url,
            {"email": "newrep@orga.com", "password": "strongpassword123"},
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        response = self.client.post(
            self.token_url,
            {"email": "newrep@orga.com", "password": "strongpassword123"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.data)

    def test_duplicate_email_returns_400(self):
        token = self._get_access_token("admin@orga.com")
        response = self.client.post(
            self.users_url,
            {"email": "rep@orga.com", "password": "strongpassword123"},
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, 400)

    def test_org_admin_cannot_create_staff_user(self):
        token = self._get_access_token("admin@orga.com")
        response = self.client.post(
            self.users_url,
            {"email": "newadmin@orga.com", "password": "strongpassword123", "is_staff": True},
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, 201)
        created = User.objects.get(email="newadmin@orga.com")
        self.assertFalse(created.is_staff)

    # ------------------------------------------------------------------
    # Batch 3 — User management
    # ------------------------------------------------------------------

    def test_org_admin_cannot_deactivate_themselves(self):
        token = self._get_access_token("admin@orga.com")
        detail_url = reverse("org_user_detail", kwargs={"pk": self.admin.pk})
        response = self.client.delete(
            detail_url,
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, 400)
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.is_active)

    def test_deactivated_user_cannot_log_in(self):
        token = self._get_access_token("admin@orga.com")
        detail_url = reverse("org_user_detail", kwargs={"pk": self.rep.pk})
        self.client.delete(detail_url, HTTP_AUTHORIZATION=f"Bearer {token}")
        response = self.client.post(
            self.token_url,
            {"email": "rep@orga.com", "password": "strongpassword123"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 401)

    def test_patch_updates_name_fields_only(self):
        token = self._get_access_token("admin@orga.com")
        detail_url = reverse("org_user_detail", kwargs={"pk": self.rep.pk})
        original_password = self.rep.password

        response = self.client.patch(
            detail_url,
            {
                "first_name": "Alice",
                "last_name": "Smith",
                "email": "hacked@evil.com",
                "password": "newpassword999",
            },
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, 200)
        self.rep.refresh_from_db()
        self.assertEqual(self.rep.first_name, "Alice")
        self.assertEqual(self.rep.last_name, "Smith")
        self.assertEqual(self.rep.email, "rep@orga.com")
        self.assertEqual(self.rep.password, original_password)

    def test_org_admin_cannot_get_user_from_another_org(self):
        other_user = User.objects.get(email="other@orgb.com")
        token = self._get_access_token("admin@orga.com")
        detail_url = reverse("org_user_detail", kwargs={"pk": other_user.pk})
        response = self.client.get(detail_url, HTTP_AUTHORIZATION=f"Bearer {token}")
        self.assertEqual(response.status_code, 404)

    def test_org_admin_cannot_patch_user_from_another_org(self):
        other_user = User.objects.get(email="other@orgb.com")
        token = self._get_access_token("admin@orga.com")
        detail_url = reverse("org_user_detail", kwargs={"pk": other_user.pk})
        response = self.client.patch(
            detail_url,
            {"first_name": "Hacked"},
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, 404)

    def test_org_admin_cannot_delete_user_from_another_org(self):
        other_user = User.objects.get(email="other@orgb.com")
        token = self._get_access_token("admin@orga.com")
        detail_url = reverse("org_user_detail", kwargs={"pk": other_user.pk})
        response = self.client.delete(detail_url, HTTP_AUTHORIZATION=f"Bearer {token}")
        self.assertEqual(response.status_code, 404)
        other_user.refresh_from_db()
        self.assertTrue(other_user.is_active)
