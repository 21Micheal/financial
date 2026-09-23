"""
audit/models.py

Immutable audit log for the financial system.
Captures authentication, licensing, and system access events.
"""
from django.db import models
from django.conf import settings
import uuid


class AuditEvent(models.TextChoices):
    # Authentication events
    USER_LOGIN = "user.login", "User Login"
    USER_LOGIN_FAILED = "user.login_failed", "Login Failed"
    USER_BREAK_GLASS_LOGIN = "user.break_glass_login", "Break-Glass Login (Emergency Native Auth)"
    USER_BREAK_GLASS_LOGIN_FAILED = "user.break_glass_login_failed", "Break-Glass Login Failed"
    USER_MFA_ENABLED = "user.mfa_enabled", "MFA Enabled"
    USER_MFA_DISABLED = "user.mfa_disabled", "MFA Disabled"
    USER_PASSWORD_CHANGED = "user.password_changed", "Password Changed"
    USER_PASSWORD_RESET = "user.password_reset", "Password Reset"
    
    # User lifecycle
    USER_CREATED = "user.created", "User Created"
    USER_UPDATED = "user.updated", "User Updated"
    USER_DELETED = "user.deleted", "User Deleted"
    USER_ACTIVATED = "user.activated", "User Activated"
    USER_DEACTIVATED = "user.deactivated", "User Deactivated"
    
    # Organization events
    ORGANIZATION_CREATED = "organization.created", "Organization Created"
    ORGANIZATION_UPDATED = "organization.updated", "Organization Updated"
    ORGANIZATION_DELETED = "organization.deleted", "Organization Deleted"
    
    # Licensing events
    LICENSE_GRANTED = "license.granted", "System License Granted"
    LICENSE_REVOKED = "license.revoked", "System License Revoked"
    LICENSE_EXPIRED = "license.expired", "System License Expired"
    
    # System role events
    SYSTEM_ROLE_GRANTED = "system_role.granted", "System Role Granted"
    SYSTEM_ROLE_REVOKED = "system_role.revoked", "System Role Revoked"
    SYSTEM_ROLE_UPDATED = "system_role.updated", "System Role Updated"
    
    # Launcher/SSO events
    SYSTEM_ACCESS_GRANTED = "system_access.granted", "System Access Granted (SSO Redirect)"
    SYSTEM_ACCESS_DENIED = "system_access.denied", "System Access Denied (Not Provisioned)"
    SYSTEM_ACCESS_BLOCKED = "system_access.blocked", "System Access Blocked (Not Licensed)"


class AuditLog(models.Model):
    """Append-only audit log. Never update or delete rows."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.CharField(max_length=60, choices=AuditEvent.choices, db_index=True)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL,
        related_name="audit_logs"
    )
    # Generic FK to any object
    object_type = models.CharField(max_length=60, blank=True)
    object_id = models.CharField(max_length=40, blank=True, db_index=True)
    object_repr = models.CharField(max_length=255, blank=True)
    # Structured diff / context
    changes = models.JSONField(default=dict, blank=True)
    # Request metadata
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-timestamp"]
        # Prevent accidental updates
        default_permissions = ("view",)

    def __str__(self):
        return f"{self.timestamp.isoformat()} | {self.event} | {self.actor}"

    def save(self, *args, **kwargs):
        if self.pk and AuditLog.objects.filter(pk=self.pk).exists():
            raise ValueError("Audit log entries are immutable")
        super().save(*args, **kwargs)
