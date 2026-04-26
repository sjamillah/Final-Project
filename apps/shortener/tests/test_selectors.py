import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from apps.shortener.models import URL
from apps.shortener.selectors import (
    get_active_urls_with_owner,
    get_url_by_code,
    get_popular_urls_with_tags,
    get_url_by_code_with_owner,
    get_urls_for_user,
    get_urls_full,
    get_urls_with_owner,
    get_urls_with_tags,
    resolve_redirect_url,
)


@pytest.mark.django_db
class TestGetUrlsWithOwner:

    def test_returns_urls(self, url):
        result = list(get_urls_with_owner())
        assert url in result

    def test_no_extra_queries_for_owner(self, url):
        urls = list(get_urls_with_owner())
        with CaptureQueriesContext(connection) as ctx:
            for u in urls:
                _ = u.owner.username if u.owner else None
        assert len(ctx.captured_queries) == 0

    def test_returns_queryset(self):
        from django.db.models.query import QuerySet

        assert isinstance(get_urls_with_owner(), QuerySet)


@pytest.mark.django_db
class TestGetUrlsWithTags:

    def test_returns_urls(self, url):
        result = list(get_urls_with_tags())
        assert url in result

    def test_no_extra_queries_for_tags(self, url, tag):
        url.tags.add(tag)
        urls = list(get_urls_with_tags())
        with CaptureQueriesContext(connection) as ctx:
            for u in urls:
                _ = list(u.tags.all())
        assert len(ctx.captured_queries) == 0


@pytest.mark.django_db
class TestGetUrlsFull:

    def test_returns_urls(self, url):
        result = list(get_urls_full())
        assert url in result

    def test_owner_and_tags_prefetched(self, url, tag, click):
        url.tags.add(tag)
        urls = list(get_urls_full())
        with CaptureQueriesContext(connection) as ctx:
            for u in urls:
                _ = u.owner.username if u.owner else None
                _ = list(u.tags.all())
                _ = list(u.clicks.all())
        assert len(ctx.captured_queries) == 0


@pytest.mark.django_db
class TestGetActiveUrlsWithOwner:

    def test_returns_active_urls(self, url):
        result = list(get_active_urls_with_owner())
        assert url in result

    def test_excludes_inactive(self, url_inactive):
        result = list(get_active_urls_with_owner())
        assert url_inactive not in result

    def test_excludes_expired(self, url_expired):
        result = list(get_active_urls_with_owner())
        assert url_expired not in result


@pytest.mark.django_db
class TestGetPopularUrlsWithTags:

    def test_returns_popular_urls(self, db, user):
        popular = URL.objects.create(
            original_url="https://popular.com",
            short_code="pop999",
            owner=user,
            click_count=200,
        )
        result = list(get_popular_urls_with_tags(threshold=100))
        assert popular in result

    def test_excludes_unpopular(self, url):
        assert url.click_count == 0
        result = list(get_popular_urls_with_tags(threshold=100))
        assert url not in result

    def test_tags_prefetched(self, db, user, tag):
        popular = URL.objects.create(
            original_url="https://pop2.com",
            short_code="pop998",
            owner=user,
            click_count=200,
        )
        popular.tags.add(tag)
        urls = list(get_popular_urls_with_tags(threshold=100))
        with CaptureQueriesContext(connection) as ctx:
            for u in urls:
                _ = list(u.tags.all())
        assert len(ctx.captured_queries) == 0


@pytest.mark.django_db
class TestGetUrlByCodeWithOwner:

    def test_returns_url_for_valid_code(self, url):
        result = get_url_by_code_with_owner(url.short_code)
        assert result is not None
        assert result.pk == url.pk

    def test_returns_none_for_invalid_code(self, db):
        result = get_url_by_code_with_owner("xxxxxx")
        assert result is None

    def test_owner_prefetched(self, url):
        result = get_url_by_code_with_owner(url.short_code)
        with CaptureQueriesContext(connection) as ctx:
            _ = result.owner.username if result.owner else None
        assert len(ctx.captured_queries) == 0


@pytest.mark.django_db
class TestGetUrlByCode:

    def test_returns_url_for_valid_code(self, url):
        result = get_url_by_code(url.short_code)
        assert result is not None
        assert result.pk == url.pk

    def test_returns_none_for_invalid_code(self):
        result = get_url_by_code("xxxxxx")
        assert result is None


@pytest.mark.django_db
class TestGetUrlsForUser:

    def test_returns_urls_for_user(self, url, user):
        result = list(get_urls_for_user(user))
        assert url in result

    def test_excludes_other_user_urls(self, url, premium_user):
        result = list(get_urls_for_user(premium_user))
        assert url not in result

    def test_ordered_by_created_at_desc(self, db, user):
        URL.objects.create(
            original_url="https://first.com",
            short_code="first1",
            owner=user,
        )
        URL.objects.create(
            original_url="https://second.com",
            short_code="secnd1",
            owner=user,
        )
        result = list(get_urls_for_user(user))
        assert result[0].created_at >= result[-1].created_at

    def test_tags_prefetched(self, url, user, tag):
        url.tags.add(tag)
        urls = list(get_urls_for_user(user))
        with CaptureQueriesContext(connection) as ctx:
            for u in urls:
                _ = list(u.tags.all())
        assert len(ctx.captured_queries) == 0


@pytest.mark.django_db
class TestResolveRedirectUrl:

    def test_returns_active_state(self, url):
        state, resolved = resolve_redirect_url(url.short_code)
        assert state == "active"
        assert resolved is not None
        assert resolved.pk == url.pk

    def test_returns_not_found_state(self):
        state, resolved = resolve_redirect_url("missing1")
        assert state == "not_found"
        assert resolved is None

    def test_returns_inactive_state(self, url_inactive):
        state, resolved = resolve_redirect_url(url_inactive.short_code)
        assert state == "inactive"
        assert resolved is not None

    def test_returns_expired_state(self, url_expired):
        state, resolved = resolve_redirect_url(url_expired.short_code)
        assert state == "expired"
        assert resolved is not None
