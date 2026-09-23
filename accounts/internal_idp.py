"""
Internal identity API for Keycloak User Storage SPI federation.

HTTP shape matches the working SSO SPI contract:
  Authorization: Bearer <FINANCIAL_INTERNAL_IDP_API_KEY>
  mounted at /api/v1/internal/idp/

authentication_classes and permission_classes are empty so DRF's default
JWT/session auth cannot intercept the service bearer before the API-key check.
"""
from __future__ import annotations

from django.conf import settings
from django.contrib.auth.hashers import check_password
from django.db.models import Q
from django.utils.crypto import constant_time_compare
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Role, User


class InternalIdpAPIView(APIView):
    authentication_classes = []
    permission_classes = []

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        configured_key = getattr(settings, "FINANCIAL_INTERNAL_IDP_API_KEY", "") or ""
        supplied = request.headers.get("Authorization", "")
        prefix = "Bearer "
        token = supplied[len(prefix):].strip() if supplied.startswith(prefix) else ""

        if not configured_key or not token or not constant_time_compare(token, configured_key):
            self.permission_denied(request, message="Invalid internal IdP credentials.")


def _user_payload(user: User) -> dict:
    return {
        "id": str(user.id),
        "username": user.email,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "enabled": user.is_active,
        "email_verified": True,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "updated_at": user.updated_at.isoformat() if user.updated_at else None,
    }


def _financial_permissions(user: User) -> list[str]:
    if user.is_superuser or user.role == Role.ADMIN:
        return ["*"]
    if user.role == Role.FINANCE_STAFF:
        return ["finance.read", "finance.write"]
    if user.role == Role.CLIENT_ADMIN:
        return ["finance.read", "org.manage"]
    return ["finance.read"]


def _authorization_payload(user: User) -> dict:
    return {
        "financial_role": user.role,
        "permissions": _financial_permissions(user),
        "organization_id": str(user.organization_id) if user.organization_id else None,
        "is_staff": bool(user.is_staff or user.is_superuser),
    }


class InternalIdpUserLookupView(InternalIdpAPIView):
    def get(self, request):
        email = request.query_params.get("email", "").strip().lower()
        user_id = request.query_params.get("id", "").strip()
        username = request.query_params.get("username", "").strip().lower()

        query = Q()
        if user_id:
            query |= Q(id=user_id)
        if email:
            query |= Q(email=email)
        if username:
            query |= Q(email=username)
        if not query:
            return Response(
                {"detail": "Provide id, email, or username."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = User.objects.filter(query).first()
        if not user:
            return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(_user_payload(user))


class InternalIdpUserSearchView(InternalIdpAPIView):
    def get(self, request):
        q = request.query_params.get("q", "").strip()
        try:
            first = max(int(request.query_params.get("first", 0)), 0)
            max_results = min(max(int(request.query_params.get("max", 20)), 1), 100)
        except ValueError:
            return Response(
                {"detail": "first and max must be integers."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        users = User.objects.all().order_by("email")
        if q:
            users = users.filter(
                Q(email__icontains=q)
                | Q(first_name__icontains=q)
                | Q(last_name__icontains=q)
            )
        count = users.count()
        results = [_user_payload(user) for user in users[first:first + max_results]]
        return Response({"count": count, "results": results})


class InternalIdpValidatePasswordView(InternalIdpAPIView):
    def post(self, request):
        username = (request.data.get("username") or "").strip().lower()
        password = request.data.get("password") or ""
        if not username or not password:
            return Response({"valid": False})

        user = User.objects.filter(email__iexact=username).first()
        if not user or not user.is_active or not check_password(password, user.password):
            return Response({"valid": False})
        return Response({"valid": True, "user": _user_payload(user)})


class InternalIdpUserCreateView(InternalIdpAPIView):
    def post(self, request):
        email = (request.data.get("email") or "").strip().lower()
        first_name = (request.data.get("first_name") or "").strip()
        last_name = (request.data.get("last_name") or "").strip()
        enabled = bool(request.data.get("enabled", True))

        if not email:
            return Response({"detail": "email is required."}, status=status.HTTP_400_BAD_REQUEST)

        user = User.objects.filter(email=email).first()
        created = False
        if user is None:
            user = User.objects.create_user(
                email=email,
                password=None,
                first_name=first_name,
                last_name=last_name,
                is_active=enabled,
                role=Role.CLIENT_USER,
                must_change_password=True,
            )
            created = True

        payload = _user_payload(user)
        payload["default_role"] = Role.CLIENT_USER
        return Response(payload, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class InternalIdpUserProfileView(InternalIdpAPIView):
    def patch(self, request, user_id):
        user = User.objects.filter(id=user_id).first()
        if not user:
            return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        update_fields = []
        for field, attr in (
            ("email", "email"),
            ("first_name", "first_name"),
            ("last_name", "last_name"),
            ("enabled", "is_active"),
        ):
            if field not in request.data:
                continue
            value = request.data[field]
            if field == "email":
                value = str(value).strip().lower()
                if not value:
                    return Response(
                        {"detail": "email cannot be blank."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
            elif field == "enabled":
                value = bool(value)
            else:
                value = str(value).strip()
            if getattr(user, attr) != value:
                setattr(user, attr, value)
                update_fields.append(attr)

        if update_fields:
            user.save(update_fields=update_fields)
        return Response(_user_payload(user))


class InternalIdpUserPasswordView(InternalIdpAPIView):
    def put(self, request, user_id):
        password = request.data.get("password") or ""
        temporary = bool(request.data.get("temporary", False))
        if not password:
            return Response({"detail": "password is required."}, status=status.HTTP_400_BAD_REQUEST)

        user = User.objects.filter(id=user_id).first()
        if not user:
            return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        user.set_password(password)
        user.must_change_password = temporary
        user.save(update_fields=["password", "must_change_password"])
        return Response({"updated": True, "must_change_password": user.must_change_password})


class InternalIdpUserAuthorizationView(InternalIdpAPIView):
    def get(self, request, user_id=None):
        user = None
        if user_id:
            user = User.objects.filter(id=user_id).first()
        else:
            email = (request.query_params.get("email") or "").strip().lower()
            if not email:
                return Response(
                    {"detail": "Provide user id or email."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            user = User.objects.filter(email=email).first()

        if not user:
            return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(_authorization_payload(user))
