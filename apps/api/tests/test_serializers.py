import pytest
from apps.api.v1.url_serializers import URLCreateSerializer, URLResponseSerializer


class TestURLCreateSerializer:

    def test_valid_url(self):
        s = URLCreateSerializer(data={"original_url": "https://example.com"})
        assert s.is_valid()

    def test_invalid_url(self):
        s = URLCreateSerializer(data={"original_url": "not-a-url"})
        assert not s.is_valid()
        assert "original_url" in s.errors

    def test_missing_url(self):
        s = URLCreateSerializer(data={})
        assert not s.is_valid()
        assert "original_url" in s.errors

    def test_empty_string(self):
        s = URLCreateSerializer(data={"original_url": ""})
        assert not s.is_valid()

    def test_url_too_long(self):
        s = URLCreateSerializer(
            data={"original_url": "https://example.com/" + "a" * 2048}
        )
        assert not s.is_valid()

    def test_http_url_valid(self):
        s = URLCreateSerializer(data={"original_url": "http://example.com"})
        assert s.is_valid()

    def test_extra_fields_ignored(self):
        s = URLCreateSerializer(
            data={"original_url": "https://example.com", "short_code": "hacked"}
        )
        assert s.is_valid()
        assert "short_code" not in s.validated_data


@pytest.mark.django_db
class TestURLResponseSerializer:

    def test_contains_expected_fields(self, url):
        s = URLResponseSerializer(url)
        assert set(s.data.keys()) == {
            "id",
            "original_url",
            "short_code",
            "custom_alias",
            "short_url",
            "title",
            "click_count",
            "is_active",
            "expires_at",
            "tags",
            "owner_username",
            "created_at",
        }

    def test_short_code_correct(self, url):
        s = URLResponseSerializer(url)
        assert s.data["short_code"] == url.short_code

    def test_original_url_correct(self, url):
        s = URLResponseSerializer(url)
        assert s.data["original_url"] == url.original_url

    def test_created_at_present(self, url):
        s = URLResponseSerializer(url)
        assert s.data["created_at"] is not None

    def test_short_url_uses_short_code_when_no_alias(self, url):
        s = URLResponseSerializer(url)
        assert s.data["short_url"] == f"/{url.short_code}/"
