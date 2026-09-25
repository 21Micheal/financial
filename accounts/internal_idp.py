"""
accounts/internal_idp.py

Internal IDP API consumed by Keycloak (user federation SPI) and the DMS launcher.
Protected by a pre-shared API key (Authorization: Bearer ... or X-Api-Key).

Contract with providers/financial-keycloak-provider (SSO repo) -- keep in sync:
  user payload          -> FinancialUser record (snake_case keys)
  authorization payload -> FinancialRoleProtocolMapper (financial_role, permissions,
                           organization_id, is_staff, enabled)

Security fixes applied
----------------------
fix #9B: duplicate email PATCH now returns 409 instead of IntegrityError 500.
fix #9C: password write validates against Django password validators.
fix #9D: audit log entries written for create, profile update, and password change.
stage 1: payload shapes match the Keycloak SPI; malformed ids -> 404; emails validated.
"""

import uuid

from django.contrib.auth.hashers import check_password
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import validate_email
from django.db import IntegrityError
from django.db.models import Q
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from audit.models import AuditEvent, AuditLog
from .models import Role, User


# Note: Permissions are now derived from role in the database on each request.
# The internal IdP API now emits only the role; the hub authorizes from the database.


# ── Key guard ─────────────────────────────────────────────────────────────────

class InternalIdpAPIView(APIView):
    """Base class: verifies the shared secret from either supported header."""
    authentication_classes = []
    permission_classes = []

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        from django.conf import settings
        expected = settings.FINANCIAL_INTERNAL_IDP_API_KEY
        authorization = request.headers.get("Authorization", "")
        bearer_key = authorization[7:] if authorization.startswith("Bearer ") else ""
        supplied = request.headers.get("X-Api-Key") or bearer_key
        if not expected or supplied != expected:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Invalid or missing API key.")


# ── Payload helpers ───────────────────────────────────────────────────────────

def _user_payload(user):
    """Shape read by the SPI's FinancialUser record. Keys are snake_case on purpose."""
    return {
        "id": str(user.id),
        "username": user.email,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "enabled": user.is_active,
        # Django has no verification field; accounts are provisioned by admins and sign-in
        # is gated by password (+ OTP natively), so Keycloak must not ask for verification.
        "email_verified": True,
        "must_change_password": user.must_change_password,
        "has_usable_password": user.has_usable_password,
        "role": user.role,
        "organization_id": str(user.organization_id) if user.organization_id else None,
        "is_staff": user.is_staff,
        "is_superuser": user.is_superuser,
    }


def _authorization_payload(user):
    """Shape read by FinancialRoleProtocolMapper."""
    return {
        "id": str(user.id),
        "email": user.email,
        "enabled": user.is_active,
        "financial_role": user.role,
        "organization_id": str(user.organization_id) if user.organization_id else None,
        "is_staff": user.is_staff,
        "is_superuser": user.is_superuser,
        "must_change_password": user.must_change_password,
        "has_usable_password": user.has_usable_password,
    }


def _valid_email(value):
    try:
        validate_email(value)
    except DjangoValidationError:
        return False
    return True


# ── Views ─────────────────────────────────────────────────────────────────────

class InternalIdpUserLookupView(InternalIdpAPIView):
    def get(self, request):
        raw_id = request.query_params.get("id")
        email = (request.query_params.get("email") or "").strip().lower() or None
        username = (request.query_params.get("username") or "").strip().lower() or None

        user_id = None
        if raw_id:
            try:
                user_id = uuid.UUID(raw_id)
            except ValueError:
                user_id = None  # not one of ours; never let it reach the ORM as a UUID

        query = Q()
        if user_id:
            query |= Q(id=user_id)
        if email:
            query |= Q(email=email)
        if username:
            query |= Q(email=username)
        if not query:
            if raw_id:  # only a malformed id was supplied
                return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)
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
        if not _valid_email(email):
            return Response(
                {"detail": "Enter a valid email address; it is the login identity."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = User.objects.filter(email=email).first()
        created = False
        if user is None:
            user = User.objects.create_user(
                email=email,
                password=None,
                first_name=first_name,
                last_name=last_name,
                is_active=enabled,
                role=Role.FINANCIAL_USER,
                must_change_password=True,
            )
            created = True
            # fix #9D: audit user creation
            AuditLog.objects.create(
                event=AuditEvent.USER_CREATED,
                actor=None,
                changes={"email": email, "source": "internal_idp"},
            )

        payload = _user_payload(user)
        payload["default_role"] = Role.FINANCIAL_USER
        return Response(payload, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class InternalIdpUserProfileView(InternalIdpAPIView):
    def patch(self, request, user_id):
        user = User.objects.filter(id=user_id).first()
        if not user:
            return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        update_fields = []
        changes = {}
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
                if not _valid_email(value):
                    return Response(
                        {"detail": "Enter a valid email address."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
            elif field == "enabled":
                value = bool(value)
            else:
                value = str(value).strip()
            if getattr(user, attr) != value:
                changes[attr] = value
                setattr(user, attr, value)
                update_fields.append(attr)

        if update_fields:
            try:
                user.save(update_fields=update_fields)
            except IntegrityError:
                # fix #9B: duplicate email → 409 instead of 500
                return Response(
                    {"detail": "A user with that email already exists."},
                    status=status.HTTP_409_CONFLICT,
                )
            # fix #9D: audit profile update
            AuditLog.objects.create(
                event=AuditEvent.USER_UPDATED,
                actor=None,
                changes={"user_id": str(user_id), "fields": changes, "source": "internal_idp"},
            )
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

        # fix #9C: validate password before setting it
        try:
            validate_password(password, user)
        except DjangoValidationError as exc:
            return Response({"detail": exc.messages}, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(password)
        user.must_change_password = temporary
        user.save(update_fields=["password", "must_change_password"])

        # fix #9D: audit password change
        AuditLog.objects.create(
            event=AuditEvent.USER_PASSWORD_CHANGED,
            actor=None,
            changes={"user_id": str(user_id), "temporary": temporary, "source": "internal_idp"},
        )
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