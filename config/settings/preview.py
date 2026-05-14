"""
Minimal settings for the preview_service container.

This module is intentionally stripped down: no database, no Redis, no Celery,
no JWT.  The container has one job — accept a URL, fetch its metadata, return
JSON.  Keeping it lean means it starts fast and has no unnecessary attack surface.
"""

SECRET_KEY = "preview-service-internal-only-not-used-for-auth"
DEBUG = False
ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "rest_framework",
    "apps.preview",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
]

ROOT_URLCONF = "config.urls_preview"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": False,
        "OPTIONS": {"context_processors": []},
    }
]

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_THROTTLE_CLASSES": ["rest_framework.throttling.AnonRateThrottle"],
    "DEFAULT_THROTTLE_RATES": {"anon": "300/minute"},
    "UNAUTHENTICATED_USER": None,
}

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_TZ = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Fetch tunables — can be overridden via env in docker-compose
PREVIEW_FETCH_TIMEOUT = 10  # seconds to wait for target site
PREVIEW_USER_AGENT = "URLShortener-Preview/1.0"
PREVIEW_MAX_BYTES = 1024 * 512  # max HTML bytes to parse (512 KB)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "WARNING",
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "django.request": {
            "handlers": ["console"],
            "level": "ERROR",
            "propagate": False,
        },
        "apps.preview": {
            "handlers": ["console"],
            "level": "DEBUG",
            "propagate": False,
        },
    },
}
