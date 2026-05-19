import logging

from celery import shared_task
from django.db import transaction
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
