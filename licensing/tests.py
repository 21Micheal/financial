import json
import os
from datetime import timedelta
from io import StringIO
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError, URLError

from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import User
from audit.models import AuditEvent, AuditLog

from .models import ClientOrganization, Product, SystemLicense

INTEGRATIONS = {
    "dms": {
        "base_url": "http://dms.test/api/v1/internal/idp",
        "api_key": "dms-key",
        "public_url": "http://localhost:3000",
        "role_field": "dms_role",
    }
}


def _json_response(payload):
    response = MagicMock()
    response.read.return_value = json.dumps(payload).encode()
    response.__enter__.return_value = response
    return response


@override_settings(PRODUCT_INTEGRATIONS=INTEGRATIONS)
class LauncherTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.org = ClientOrganization.objects.create(name="Acme", code="acme", contact_email="ops@acme.test")
        self.dms = Product.objects.create(slug="dms", name="FSE DMS")
        self.user = User.objects.create_user(
            email="staff@acme.test", password="secret-pass",
            first_name="Staff", last_name="User", organization=self.org,
        )
        self.license = SystemLicense.objects.create(organization=self.org, product=self.dms)
        self.client.force_authenticate(self.user)

    def _systems(self):
        response = self.client.get("/api/v1/launcher/systems/")
        self.assertEqual(response.status_code, 200)
        return response.data["systems"]

    @patch("licensing.integrations.urlopen")
    def test_provisioned_user_can_launch(self, urlopen):
        urlopen.return_value = _json_response({"dms_role": "dms_admin"})

        card = self._systems()[0]
        self.assertEqual(card["system"], "dms")
        self.assertEqual(card["status"], "ready")

        granted = self.client.post("/api/v1/launcher/sso/dms/")
        self.assertEqual(granted.status_code, 200)
        self.assertEqual(granted.data["redirect_url"], "http://localhost:3000")
        self.assertTrue(AuditLog.objects.filter(event=AuditEvent.SYSTEM_ACCESS_GRANTED, actor=self.user).exists())

    @patch("licensing.integrations.urlopen")
    def test_empty_role_is_not_provisioned(self, urlopen):
        urlopen.return_value = _json_response({"dms_role": ""})

        self.assertEqual(self._systems()[0]["status"], "not_provisioned")
        denied = self.client.post("/api/v1/launcher/sso/dms/")
        self.assertEqual(denied.status_code, 403)
        self.assertIsNone(denied.data["redirect_url"])
        self.assertTrue(AuditLog.objects.filter(event=AuditEvent.SYSTEM_ACCESS_DENIED, actor=self.user).exists())

    @patch("licensing.integrations.urlopen")
    def test_unknown_user_in_product_is_not_provisioned(self, urlopen):
        urlopen.side_effect = HTTPError("http://dms.test", 404, "Not Found", {}, None)
        self.assertEqual(self._systems()[0]["status"], "not_provisioned")

    @patch("licensing.integrations.urlopen")
    def test_unreachable_product_is_unavailable_not_provisioned(self, urlopen):
        urlopen.side_effect = URLError("connection refused")

        self.assertEqual(self._systems()[0]["status"], "unavailable")
        denied = self.client.post("/api/v1/launcher/sso/dms/")
        self.assertEqual(denied.status_code, 503)
        self.assertIsNone(denied.data["redirect_url"])

    @patch("licensing.integrations.urlopen")
    def test_rejected_api_key_fails_closed(self, urlopen):
        urlopen.side_effect = HTTPError("http://dms.test", 401, "Unauthorized", {}, None)
        self.assertEqual(self._systems()[0]["status"], "unavailable")

    @override_settings(PRODUCT_INTEGRATIONS={})
    @patch("licensing.integrations.urlopen")
    def test_role_api_product_without_integration_config_fails_closed(self, urlopen):
        self.dms.launch_url = "http://dms.example"
        self.dms.save()

        self.assertEqual(self._systems()[0]["status"], "unavailable")
        urlopen.assert_not_called()

    @patch("licensing.integrations.urlopen")
    def test_license_only_product_launches_without_probe(self, urlopen):
        Product.objects.create(
            slug="power-bi", name="Power BI", launch_url="http://bi.example",
            provisioning_mode=Product.Provisioning.LICENSE_ONLY, sort_order=5,
        )
        SystemLicense.objects.create(organization=self.org, product=Product.objects.get(slug="power-bi"))
        urlopen.return_value = _json_response({"dms_role": "viewer"})

        cards = {c["system"]: c for c in self._systems()}
        self.assertEqual(cards["power-bi"]["status"], "ready")
        self.assertEqual(urlopen.call_count, 1)  # only DMS was probed

    def test_product_without_launch_url_is_unavailable(self):
        Product.objects.create(slug="infor-os", name="Infor OS")
        SystemLicense.objects.create(organization=self.org, product=Product.objects.get(slug="infor-os"))
        with patch("licensing.integrations.urlopen") as urlopen:
            urlopen.return_value = _json_response({"dms_role": "viewer"})
            cards = {c["system"]: c for c in self._systems()}
        self.assertEqual(cards["infor-os"]["status"], "unavailable")

    def test_expired_license_is_hidden_and_blocked(self):
        self.license.expires_at = timezone.now() - timedelta(days=1)
        self.license.save()

        self.assertEqual(self._systems(), [])
        blocked = self.client.post("/api/v1/launcher/sso/dms/")
        self.assertEqual(blocked.status_code, 403)
        self.assertTrue(AuditLog.objects.filter(event=AuditEvent.SYSTEM_ACCESS_BLOCKED, actor=self.user).exists())

    def test_revoked_license_is_hidden(self):
        self.license.is_active = False
        self.license.save()
        self.assertEqual(self._systems(), [])

    def test_inactive_organization_is_hidden(self):
        self.org.is_active = False
        self.org.save()
        self.assertEqual(self._systems(), [])

    def test_disabled_product_is_hidden(self):
        self.dms.is_enabled = False
        self.dms.save()
        self.assertEqual(self._systems(), [])

    def test_other_organizations_licences_are_not_visible(self):
        other = ClientOrganization.objects.create(name="Other", code="other", contact_email="o@other.test")
        Product.objects.create(slug="efris", name="EFRIS")
        SystemLicense.objects.create(organization=other, product=Product.objects.get(slug="efris"))
        with patch("licensing.integrations.urlopen") as urlopen:
            urlopen.return_value = _json_response({"dms_role": "viewer"})
            self.assertEqual([c["system"] for c in self._systems()], ["dms"])
        self.assertEqual(self.client.post("/api/v1/launcher/sso/efris/").status_code, 403)

    def test_unknown_system_is_rejected(self):
        self.assertEqual(self.client.post("/api/v1/launcher/sso/nope/").status_code, 400)

    def test_user_without_organization_sees_nothing(self):
        self.user.organization = None
        self.user.save()
        self.assertEqual(self._systems(), [])


