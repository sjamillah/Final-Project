import pytest
from django.db.utils import IntegrityError

from apps.shortener.models import URL
from apps.shortener import services


@pytest.mark.django_db
def test_create_short_url_handles_integrity_error(monkeypatch):
    original = "https://example.com/conflict"
    call_count = {"n": 0}
    real_create = URL.objects.create

    def flaky_create(*args, **kwargs):
        # fail once with IntegrityError, then delegate to real create
        if call_count["n"] == 0:
            call_count["n"] += 1
            raise IntegrityError("unique constraint")
        return real_create(*args, **kwargs)

    monkeypatch.setattr(URL.objects, "create", flaky_create, raising=True)

    url = services.create_short_url(original)

    assert url.original_url == original
    assert len(url.short_code) == 6


@pytest.mark.django_db
def test_create_short_url_exhausts_retries(monkeypatch):
    # Force _generate_code to always return the same code so retries fail
    monkeypatch.setattr(services, "_generate_code", lambda: "fixedcode")

    # Ensure no existing URL has that original
    original = "https://example.com/exhaust"

    # Force the manager to always raise IntegrityError on create attempts
    def always_raise(*args, **kwargs):
        raise IntegrityError("unique constraint")

    monkeypatch.setattr(URL.objects, "get_or_create", always_raise, raising=True)

    with pytest.raises(services.UniqueCodeError):
        services.create_short_url(original)
