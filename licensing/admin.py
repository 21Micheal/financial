from django.contrib import admin
from .models import ClientOrganization, SystemLicense


@admin.register(ClientOrganization)
class ClientOrganizationAdmin(admin.ModelAdmin):
    list_display = ["name", "code", "domain", "contact_email", "is_active"]
    list_filter = ["is_active"]
    search_fields = ["name", "code", "domain", "contact_email"]
    readonly_fields = ["id", "created_at", "updated_at"]


@admin.register(SystemLicense)
class SystemLicenseAdmin(admin.ModelAdmin):
    list_display = ["organization", "system", "is_active", "licensed_at", "expires_at"]
    list_filter = ["system", "is_active"]
    search_fields = ["organization__name", "license_key"]
    readonly_fields = ["id", "licensed_at"]
