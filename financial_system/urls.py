from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from accounts.break_glass_views import break_glass_page
from licensing.views import ConfigView

urlpatterns = [
    path("operations/console/", break_glass_page, name="break-glass-login"),
    path("admin/", admin.site.urls),
    path("api/v1/config/", ConfigView.as_view(), name="config"),
    path("api/v1/launcher/", include("licensing.urls")),
    path("api/v1/auth/", include("accounts.urls")),
    path("api/v1/internal/idp/", include("accounts.internal_urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
