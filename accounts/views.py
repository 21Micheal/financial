"""
accounts/views.py

Authentication views for the financial system
"""
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.contrib.auth.hashers import check_password
from django.utils import timezone
from .models import User, EmailOTP
from .otp_delivery import deliver_otp
from audit.models import AuditLog, AuditEvent


class LoginView(APIView):
    """
    Native login endpoint - validates credentials and initiates OTP flow
    """
    authentication_classes = []
    permission_classes = [AllowAny]
    
    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')
        
        if not email or not password:
            return Response(
                {'detail': 'Email and password required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            user = User.objects.get(email__iexact=email)
            
            if not user.is_active:
                AuditLog.objects.create(
                    event=AuditEvent.USER_LOGIN_FAILED,
                    actor=user,
                    changes={'reason': 'Account inactive'}
                )
                return Response(
                    {'detail': 'Account is inactive'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            if check_password(password, user.password):
                otp = EmailOTP.generate(user)
                if not deliver_otp(user, otp):
                    return Response(
                        {'detail': 'Could not send the verification code. Please try again shortly.'},
                        status=status.HTTP_503_SERVICE_UNAVAILABLE,
                    )
                
                return Response({
                    'user_id': str(user.id),
                    'message': 'OTP sent to your email'
                })
            else:
                AuditLog.objects.create(
                    event=AuditEvent.USER_LOGIN_FAILED,
                    actor=None,
                    changes={'email': email, 'reason': 'Invalid password'}
                )
                return Response(
                    {'detail': 'Invalid credentials'},
                    status=status.HTTP_401_UNAUTHORIZED
                )
        except User.DoesNotExist:
            AuditLog.objects.create(
                event=AuditEvent.USER_LOGIN_FAILED,
                actor=None,
                changes={'email': email, 'reason': 'User not found'}
            )
            return Response(
                {'detail': 'Invalid credentials'},
                status=status.HTTP_401_UNAUTHORIZED
            )


class VerifyOTPView(APIView):
    """
    Verify OTP and issue JWT tokens
    """
    authentication_classes = []
    permission_classes = [AllowAny]
    
    def post(self, request):
        user_id = request.data.get('user_id')
        otp_code = request.data.get('otp')
        break_glass = request.data.get('break_glass', False)
        
        if not user_id or not otp_code:
            return Response(
                {'detail': 'user_id and otp required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            user = User.objects.get(id=user_id)
            
            # Get the most recent unused OTP
            otp = EmailOTP.objects.filter(
                user=user,
                used=False
            ).order_by('-created_at').first()
            
            if not otp:
                return Response(
                    {'detail': 'No valid OTP found'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if not otp.is_valid():
                return Response(
                    {'detail': 'OTP has expired'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if otp.code != otp_code:
                AuditLog.objects.create(
                    event=AuditEvent.USER_LOGIN_FAILED if not break_glass else AuditEvent.USER_BREAK_GLASS_LOGIN_FAILED,
                    actor=user,
                    changes={'reason': 'Invalid OTP'}
                )
                return Response(
                    {'detail': 'Invalid OTP'},
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            # Mark OTP as used
            otp.mark_used()
            
            # Update last login
            user.last_login = timezone.now()
            user.save()
            
            # Generate JWT tokens
            from rest_framework_simplejwt.tokens import RefreshToken
            refresh = RefreshToken.for_user(user)
            
            # Log successful login
            AuditLog.objects.create(
                event=AuditEvent.USER_LOGIN if not break_glass else AuditEvent.USER_BREAK_GLASS_LOGIN,
                actor=user
            )
            
            return Response({
                'access': str(refresh.access_token),
                'refresh': str(refresh),
                'user': {
                    'id': str(user.id),
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'role': user.role,
                    'organization_id': str(user.organization.id) if user.organization else None,
                    'is_staff': user.is_staff,
                    'is_superuser': user.is_superuser,
                }
            })
            
        except User.DoesNotExist:
            return Response(
                {'detail': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )


class MeView(APIView):
    """
    Get current user information
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        return Response({
            'id': str(user.id),
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'role': user.role,
            'organization_id': str(user.organization.id) if user.organization else None,
            'is_staff': user.is_staff,
            'is_superuser': user.is_superuser,
        })


class OIDCExchangeView(APIView):
    """
    SPA PKCE completed against Keycloak; exchange a validated id_token for hub JWTs.
    """
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        import jwt as pyjwt
        from rest_framework_simplejwt.tokens import RefreshToken
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
            return Response({"detail": "Account is inactive"}, status=status.HTTP_403_FORBIDDEN)

        user.last_login = timezone.now()
        user.save(update_fields=["last_login"])
        refresh = RefreshToken.for_user(user)
        AuditLog.objects.create(event=AuditEvent.USER_LOGIN, actor=user, changes={"auth_mode": "keycloak"})
        return Response({
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": {
                "id": str(user.id),
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "role": user.role,
                "organization_id": str(user.organization.id) if user.organization else None,
                "is_staff": user.is_staff,
                "is_superuser": user.is_superuser,
            },
        })
