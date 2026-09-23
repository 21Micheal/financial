"""
accounts/urls.py

URL configuration for accounts app
"""
from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from . import views
from . import break_glass_views

urlpatterns = [
    path('login/', views.LoginView.as_view(), name='login'),
    path('verify-otp/', views.VerifyOTPView.as_view(), name='verify-otp'),
    path('me/', views.MeView.as_view(), name='me'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    # Break-glass endpoints (hidden)
    path('break-glass-login/', break_glass_views.BreakGlassLoginView.as_view(), name='break-glass-login-api'),
]
