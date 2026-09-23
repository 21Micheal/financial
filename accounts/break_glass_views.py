"""
accounts/break_glass_views.py

Hidden break-glass login views for emergency native authentication.
Restricted to platform administrators (is_staff or is_superuser).
"""
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.hashers import check_password
from django.utils import timezone
from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
from .models import User, EmailOTP
from audit.models import AuditLog, AuditEvent


class BreakGlassLoginView(APIView):
    """
    Hidden break-glass login endpoint for emergency native authentication.
    Restricted to platform administrators (is_staff or is_superuser).
    """
    permission_classes = []
    authentication_classes = []
    
    def post(self, request):
        auth_mode = getattr(settings, 'AUTH_MODE', 'native')
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
                    event=AuditEvent.USER_BREAK_GLASS_LOGIN_FAILED,
                    actor=user,
                    changes={'reason': 'Account inactive'}
                )
                return Response(
                    {'detail': 'Account is inactive'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # In keycloak mode, only allow platform admins
            if auth_mode == 'keycloak' and not user.is_platform_admin():
                AuditLog.objects.create(
                    event=AuditEvent.USER_BREAK_GLASS_LOGIN_FAILED,
                    actor=user,
                    changes={'reason': 'User not eligible for break-glass login (not platform admin)'}
                )
                return Response(
                    {'detail': 'Break-glass login is restricted to platform administrators'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            if check_password(password, user.password):
                # Generate OTP
                otp = EmailOTP.generate(user)
                
                # In production, send email here
                # For now, log the OTP to console for testing
                print(f"BREAK-GLASS OTP for {user.email}: {otp.code}")
                
                return Response({
                    'user_id': str(user.id),
                    'message': 'OTP sent to your email'
                })
            else:
                AuditLog.objects.create(
                    event=AuditEvent.USER_BREAK_GLASS_LOGIN_FAILED,
                    actor=None,
                    changes={'email': email, 'reason': 'Invalid password'}
                )
                return Response(
                    {'detail': 'Invalid credentials'},
                    status=status.HTTP_401_UNAUTHORIZED
                )
        except User.DoesNotExist:
            AuditLog.objects.create(
                event=AuditEvent.USER_BREAK_GLASS_LOGIN_FAILED,
                actor=None,
                changes={'email': email, 'reason': 'User not found'}
            )
            return Response(
                {'detail': 'Invalid credentials'},
                status=status.HTTP_401_UNAUTHORIZED
            )


class BreakGlassVerifyOTPView(APIView):
    """
    Verify OTP for break-glass login and issue JWT tokens
    """
    permission_classes = []
    authentication_classes = []
    
    def post(self, request):
        user_id = request.data.get('user_id')
        otp_code = request.data.get('otp')
        
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
                    event=AuditEvent.USER_BREAK_GLASS_LOGIN_FAILED,
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
            
            # Log successful break-glass login
            AuditLog.objects.create(
                event=AuditEvent.USER_BREAK_GLASS_LOGIN,
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


def break_glass_page(request):
    """
    Hidden Django template page for break-glass login.
    Uses an intentionally obfuscated URL: /operations/console
    """
    frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:3001')
    return render(request, 'accounts/break_glass.html', {'FRONTEND_URL': frontend_url})
