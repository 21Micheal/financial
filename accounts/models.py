"""
accounts/models.py

Financial System User and Organization Models
"""
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone
from django.utils.functional import cached_property
from datetime import timedelta
import uuid
import secrets


class Role(models.TextChoices):
    ADMIN = "admin", "Platform Administrator"
    FINANCE_STAFF = "finance_staff", "Finance Staff"
    CLIENT_ADMIN = "client_admin", "Client Administrator"
    CLIENT_USER = "client_user", "Client User"


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra):
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email).lower()
        user = self.model(email=email, **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password, **extra):
        extra.setdefault("role", Role.ADMIN)
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        extra.setdefault("must_change_password", False)
        user = self.create_user(email, password, **extra)
        return user


class User(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    role = models.CharField(max_length=50, choices=Role.choices, default=Role.CLIENT_USER)
    
    # Platform admin flags (for break-glass access)
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_superuser = models.BooleanField(default=False)
    
    # Organization
    organization = models.ForeignKey(
        'licensing.ClientOrganization',
        on_delete=models.PROTECT,
        related_name='users',
        null=True,
        blank=True
    )
    
    # Password management
    must_change_password = models.BooleanField(default=True)
    password_changed_at = models.DateTimeField(null=True, blank=True)
    
    # OTP for MFA
    mfa_enabled = models.BooleanField(default=False)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_login = models.DateTimeField(null=True, blank=True)
    
    objects = UserManager()
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']
    
    class Meta:
        ordering = ['email']
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['organization']),
        ]
    
    def __str__(self):
        return f"{self.email} ({self.get_role_display()})"
    
    @cached_property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()
    
    def is_platform_admin(self):
        """Check if user is a platform administrator (for break-glass access)"""
        return self.is_staff or self.is_superuser
    
    def check_password_change_required(self):
        """Check if user needs to change password"""
        if self.must_change_password:
            return True
        # Also require change if password hasn't been changed in 90 days
        if self.password_changed_at:
            if timezone.now() - self.password_changed_at > timedelta(days=90):
                return True
        return False


class EmailOTP(models.Model):
    """Short-lived OTP codes for email-based MFA"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='otps')
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'created_at']),
        ]
    
    def __str__(self):
        return f"OTP for {self.user.email}"
    
    @classmethod
    def generate(cls, user):
        """Generate a new 6-digit OTP code"""
        code = f"{secrets.randbelow(10**6):06d}"
        expires_at = timezone.now() + timedelta(minutes=10)
        # Mark all existing OTPs for this user as used
        cls.objects.filter(user=user, used=False).update(used=True)
        return cls.objects.create(user=user, code=code, expires_at=expires_at)
    
    def is_valid(self):
        """Check if OTP is still valid"""
        return not self.used and timezone.now() < self.expires_at
    
    def mark_used(self):
        """Mark OTP as used"""
        self.used = True
        self.save()
