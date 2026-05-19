import logging
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup
from django.conf import settings
from rest_framework import serializers, status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

logger = logging.getLogger(__name__)

_USER_AGENT = "URLShortener-Preview/1.0"
_MAX_BYTES = 1024 * 512  # 512 KB — enough for any <head> section

# Explicit per-phase caps so the total never exceeds ~25 s (under gunicorn's 60 s limit).
# httpx's single float timeout means 10 s *per phase* (connect + read + write),
# which can stack to 30 s+ on a slow site and kill the gunicorn worker.
_HTTP_TIMEOUT = httpx.Timeout(connect=5.0, read=10.0, write=5.0, pool=5.0)


class PreviewRequestSerializer(serializers.Serializer):
    url = serializers.URLField(max_length=2048)


class PreviewView(APIView):
    """
    POST /api/preview/
    Body: {"url": "https://example.com"}
    Returns: {"title": "...", "description": "...", "favicon": "..."}

    Always responds 200.  If the target URL is unreachable or unparseable
    every field is null — the caller decides what to do with missing data.
    """

    authentication_classes = []
    permission_classes = []

    def post(self, request: Request) -> Response:
        serializer = PreviewRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = _fetch_preview(serializer.validated_data["url"])
        return Response(result, status=status.HTTP_200_OK)


def health(request):
    from django.http import JsonResponse

    return JsonResponse({"status": "ok"})


# ---------------------------------------------------------------------------
# Internal helpers — pure functions, no side effects
# ---------------------------------------------------------------------------


def _fetch_preview(url: str) -> dict:
    """Fetch *url* and extract Open Graph / meta title, description, favicon."""
    user_agent = getattr(settings, "PREVIEW_USER_AGENT", _USER_AGENT)

    try:
        with httpx.Client(
            timeout=_HTTP_TIMEOUT,
            follow_redirects=True,
            max_redirects=5,
            headers={"User-Agent": user_agent},
        ) as client:
            response = client.get(url)
            response.raise_for_status()

        content_type = response.headers.get("content-type", "")
        if "text/html" not in content_type:
            return _empty()

        html = response.text[: getattr(settings, "PREVIEW_MAX_BYTES", _MAX_BYTES)]

    except Exception as exc:
        logger.warning("preview.fetch_failed url=%s err=%s", url, exc)
        return _empty()

    try:
        return _parse(html, url)
    except Exception as exc:
        logger.warning("preview.parse_failed url=%s err=%s", url, exc)
        return _empty()


def _parse(html: str, base_url: str) -> dict:
    try:
        soup = BeautifulSoup(html, "lxml")
    except Exception:
        soup = BeautifulSoup(html, "html.parser")

    title = (
        _og(soup, "og:title")
        or _meta(soup, "twitter:title")
        or _tag_text(soup, "title")
    )
    description = (
        _og(soup, "og:description")
        or _meta(soup, "twitter:description")
        or _meta(soup, "description")
    )
    favicon = _favicon(soup, base_url)

    return {
        "title": title[:255] if title else None,
        "description": description[:255] if description else None,
        "favicon": favicon[:2048] if favicon else None,
    }


def _og(soup, prop: str) -> str | None:
    tag = soup.find("meta", attrs={"property": prop})
    return tag.get("content") if tag else None


def _meta(soup, name: str) -> str | None:
    tag = soup.find("meta", attrs={"name": name})
    return tag.get("content") if tag else None


def _tag_text(soup, tag_name: str) -> str | None:
    tag = soup.find(tag_name)
    return tag.get_text(strip=True) if tag else None


def _favicon(soup, base_url: str) -> str | None:
    parsed = urlparse(base_url)
    origin = f"{parsed.scheme}://{parsed.netloc}"

    for tag in soup.find_all("link"):
        rel = tag.get("rel", [])
        if isinstance(rel, str):
            rel = [rel]
        if any(r in ("icon", "shortcut icon", "apple-touch-icon") for r in rel):
            href = tag.get("href", "").strip()
            if href:
                return href if href.startswith("http") else urljoin(origin, href)

    # Conventional fallback
    return f"{origin}/favicon.ico"


def _empty() -> dict:
    return {"title": None, "description": None, "favicon": None}
