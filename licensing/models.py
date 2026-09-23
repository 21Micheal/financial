"""
Client organization licensing. Authorization for each product stays in that
product (DMS dms_role, financial_role here) — this app only stores entitlements.
"""
from django.db import models
import uuid


class SystemType(models.TextChoices):
    DMS = "dms", "Document Management"
    INVENTORY = "inventory", "Inventory Management"


class ClientOrganization(models.Model):
    """Client organization that licenses platform systems."""
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


class SystemLicense(models.Model):
    """Which systems a client organization is entitled to use."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        ClientOrganization,
        on_delete=models.CASCADE,
        related_name='licenses'
    )
    system = models.CharField(max_length=50, choices=SystemType.choices)
    is_active = models.BooleanField(default=True)
    licensed_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True, help_text="Null means perpetual")
    license_key = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        unique_together = ['organization', 'system']
        ordering = ['organization', 'system']
        indexes = [
            models.Index(fields=['organization', 'system']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return f"{self.organization.name} - {self.get_system_display()}"
