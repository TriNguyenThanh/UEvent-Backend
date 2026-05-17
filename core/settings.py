"""
Django settings for core project.
"""
import os
import environ
from pathlib import Path

env = environ.Env()

BASE_DIR = Path(__file__).resolve().parent.parent
environ.Env.read_env(os.path.join(BASE_DIR, '.env'))
LOG_DIR = BASE_DIR / 'logs'
LOG_DIR.mkdir(parents=True, exist_ok=True)

SECRET_KEY = env('SECRET_KEY')
DEBUG = env.bool('DEBUG', default=False)

ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['*'])

CORS_ALLOWED_ORIGINS = env.list(
    'CORS_ALLOWED_ORIGINS',
    default=[
        'http://localhost:3000',
        'http://127.0.0.1:3000',
    ],
)
CORS_ALLOWED_METHODS = ['DELETE', 'GET', 'OPTIONS', 'PATCH', 'POST', 'PUT']
CORS_ALLOWED_HEADERS = [
    'accept',
    'authorization',
    'content-type',
    'idempotency-key',
    'origin',
    'x-request-id',
]
CORS_ALLOW_CREDENTIALS = env.bool('CORS_ALLOW_CREDENTIALS', default=True)
CORS_PREFLIGHT_MAX_AGE = env.int('CORS_PREFLIGHT_MAX_AGE', default=86400)
USE_SQLITE = env.bool('USE_SQLITE', default=env.bool('CI', default=False))



INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'drf_yasg',
    'django_filters',
    'apps.users',
    'apps.locations',
    'apps.events',
    'apps.registrations',
    'apps.interactions',
    'apps.notifications',
    'apps.moderation',
    'apps.support',
    'apps.app_settings',
    'apps.system_admin',
    'apps.utils',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'common.middleware.CorsMiddleware',
    'common.middleware.RequestIdMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'

if USE_SQLITE:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': env('POSTGRES_DB'),
            'USER': env('POSTGRES_USER'),
            'PASSWORD': env('POSTGRES_PASSWORD'),
            'HOST': env('HOST'),
            'PORT': env('PORT'),
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'

AUTH_USER_MODEL = 'users.User'

KEYCLOAK_SERVER_URL = env('KEYCLOAK_SERVER_URL', default='http://localhost').rstrip('/')
KEYCLOAK_REALM = env('KEYCLOAK_REALM', default='test-realm')
KEYCLOAK_AUDIENCE = env('KEYCLOAK_AUDIENCE', default='test-audience')
KEYCLOAK_CLIENT_ID = env('KEYCLOAK_CLIENT_ID', default=KEYCLOAK_AUDIENCE)
KEYCLOAK_CLIENT_SECRET = env('KEYCLOAK_CLIENT_SECRET', default='')
KEYCLOAK_SCOPE = env('KEYCLOAK_SCOPE', default='openid email profile')
KEYCLOAK_ISSUER = f"{KEYCLOAK_SERVER_URL}/realms/{KEYCLOAK_REALM}"
KEYCLOAK_TOKEN_URL = f"{KEYCLOAK_ISSUER}/protocol/openid-connect/token"
KEYCLOAK_LOGOUT_URL = f"{KEYCLOAK_ISSUER}/protocol/openid-connect/logout"
KEYCLOAK_JWKS_URL = f"{KEYCLOAK_ISSUER}/protocol/openid-connect/certs"
KEYCLOAK_JWKS_CACHE_TTL = env.int('KEYCLOAK_JWKS_CACHE_TTL', default=300)
KEYCLOAK_JWKS_TIMEOUT = env.int('KEYCLOAK_JWKS_TIMEOUT', default=5)
KEYCLOAK_TOKEN_TIMEOUT = env.int('KEYCLOAK_TOKEN_TIMEOUT', default=10)
KEYCLOAK_JWT_ALGORITHMS = env.list('KEYCLOAK_JWT_ALGORITHMS', default=['RS256'])

REST_FRAMEWORK = {
    'EXCEPTION_HANDLER': 'common.exceptions.custom_exception_handler',
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'common.authentication.KeycloakJWTAuthentication',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 10,
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
}

SWAGGER_SETTINGS = {
    'SECURITY_DEFINITIONS': {
        'Bearer': {
            'type': 'apiKey',
            'name': 'Authorization',
            'in': 'header',
            'description': 'Nhập JWT token theo format: **Bearer &lt;access_token&gt;**',
        },
    },
    'USE_SESSION_AUTH': False,
}

OPENSEARCH_URL = env('OPENSEARCH_URL', default='http://localhost:9200')
OPENSEARCH_AUDIT_INDEX = env('OPENSEARCH_AUDIT_INDEX', default='uevent-audit-*')
OPENSEARCH_TIMEOUT_SECONDS = env.int('OPENSEARCH_TIMEOUT_SECONDS', default=5)

CELERY_BROKER_URL = env('CELERY_BROKER_URL', default='redis://localhost:6379/0')
CELERY_RESULT_BACKEND = env('CELERY_RESULT_BACKEND', default='redis://localhost:6379/1')
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = env.int('CELERY_TASK_TIME_LIMIT', default=300)
CELERY_TASK_ALWAYS_EAGER = env.bool('CELERY_TASK_ALWAYS_EAGER', default=False)
CELERY_TASK_EAGER_PROPAGATES = env.bool('CELERY_TASK_EAGER_PROPAGATES', default=True)

FCM_ENABLED = env.bool('FCM_ENABLED', default=False)
FCM_DRY_RUN = env.bool('FCM_DRY_RUN', default=False)
FIREBASE_CREDENTIALS_PATH = env('FIREBASE_CREDENTIALS_PATH', default='')
FIREBASE_CREDENTIALS_JSON = env('FIREBASE_CREDENTIALS_JSON', default='')
FCM_BATCH_SIZE = env.int('FCM_BATCH_SIZE', default=500)
FCM_MAX_RETRIES = env.int('FCM_MAX_RETRIES', default=3)
FCM_DEVICE_TOKEN_TTL_DAYS = env.int('FCM_DEVICE_TOKEN_TTL_DAYS', default=365)


LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '%(asctime)s %(levelname)s %(name)s %(message)s',
        },
        'json': {
            '()': 'common.logging.TraceIdJsonFormatter',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        'audit_file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': str(LOG_DIR / 'audit.json'),
            'maxBytes': 50 * 1024 * 1024,
            'backupCount': 5,
            'formatter': 'json',
            'encoding': 'utf-8',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': True,
        },
        'django.request': {
            'handlers': ['console'],
            'level': 'ERROR',
            'propagate': False,
        },
        'uevent.audit': {
            'handlers': ['console', 'audit_file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}
