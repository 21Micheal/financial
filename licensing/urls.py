from django.urls import path
from . import views

urlpatterns = [
    path("systems/", views.LauncherView.as_view(), name="launcher-systems"),
    path("sso/<str:system>/", views.SSOInitiateView.as_view(), name="sso-initiate"),
]
