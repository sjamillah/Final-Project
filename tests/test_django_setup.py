import os
import django

# Configure Django for tests
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
django.setup()
