"""
Financial System Django Settings
Reads environment via django-environ. Copy .env.example → .env and adjust.
"""
from pathlib import Path
from datetime import timedelta
import sys
import environ
import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(DEBUG=(bool, False))
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("SECRET_KEY", default="insecure-dev-secret-change-me")
DEBUG = env("DEBUG")

ALLOWED_HOSTS = env.list(
    "ALLOWED_HOSTS",
    default=[
        "localhost",
        "127.0.0.1",
        "financial-backend",
        "frontend",
        "nginx",
    ],
)

CSRF_TRUSTED_ORIGINS = env.list(
    "CSRF_TRUSTED_ORIGINS",
    default=[
        "http://localhost:3001",
    ]
)

FRONTEND_URL = env("FRONTEND_URL", default="http://localhost:3001")

USE_X_FORWARDED_HOST = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third-party
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",  # fix #7B: enables blacklist on rotation
    "corsheaders",
    "django_filters",
    # Local
    "accounts",
    "licensing",
    "audit",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = 'financial_system.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'financial_system.wsgi.application'

DATABASES = {
    "default": dj_database_url.parse(
        env(
            "DATABASE_URL",
            default="postgres://financial_user:financial_password@db:5432/financial_db",
        ),
        conn_max_age=600,
        conn_health_checks=True,
    )
}

if "test" in sys.argv:
    DATABASES["default"] = {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }

# Redis cache — used by DRF throttling and JWKS cache
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": env("REDIS_URL", default="redis://localhost:6379/0"),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {'min_length': 10},
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

AUTH_USER_MODEL = 'accounts.User'

# CORS
CORS_ALLOWED_ORIGINS = env.list(
    "CORS_ALLOWED_ORIGINS",
    default=[
        "http://localhost:3001",
        "http://127.0.0.1:3001",
    ],
)
CORS_ALLOW_CREDENTIALS = True

# REST Framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    # Throttling — fix #1: rate-limit login endpoint
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '60/min',
        'login': '10/min',
    },
    'EXCEPTION_HANDLER': 'rest_framework.views.exception_handler',
}

# Simple JWT — fix #7B: blacklist app installed above, so rotation blacklisting works
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
}

# Auth Mode — "native" or "keycloak"
AUTH_MODE = env("AUTH_MODE", default="native")

# Internal IDP API Key (must match FINANCIAL_INTERNAL_IDP_API_KEY in SSO/.env)
FINANCIAL_INTERNAL_IDP_API_KEY = env("FINANCIAL_INTERNAL_IDP_API_KEY", default="")

# Split-horizon Keycloak URLs. Browser sees KEYCLOAK_URL; containers use KEYCLOAK_INTERNAL_URL.
KEYCLOAK_URL = env("KEYCLOAK_URL", default="http://localhost:8080")
KEYCLOAK_INTERNAL_URL = env("KEYCLOAK_INTERNAL_URL", default="http://keycloak:8080")
KEYCLOAK_REALM = env("KEYCLOAK_REALM", default="idp-dev")
OIDC_CLIENT_ID = env("OIDC_CLIENT_ID", default="financial-client")
OIDC_OP_ISSUER = env(
    "OIDC_OP_ISSUER",
    default=f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}",
)
OIDC_OP_JWKS_ENDPOINT = env(
    "OIDC_OP_JWKS_ENDPOINT",
    default=f"{KEYCLOAK_INTERNAL_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/certs",
)
OIDC_JWKS_CACHE_TTL = env.int("OIDC_JWKS_CACHE_TTL", default=3600)

# Launcher: DMS integration
DMS_INTERNAL_API_BASE_URL = env(
    "DMS_INTERNAL_API_BASE_URL",
    default="http://backend:8000/api/v1/internal/idp",
)
DMS_INTERNAL_IDP_API_KEY = env("DMS_INTERNAL_IDP_API_KEY", default="")
DMS_PUBLIC_URL = env("DMS_PUBLIC_URL", default="http://localhost:3000")

PRODUCT_INTEGRATIONS = {
    "dms": {
        "base_url": DMS_INTERNAL_API_BASE_URL,
        "api_key": DMS_INTERNAL_IDP_API_KEY,
        "public_url": DMS_PUBLIC_URL,
        "role_field": "dms_role",
    },
}

# Email — fix #8A: use typed env methods to avoid "False" string being truthy
EMAIL_BACKEND = env('EMAIL_BACKEND', default='django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = env('EMAIL_HOST', default='')
EMAIL_PORT = env.int('EMAIL_PORT', default=587)
EMAIL_USE_TLS = env.bool('EMAIL_USE_TLS', default=True)
EMAIL_HOST_USER = env('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL', default='financial@example.com')

OTP_EMAIL_SUBJECT = 'Your Financial System Login Code'
OTP_EMAIL_SENDER = DEFAULT_FROM_EMAIL
