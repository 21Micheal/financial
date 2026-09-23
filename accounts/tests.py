from unittest.mock import patch

from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import User
from audit.models import AuditEvent, AuditLog
from licensing.models import ClientOrganization, SystemLicense, SystemType


@override_settings(FINANCIAL_INTERNAL_IDP_API_KEY="financial-test-key")
class InternalIdpApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="hub@example.com",
            password="secret-pass",
            first_name="Hub",
            last_name="User",
        )

    def test_jwt_header_does_not_authenticate_internal_routes(self):
        access = str(RefreshToken.for_user(self.user).access_token)
        response = self.client.get(
            "/api/v1/internal/idp/users/lookup/",
            {"email": self.user.email},
            HTTP_AUTHORIZATION=f"Bearer {access}",
        )
        self.assertEqual(response.status_code, 403)

    def test_api_key_allows_lookup(self):
        response = self.client.get(
            "/api/v1/internal/idp/users/lookup/",
            {"email": self.user.email},
            HTTP_AUTHORIZATION="Bearer financial-test-key",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["email"], self.user.email)

    def test_validate_password(self):
        ok = self.client.post(
            "/api/v1/internal/idp/users/validate-password/",
            {"username": self.user.email, "password": "secret-pass"},
            format="json",
            HTTP_AUTHORIZATION="Bearer financial-test-key",
        )
        self.assertEqual(ok.status_code, 200)
        self.assertTrue(ok.data["valid"])


@override_settings(
    DMS_INTERNAL_API_BASE_URL="http://backend:8000/api/v1/internal/idp",
    DMS_INTERNAL_IDP_API_KEY="dms-test-key",
    DMS_PUBLIC_URL="http://localhost:3000",
)
class LauncherTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.org = ClientOrganization.objects.create(
            name="Acme",
            code="acme",
            contact_email="ops@acme.test",
        )
        self.user = User.objects.create_user(
            email="staff@acme.test",
            password="secret-pass",
            first_name="Staff",
            last_name="User",
            organization=self.org,
        )
        SystemLicense.objects.create(organization=self.org, system=SystemType.DMS, is_active=True)
        self.client.force_authenticate(self.user)

    def test_licensed_not_provisioned_does_not_redirect(self):
        with patch("licensing.views._dms_provisioned", return_value=False):
            listed = self.client.get("/api/v1/launcher/systems/")
            self.assertEqual(listed.status_code, 200)
            card = listed.data["systems"][0]
            self.assertTrue(card["licensed"])
            self.assertFalse(card["provisioned"])

            denied = self.client.post("/api/v1/launcher/sso/dms/")
            self.assertEqual(denied.status_code, 403)
            self.assertIsNone(denied.data["redirect_url"])
            self.assertTrue(
                AuditLog.objects.filter(
                    event=AuditEvent.SYSTEM_ACCESS_DENIED,
                    actor=self.user,
                ).exists()
            )

    def test_provisioned_returns_origin_redirect(self):
        with patch("licensing.views._dms_provisioned", return_value=True):
            granted = self.client.post("/api/v1/launcher/sso/dms/")
            self.assertEqual(granted.status_code, 200)
            self.assertEqual(granted.data["redirect_url"], "http://localhost:3000")


class BreakGlassTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.staff = User.objects.create_user(
            email="admin@example.com",
            password="secret-pass",
            first_name="Plat",
            last_name="Admin",
            is_staff=True,
        )
        self.regular = User.objects.create_user(
            email="user@example.com",
            password="secret-pass",
            first_name="Reg",
            last_name="User",
        )

    def test_non_staff_is_rejected(self):
        response = self.client.post(
            "/api/v1/auth/break-glass-login/",
            {"email": self.regular.email, "password": "secret-pass"},
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertTrue(
            AuditLog.objects.filter(event=AuditEvent.USER_BREAK_GLASS_LOGIN_FAILED).exists()
        )

    def test_staff_can_start_otp(self):
        response = self.client.post(
            "/api/v1/auth/break-glass-login/",
            {"email": self.staff.email, "password": "secret-pass"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("user_id", response.data)
