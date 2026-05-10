import pytest
from django.utils import timezone
from datetime import timedelta

from apps.shortener.models import Click, URL
from apps.shortener.tasks import cleanup_expired_urls, track_click_task


@pytest.mark.django_db
class TestTrackClickTask:

    def test_creates_click_record(self, url):
        track_click_task(url.pk, "1.2.3.4", "Mozilla/5.0", None)
        assert Click.objects.filter(url=url).count() == 1

    def test_increments_click_count(self, url):
        track_click_task(url.pk, "1.2.3.4", "Mozilla/5.0", None)
        url.refresh_from_db()
        assert url.click_count == 1

    def test_stores_ip_user_agent_and_referrer(self, url):
        track_click_task(url.pk, "9.9.9.9", "TestAgent/1.0", "https://referrer.com")
        click = Click.objects.get(url=url)
        assert click.ip_address == "9.9.9.9"
        assert click.user_agent == "TestAgent/1.0"
        assert click.referrer == "https://referrer.com"

    def test_null_metadata_is_accepted(self, url):
        track_click_task(url.pk, None, None, None)
        click = Click.objects.get(url=url)
        assert click.ip_address is None
        assert click.user_agent is None

    def test_nonexistent_url_does_not_raise(self, db):
        # Should log a warning and return, not raise.
        track_click_task(99999, "1.2.3.4", "Agent", None)

    def test_multiple_clicks_accumulate(self, url):
        track_click_task(url.pk, "1.1.1.1", "A", None)
        track_click_task(url.pk, "2.2.2.2", "B", None)
        url.refresh_from_db()
        assert url.click_count == 2
        assert Click.objects.filter(url=url).count() == 2


@pytest.mark.django_db
class TestCleanupExpiredUrlsTask:

    def test_deactivates_expired_url(self, db, user):
        url = URL.objects.create(
            original_url="https://expired-cleanup.com",
            short_code="expclup",
            owner=user,
            is_active=True,
            expires_at=timezone.now() - timedelta(hours=1),
        )
        count = cleanup_expired_urls()
        assert count == 1
        url.refresh_from_db()
        assert url.is_active is False

    def test_does_not_touch_active_url(self, url):
        cleanup_expired_urls()
        url.refresh_from_db()
        assert url.is_active is True

    def test_does_not_touch_future_expiry(self, url_future_expiry):
        cleanup_expired_urls()
        url_future_expiry.refresh_from_db()
        assert url_future_expiry.is_active is True

    def test_deactivates_multiple_expired_urls(self, db, user):
        for i in range(3):
            URL.objects.create(
                original_url=f"https://exp{i}.com",
                short_code=f"exp{i:04d}",
                owner=user,
                is_active=True,
                expires_at=timezone.now() - timedelta(minutes=1),
            )
        count = cleanup_expired_urls()
        assert count == 3

    def test_returns_zero_when_nothing_to_clean(self, url):
        count = cleanup_expired_urls()
        assert count == 0
