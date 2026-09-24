from django.core import mail
from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import EmailOTP, User
from audit.models import AuditEvent, AuditLog


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

    def test_create_user_respects_enabled_flag(self):
        response = self.client.post(
            "/api/v1/internal/idp/users/",
            {"email": "New@Example.com", "first_name": "New", "last_name": "User", "enabled": False},
            format="json",
            HTTP_AUTHORIZATION="Bearer financial-test-key",
        )
        self.assertEqual(response.status_code, 201)
        self.assertFalse(response.data["enabled"])
        self.assertFalse(User.objects.get(email="new@example.com").is_active)

    def test_disabling_a_user_through_the_api_persists(self):
        response = self.client.patch(
            f"/api/v1/internal/idp/users/{self.user.id}/",
            {"enabled": False},
            format="json",
            HTTP_AUTHORIZATION="Bearer financial-test-key",
        )
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_active)


class NativeLoginTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="person@example.com", password="secret-pass",
            first_name="Per", last_name="Son",
        )

    def test_login_emails_the_code_instead_of_printing_it(self):
        response = self.client.post(
            "/api/v1/auth/login/",
            {"email": self.user.email, "password": "secret-pass"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        code = EmailOTP.objects.get(user=self.user).code
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [self.user.email])
        self.assertIn(code, mail.outbox[0].body)

    def test_deactivated_user_cannot_start_login(self):
        self.user.is_active = False
        self.user.save()
        response = self.client.post(
            "/api/v1/auth/login/",
            {"email": self.user.email, "password": "secret-pass"},
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(len(mail.outbox), 0)


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
        self.assertEqual(len(mail.outbox), 0)

    def test_staff_can_start_otp(self):
        response = self.client.post(
            "/api/v1/auth/break-glass-login/",
            {"email": self.staff.email, "password": "secret-pass"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("user_id", response.data)
        self.assertEqual(len(mail.outbox), 1)