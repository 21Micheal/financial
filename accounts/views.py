"""
accounts/views.py

Auth endpoints for the Financial System hub.

Security notes
--------------
fix #1  LoginView is rate-limited (10/min per IP) via LoginRateThrottle.
fix #2  LoginView and VerifyOTPView return HTTP 403 when AUTH_MODE == "keycloak".
fix #3C VerifyOTPView no longer accepts a client-supplied break_glass param.
fix #3B OTPs are filtered by purpose='login' only.
fix #4  Password check runs before is_active check; non-existent users go
        through a dummy hash to equalize timing (account enumeration defence).
fix #7D must_change_password is returned in every token response; ChangePasswordView
        enforces the policy.
"""

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError

from .models import User, EmailOTP, OTPPurpose
from .otp_delivery import deliver_otp
from audit.models import AuditLog, AuditEvent

# A pre-hashed unusable password used as a timing equaliser when a user is
# not found — prevents measurably faster responses for non-existent accounts.
_DUMMY_HASH = make_password("dummy-constant-for-timing-equalisation")


# ── Throttle ──────────────────────────────────────────────────────────────────

class LoginRateThrottle(AnonRateThrottle):
    """10 requests/min per IP on the login endpoint (fix #1)."""
    scope = 'login'


# ── Permission guard ──────────────────────────────────────────────────────────

def _native_mode_check():
    """Return a 403 response if AUTH_MODE is not 'native', else None."""
    if getattr(settings, "AUTH_MODE", "native") != "native":
        return Response(
            {"detail": "Native login is disabled. Please use your organisation's SSO portal."},
            status=status.HTTP_403_FORBIDDEN,
        )
    return None


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

class LoginView(APIView):
    """
    Native credential check → OTP dispatch.

    fix #1:  rate-limited to 10/min per IP
    fix #2:  blocked when AUTH_MODE != "native"
    fix #4:  inactive check AFTER password check; non-existent path runs dummy hash
    """
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [LoginRateThrottle]

    def post(self, request):
        blocked = _native_mode_check()
        if blocked:
            return blocked

        email = (request.data.get('email') or '').strip().lower()
        password = request.data.get('password') or ''

        if not email or not password:
            return Response(
                {'detail': 'Email and password required'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Always look up; use dummy hash if not found to equalise timing.
        try:
            user = User.objects.get(email__iexact=email)
            stored_hash = user.password
        except User.DoesNotExist:
            user = None
            stored_hash = _DUMMY_HASH

        password_ok = check_password(password, stored_hash)

        # Evaluate success only after the constant-time hash comparison.
        if not password_ok or user is None:
            AuditLog.objects.create(
                event=AuditEvent.USER_LOGIN_FAILED,
                actor=None,
                changes={'email': email, 'reason': 'Invalid credentials'},
            )
            return Response(
                {'detail': 'Invalid credentials'},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        # Inactive check comes AFTER successful password check (no enumeration).
        if not user.is_active:
            AuditLog.objects.create(
                event=AuditEvent.USER_LOGIN_FAILED,
                actor=user,
                changes={'reason': 'Account inactive'},
            )
            return Response(
                {'detail': 'Account is inactive'},
                status=status.HTTP_403_FORBIDDEN,
            )

        otp = EmailOTP.generate(user, purpose=OTPPurpose.LOGIN)
        if not deliver_otp(user, otp):
            return Response(
                {'detail': 'Could not send the verification code. Please try again shortly.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        return Response({
            'user_id': str(user.id),
            'message': 'OTP sent to your email',
        })


class VerifyOTPView(APIView):
    """
    Verify a login OTP and issue JWT tokens.

    fix #2:  blocked when AUTH_MODE != "native"
    fix #1:  OTP voided after 5 wrong attempts (enforced in EmailOTP.record_failed_attempt)
    fix #3B: only looks at purpose='login' OTPs
    fix #3C: break_glass body param is completely ignored
    fix #7D: returns must_change_password
    """
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        blocked = _native_mode_check()
        if blocked:
            return blocked

        user_id = request.data.get('user_id')
        otp_code = request.data.get('otp')

        if not user_id or not otp_code:
            return Response(
                {'detail': 'user_id and otp required'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user = User.objects.get(id=user_id)
        except (User.DoesNotExist, ValueError):
            return Response({'detail': 'Invalid session.'}, status=status.HTTP_400_BAD_REQUEST)

        # Fetch the most recent valid login OTP only (fix #3B — no break_glass OTPs here)
        otp = (
            EmailOTP.objects
            .filter(user=user, used=False, purpose=OTPPurpose.LOGIN)
            .order_by('-created_at')
            .first()
        )

        if not otp or not otp.is_valid():
            return Response({'detail': 'No valid OTP found. Please restart the login.'}, status=status.HTTP_400_BAD_REQUEST)

        if otp.code != otp_code:
            otp.record_failed_attempt()  # voids after 5 tries (fix #1)
            AuditLog.objects.create(
                event=AuditEvent.USER_LOGIN_FAILED,
                actor=user,
                changes={'reason': 'Invalid OTP'},
            )
            remaining = max(0, EmailOTP.MAX_ATTEMPTS - otp.attempts)
            detail = (
                'Invalid OTP.' if remaining > 0
                else 'Too many failed attempts. Please restart the login.'
            )
            return Response({'detail': detail}, status=status.HTTP_401_UNAUTHORIZED)

        otp.mark_used()
        user.last_login = timezone.now()
        user.save(update_fields=['last_login'])

        refresh = RefreshToken.for_user(user)
        AuditLog.objects.create(event=AuditEvent.USER_LOGIN, actor=user)

        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': _user_payload(user),
        })


class MeView(APIView):
    """Get current user information. fix #7D: includes must_change_password."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(_user_payload(request.user))


class ChangePasswordView(APIView):
    """
    Allow a user to change their own password.
    fix #7D: clears must_change_password on success.
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


class TokenRefreshWithBlacklistView(APIView):
    """
    Thin wrapper — simplejwt's built-in TokenRefreshView handles blacklisting
    automatically when BLACKLIST_AFTER_ROTATION is True (fix #7B). This view
    is here only to centralise the logout path.
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
    Blacklist the refresh token on logout (fix #7B).
    Frontend must also call oidcLogout() to end the Keycloak session (fix #7C).
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
    fix #7D: returns must_change_password (always False for KC-provisioned users).
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
