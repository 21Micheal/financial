"""
Product catalog and client licensing.

Licensing (what an organization purchased) is separate from authorization
(the role a user holds inside each product). This app stores the catalog and
entitlements only; per-user roles stay in each product and are probed live by
licensing.integrations.
"""
import uuid

from django.db import models
from django.db.models import Q
from django.utils import timezone


class ClientOrganization(models.Model):
    """Client organization that licenses platform products."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200, unique=True)
    code = models.CharField(max_length=50, unique=True, help_text="Short code for API references")
    domain = models.CharField(max_length=200, blank=True, help_text="Primary domain (e.g., company.com)")
    is_active = models.BooleanField(default=True)
    contact_email = models.EmailField()
    contact_phone = models.CharField(max_length=50, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['code']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return self.name


class Product(models.Model):
    """A product Flaxem sells. Adding a product is data, not a code change."""

    class Provisioning(models.TextChoices):
        ROLE_API = "role_api", "Product role API (per-user provisioning)"
        LICENSE_ONLY = "license_only", "Licence only (no per-user check)"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    slug = models.SlugField(
        max_length=50,
        unique=True,
        help_text="Stable identifier used in URLs and integrations, e.g. 'dms'.",
    )
    name = models.CharField(max_length=200, unique=True)
    description = models.TextField(blank=True)
    info_url = models.URLField(blank=True, help_text="Public product page.")
    launch_url = models.URLField(
        blank=True,
        help_text="Where users land after SSO. Leave blank to use this deployment's default for the product.",
    )
    provisioning_mode = models.CharField(
        max_length=20,
        choices=Provisioning.choices,
        default=Provisioning.ROLE_API,
        help_text="How per-user access is decided. 'Product role API' fails closed if the integration is not configured.",
    )
    is_enabled = models.BooleanField(
        default=True,
        help_text="Disabled products are hidden from every launcher, licensed or not.",
    )
    sort_order = models.PositiveSmallIntegerField(default=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['sort_order', 'name']

    def __str__(self):
        return self.name


class LicenseQuerySet(models.QuerySet):
    def current(self):
        """Licences that entitle their organization to launch a product right now."""
        return self.filter(
            is_active=True,
            organization__is_active=True,
            product__is_enabled=True,
        ).filter(Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now()))


class SystemLicense(models.Model):
    """Which products a client organization is entitled to use."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        ClientOrganization,
        on_delete=models.CASCADE,
        related_name='licenses',
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name='licenses',
    )
    is_active = models.BooleanField(default=True)
    licensed_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True, help_text="Null means perpetual")
    license_key = models.CharField(max_length=100, blank=True, help_text="External license key if applicable")
    notes = models.TextField(blank=True)

    objects = LicenseQuerySet.as_manager()

    class Meta:
        unique_together = [('organization', 'product')]
        ordering = ['organization', 'product']
        indexes = [
            models.Index(fields=['is_active'], name='licensing_s_is_acti_d60234_idx'),
        ]

    def __str__(self):
        return f"{self.organization.name} - {self.product.name}"

    @property
    def is_current(self):
        return self.is_active and (self.expires_at is None or self.expires_at > timezone.now())
