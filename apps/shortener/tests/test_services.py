import pytest
from unittest.mock import patch
from django.db import IntegrityError
from django.test import override_settings

from apps.shortener.models import Click, URL
from apps.shortener.services import (
    _generate_code,
    build_click_metadata,
    create_click_for_url,
    create_short_url,
)


@pytest.mark.django_db
class TestGenerateCode:

    def test_returns_string(self):
        code = _generate_code()
        assert isinstance(code, str)

    def test_correct_length(self):
        code = _generate_code()
        assert len(code) == 6

    def test_alphanumeric_only(self):
        for _ in range(20):
            code = _generate_code()
            assert code.isalnum()

    def test_generates_unique_values(self):
        codes = {_generate_code() for _ in range(50)}
        assert len(codes) > 1


@pytest.mark.django_db
class TestCreateShortUrl:

    def test_creates_new_url(self, db):
        result = create_short_url("https://example.com/new")
        assert result.pk is not None
        assert result.original_url == "https://example.com/new"
        assert len(result.short_code) == 6

    def test_returns_existing_for_duplicate(self, db):
        first = create_short_url("https://example.com/dup")
        second = create_short_url("https://example.com/dup")
        assert first.pk == second.pk
        assert URL.objects.filter(original_url="https://example.com/dup").count() == 1

    def test_returns_existing_for_same_owner(self, db, user):
        first = create_short_url("https://example.com/owned-dup", owner=user)
        second = create_short_url("https://example.com/owned-dup", owner=user)
        assert first.pk == second.pk

    def test_different_owner_gets_different_url(self, db, user, premium_user):
        first = create_short_url("https://example.com/shared", owner=user)
        second = create_short_url("https://example.com/shared", owner=premium_user)
        assert first.pk != second.pk

    def test_retries_on_integrity_error_then_succeeds(self, db):
        with patch("apps.shortener.services.URL.objects.create") as mock_create:
            mock_create.side_effect = [
                IntegrityError(
                    "duplicate key value violates unique constraint urls_short_code"
                ),
                URL(original_url="https://example.com/retry", short_code="ret123"),
            ]
            result = create_short_url("https://example.com/retry")
            assert result.short_code == "ret123"
            assert mock_create.call_count == 2

    def test_raises_for_unexpected_integrity_error(self, db):
        with patch("apps.shortener.services.URL.objects.create") as mock_create:
            mock_create.side_effect = IntegrityError("other constraint failure")
            with pytest.raises(IntegrityError):
                create_short_url("https://example.com/fail")

    def test_different_urls_get_different_codes(self, db):
        first = create_short_url("https://example.com/one")
        second = create_short_url("https://example.com/two")
        assert first.short_code != second.short_code

    def test_returns_url_instance(self, db):
        result = create_short_url("https://example.com/typed")
        assert isinstance(result, URL)

    def test_short_code_is_stored(self, db):
        result = create_short_url("https://example.com/stored")
        from_db = URL.objects.get(pk=result.pk)
        assert from_db.short_code == result.short_code


@pytest.mark.django_db
class TestCreateClickForUrl:

    def test_creates_click_entry(self, url):
        click = create_click_for_url(url=url, ip_address="127.0.0.1")
        assert isinstance(click, Click)
        assert click.url_id == url.pk
        assert click.ip_address == "127.0.0.1"

    def test_increments_click_count(self, url):
        assert url.click_count == 0
        create_click_for_url(url=url)
        url.refresh_from_db()
        assert url.click_count == 1


class TestBuildClickMetadata:

    @override_settings(TRUST_PROXY_HEADERS=False)
    def test_uses_remote_addr_when_proxy_headers_not_trusted(self):
        data = build_click_metadata(
            {
                "HTTP_X_FORWARDED_FOR": "1.1.1.1, 2.2.2.2",
                "REMOTE_ADDR": "9.9.9.9",
            }
        )
        assert data.ip_address == "9.9.9.9"

    @override_settings(TRUST_PROXY_HEADERS=True)
    def test_uses_forwarded_for_when_proxy_headers_trusted(self):
        data = build_click_metadata(
            {
                "HTTP_X_FORWARDED_FOR": "1.1.1.1, 2.2.2.2",
                "REMOTE_ADDR": "9.9.9.9",
            }
        )
        assert data.ip_address == "1.1.1.1"
