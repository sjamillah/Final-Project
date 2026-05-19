import pytest
from django.db.utils import IntegrityError

from apps.shortener.models import URL
from apps.shortener import services
from apps.shortener.exceptions import UniqueCodeError


@pytest.mark.django_db
def test_create_short_url_handles_integrity_error(monkeypatch):
    """Test that service retries on IntegrityError from short_code collision."""
    original = "https://example.com/conflict"
    attempt_count = {"n": 0}
    real_create = URL.objects.create

    def flaky_create(*args, **kwargs):
        # Fail first time if short_code is "abc123", then allow through
        attempt_count["n"] += 1
        if attempt_count["n"] == 1 and kwargs.get("short_code") == "abc123":
            raise IntegrityError("short_code")
        return real_create(*args, **kwargs)

    monkeypatch.setattr(URL.objects, "create", flaky_create)
    monkeypatch.setattr(
        services,
        "_generate_code",
        lambda: "abc123" if attempt_count["n"] == 1 else "def456",
    )

    url = services.create_short_url(original)

    assert url.original_url == original
    assert len(url.short_code) == 6


@pytest.mark.django_db
def test_create_short_url_exhausts_retries(monkeypatch):
    """Test that service raises UniqueCodeError after MAX_RETRIES."""
    original = "https://example.com/exhaust"

    # Always raise IntegrityError on short_code collisions
    real_create = URL.objects.create

    def always_short_code_error(*args, **kwargs):
        if kwargs.get("short_code"):
            raise IntegrityError("short_code")
        return real_create(*args, **kwargs)

    monkeypatch.setattr(URL.objects, "create", always_short_code_error)
    # Force same code every time so we exceed retries
    monkeypatch.setattr(services, "_generate_code", lambda: "samecode")

    with pytest.raises(UniqueCodeError):
        services.create_short_url(original)
