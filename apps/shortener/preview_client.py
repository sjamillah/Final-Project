"""
HTTP client that calls the preview_service container.

Why a dedicated module and not inline in the task?
  Single-responsibility: the task owns retry/scheduling logic; this module owns
  HTTP transport and circuit-breaker decisions.  Easier to mock in tests too.
"""

import logging
from dataclasses import dataclass

import httpx
from django.conf import settings

from apps.shortener.circuit_breaker import (
    domain_from_url,
    is_open,
    record_failure,
    record_success,
)

logger = logging.getLogger(__name__)

_DEFAULT_SERVICE_URL = "http://preview_service:8001"
_HTTP_TIMEOUT = 15.0  # seconds — preview service has its own inner timeout of 10s


@dataclass
class PreviewData:
    title: str | None = None
    description: str | None = None
    favicon: str | None = None


def fetch_preview(original_url: str) -> PreviewData | None:
    """
    Ask the preview_service to return metadata for *original_url*.

    Returns PreviewData (fields may be None) on success.
    Returns None when:
      - the circuit for the target domain is open, OR
      - the preview service itself is unreachable (caller should retry).

    Raises nothing — all exceptions are caught and logged.
    """
    domain = domain_from_url(original_url)

    if is_open(domain):
        logger.info("preview.circuit_open domain=%s url=%s", domain, original_url)
        return None

    service_url = getattr(settings, "PREVIEW_SERVICE_URL", _DEFAULT_SERVICE_URL)
    endpoint = f"{service_url}/api/preview/"

    try:
        with httpx.Client(timeout=_HTTP_TIMEOUT) as client:
            response = client.post(endpoint, json={"url": original_url})
            response.raise_for_status()
            data = response.json()

        record_success(domain)
        return PreviewData(
            title=data.get("title"),
            description=data.get("description"),
            favicon=data.get("favicon"),
        )

    except httpx.TimeoutException:
        record_failure(domain)
        logger.warning("preview.timeout domain=%s url=%s", domain, original_url)
        return None

    except httpx.HTTPStatusError as exc:
        record_failure(domain)
        logger.warning(
            "preview.http_error domain=%s status=%d url=%s",
            domain,
            exc.response.status_code,
            original_url,
        )
        return None

    except Exception as exc:
        record_failure(domain)
        logger.warning(
            "preview.error domain=%s err=%s url=%s", domain, exc, original_url
        )
        return None
