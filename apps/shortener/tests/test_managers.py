import pytest

from apps.shortener.models import URL


@pytest.mark.django_db
class TestURLManagerActive:

    def test_active_returns_active_url(self, url):
        result = URL.objects.active()
        assert url in result

    def test_active_excludes_inactive(self, url_inactive):
        result = URL.objects.active()
        assert url_inactive not in result

    def test_active_excludes_expired(self, url_expired):
        result = URL.objects.active()
        assert url_expired not in result

    def test_active_includes_future_expiry(self, url_future_expiry):
        result = URL.objects.active()
        assert url_future_expiry in result

    def test_active_includes_no_expiry(self, url):
        assert url.expires_at is None
        result = URL.objects.active()
        assert url in result

    def test_active_is_chainable(self, url, user):
        result = URL.objects.active().filter(owner=user)
        assert url in result

    def test_active_excludes_both_inactive_and_expired(
        self, url, url_inactive, url_expired
    ):
        result = list(URL.objects.active())
        assert url in result
        assert url_inactive not in result
        assert url_expired not in result


@pytest.mark.django_db
class TestURLManagerExpired:

    def test_expired_returns_inactive_url(self, url_inactive):
        result = URL.objects.expired()
        assert url_inactive in result

    def test_expired_returns_past_expiry(self, url_expired):
        result = URL.objects.expired()
        assert url_expired in result

    def test_expired_excludes_active(self, url):
        result = URL.objects.expired()
        assert url not in result

    def test_expired_excludes_future_expiry(self, url_future_expiry):
        result = URL.objects.expired()
        assert url_future_expiry not in result

    def test_expired_is_chainable(self, url_expired, user):
        result = URL.objects.expired().filter(owner=user)
        assert url_expired in result


@pytest.mark.django_db
class TestURLManagerPopular:

    def test_popular_returns_high_click_urls(self, db, user):
        popular = URL.objects.create(
            original_url="https://popular.com",
            short_code="pop123",
            owner=user,
            click_count=500,
        )
        result = URL.objects.popular(threshold=100)
        assert popular in result

    def test_popular_excludes_low_click_urls(self, url):
        assert url.click_count == 0
        result = URL.objects.popular(threshold=100)
        assert url not in result

    def test_popular_respects_custom_threshold(self, db, user):
        url = URL.objects.create(
            original_url="https://medium.com",
            short_code="med123",
            owner=user,
            click_count=50,
        )
        assert url in URL.objects.popular(threshold=10)
        assert url not in URL.objects.popular(threshold=100)

    def test_popular_ordered_by_click_count_desc(self, db, user):
        URL.objects.create(
            original_url="https://a.com",
            short_code="aaa111",
            owner=user,
            click_count=200,
        )
        URL.objects.create(
            original_url="https://b.com",
            short_code="bbb111",
            owner=user,
            click_count=500,
        )
        result = list(URL.objects.popular(threshold=100))
        assert result[0].click_count >= result[1].click_count

    def test_popular_is_chainable(self, db, user):
        URL.objects.create(
            original_url="https://popular2.com",
            short_code="pop456",
            owner=user,
            click_count=300,
        )
        result = URL.objects.popular(threshold=100).filter(owner=user)
        assert result.exists()
