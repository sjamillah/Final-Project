import tests.test_django_setup as test_django_setup
import pytest

from rest_framework.test import APIClient
from apps.shortener.models import URL

DJANGO_SETUP = test_django_setup


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def url(db):
    return URL.objects.create(
        original_url="https://example.com",
        short_code="abc123",
    )
