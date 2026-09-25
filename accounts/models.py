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
    PLATFORM_ADMIN = "platform_admin", "Platform Administrator"
    ADMIN = "admin", "Administrator"
    FINANCIAL_USER = "financial_user", "Financial User"


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
        extra.setdefault("role", Role.PLATFORM_ADMIN)
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
    role = models.CharField(max_length=50, choices=Role.choices, default=Role.FINANCIAL_USER)

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
    has_usable_password = models.BooleanField(default=True)

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
        return self.role == Role.PLATFORM_ADMIN or self.is_staff or self.is_superuser

    def check_password_change_required(self):
        """Check if user needs to change password"""
        if self.must_change_password:
            return True
        if self.password_changed_at:
            if timezone.now() - self.password_changed_at > timedelta(days=90):
                return True
        return False


class OTPPurpose(models.TextChoices):
    LOGIN = "login", "Standard Login"
    BREAK_GLASS = "break_glass", "Break-Glass Emergency Access"


class EmailOTP(models.Model):
    """Short-lived OTP codes for email-based MFA.

    fix #1:  attempts counter — OTP is voided after MAX_ATTEMPTS wrong guesses.
    fix #3B: purpose field isolates login OTPs from break-glass OTPs so they
             cannot be used interchangeably.
    """
    MAX_ATTEMPTS = 5

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='otps')
    code = models.CharField(max_length=6)
    purpose = models.CharField(
        max_length=20,
        choices=OTPPurpose.choices,
        default=OTPPurpose.LOGIN,
    )
    attempts = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'purpose', 'created_at']),
        ]

    def __str__(self):
        return f"OTP({self.purpose}) for {self.user.email}"

    @classmethod
    def generate(cls, user, purpose=OTPPurpose.LOGIN):
        """Generate a new 6-digit OTP code for the given purpose.

        Invalidates all prior unused OTPs with the same purpose for this user
        so old codes are never reusable after a fresh request.
        """
        code = f"{secrets.randbelow(10**6):06d}"
        expires_at = timezone.now() + timedelta(minutes=10)
        cls.objects.filter(user=user, used=False, purpose=purpose).update(used=True)
        return cls.objects.create(
            user=user,
            code=code,
            purpose=purpose,
            expires_at=expires_at,
        )

    def is_valid(self):
        """Return True if the OTP is unused, unexpired, and under attempt limit."""
        return (
            not self.used
            and timezone.now() < self.expires_at
            and self.attempts < self.MAX_ATTEMPTS
        )

    def record_failed_attempt(self):
        """Increment the attempt counter; void the OTP if limit is reached."""
        self.attempts += 1
        if self.attempts >= self.MAX_ATTEMPTS:
            self.used = True  # void after too many guesses
        self.save(update_fields=['attempts', 'used'])

    def mark_used(self):
        """Mark OTP as successfully consumed."""
        self.used = True
        self.save(update_fields=['used'])
