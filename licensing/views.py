"""
Launcher API.

The launcher lists the products the user's organization holds a current
licence for, and reports per product whether this user can launch it.
SSO initiate re-checks everything server-side and returns the product's
public origin — never a Keycloak token URL.
"""
from django.conf import settings
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from audit.models import AuditEvent, AuditLog

from .integrations import NOT_PROVISIONED, READY, resolve_access, resolve_access_many
from .models import Product, SystemLicense


def _system_payload(license, access):
    product = license.product
    return {
        "system": product.slug,
        "display": product.name,
        "description": product.description,
        "info_url": product.info_url,
        "public_url": access.launch_url,
        "licensed": True,
        "expires_at": license.expires_at.isoformat() if license.expires_at else None,
        "status": access.status,
        "access_message": access.message,
    }


class ConfigView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({
            "auth_mode": getattr(settings, "AUTH_MODE", "native"),
            "launcher_enabled": True,
            "keycloak_url": getattr(settings, "KEYCLOAK_URL", "http://localhost:8080"),
            "keycloak_realm": getattr(settings, "KEYCLOAK_REALM", "idp-dev"),
            "oidc_client_id": getattr(settings, "OIDC_CLIENT_ID", "financial-client"),
        })


class LauncherView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        if not user.organization_id:
            return Response({"systems": [], "message": "User is not assigned to an organization"})

        licenses = list(
            SystemLicense.objects.current()
            .filter(organization_id=user.organization_id)
            .select_related("product")
            .order_by("product__sort_order", "product__name")
        )
        access = resolve_access_many(user, [lic.product for lic in licenses])
        return Response({
            "systems": [_system_payload(lic, access[lic.product.slug]) for lic in licenses],
        })


class SSOInitiateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, system):
        user = request.user

        if not Product.objects.filter(slug=system).exists():
            return Response({"detail": "Invalid system"}, status=status.HTTP_400_BAD_REQUEST)

        if not user.organization_id:
            return Response(
                {"detail": "User is not assigned to an organization"},
                status=status.HTTP_403_FORBIDDEN,
            )

        license = (
            SystemLicense.objects.current()
            .filter(organization_id=user.organization_id, product__slug=system)
            .select_related("product")
            .first()
        )
        if license is None:
            AuditLog.objects.create(
                event=AuditEvent.SYSTEM_ACCESS_BLOCKED,
                actor=user,
                changes={"system": system, "reason": "No current licence for this organization"},
            )
            return Response(
                {"detail": "Your organization is not licensed for this system."},
                status=status.HTTP_403_FORBIDDEN,
            )

        access = resolve_access(user, license.product)
        payload = _system_payload(license, access)

        if access.status == READY:
            AuditLog.objects.create(
                event=AuditEvent.SYSTEM_ACCESS_GRANTED,
                actor=user,
                changes={"system": system, "redirect_url": access.launch_url},
            )
            return Response({**payload, "redirect_url": access.launch_url})

        AuditLog.objects.create(
            event=AuditEvent.SYSTEM_ACCESS_DENIED,
            actor=user,
            changes={
                "system": system,
                "reason": "User not provisioned" if access.status == NOT_PROVISIONED else "Product unavailable",
            },
        )
        http_status = (
            status.HTTP_403_FORBIDDEN if access.status == NOT_PROVISIONED
            else status.HTTP_503_SERVICE_UNAVAILABLE
        )
        return Response({**payload, "redirect_url": None}, status=http_status)
