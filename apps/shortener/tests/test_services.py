import pytest
from unittest.mock import patch

from apps.shortener.models import URL
from apps.shortener.services import (
    _generate_code,
    _unique_code,
    create_short_url,
    get_url_by_code,
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
class TestUniqueCode:

    def test_returns_unique_code(self, db):
        code = _unique_code()
        assert isinstance(code, str)
        assert len(code) == 6

    def test_skips_existing_codes(self, url):
        existing = url.short_code
        with patch("apps.shortener.services._generate_code") as mock_gen:
            mock_gen.side_effect = [existing, "newcde"]
            code = _unique_code()
            assert code == "newcde"
            assert mock_gen.call_count == 2

    def test_raises_after_max_retries(self, url):
        with patch(
            "apps.shortener.services._generate_code", return_value=url.short_code
        ):
            with pytest.raises(RuntimeError, match="Failed to generate"):
                _unique_code()


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
class TestGetUrlByCode:

    def test_returns_url_for_valid_code(self, url):
        result = get_url_by_code(url.short_code)
        assert result is not None
        assert result.pk == url.pk

    def test_returns_none_for_invalid_code(self, db):
        result = get_url_by_code("xxxxxx")
        assert result is None

    def test_returns_correct_url(self, db, user):
        url_a = URL.objects.create(
            original_url="https://a.com", short_code="aaaaaa", owner=user
        )
        url_b = URL.objects.create(
            original_url="https://b.com", short_code="bbbbbb", owner=user
        )
        assert get_url_by_code("aaaaaa").pk == url_a.pk
        assert get_url_by_code("bbbbbb").pk == url_b.pk
