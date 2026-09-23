"""
accounts/admin.py
"""
from django.contrib import admin
from .models import User, EmailOTP


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ['email', 'first_name', 'last_name', 'role', 'organization', 'is_staff', 'is_superuser']
    list_filter = ['role', 'organization', 'is_staff', 'is_superuser', 'mfa_enabled']
    search_fields = ['email', 'first_name', 'last_name']
    readonly_fields = ['id', 'created_at', 'updated_at', 'last_login']


@admin.register(EmailOTP)
class EmailOTPAdmin(admin.ModelAdmin):
    list_display = ['user', 'code', 'created_at', 'expires_at', 'used']
    list_filter = ['used']
    search_fields = ['user__email', 'code']
    readonly_fields = ['id', 'created_at']
