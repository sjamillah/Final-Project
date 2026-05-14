"""
Redis-backed circuit breaker, keyed per target domain.

States (implemented via Redis TTLs — no extra state machine needed):
  CLOSED  — key absent or failure count below threshold → requests flow through
  OPEN    — "open" key present in Redis → requests are rejected until TTL expires
  Recovery — once the open key expires, the next request is automatically allowed
             (half-open behaviour via natural TTL without extra state)

Why Redis and not in-process?
  Multiple Celery workers run concurrently.  An in-process counter would be
  per-worker and never accumulate across the fleet, defeating the purpose.
"""

import logging
from urllib.parse import urlparse

from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

_DEFAULT_THRESHOLD = 5
_DEFAULT_TIMEOUT = 300  # 5 minutes


def _threshold() -> int:
    return getattr(settings, "CIRCUIT_BREAKER_FAILURE_THRESHOLD", _DEFAULT_THRESHOLD)


def _timeout() -> int:
    return getattr(settings, "CIRCUIT_BREAKER_RECOVERY_TIMEOUT", _DEFAULT_TIMEOUT)


def _keys(domain: str) -> tuple[str, str]:
    return f"cb:{domain}:failures", f"cb:{domain}:open"


def domain_from_url(url: str) -> str:
    return urlparse(url).netloc or url


def is_open(domain: str) -> bool:
    """Return True when the circuit is open and requests should be skipped."""
    _, open_key = _keys(domain)
    return cache.get(open_key) is not None


def record_success(domain: str) -> None:
    """Reset the circuit after a successful fetch."""
    failures_key, open_key = _keys(domain)
    cache.delete_many([failures_key, open_key])


def record_failure(domain: str) -> None:
    """
    Increment the failure counter for *domain*.
    Opens the circuit once the threshold is reached.
    """
    threshold = _threshold()
    timeout = _timeout()
    failures_key, open_key = _keys(domain)

    # Non-atomic get-increment-set is acceptable here: a transient race
    # might delay opening the circuit by one request, which is harmless.
    count = (cache.get(failures_key) or 0) + 1
    cache.set(failures_key, count, timeout)

    if count >= threshold:
        cache.set(open_key, 1, timeout)
        logger.warning(
            "circuit_breaker.opened domain=%s failures=%d recovery_in=%ds",
            domain,
            count,
            timeout,
        )
