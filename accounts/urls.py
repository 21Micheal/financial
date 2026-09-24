from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from . import views
from . import break_glass_views

urlpatterns = [
    # Native auth (blocked when AUTH_MODE=keycloak)
    path('login/', views.LoginView.as_view(), name='login'),
    path('verify-otp/', views.VerifyOTPView.as_view(), name='verify-otp'),
    # OIDC exchange
    path('oidc/exchange/', views.OIDCExchangeView.as_view(), name='oidc-exchange'),
    # Session
    path('me/', views.MeView.as_view(), name='me'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('change-password/', views.ChangePasswordView.as_view(), name='change-password'),
    # Break-glass (always active regardless of AUTH_MODE)
    path('break-glass-login/', break_glass_views.BreakGlassLoginView.as_view(), name='break-glass-login-api'),
    path('break-glass-verify-otp/', break_glass_views.BreakGlassVerifyOTPView.as_view(), name='break-glass-verify-otp'),
    path('break-glass-redeem/', break_glass_views.BreakGlassRedeemView.as_view(), name='break-glass-redeem'),
]
