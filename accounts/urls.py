from django.urls import path
from . import views
from . import break_glass_views

urlpatterns = [
    # OIDC exchange (Keycloak mode)
    path('oidc/exchange/', views.OIDCExchangeView.as_view(), name='oidc-exchange'),
    # Session
    path('me/', views.MeView.as_view(), name='me'),
    path('token/refresh/', views.TokenRefreshView.as_view(), name='token_refresh'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('change-password/', views.ChangePasswordView.as_view(), name='change-password'),
    # Break-glass (emergency access when Keycloak is down)
    path('break-glass-login/', break_glass_views.BreakGlassLoginView.as_view(), name='break-glass-login-api'),
    path('break-glass-verify-otp/', break_glass_views.BreakGlassVerifyOTPView.as_view(), name='break-glass-verify-otp'),
    path('break-glass-redeem/', break_glass_views.BreakGlassRedeemView.as_view(), name='break-glass-redeem'),
]
