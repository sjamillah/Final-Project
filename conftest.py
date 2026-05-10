import pytest


@pytest.fixture(autouse=True)
def use_locmem_cache(settings):
    """Replace Redis cache with in-memory cache for all tests."""
    settings.CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        }
    }


@pytest.fixture(autouse=True)
def celery_eager(settings):
    """Run Celery tasks synchronously so tests can assert their side-effects."""
    settings.CELERY_TASK_ALWAYS_EAGER = True
    settings.CELERY_TASK_EAGER_PROPAGATES = True
