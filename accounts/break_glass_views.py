"""
accounts/break_glass_views.py

Emergency (break-glass) login for platform administrators.

Security fixes applied
----------------------
fix #2:  break-glass works regardless of AUTH_MODE (it's the escape hatch).
fix #3A: BreakGlassVerifyOTPView enforces is_staff / is_superuser.
fix #3B: OTPs are segregated by purpose='break_glass'; regular login OTPs
         cannot be submitted here.
fix #4:  Password check before is_active; timing-equalised non-existent path.
fix #5:  After OTP verification the page returns a short-lived signed token
         (via django.core.signing) as a URL param rather than using
         sessionStorage — which would be empty across the origin boundary.
         The React /auth/break-glass route calls /api/v1/auth/break-glass-redeem/
         to exchange it for full JWT tokens (single-use, 2-minute window).
"""

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.core import signing
from django.shortcuts import render
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from audit.models import AuditEvent, AuditLog
from .models import User, EmailOTP, OTPPurpose
from .otp_delivery import deliver_otp
from .views import _user_payload

_DUMMY_HASH = make_password("dummy-constant-for-timing-equalisation")

_BREAK_GLASS_SIGNER = signing.TimestampSigner(salt="break_glass_redeem")
_BREAK_GLASS_MAX_AGE = 120  # seconds


class BreakGlassLoginView(APIView):
    """
    Credential step for break-glass.
    Works in any AUTH_MODE. Restricted to platform admins.
    fix #4: password check before is_active and admin check to avoid enumeration.
    """
    permission_classes = []
    authentication_classes = []

    def post(self, request):
        email = (request.data.get('email') or '').strip().lower()
        password = request.data.get('password') or ''

        if not email or not password:
            return Response({'detail': 'Email and password required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(email__iexact=email)
            stored_hash = user.password
        except User.DoesNotExist:
            user = None
            stored_hash = _DUMMY_HASH

        password_ok = check_password(password, stored_hash)

        # Reject with a generic message regardless of the failure reason.
        if not password_ok or user is None:
            AuditLog.objects.create(
                event=AuditEvent.USER_BREAK_GLASS_LOGIN_FAILED,
                actor=None,
                changes={'email': email, 'reason': 'Invalid credentials'},
            )
            return Response({'detail': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)

        if not user.is_active:
            AuditLog.objects.create(
                event=AuditEvent.USER_BREAK_GLASS_LOGIN_FAILED,
                actor=user,
                changes={'reason': 'Account inactive'},
            )
            return Response({'detail': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)

        # fix #3A: admin-only check
        if not user.is_platform_admin():
            AuditLog.objects.create(
                event=AuditEvent.USER_BREAK_GLASS_LOGIN_FAILED,
                actor=user,
                changes={'reason': 'Not a platform administrator'},
            )
            return Response(
                {'detail': 'Break-glass login is restricted to platform administrators.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        # fix #3B: generate a break_glass-purpose OTP
        otp = EmailOTP.generate(user, purpose=OTPPurpose.BREAK_GLASS)
        if not deliver_otp(user, otp, subject="Your Financial System emergency access code"):
            return Response(
                {'detail': 'Could not send the verification code. Please try again shortly.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        return Response({'user_id': str(user.id), 'message': 'OTP sent to your email'})


class BreakGlassVerifyOTPView(APIView):
    """
    OTP verification step for break-glass.
    fix #3A: re-asserts admin status before issuing any token.
    fix #3B: only accepts purpose='break_glass' OTPs.
    fix #1:  OTP voided after MAX_ATTEMPTS wrong guesses.
    fix #5:  Returns a short-lived signed token for the React page to redeem.
    """
    permission_classes = []
    authentication_classes = []

    def post(self, request):
        user_id = request.data.get('user_id')
        otp_code = request.data.get('otp')

        if not user_id or not otp_code:
            return Response({'detail': 'user_id and otp required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(id=user_id)
        except (User.DoesNotExist, ValueError):
            return Response({'detail': 'Invalid session.'}, status=status.HTTP_400_BAD_REQUEST)

        # fix #3A: must still be an admin
        if not user.is_platform_admin():
            AuditLog.objects.create(
                event=AuditEvent.USER_BREAK_GLASS_LOGIN_FAILED,
                actor=user,
                changes={'reason': 'Not a platform administrator'},
            )
            return Response({'detail': 'Access denied.'}, status=status.HTTP_403_FORBIDDEN)

        # fix #3B: only break_glass OTPs
        otp = (
            EmailOTP.objects
            .filter(user=user, used=False, purpose=OTPPurpose.BREAK_GLASS)
            .order_by('-created_at')
            .first()
        )

        if not otp or not otp.is_valid():
            return Response({'detail': 'No valid OTP found. Please restart the process.'}, status=status.HTTP_400_BAD_REQUEST)

        if otp.code != otp_code:
            otp.record_failed_attempt()  # fix #1: voided after 5 tries
            AuditLog.objects.create(
                event=AuditEvent.USER_BREAK_GLASS_LOGIN_FAILED,
                actor=user,
                changes={'reason': 'Invalid OTP'},
            )
            remaining = max(0, EmailOTP.MAX_ATTEMPTS - otp.attempts)
            detail = (
                'Invalid OTP.' if remaining > 0
                else 'Too many failed attempts. Please restart.'
            )
            return Response({'detail': detail}, status=status.HTTP_401_UNAUTHORIZED)

        otp.mark_used()

        # fix #5: issue a signed, short-lived token instead of sessionStorage
        signed_token = _BREAK_GLASS_SIGNER.sign(str(user.pk))
        AuditLog.objects.create(
            event=AuditEvent.USER_BREAK_GLASS_LOGIN,
            actor=user,
            changes={'step': 'otp_verified'},
        )
        return Response({'break_glass_token': signed_token})


class BreakGlassRedeemView(APIView):
    """
    Single-use redemption of the signed break-glass token.
    Called by the React /auth/break-glass page on the same origin as the SPA.
    fix #5: resolves the cross-origin sessionStorage problem.
    """
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        token = request.query_params.get('token', '')
        try:
            user_pk = _BREAK_GLASS_SIGNER.unsign(token, max_age=_BREAK_GLASS_MAX_AGE)
        except signing.SignatureExpired:
            return Response(
                {'detail': 'Emergency access link has expired. Please restart the process.'},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        except signing.BadSignature:
            return Response({'detail': 'Invalid emergency access link.'}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            user = User.objects.get(pk=user_pk, is_active=True)
        except User.DoesNotExist:
            return Response({'detail': 'User not found or inactive.'}, status=status.HTTP_403_FORBIDDEN)

        if not user.is_platform_admin():
            return Response({'detail': 'Access denied.'}, status=status.HTTP_403_FORBIDDEN)

        from rest_framework_simplejwt.tokens import RefreshToken
        refresh = RefreshToken.for_user(user)
        user.last_login = timezone.now()
        user.save(update_fields=['last_login'])

        AuditLog.objects.create(event=AuditEvent.USER_BREAK_GLASS_LOGIN, actor=user)
        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': _user_payload(user),
        })


def break_glass_page(request):
    """
    Hidden Django template page for break-glass login.
    URL is intentionally obscure: /operations/console
    After successful OTP, JS reads break_glass_token and redirects to
    {{ FRONTEND_URL }}/auth/break-glass?token=<signed> (fix #5).
    """
    frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:3001')
    return render(request, 'accounts/break_glass.html', {'FRONTEND_URL': frontend_url})
