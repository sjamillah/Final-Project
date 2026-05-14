import logging

from celery import shared_task
from django.db import IntegrityError, transaction
from django.db.models import F
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=2)
def track_click_task(
    self,
    url_id: int,
    ip_address: str | None,
    user_agent: str | None,
    referrer: str | None = None,
) -> None:
    """
    Write a Click row and increment click_count atomically.
    Retries up to 3 times on transient failures.
    Models are imported inside the function — standard Celery pattern to avoid
    import-time side effects before Django is fully initialised.
    """
    from apps.shortener.models import Click, URL

    try:
        url = URL.objects.get(pk=url_id)
    except URL.DoesNotExist:
        logger.warning("track_click_task: URL %d not found, skipping.", url_id)
        return

    try:
        with transaction.atomic():
            Click.objects.create(
                url=url,
                ip_address=ip_address,
                user_agent=user_agent,
                referrer=referrer,
            )
            URL.objects.filter(pk=url_id).update(click_count=F("click_count") + 1)
    except Exception as exc:
        logger.exception("track_click_task failed for url_id=%d", url_id)
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3)
def fetch_url_preview_task(self, url_id: int, original_url: str) -> None:
    """
    Fetch title / description / favicon for a shortened URL and persist them.

    Design choices:
    - Runs asynchronously via Celery so URL creation is never slowed by an
      external HTTP call.
    - Dispatched with transaction.on_commit in services.py so the task is
      guaranteed to see the committed URL row.
    - Respects user-supplied metadata: only fills fields that are still null.
    - Circuit-breaker in preview_client stops hammering dead domains.
    - Retries up to 3× with exponential backoff when the preview_service
      container is temporarily unreachable (httpx returns None in that case,
      so we retry; circuit-open returns None and we DON'T retry — by design).
    """
    from apps.shortener.models import URL
    from apps.shortener.preview_client import fetch_preview

    try:
        url = URL.objects.get(pk=url_id)
    except URL.DoesNotExist:
        logger.warning("fetch_url_preview_task: URL %d not found, skipping.", url_id)
        return

    # Nothing to do if all fields were already provided by the user.
    if url.title and url.description and url.favicon:
        return

    preview = fetch_preview(original_url)

    # None means circuit is open OR transport error — retry on transport error.
    # We distinguish: circuit open → preview_client already logged it, skip.
    # Transport / HTTP error → preview_client returns None AND records a failure.
    # We retry unless the circuit just opened (is_open check after the call).
    if preview is None:
        from apps.shortener.circuit_breaker import domain_from_url, is_open

        if not is_open(domain_from_url(original_url)):
            # Service unreachable — retry with exponential backoff.
            raise self.retry(countdown=2**self.request.retries * 5)
        return  # Circuit open — give up gracefully.

    update = {}
    if preview.title and not url.title:
        update["title"] = preview.title[:255]
    if preview.description and not url.description:
        update["description"] = preview.description[:255]
    if preview.favicon and not url.favicon:
        update["favicon"] = preview.favicon[:2048]

    if not update:
        return

    try:
        URL.objects.filter(pk=url_id).update(**update)
    except IntegrityError:
        # Unique constraint still on one of the fields in an old schema —
        # fall back to field-by-field so we save as much as possible.
        for field, value in update.items():
            try:
                URL.objects.filter(pk=url_id).update(**{field: value})
            except IntegrityError:
                logger.debug(
                    "fetch_url_preview_task: unique conflict on %s for url_id=%d",
                    field,
                    url_id,
                )


@shared_task
def cleanup_expired_urls() -> int:
    """Nightly task: soft-deactivate URLs whose expiry timestamp has passed."""
    from apps.shortener.models import URL

    count = URL.objects.filter(
        is_active=True,
        expires_at__lt=timezone.now(),
    ).update(is_active=False)

    logger.info("cleanup_expired_urls: deactivated %d expired URLs.", count)
    return count