class SeedPlatformTests(TestCase):
    def _seed(self, *extra):
        call_command(
            "seed_platform",
            "--org-code", "flaxem", "--org-name", "Flaxem System Enterprises Ltd",
            "--contact-email", "info@flaxem.com", "--license", "dms",
            "--admin-email", "Admin@Flaxem.com",
            *extra, stdout=StringIO(),
        )

    @patch.dict(os.environ, {"SEED_ADMIN_PASSWORD": "Str0ng-Passw0rd-Here"})
    def test_seed_creates_org_license_and_admin_idempotently(self):
        self._seed()

        self.assertEqual(Product.objects.count(), 10)
        org = ClientOrganization.objects.get(code="flaxem")
        self.assertTrue(SystemLicense.objects.current().filter(organization=org, product__slug="dms").exists())
        admin = User.objects.get(email="admin@flaxem.com")
        self.assertEqual(admin.organization, org)
        self.assertTrue(admin.is_staff and admin.is_superuser)
        self.assertTrue(admin.check_password("Str0ng-Passw0rd-Here"))
        self.assertTrue(AuditLog.objects.filter(event=AuditEvent.LICENSE_GRANTED).exists())

        self._seed()  # second run changes nothing
        self.assertEqual(Product.objects.count(), 10)
        self.assertEqual(SystemLicense.objects.count(), 1)
        self.assertEqual(User.objects.count(), 1)

    def test_seed_does_not_overwrite_operator_settings(self):
        call_command("seed_platform", stdout=StringIO())
        Product.objects.filter(slug="dms").update(launch_url="http://dms.example", is_enabled=False)
        call_command("seed_platform", stdout=StringIO())
        dms = Product.objects.get(slug="dms")
        self.assertEqual(dms.launch_url, "http://dms.example")
        self.assertFalse(dms.is_enabled)
