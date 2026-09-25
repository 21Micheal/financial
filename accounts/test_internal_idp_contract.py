"""Contract tests: what the Keycloak SPI / mapper (SSO repo) reads from the internal IdP API."""
import uuid

from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from accounts.models import Role, User

AUTH = {"HTTP_AUTHORIZATION": "Bearer contract-test-key"}


@override_settings(FINANCIAL_INTERNAL_IDP_API_KEY="contract-test-key")
class InternalIdpContractTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="ada@example.com", password="secret-pass-123",
            first_name="Ada", last_name="Lovelace", role=Role.FINANCIAL_USER,
        )

    def test_user_payload_matches_financial_user_record(self):
        data = self.client.get("/api/v1/internal/idp/users/lookup/", {"email": self.user.email}, **AUTH).data
        for key in ("id", "username", "email", "first_name", "last_name", "enabled",
                    "email_verified", "must_change_password"):
            self.assertIn(key, data)
        self.assertEqual(data["first_name"], "Ada")
        self.assertEqual(data["last_name"], "Lovelace")
        self.assertTrue(data["email_verified"])
        self.assertNotIn("firstName", data)

    def test_authorization_payload_matches_mapper(self):
        for url in (
            f"/api/v1/internal/idp/users/{self.user.id}/authorization/",
            "/api/v1/internal/idp/users/authorization/?email=ada@example.com",
        ):
            data = self.client.get(url, **AUTH).data
            self.assertEqual(data["financial_role"], "financial_user")
            self.assertIs(data["enabled"], True)
            self.assertIn("organization_id", data)
            self.assertIn("is_staff", data)
            self.assertIn("has_usable_password", data)

    def test_authorization_reports_disabled_user(self):
        self.user.is_active = False
        self.user.save()
        data = self.client.get(f"/api/v1/internal/idp/users/{self.user.id}/authorization/", **AUTH).data
        self.assertIs(data["enabled"], False)

    def test_has_usable_password_for_microsoft_users(self):
        self.user.has_usable_password = False
        self.user.save()
        data = self.client.get(f"/api/v1/internal/idp/users/{self.user.id}/authorization/", **AUTH).data
        self.assertIs(data["has_usable_password"], False)

    def test_lookup_with_malformed_id_is_404_not_500(self):
        response = self.client.get("/api/v1/internal/idp/users/lookup/", {"id": "not-a-uuid"}, **AUTH)
        self.assertEqual(response.status_code, 404)

    def test_lookup_with_unknown_uuid_is_404(self):
        response = self.client.get("/api/v1/internal/idp/users/lookup/", {"id": str(uuid.uuid4())}, **AUTH)
        self.assertEqual(response.status_code, 404)

    def test_lookup_without_identifiers_is_400(self):
        self.assertEqual(self.client.get("/api/v1/internal/idp/users/lookup/", **AUTH).status_code, 400)

    def test_create_rejects_invalid_email(self):
        response = self.client.post(
            "/api/v1/internal/idp/users/", {"email": "not-an-email"}, format="json", **AUTH
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(User.objects.filter(email="not-an-email").exists())

    def test_patch_rejects_invalid_email(self):
        response = self.client.patch(
            f"/api/v1/internal/idp/users/{self.user.id}/", {"email": "nope"}, format="json", **AUTH
        )
        self.assertEqual(response.status_code, 400)
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, "ada@example.com")

    def test_weak_password_is_400_with_messages(self):
        response = self.client.put(
            f"/api/v1/internal/idp/users/{self.user.id}/password/",
            {"password": "short"}, format="json", **AUTH,
        )
        self.assertEqual(response.status_code, 400)
        self.assertIsInstance(response.data["detail"], list)

    # ── additional coverage (review pass) ────────────────────────────────────

    def test_create_returns_snake_case_payload_and_default_role(self):
        response = self.client.post(
            "/api/v1/internal/idp/users/",
            {"email": "New.Person@Example.com", "first_name": "New", "last_name": "Person"},
            format="json", **AUTH,
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["email"], "new.person@example.com")
        self.assertEqual(response.data["first_name"], "New")
        self.assertIs(response.data["must_change_password"], True)
        self.assertEqual(response.data["default_role"], "financial_user")
        self.assertNotIn("firstName", response.data)

    def test_search_results_use_the_same_payload_shape(self):
        data = self.client.get("/api/v1/internal/idp/users/search/", {"q": "ada"}, **AUTH).data
        self.assertEqual(data["count"], 1)
        row = data["results"][0]
        self.assertEqual(row["first_name"], "Ada")
        self.assertIn("email_verified", row)

    def test_validate_password_payload_is_snake_case(self):
        data = self.client.post(
            "/api/v1/internal/idp/users/validate-password/",
            {"username": "ada@example.com", "password": "secret-pass-123"}, format="json", **AUTH,
        ).data
        self.assertTrue(data["valid"])
        self.assertEqual(data["user"]["last_name"], "Lovelace")

    def test_patch_duplicate_email_is_409(self):
        User.objects.create_user(email="bob@example.com", password="secret-pass-123",
                                 first_name="Bob", last_name="B")
        response = self.client.patch(
            f"/api/v1/internal/idp/users/{self.user.id}/", {"email": "bob@example.com"},
            format="json", **AUTH,
        )
        self.assertEqual(response.status_code, 409)

    def test_password_change_clears_must_change_password(self):
        self.user.must_change_password = True
        self.user.save()
        response = self.client.put(
            f"/api/v1/internal/idp/users/{self.user.id}/password/",
            {"password": "a-Long-Enough-Passphrase-42"}, format="json", **AUTH,
        )
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertFalse(self.user.must_change_password)
        # The SPI relies on this: the required action must disappear after a change.
        data = self.client.get("/api/v1/internal/idp/users/lookup/", {"email": self.user.email}, **AUTH).data
        self.assertIs(data["must_change_password"], False)

    def test_missing_or_wrong_key_is_rejected(self):
        self.assertEqual(self.client.get("/api/v1/internal/idp/users/lookup/",
                                         {"email": self.user.email}).status_code, 403)
        self.assertEqual(self.client.get("/api/v1/internal/idp/users/lookup/",
                                         {"email": self.user.email},
                                         HTTP_AUTHORIZATION="Bearer wrong").status_code, 403)
