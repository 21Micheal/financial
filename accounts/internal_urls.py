"""
accounts/internal_urls.py

URL configuration for internal IDP API endpoints
These are protected by shared secret API key and used by Keycloak User Storage SPI
"""
from django.urls import path
from .internal_idp import (
    UserLookupView,
    UserSearchView,
    UserValidateView,
    UserCreateView,
    UserUpdateView,
    UserDeleteView,
)

urlpatterns = [
    path('user/lookup/', UserLookupView.as_view(), name='internal-user-lookup'),
    path('user/search/', UserSearchView.as_view(), name='internal-user-search'),
    path('user/validate/', UserValidateView.as_view(), name='internal-user-validate'),
    path('user/create/', UserCreateView.as_view(), name='internal-user-create'),
    path('user/update/', UserUpdateView.as_view(), name='internal-user-update'),
    path('user/delete/', UserDeleteView.as_view(), name='internal-user-delete'),
]
