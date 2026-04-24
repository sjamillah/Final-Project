import pytest

from apps.shortener.models import URL


@pytest.fixture
def url(db):
    return URL.objects.create(
        original_url="https://example.com",
        short_code="abc123",
    )
