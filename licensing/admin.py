from django.contrib import admin

from audit.models import AuditEvent, AuditLog

from .models import ClientOrganization, Product, SystemLicense


@admin.register(ClientOrganization)
class ClientOrganizationAdmin(admin.ModelAdmin):
    list_display = ["name", "code", "domain", "contact_email", "is_active"]
    list_filter = ["is_active"]
    search_fields = ["name", "code", "domain", "contact_email"]
    readonly_fields = ["id", "created_at", "updated_at"]


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "provisioning_mode", "is_enabled", "launch_url", "sort_order"]
    list_filter = ["provisioning_mode", "is_enabled"]
    search_fields = ["name", "slug"]
    readonly_fields = ["id", "created_at", "updated_at"]

    def get_readonly_fields(self, request, obj=None):
        # The slug is referenced by URLs and integration config; freeze it once created.
        fields = list(super().get_readonly_fields(request, obj))
        if obj is not None:
            fields.append("slug")
        return fields


@admin.register(SystemLicense)
class SystemLicenseAdmin(admin.ModelAdmin):
    list_display = ["organization", "product", "is_active", "licensed_at", "expires_at"]
    list_filter = ["product", "is_active"]
    search_fields = ["organization__name", "organization__code", "product__name", "license_key"]
    readonly_fields = ["id", "licensed_at"]

    def has_delete_permission(self, request, obj=None):
        # Licences are revoked (is_active off), never deleted, so history stays intact.
        return False

    def save_model(self, request, obj, form, change):
        previously_active = None
        if change:
            previously_active = (
                SystemLicense.objects.filter(pk=obj.pk).values_list("is_active", flat=True).first()
            )
        super().save_model(request, obj, form, change)

        if not change or (previously_active is False and obj.is_active):
            event = AuditEvent.LICENSE_GRANTED
        elif previously_active and not obj.is_active:
            event = AuditEvent.LICENSE_REVOKED
        else:
            return
        AuditLog.objects.create(
            event=event,
            actor=request.user,
            object_type="SystemLicense",
            object_id=str(obj.pk),
            object_repr=str(obj),
            changes={
                "organization": obj.organization.code,
                "product": obj.product.slug,
                "expires_at": obj.expires_at.isoformat() if obj.expires_at else None,
            },
        )
