from apps.shortener.cache import (
    cache_redirect_url,
    get_cached_redirect,
    invalidate_redirect_cache,
)


class TestCacheRedirectUrl:
    """LocMemCache is injected via the root conftest autouse fixture."""

    def test_cache_and_retrieve(self):
        cache_redirect_url("abc123", 1, "https://example.com")
        result = get_cached_redirect("abc123")
        assert result is not None
        assert result["url_id"] == 1
        assert result["original_url"] == "https://example.com"

    def test_cache_miss_returns_none(self):
        result = get_cached_redirect("notcached")
        assert result is None

    def test_different_codes_are_independent(self):
        cache_redirect_url("code1", 1, "https://one.com")
        cache_redirect_url("code2", 2, "https://two.com")
        assert get_cached_redirect("code1")["url_id"] == 1
        assert get_cached_redirect("code2")["url_id"] == 2


class TestInvalidateRedirectCache:

    def test_invalidate_removes_short_code(self):
        cache_redirect_url("abc123", 1, "https://example.com")
        invalidate_redirect_cache("abc123")
        assert get_cached_redirect("abc123") is None

    def test_invalidate_also_removes_alias(self):
        cache_redirect_url("abc123", 1, "https://example.com")
        cache_redirect_url("myalias", 1, "https://example.com")
        invalidate_redirect_cache("abc123", custom_alias="myalias")
        assert get_cached_redirect("abc123") is None
        assert get_cached_redirect("myalias") is None

    def test_invalidate_without_alias_only_clears_code(self):
        cache_redirect_url("abc123", 1, "https://example.com")
        cache_redirect_url("otheralias", 2, "https://other.com")
        invalidate_redirect_cache("abc123")
        assert get_cached_redirect("abc123") is None
        assert get_cached_redirect("otheralias") is not None

    def test_invalidate_nonexistent_key_is_safe(self):
        invalidate_redirect_cache("doesnotexist")
