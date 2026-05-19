from django.core.cache import cache

_TTL = 60 * 60 * 24  # 24 hours
_PREFIX = "redirect"


def _key(code: str) -> str:
    return f"{_PREFIX}:{code}"


def get_cached_redirect(code: str) -> dict | None:
    """Return {"url_id": int, "original_url": str} or None on cache miss."""
    return cache.get(_key(code))


def cache_redirect_url(code: str, url_id: int, original_url: str) -> None:
    cache.set(
        _key(code), {"url_id": url_id, "original_url": original_url}, timeout=_TTL
    )


def invalidate_redirect_cache(short_code: str, custom_alias: str | None = None) -> None:
    keys = [_key(short_code)]
    if custom_alias:
        keys.append(_key(custom_alias))
    cache.delete_many(keys)
