import pytest
from django.utils import timezone
from datetime import timedelta

from apps.shortener.analytics import (
    get_click_summary_per_url,
    get_clicks_by_country,
    get_clicks_last_n_days,
    get_most_popular_urls,
    get_recent_clicks,
    get_total_clicks_per_url,
    get_urls_with_no_clicks,
)
from apps.shortener.models import Click, URL


@pytest.mark.django_db
class TestGetTotalClicksPerUrl:

    def test_annotates_click_count(self, url, multiple_clicks):
        result = get_total_clicks_per_url()
        annotated = result.get(pk=url.pk)
        assert annotated.total_clicks == len(multiple_clicks)

    def test_url_with_no_clicks(self, url):
        result = get_total_clicks_per_url()
        annotated = result.get(pk=url.pk)
        assert annotated.total_clicks == 0

    def test_ordered_by_clicks_desc(self, db, user):
        url_a = URL.objects.create(
            original_url="https://a.com", short_code="aaa001", owner=user
        )
        url_b = URL.objects.create(
            original_url="https://b.com", short_code="bbb001", owner=user
        )
        for _ in range(3):
            Click.objects.create(url=url_a)
        Click.objects.create(url=url_b)
        result = list(get_total_clicks_per_url())
        assert result[0].total_clicks >= result[1].total_clicks


@pytest.mark.django_db
class TestGetClicksByCountry:

    def test_groups_by_country(self, url, multiple_clicks):
        result = list(get_clicks_by_country(url))
        countries = [r["country"] for r in result]
        assert "Rwanda" in countries
        assert "Kenya" in countries

    def test_counts_correctly(self, url, multiple_clicks):
        result = {r["country"]: r["total"] for r in get_clicks_by_country(url)}
        assert result["Rwanda"] == 2
        assert result["Kenya"] == 1
        assert result["Uganda"] == 1

    def test_ordered_by_total_desc(self, url, multiple_clicks):
        result = list(get_clicks_by_country(url))
        totals = [r["total"] for r in result]
        assert totals == sorted(totals, reverse=True)

    def test_handles_none_country(self, url, multiple_clicks):
        result = {r["country"]: r["total"] for r in get_clicks_by_country(url)}
        assert None in result

    def test_empty_for_url_with_no_clicks(self, url):
        result = list(get_clicks_by_country(url))
        assert result == []


@pytest.mark.django_db
class TestGetMostPopularUrls:

    def test_returns_top_n(self, db, user):
        for i in range(15):
            URL.objects.create(
                original_url=f"https://example{i}.com",
                short_code=f"pop{i:03d}",
                owner=user,
                click_count=i * 10,
            )
        result = list(get_most_popular_urls(limit=5))
        assert len(result) == 5

    def test_ordered_by_clicks_desc(self, db, user):
        URL.objects.create(
            original_url="https://low.com",
            short_code="low001",
            owner=user,
            click_count=10,
        )
        URL.objects.create(
            original_url="https://high.com",
            short_code="hgh001",
            owner=user,
            click_count=500,
        )
        result = list(get_most_popular_urls(limit=10))
        assert result[0].total_clicks >= result[-1].total_clicks

    def test_default_limit_is_ten(self, db, user):
        for i in range(15):
            URL.objects.create(
                original_url=f"https://limit{i}.com",
                short_code=f"lmt{i:03d}",
                owner=user,
                click_count=100,
            )
        result = list(get_most_popular_urls())
        assert len(result) == 10


@pytest.mark.django_db
class TestGetRecentClicks:

    def test_returns_clicks_for_url(self, url, multiple_clicks):
        result = list(get_recent_clicks(url))
        assert len(result) == len(multiple_clicks)

    def test_ordered_by_clicked_at_desc(self, url, multiple_clicks):
        result = list(get_recent_clicks(url))
        timestamps = [c.clicked_at for c in result]
        assert timestamps == sorted(timestamps, reverse=True)

    def test_respects_limit(self, url, multiple_clicks):
        result = list(get_recent_clicks(url, limit=2))
        assert len(result) == 2

    def test_returns_empty_for_no_clicks(self, url):
        result = list(get_recent_clicks(url))
        assert result == []


@pytest.mark.django_db
class TestGetClicksLastNDays:

    def test_returns_clicks_within_window(self, url):
        Click.objects.create(url=url, country="Rwanda")
        result = list(get_clicks_last_n_days(url, days=7))
        assert len(result) > 0

    def test_excludes_old_clicks(self, url):
        old_click = Click.objects.create(url=url, country="Kenya")
        old_click.clicked_at = timezone.now() - timedelta(days=30)
        old_click.save()
        result = {r["country"]: r["total"] for r in get_clicks_last_n_days(url, days=7)}
        assert "Kenya" not in result

    def test_groups_by_country(self, url):
        Click.objects.create(url=url, country="Rwanda")
        Click.objects.create(url=url, country="Rwanda")
        Click.objects.create(url=url, country="Kenya")
        result = {r["country"]: r["total"] for r in get_clicks_last_n_days(url, days=7)}
        assert result["Rwanda"] == 2
        assert result["Kenya"] == 1


@pytest.mark.django_db
class TestGetUrlsWithNoClicks:

    def test_returns_urls_with_zero_clicks(self, url):
        result = list(get_urls_with_no_clicks())
        assert url in result

    def test_excludes_urls_with_clicks(self, url, click):
        result = list(get_urls_with_no_clicks())
        assert url not in result


@pytest.mark.django_db
class TestGetClickSummaryPerUrl:

    def test_annotates_total_clicks(self, url, click):
        result = get_click_summary_per_url()
        annotated = result.get(pk=url.pk)
        assert annotated.total_clicks == 1

    def test_annotates_last_clicked(self, url, click):
        result = get_click_summary_per_url()
        annotated = result.get(pk=url.pk)
        assert annotated.last_clicked is not None
        assert annotated.last_clicked >= click.clicked_at

    def test_last_clicked_none_for_no_clicks(self, url):
        result = get_click_summary_per_url()
        annotated = result.get(pk=url.pk)
        assert annotated.last_clicked is None

    def test_ordered_by_total_clicks_desc(self, db, user):
        url_a = URL.objects.create(
            original_url="https://sumA.com", short_code="smA001", owner=user
        )
        url_b = URL.objects.create(
            original_url="https://sumB.com", short_code="smB001", owner=user
        )
        for _ in range(3):
            Click.objects.create(url=url_a)
        Click.objects.create(url=url_b)
        result = list(get_click_summary_per_url())
        assert result[0].total_clicks >= result[1].total_clicks
