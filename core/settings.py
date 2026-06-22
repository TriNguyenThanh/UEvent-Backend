"""
Django settings for core project.
"""

import os
import environ
from pathlib import Path

env = environ.Env()

BASE_DIR = Path(__file__).resolve().parent.parent
environ.Env.read_env(os.path.join(BASE_DIR, ".env"))
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

SECRET_KEY = env("SECRET_KEY")
TICKET_QR_SECRET = env("TICKET_QR_SECRET", default=SECRET_KEY)
DEBUG = env.bool("DEBUG", default=False)

ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["*"])

CORS_ALLOWED_ORIGINS = env.list(
    "CORS_ALLOWED_ORIGINS",
    default=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
)
CORS_ALLOWED_METHODS = ["DELETE", "GET", "OPTIONS", "PATCH", "POST", "PUT"]
CORS_ALLOWED_HEADERS = [
    "accept",
    "authorization",
    "content-type",
    "idempotency-key",
    "origin",
    "x-request-id",
]
CORS_ALLOW_CREDENTIALS = env.bool("CORS_ALLOW_CREDENTIALS", default=True)
CORS_PREFLIGHT_MAX_AGE = env.int("CORS_PREFLIGHT_MAX_AGE", default=86400)
CI = env.bool("CI", default=False)
USE_SQLITE = env.bool("USE_SQLITE", default=CI)


INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "drf_yasg",
    "django_filters",
    "apps.users",
    "apps.organizer_requests",
    "apps.locations",
    "apps.events",
    "apps.registrations",
    "apps.interactions",
    "apps.notifications",
    "apps.moderation",
    "apps.support",
    "apps.app_settings",
    "apps.system_admin",
    "apps.utils",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "common.middleware.CorsMiddleware",
    "common.middleware.RequestIdMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "core.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "core.wsgi.application"

if USE_SQLITE:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": env("POSTGRES_DB"),
            "USER": env("POSTGRES_USER"),
            "PASSWORD": env("POSTGRES_PASSWORD"),
            "HOST": env("HOST"),
            "PORT": env("PORT"),
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "vi"
TIME_ZONE = "Asia/Ho_Chi_Minh"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"

AUTH_USER_MODEL = "users.User"

AWS_ACCESS_KEY_ID = env("AWS_ACCESS_KEY_ID", default="")
AWS_SECRET_ACCESS_KEY = env("AWS_SECRET_ACCESS_KEY", default="")
AWS_STORAGE_BUCKET_NAME = env("AWS_STORAGE_BUCKET_NAME", default="")
AWS_S3_REGION_NAME = env("AWS_S3_REGION_NAME", default="ap-southeast-1")
AWS_S3_ENDPOINT_URL = env("AWS_S3_ENDPOINT_URL", default="")
AWS_S3_CUSTOM_DOMAIN = env("AWS_S3_CUSTOM_DOMAIN", default="")
AWS_S3_OBJECT_PARAMETERS = {
    "CacheControl": env("AWS_S3_CACHE_CONTROL", default="max-age=86400"),
}
AWS_S3_PRESIGNED_URL_EXPIRES = env.int("AWS_S3_PRESIGNED_URL_EXPIRES", default=3600)
AWS_S3_PRESIGNED_GET_URL_CACHE_TTL = env.int(
    "AWS_S3_PRESIGNED_GET_URL_CACHE_TTL",
    default=max(0, AWS_S3_PRESIGNED_URL_EXPIRES - 60),
)

