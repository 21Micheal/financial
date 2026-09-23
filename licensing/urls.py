"""
licensing/urls.py

URL configuration for licensing app
"""
from django.urls import path
from . import views

urlpatterns = [
    path('', views.ConfigView.as_view(), name='config'),
    path('launcher/systems/', views.LauncherView.as_view(), name='launcher-systems'),
    path('launcher/sso/<str:system>/', views.SSOInitiateView.as_view(), name='sso-initiate'),
]
