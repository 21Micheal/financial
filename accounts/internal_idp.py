"""
accounts/internal_idp.py

Internal API endpoints for Keycloak User Storage SPI federation.
These endpoints are protected by a shared secret (FINANCIAL_INTERNAL_IDP_API_KEY)
and must NOT inherit DRF's global authentication classes.
"""
from django.conf import settings
from django.contrib.auth.hashers import check_password
from django.http import JsonResponse, Http404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Q
from django.utils import timezone
from .models import User


class InternalIdpAPIView(APIView):
    """
    Base view for internal IDP API endpoints.
    Protected by shared secret API key, NOT DRF's global authentication.
    """
    authentication_classes = []  # Critical: empty to avoid DRF global auth interception
    permission_classes = []
    
    def dispatch(self, request, *args, **kwargs):
        # Verify API key
        api_key = request.headers.get('X-Internal-IDP-API-Key')
        expected_key = getattr(settings, 'FINANCIAL_INTERNAL_IDP_API_KEY', '')
        
        if not api_key or api_key != expected_key:
            return Response(
                {'detail': 'Invalid or missing API key'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        return super().dispatch(request, *args, **kwargs)


class UserLookupView(InternalIdpAPIView):
    """
    Look up a user by username (email).
    Used by Keycloak User Storage SPI for authentication.
    """
    def get(self, request):
        username = request.query_params.get('username')
        if not username:
            return Response(
                {'detail': 'username parameter required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            user = User.objects.get(email__iexact=username)
            return Response({
                'id': str(user.id),
                'username': user.email,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'enabled': user.is_active,
                'email_verified': True,
                'attributes': {
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


class UserSearchView(InternalIdpAPIView):
    """
    Search for users by email or name.
    Used by Keycloak User Storage SPI for user search.
    """
    def get(self, request):
        query = request.query_params.get('search', '')
        max_results = int(request.query_params.get('max', '10'))
        
        if not query:
            return Response(
                {'detail': 'search parameter required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        users = User.objects.filter(
            Q(email__icontains=query) |
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query)
        ).filter(is_active=True)[:max_results]
        
        results = [
            {
                'id': str(user.id),
                'username': user.email,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'enabled': user.is_active,
            }
            for user in users
        ]
        
        return Response({'users': results})


class UserValidateView(InternalIdpAPIView):
    """
    Validate user credentials.
    Used by Keycloak User Storage SPI for password authentication.
    """
    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        
        if not username or not password:
            return Response(
                {'detail': 'username and password required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            user = User.objects.get(email__iexact=username)
            if not user.is_active:
                return Response(
                    {'detail': 'User account is disabled'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            if check_password(password, user.password):
                return Response({'valid': True})
            else:
                return Response(
                    {'valid': False, 'detail': 'Invalid password'},
                    status=status.HTTP_401_UNAUTHORIZED
                )
        except User.DoesNotExist:
            return Response(
                {'valid': False, 'detail': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )


class UserCreateView(InternalIdpAPIView):
    """
    Create a new user (write-through from Keycloak admin console).
    Used by Keycloak User Storage SPI when users are created via Keycloak admin.
    """
    def post(self, request):
        email = request.data.get('email')
        first_name = request.data.get('first_name', '')
        last_name = request.data.get('last_name', '')
        password = request.data.get('password', '')
        
        if not email:
            return Response(
                {'detail': 'email required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if user already exists
        if User.objects.filter(email__iexact=email).exists():
            return Response(
                {'detail': 'User already exists'},
                status=status.HTTP_409_CONFLICT
            )
        
        # Create user
        user = User.objects.create_user(
            email=email,
            first_name=first_name,
            last_name=last_name,
            password=password if password else None,
            role='client_user',  # Default role for Keycloak-created users
            must_change_password=True if password else False
        )
        
        return Response({
            'id': str(user.id),
            'username': user.email,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'enabled': user.is_active,
        }, status=status.HTTP_201_CREATED)


class UserUpdateView(InternalIdpAPIView):
    """
    Update user profile or password.
    Used by Keycloak User Storage SPI for profile updates.
    """
    def put(self, request):
        username = request.data.get('username')
        if not username:
            return Response(
                {'detail': 'username required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            user = User.objects.get(email__iexact=username)
            
            # Update fields if provided
            if 'first_name' in request.data:
                user.first_name = request.data['first_name']
            if 'last_name' in request.data:
                user.last_name = request.data['last_name']
            if 'email' in request.data:
                user.email = request.data['email']
            if 'password' in request.data:
                user.set_password(request.data['password'])
                user.password_changed_at = timezone.now()
                user.must_change_password = False
            
            user.save()
            
            return Response({
                'id': str(user.id),
                'username': user.email,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'enabled': user.is_active,
            })
        except User.DoesNotExist:
            return Response(
                {'detail': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )


class UserDeleteView(InternalIdpAPIView):
    """
    Soft-delete a user (deactivate account).
    Used by Keycloak User Storage SPI for user deletion.
    """
    def delete(self, request):
        username = request.query_params.get('username')
        if not username:
            return Response(
                {'detail': 'username parameter required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            user = User.objects.get(email__iexact=username)
            user.is_active = False
            user.save()
            
            return Response({'detail': 'User deactivated'})
        except User.DoesNotExist:
            return Response(
                {'detail': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )
