"""
licensing/models.py

Client organization licensing and system access models
"""
from django.db import models
import uuid


class SystemType(models.TextChoices):
    DMS = "dms", "Document Management System"
    INVENTORY = "inventory", "Inventory Management"
    FINANCIAL = "financial", "Financial System"
    # Add more systems as they're added to the platform


class ClientOrganization(models.Model):
    """Represents a client organization that licenses systems"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200, unique=True)
    code = models.CharField(max_length=50, unique=True, help_text="Short code for API references")
    domain = models.CharField(max_length=200, blank=True, help_text="Primary domain (e.g., company.com)")
    is_active = models.BooleanField(default=True)
    
    # Contact info
    contact_email = models.EmailField()
    contact_phone = models.CharField(max_length=50, blank=True)
    
    # Timestamps
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
    """Defines which systems a client organization is licensed to use"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        ClientOrganization,
        on_delete=models.CASCADE,
        related_name='licenses'
    )
    system = models.CharField(max_length=50, choices=SystemType.choices)
    
    # License terms
    is_active = models.BooleanField(default=True)
    licensed_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True, help_text="Null means perpetual")
    
    # Metadata
    license_key = models.CharField(max_length=100, blank=True, help_text="External license key if applicable")
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


class SystemRole(models.TextChoices):
    """Role definitions for system-specific access"""
    # DMS roles
    DMS_ADMIN = "dms_admin", "DMS Administrator"
    DMS_EDITOR = "dms_editor", "DMS Editor"
    DMS_VIEWER = "dms_viewer", "DMS Viewer"
    
    # Inventory roles
    INVENTORY_ADMIN = "inventory_admin", "Inventory Administrator"
    INVENTORY_USER = "inventory_user", "Inventory User"
    
    # Financial roles
    FINANCIAL_ADMIN = "financial_admin", "Financial Administrator"
    FINANCIAL_USER = "financial_user", "Financial User"


class UserSystemRole(models.Model):
    """Defines a user's role within a specific licensed system"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='system_roles'
    )
    organization = models.ForeignKey(
        ClientOrganization,
        on_delete=models.CASCADE,
        related_name='user_system_roles'
    )
    system = models.CharField(max_length=50, choices=SystemType.choices)
    role = models.CharField(max_length=50, choices=SystemRole.choices)
    
    # Provisioning metadata
    provisioned_at = models.DateTimeField(auto_now_add=True)
    provisioned_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='provisioned_roles'
    )
    is_active = models.BooleanField(default=True)
    
    class Meta:
        unique_together = ['user', 'organization', 'system']
        ordering = ['user', 'system']
        indexes = [
            models.Index(fields=['user', 'system']),
            models.Index(fields=['organization', 'system']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return f"{self.user.email} - {self.get_system_display()} ({self.get_role_display()})"
    
    @classmethod
    def has_access(cls, user, system):
        """Check if user has any role in the specified system"""
        return cls.objects.filter(
            user=user,
            system=system,
            is_active=True
        ).exists()
    
    @classmethod
    def get_role(cls, user, system):
        """Get user's role in the specified system"""
        try:
            role_obj = cls.objects.get(
                user=user,
                system=system,
                is_active=True
            )
            return role_obj.role
        except cls.DoesNotExist:
            return None
