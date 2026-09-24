"""
Bootstrap real platform data.

    # catalog only (safe to run on every deploy; idempotent)
    python manage.py seed_platform

    # create an organization, license it for DMS, and create its platform admin
    python manage.py seed_platform \
        --org-code flaxem --org-name "Flaxem System Enterprises Ltd" \
        --org-domain flaxem.com --contact-email info@flaxem.com \
        --license dms \
        --admin-email you@flaxem.com --admin-first-name You --admin-last-name Name

--license accepts SLUG or SLUG:YYYY-MM-DD (expiry, end of that day).
The admin password comes from $SEED_ADMIN_PASSWORD or an interactive prompt,
and is never accepted as a CLI argument (it would land in shell history).
"""
import getpass
import os
from datetime import datetime, time

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from accounts.models import User
from audit.models import AuditEvent, AuditLog
from licensing.catalog import CATALOG
from licensing.models import ClientOrganization, Product, SystemLicense


class Command(BaseCommand):
    help = "Upsert the product catalog and optionally bootstrap an organization, licences and a platform admin."

    def add_arguments(self, parser):
        parser.add_argument("--refresh-catalog", action="store_true",
                            help="Also overwrite name/description/info_url/sort_order on existing products.")
        parser.add_argument("--org-code")
        parser.add_argument("--org-name")
        parser.add_argument("--org-domain", default="")
        parser.add_argument("--contact-email")
        parser.add_argument("--license", action="append", default=[], metavar="SLUG[:YYYY-MM-DD]")
        parser.add_argument("--admin-email")
        parser.add_argument("--admin-first-name", default="Platform")
        parser.add_argument("--admin-last-name", default="Admin")

    @transaction.atomic
    def handle(self, *args, **opts):
        self._sync_catalog(refresh=opts["refresh_catalog"])
        org = self._ensure_organization(opts)

        if opts["license"]:
            if org is None:
                raise CommandError("--license requires --org-code.")
            for spec in opts["license"]:
                self._grant_license(org, spec)

        if opts["admin_email"]:
            if org is None:
                raise CommandError("--admin-email requires --org-code (the admin must belong to an organization to use the launcher).")
            self._ensure_admin(org, opts)

    # -- catalog ---------------------------------------------------------
    def _sync_catalog(self, refresh):
        created = updated = 0
        for entry in CATALOG:
            fields = {k: v for k, v in entry.items() if k != "slug"}
            product, was_created = Product.objects.get_or_create(slug=entry["slug"], defaults=fields)
            if was_created:
                created += 1
            elif refresh:
                for key, value in fields.items():
                    setattr(product, key, value)
                product.save()
                updated += 1
        self.stdout.write(f"Catalog: {created} created, {updated} refreshed, {len(CATALOG) - created - updated} left as-is.")

    # -- organization ----------------------------------------------------
    def _ensure_organization(self, opts):
        code = opts["org_code"]
        if not code:
            return None
        org = ClientOrganization.objects.filter(code=code).first()
        if org:
            self.stdout.write(f"Organization '{code}' already exists.")
            return org
        if not (opts["org_name"] and opts["contact_email"]):
            raise CommandError("Creating an organization needs --org-name and --contact-email.")
        org = ClientOrganization.objects.create(
            code=code,
            name=opts["org_name"],
            domain=opts["org_domain"],
            contact_email=opts["contact_email"],
        )
        AuditLog.objects.create(
            event=AuditEvent.ORGANIZATION_CREATED, actor=None,
            object_type="ClientOrganization", object_id=str(org.pk), object_repr=str(org),
            changes={"source": "seed_platform"},
        )
        self.stdout.write(self.style.SUCCESS(f"Created organization '{org.name}'."))
        return org

    # -- licences --------------------------------------------------------
    def _grant_license(self, org, spec):
        slug, _, expiry = spec.partition(":")
        product = Product.objects.filter(slug=slug).first()
        if product is None:
            known = ", ".join(Product.objects.values_list("slug", flat=True))
            raise CommandError(f"Unknown product '{slug}'. Known products: {known}")

        license, created = SystemLicense.objects.get_or_create(
            organization=org,
            product=product,
            defaults={"is_active": True, "expires_at": self._parse_expiry(expiry) if expiry else None},
        )
        if not created:
            state = "active" if license.is_current else "inactive or expired"
            self.stdout.write(f"{org.code} already holds a licence for {slug} ({state}); left unchanged.")
            return
        AuditLog.objects.create(
            event=AuditEvent.LICENSE_GRANTED, actor=None,
            object_type="SystemLicense", object_id=str(license.pk), object_repr=str(license),
            changes={
                "source": "seed_platform",
                "organization": org.code,
                "product": slug,
                "expires_at": license.expires_at.isoformat() if license.expires_at else None,
            },
        )
        self.stdout.write(self.style.SUCCESS(f"Licensed {org.code} for {slug}."))

    @staticmethod
    def _parse_expiry(value):
        try:
            day = datetime.strptime(value, "%Y-%m-%d").date()
        except ValueError:
            raise CommandError(f"Invalid expiry '{value}'; use YYYY-MM-DD.")
        return timezone.make_aware(datetime.combine(day, time(23, 59, 59)))

    # -- platform admin --------------------------------------------------
    def _ensure_admin(self, org, opts):
        email = opts["admin_email"].strip().lower()
        user = User.objects.filter(email=email).first()
        if user:
            if user.organization_id is None:
                user.organization = org
                user.save(update_fields=["organization"])
                self.stdout.write(f"User {email} already existed; assigned to {org.code}.")
            else:
                self.stdout.write(f"User {email} already exists; left unchanged.")
            return

        password = os.environ.get("SEED_ADMIN_PASSWORD") or getpass.getpass(f"Password for {email}: ")
        try:
            validate_password(password)
        except ValidationError as exc:
            raise CommandError("Password rejected: " + " ".join(exc.messages))

        user = User.objects.create_superuser(
            email=email,
            password=password,
            first_name=opts["admin_first_name"],
            last_name=opts["admin_last_name"],
            organization=org,
        )
        AuditLog.objects.create(
            event=AuditEvent.USER_CREATED, actor=None,
            object_type="User", object_id=str(user.pk), object_repr=str(user),
            changes={"source": "seed_platform", "role": user.role},
        )
        self.stdout.write(self.style.SUCCESS(f"Created platform admin {email}."))
