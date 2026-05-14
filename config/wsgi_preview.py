"""WSGI entry point for the preview_service container."""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.preview")

application = get_wsgi_application()
