import pytest
from django.core.cache import cache
from django.core.cache.backends.locmem import _caches, _expire_info


def _clear_locmem():
    cache.clear()
    _caches.clear()
    _expire_info.clear()


@pytest.fixture(autouse=True)
def use_locmem_cache(settings):
    """Replace Redis cache with in-memory cache for all tests."""
    settings.CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        }
    }
    _clear_locmem()
    yield
    _clear_locmem()


@pytest.fixture(autouse=True)
def celery_eager(settings):
    """Run Celery tasks synchronously so tests can assert their side-effects."""
    settings.CELERY_TASK_ALWAYS_EAGER = True
    settings.CELERY_TASK_EAGER_PROPAGATES = True
