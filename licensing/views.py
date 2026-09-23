"""
licensing/views.py

Views for licensing and launcher functionality
"""
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from .models import ClientOrganization, SystemLicense, UserSystemRole, SystemType, SystemRole
from audit.models import AuditLog, AuditEvent


class ConfigView(APIView):
    """
    Public configuration endpoint.
    Returns deployment settings like AUTH_MODE that the frontend needs to
    conditionally render the appropriate login UI.
    """
    permission_classes = [AllowAny]
    
    def get(self, request):
        return Response({
            'auth_mode': getattr(settings, 'AUTH_MODE', 'native'),
            'launcher_enabled': True,  # Launcher is always enabled in financial system
        })


class LauncherView(APIView):
    """
    Launcher endpoint - returns list of licensed systems for the user's organization
    along with their provisioning status and access information.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        
        if not user.organization:
            return Response({
                'systems': [],
                'message': 'User is not assigned to an organization'
            })
        
        # Get all active licenses for the user's organization
        licenses = SystemLicense.objects.filter(
            organization=user.organization,
            is_active=True
        ).select_related('organization')
        
        systems = []
        
        for license in licenses:
            # Check if user has a role in this system
            user_role = UserSystemRole.objects.filter(
                user=user,
                organization=user.organization,
                system=license.system,
                is_active=True
            ).first()
            
            system_data = {
                'system': license.system,
                'system_display': license.get_system_display(),
                'is_active': license.is_active,
                'user_role': user_role.role if user_role else None,
                'user_role_display': user_role.get_role_display() if user_role else None,
                'access_granted': bool(user_role),
                'access_message': None,
            }
            
            # Set access message if not provisioned
            if not user_role:
                system_data['access_message'] = (
                    f"Your organization is licensed for {license.get_system_display()}, "
                    f"but you have not been granted access. Contact your administrator."
                )
            
            systems.append(system_data)
        
        return Response({'systems': systems})


class SSOInitiateView(APIView):
    """
    Initiate SSO redirect to a licensed system.
    Returns the appropriate Keycloak authorization URL for the target system.
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request, system):
        user = request.user
        
        # Validate system type
        valid_systems = [choice[0] for choice in SystemType.choices]
        if system not in valid_systems:
            return Response(
                {'detail': 'Invalid system'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if organization has license for this system
        if not user.organization:
            return Response(
                {'detail': 'User is not assigned to an organization'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        license = SystemLicense.objects.filter(
            organization=user.organization,
            system=system,
            is_active=True
        ).first()
        
        if not license:
            AuditLog.objects.create(
                event=AuditEvent.SYSTEM_ACCESS_BLOCKED,
                actor=user,
                changes={'system': system, 'reason': 'Organization not licensed'}
            )
            return Response(
                {'detail': f'Your organization is not licensed for {license.get_system_display() if license else system}'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Check if user has role in this system
        user_role = UserSystemRole.objects.filter(
            user=user,
            organization=user.organization,
            system=system,
            is_active=True
        ).first()
        
        if not user_role:
            AuditLog.objects.create(
                event=AuditEvent.SYSTEM_ACCESS_DENIED,
                actor=user,
                changes={'system': system, 'reason': 'User not provisioned'}
            )
            return Response(
                {
                    'detail': (
                        f'Your organization is licensed for {license.get_system_display()}, '
                        f'but you have not been granted access. Contact your administrator.'
                    )
                },
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Generate SSO URL based on system
        # Each system has its own Keycloak client ID
        system_client_ids = {
            'dms': 'dms-client',
            'inventory': 'inventory-client',  # To be created
            'financial': 'financial-client',  # This system itself
        }
        
        client_id = system_client_ids.get(system, 'dms-client')
        
        # Build Keycloak authorization URL
        keycloak_url = getattr(settings, 'KEYCLOAK_URL', 'http://localhost:8080')
        realm = getattr(settings, 'KEYCLOAK_REALM', 'idp-dev')
        
        # For DMS, use the existing frontend URL
        system_redirect_urls = {
            'dms': 'http://localhost:3000/auth/callback',
            'inventory': 'http://localhost:3002/auth/callback',  # To be configured
            'financial': 'http://localhost:3001/auth/callback',
        }
        
        redirect_uri = system_redirect_urls.get(system, 'http://localhost:3000/auth/callback')
        
        auth_url = (
            f"{keycloak_url}/realms/{realm}/protocol/openid-connect/auth"
            f"?client_id={client_id}"
            f"&redirect_uri={redirect_uri}"
            f"&response_type=code"
            f"&scope=openid"
        )
        
        AuditLog.objects.create(
            event=AuditEvent.SYSTEM_ACCESS_GRANTED,
            actor=user,
            changes={'system': system, 'role': user_role.role}
        )
        
        return Response({
            'sso_url': auth_url,
            'system': system,
            'system_display': license.get_system_display(),
            'user_role': user_role.role,
        })
