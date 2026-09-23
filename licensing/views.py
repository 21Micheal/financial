"""
Licensing (what an org purchased) vs authorization (role inside each product).

Launcher lists licensed systems, then probes the product for provisioned roles.
SSO initiate returns the product's public origin — not a Keycloak token URL.
"""
from __future__ import annotations

import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny

from .models import SystemLicense, SystemType
from audit.models import AuditLog, AuditEvent


SYSTEM_PUBLIC_URLS = {
    SystemType.DMS: ("DMS_PUBLIC_URL", "http://localhost:3000"),
    SystemType.INVENTORY: ("INVENTORY_PUBLIC_URL", "http://localhost:3002"),
}

UNPROVISIONED_COPY = (
    "Your organization is licensed for Document Management, but your account "
    "has not been provisioned there. Contact your administrator."
)


def _public_url(system: str) -> str:
    env_name, default = SYSTEM_PUBLIC_URLS.get(system, ("", ""))
    if not env_name:
        return ""
    return getattr(settings, env_name, "") or default


def _dms_provisioned(email: str) -> bool:
    """Join on email against IDM's role-only internal API. Empty role = not provisioned."""
    base = (getattr(settings, "DMS_INTERNAL_API_BASE_URL", "") or "").rstrip("/")
    api_key = getattr(settings, "DMS_INTERNAL_IDP_API_KEY", "") or ""
    if not base or not api_key or not email:
        return False
    url = f"{base}/users/authorization/?{urlencode({'email': email})}"
    request = Request(
        url,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/json",
        },
    )
    try:
        with urlopen(request, timeout=5) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        if exc.code == 404:
            return False
        return False
    except (URLError, TimeoutError, json.JSONDecodeError, OSError):
        return False

    role = payload.get("dms_role") or ""
    return bool(str(role).strip())


def _access_message(system: str, display: str, provisioned: bool) -> str | None:
    if provisioned:
        return None
    if system == SystemType.DMS:
        return UNPROVISIONED_COPY
    return (
        f"Your organization is licensed for {display}, but your account has not "
        "been provisioned there. Contact your administrator."
    )


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
        if not user.organization:
            return Response({"systems": [], "message": "User is not assigned to an organization"})

        licenses = SystemLicense.objects.filter(
            organization=user.organization,
            is_active=True,
        ).select_related("organization")

        systems = []
        for license in licenses:
            display = license.get_system_display()
            provisioned = True
            if license.system == SystemType.DMS:
                provisioned = _dms_provisioned(user.email)
            elif license.system == SystemType.INVENTORY:
                provisioned = False

            systems.append({
                "system": license.system,
                "display": display,
                "public_url": _public_url(license.system),
                "licensed": True,
                "provisioned": provisioned,
                "access_message": _access_message(license.system, display, provisioned),
            })

        return Response({"systems": systems})


class SSOInitiateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, system):
        user = request.user
        valid_systems = [choice[0] for choice in SystemType.choices]
        if system not in valid_systems:
            return Response({"detail": "Invalid system"}, status=status.HTTP_400_BAD_REQUEST)

        if not user.organization:
            return Response(
                {"detail": "User is not assigned to an organization"},
                status=status.HTTP_403_FORBIDDEN,
            )

        license = SystemLicense.objects.filter(
            organization=user.organization,
            system=system,
            is_active=True,
        ).first()

        if not license:
            AuditLog.objects.create(
                event=AuditEvent.SYSTEM_ACCESS_BLOCKED,
                actor=user,
                changes={"system": system, "reason": "Organization not licensed"},
            )
            return Response(
                {"detail": "Your organization is not licensed for this system."},
                status=status.HTTP_403_FORBIDDEN,
            )

        provisioned = True
        if system == SystemType.DMS:
            provisioned = _dms_provisioned(user.email)
        elif system == SystemType.INVENTORY:
            provisioned = False

        display = license.get_system_display()
        if not provisioned:
            AuditLog.objects.create(
                event=AuditEvent.SYSTEM_ACCESS_DENIED,
                actor=user,
                changes={"system": system, "reason": "User not provisioned"},
            )
            return Response(
                {
                    "system": system,
                    "display": display,
                    "public_url": _public_url(system),
                    "licensed": True,
                    "provisioned": False,
                    "redirect_url": None,
                    "access_message": _access_message(system, display, False),
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        redirect_url = _public_url(system)
        AuditLog.objects.create(
            event=AuditEvent.SYSTEM_ACCESS_GRANTED,
            actor=user,
            changes={"system": system, "redirect_url": redirect_url},
        )
        return Response({
            "system": system,
            "display": display,
            "public_url": redirect_url,
            "licensed": True,
            "provisioned": True,
            "redirect_url": redirect_url,
            "access_message": None,
        })