KEYCLOAK_SERVER_URL = env("KEYCLOAK_SERVER_URL", default="http://localhost").rstrip("/")
KEYCLOAK_REALM = env("KEYCLOAK_REALM", default="test-realm")
KEYCLOAK_AUDIENCE = env("KEYCLOAK_AUDIENCE", default="test-audience")
KEYCLOAK_CLIENT_ID = env("KEYCLOAK_CLIENT_ID", default=KEYCLOAK_AUDIENCE)
KEYCLOAK_CLIENT_SECRET = env("KEYCLOAK_CLIENT_SECRET", default="")
KEYCLOAK_SCOPE = env("KEYCLOAK_SCOPE", default="openid email profile offline_access")
KEYCLOAK_ISSUER = f"{KEYCLOAK_SERVER_URL}/realms/{KEYCLOAK_REALM}"
KEYCLOAK_TOKEN_URL = f"{KEYCLOAK_ISSUER}/protocol/openid-connect/token"
KEYCLOAK_LOGOUT_URL = f"{KEYCLOAK_ISSUER}/protocol/openid-connect/logout"
KEYCLOAK_JWKS_URL = f"{KEYCLOAK_ISSUER}/protocol/openid-connect/certs"
KEYCLOAK_JWKS_CACHE_TTL = env.int("KEYCLOAK_JWKS_CACHE_TTL", default=300)
KEYCLOAK_AUTH_USER_CACHE_TTL = env.int("KEYCLOAK_AUTH_USER_CACHE_TTL", default=300)
KEYCLOAK_JWKS_TIMEOUT = env.int("KEYCLOAK_JWKS_TIMEOUT", default=5)
KEYCLOAK_TOKEN_TIMEOUT = env.int("KEYCLOAK_TOKEN_TIMEOUT", default=10)
KEYCLOAK_JWT_ALGORITHMS = env.list("KEYCLOAK_JWT_ALGORITHMS", default=["RS256"])
KEYCLOAK_JWT_LEEWAY_SECONDS = env.int("KEYCLOAK_JWT_LEEWAY_SECONDS", default=90)

# Keycloak Admin API (dùng cho OTP Email Login — Token Exchange)
KEYCLOAK_ADMIN_CLIENT_ID = env("KEYCLOAK_ADMIN_CLIENT_ID", default="uevent-backend")
KEYCLOAK_ADMIN_CLIENT_SECRET = env("KEYCLOAK_ADMIN_CLIENT_SECRET", default="")
KEYCLOAK_TOKEN_URL = f"{KEYCLOAK_ISSUER}/protocol/openid-connect/token"
KEYCLOAK_ADMIN_API_URL = f"{KEYCLOAK_SERVER_URL}/admin/realms/{KEYCLOAK_REALM}"

PASSKEY_RP_ID = env("PASSKEY_RP_ID", default="localhost")
PASSKEY_RP_NAME = env("PASSKEY_RP_NAME", default="UEvent")
PASSKEY_EXPECTED_ORIGINS = env.list(
    "PASSKEY_EXPECTED_ORIGINS",
    default=["http://localhost", "https://localhost"],
)
PASSKEY_CHALLENGE_TTL_SECONDS = env.int(
    "PASSKEY_CHALLENGE_TTL_SECONDS",
    default=300,
)

GOOGLE_OAUTH_CLIENT_IDS = env.list("GOOGLE_OAUTH_CLIENT_IDS", default=[])

REST_FRAMEWORK = {
    "EXCEPTION_HANDLER": "common.exceptions.custom_exception_handler",
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "common.authentication.KeycloakJWTAuthentication",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 10,
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
}

SWAGGER_SETTINGS = {
    "SECURITY_DEFINITIONS": {
        "Bearer": {
            "type": "apiKey",
            "name": "Authorization",
            "in": "header",
            "description": "Nhập JWT token theo format: **Bearer &lt;access_token&gt;**",
        },
    },
    "USE_SESSION_AUTH": False,
}

OPENOBSERVE_URL = env("OPENOBSERVE_URL", default="http://localhost:5080")
OPENOBSERVE_ORGANIZATION = env("OPENOBSERVE_ORGANIZATION", default="default")
OPENOBSERVE_AUDIT_STREAM = env("OPENOBSERVE_AUDIT_STREAM", default="uevent_audit")
OPENOBSERVE_USERNAME = env("OPENOBSERVE_USERNAME", default="")
OPENOBSERVE_PASSWORD = env("OPENOBSERVE_PASSWORD", default="")
OPENOBSERVE_TIMEOUT_SECONDS = env.int("OPENOBSERVE_TIMEOUT_SECONDS", default=5)

