"""
financial_system/urls.py

URL configuration for the financial system project
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from accounts.break_glass_views import break_glass_page

urlpatterns = [
    # Hidden break-glass route (intentionally obfuscated URL)
    path('operations/console/', break_glass_page, name='break-glass-login'),
    
    path('admin/', admin.site.urls),
    
    # Public API endpoints
    path('api/v1/config/', include('licensing.urls')),
    path('api/v1/auth/', include('accounts.urls')),
    
    # Internal IDP API (for Keycloak User Storage SPI)
    path('internal/idp/', include('accounts.internal_urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
