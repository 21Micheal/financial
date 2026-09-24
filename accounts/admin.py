"""
accounts/admin.py

The stock UserAdmin assumes a `username` field and a plain ModelAdmin would
store typed passwords unhashed, so this defines email-based forms that hash
passwords through Django's password machinery.
"""
from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import BaseUserCreationForm
from django.contrib.auth.forms import UserChangeForm as BaseUserChangeForm

from .models import EmailOTP, User


class UserCreationForm(BaseUserCreationForm):
    class Meta:
        model = User
        fields = ("email", "first_name", "last_name", "role", "organization")

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("A user with this email already exists.")
        return email


class UserChangeForm(BaseUserChangeForm):
    class Meta(BaseUserChangeForm.Meta):
        model = User
        field_classes = {}

    def clean_email(self):
        return self.cleaned_data["email"].strip().lower()


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    form = UserChangeForm
    add_form = UserCreationForm
    ordering = ("email",)
    list_display = ["email", "first_name", "last_name", "role", "organization", "is_active", "is_staff"]
    list_filter = ["role", "organization", "is_active", "is_staff", "is_superuser"]
    search_fields = ["email", "first_name", "last_name"]
    readonly_fields = ["id", "created_at", "updated_at", "last_login"]
    filter_horizontal = ("groups", "user_permissions")

    fieldsets = (
        (None, {"fields": ("id", "email", "password")}),
        ("Profile", {"fields": ("first_name", "last_name", "role", "organization")}),
        ("Access", {"fields": (
            "is_active", "is_staff", "is_superuser",
            "must_change_password", "password_changed_at", "groups", "user_permissions",
        )}),
        ("Timestamps", {"fields": ("last_login", "created_at", "updated_at")}),
    )
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "first_name", "last_name", "role", "organization", "password1", "password2"),
        }),
    )


@admin.register(EmailOTP)
class EmailOTPAdmin(admin.ModelAdmin):
    """Read-only. The code column is deliberately not shown."""
    list_display = ["user", "created_at", "expires_at", "used"]
    list_filter = ["used"]
    search_fields = ["user__email"]
    fields = ["user", "created_at", "expires_at", "used"]
    readonly_fields = fields

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False