CELERY_BROKER_URL = env("CELERY_BROKER_URL", default="redis://localhost:6379/0")
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", default="redis://localhost:6379/1")
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = env.int("CELERY_TASK_TIME_LIMIT", default=300)
CELERY_TASK_ALWAYS_EAGER = env.bool("CELERY_TASK_ALWAYS_EAGER", default=False)
CELERY_TASK_EAGER_PROPAGATES = env.bool("CELERY_TASK_EAGER_PROPAGATES", default=True)

FCM_ENABLED = env.bool("FCM_ENABLED", default=False)
FCM_DRY_RUN = env.bool("FCM_DRY_RUN", default=False)
FIREBASE_CREDENTIALS_PATH = env("FIREBASE_CREDENTIALS_PATH", default="")
FIREBASE_CREDENTIALS_JSON = env("FIREBASE_CREDENTIALS_JSON", default="")
FCM_BATCH_SIZE = env.int("FCM_BATCH_SIZE", default=500)
FCM_MAX_RETRIES = env.int("FCM_MAX_RETRIES", default=3)
FCM_DEVICE_TOKEN_TTL_DAYS = env.int("FCM_DEVICE_TOKEN_TTL_DAYS", default=365)

# ── Email (SMTP) ──
EMAIL_BACKEND = env(
    "EMAIL_BACKEND", default="django.core.mail.backends.smtp.EmailBackend"
)
EMAIL_HOST = env("EMAIL_HOST", default="smtp.gmail.com")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="UEvent <noreply@uevent.app>")

# ── OTP ──
OTP_TTL_SECONDS = env.int("OTP_TTL_SECONDS", default=180)  # 3 phút
OTP_MAX_ATTEMPTS = env.int("OTP_MAX_ATTEMPTS", default=5)  # Khóa sau 5 lần sai
OTP_COOLDOWN_SECONDS = env.int(
    "OTP_COOLDOWN_SECONDS", default=60
)  # Chờ 60s trước khi gửi lại

PUBLIC_WEB_BASE_URL = env(
    "PUBLIC_WEB_BASE_URL",
    default="http://localhost:3000",
).rstrip("/")

# core/settings.py
# Dify AI Configuration
DIFY_AI_QA_ENABLED = env.bool("DIFY_AI_QA_ENABLED", default=False)
DIFY_API_BASE_URL = env.str("DIFY_API_BASE_URL", default="https://api.dify.ai/v1")
DIFY_API_KEY = env.str("DIFY_API_KEY", default="")
DIFY_TIMEOUT_SECONDS = env.int("DIFY_TIMEOUT_SECONDS", default=30)
DIFY_AI_ASSISTANT_USER_ID = env.str("DIFY_AI_ASSISTANT_USER_ID", default="615a4c87-45c6-4114-a2f5-faa50b19cb49")
# ── Cache (Redis) ──
if CI or USE_SQLITE:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "uevent-ci-cache",
            "TIMEOUT": 300,
        }
    }
else:
    CACHES = {
        "default": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": env("REDIS_URL", default="redis://redis:6379/0"),
            "OPTIONS": {
                "CLIENT_CLASS": "django_redis.client.DefaultClient",
            },
            "TIMEOUT": 300,  # default TTL 5 phút (override bằng cache.set timeout)
        }
    }


LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {process:d} {thread:d} {message}",
            "style": "{",
        },
        "simple": {
            "format": "%(asctime)s %(levelname)s %(name)s %(message)s",
        },
        "json": {
            "()": "common.logging.TraceIdJsonFormatter",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "simple",
        },
        "audit_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": str(LOG_DIR / "audit.json"),
            "maxBytes": 50 * 1024 * 1024,
            "backupCount": 5,
            "formatter": "json",
            "encoding": "utf-8",
        },
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": True,
        },
        "django.request": {
            "handlers": ["console"],
            "level": "ERROR",
            "propagate": False,
        },
        "uevent.audit": {
            "handlers": ["console", "audit_file"],
            "level": "INFO",
            "propagate": False,
        },
    },
}
