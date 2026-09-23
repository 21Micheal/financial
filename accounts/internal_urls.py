from django.urls import path

from .internal_idp import (
    InternalIdpUserAuthorizationView,
    InternalIdpUserCreateView,
    InternalIdpUserLookupView,
    InternalIdpUserPasswordView,
    InternalIdpUserProfileView,
    InternalIdpUserSearchView,
    InternalIdpValidatePasswordView,
)

urlpatterns = [
    path("users/", InternalIdpUserCreateView.as_view(), name="internal-idp-user-create"),
    path("users/lookup/", InternalIdpUserLookupView.as_view(), name="internal-idp-user-lookup"),
    path("users/search/", InternalIdpUserSearchView.as_view(), name="internal-idp-user-search"),
    path("users/validate-password/", InternalIdpValidatePasswordView.as_view(), name="internal-idp-validate-password"),
    path("users/authorization/", InternalIdpUserAuthorizationView.as_view(), name="internal-idp-user-authorization-email"),
    path("users/<uuid:user_id>/", InternalIdpUserProfileView.as_view(), name="internal-idp-user-profile"),
    path("users/<uuid:user_id>/password/", InternalIdpUserPasswordView.as_view(), name="internal-idp-user-password"),
    path(
        "users/<uuid:user_id>/authorization/",
        InternalIdpUserAuthorizationView.as_view(),
        name="internal-idp-user-authorization",
    ),
]
