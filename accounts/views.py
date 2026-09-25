"""
accounts/views.py

Auth endpoints for the Financial System hub.

Authentication is now exclusively via Keycloak SSO.
Native login has been removed; only break-glass emergency access remains.
"""

from django.conf import settings
from django.contrib.auth.hashers import check_password
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError

from .models import User
from audit.models import AuditLog, AuditEvent


def _user_payload(user):
    return {
        "id": str(user.id),
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "role": user.role,
        "organization_id": str(user.organization.id) if user.organization else None,
        "is_staff": user.is_staff,
        "is_superuser": user.is_superuser,
        "must_change_password": user.must_change_password,
    }


# ── Views ─────────────────────────────────────────────────────────────────────


class MeView(APIView):
    """Get current user information. fix #7D: includes must_change_password."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(_user_payload(request.user))


class ChangePasswordView(APIView):
    """
    Allow a user to change their own password.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        current = request.data.get('current_password') or ''
        new_pw = request.data.get('new_password') or ''

        if not current or not new_pw:
            return Response(
                {'detail': 'current_password and new_password are required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not check_password(current, user.password):
            return Response(
                {'detail': 'Current password is incorrect.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            validate_password(new_pw, user)
        except DjangoValidationError as exc:
            return Response({'detail': exc.messages}, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(new_pw)
        user.must_change_password = False
        user.password_changed_at = timezone.now()
        user.save(update_fields=['password', 'must_change_password', 'password_changed_at'])

        AuditLog.objects.create(event=AuditEvent.USER_PASSWORD_CHANGED, actor=user)
        return Response({'detail': 'Password changed successfully.'})


class TokenRefreshView(APIView):
    """
    Token refresh endpoint.
    """
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        from rest_framework_simplejwt.serializers import TokenRefreshSerializer
        serializer = TokenRefreshSerializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except TokenError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_401_UNAUTHORIZED)
        return Response(serializer.validated_data)


class LogoutView(APIView):
    """
    Logout endpoint - blacklist refresh token.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get('refresh')
        if refresh_token:
            try:
                token = RefreshToken(refresh_token)
                token.blacklist()
            except TokenError:
                pass  # already invalid — that's fine
        return Response({'detail': 'Logged out.'}, status=status.HTTP_200_OK)


class OIDCExchangeView(APIView):
    """
    SPA PKCE completed against Keycloak; exchange a validated id_token for hub JWTs.
    """
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        import jwt as pyjwt
        from .oidc_auth import resolve_financial_user, validate_id_token

        raw_token = (request.data.get("id_token") or "").strip()
        if not raw_token:
            return Response({"detail": "id_token is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            claims = validate_id_token(raw_token)
            user = resolve_financial_user(claims)
        except pyjwt.ExpiredSignatureError:
            return Response({"detail": "The token has expired. Please sign in again."}, status=status.HTTP_401_UNAUTHORIZED)
        except pyjwt.PyJWTError:
            return Response({"detail": "Invalid identity token."}, status=status.HTTP_401_UNAUTHORIZED)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_403_FORBIDDEN)
        except Exception:
            return Response({"detail": "Unable to complete sign-in."}, status=status.HTTP_401_UNAUTHORIZED)

        if not user.is_active:
            return Response({"detail": "Account is inactive."}, status=status.HTTP_403_FORBIDDEN)

        user.last_login = timezone.now()
        user.save(update_fields=["last_login"])
        refresh = RefreshToken.for_user(user)
        AuditLog.objects.create(event=AuditEvent.USER_LOGIN, actor=user, changes={"auth_mode": "keycloak"})
        return Response({
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": _user_payload(user),
        })
