from django.db.models import Count, Max  # type: ignore[reportMissingImports]
from django.utils import timezone  # type: ignore[reportMissingImports]
from datetime import timedelta  # type: ignore[reportMissingImports]

from .models import Click, URL


def get_total_clicks_per_url():
    """Annotates each URL with its total click count directly in the database."""
    return URL.objects.annotate(total_clicks=Count("clicks")).order_by("-total_clicks")


def get_clicks_by_country(url: URL):
    """Groups clicks for a single URL by country and counts each group."""
    return (
        Click.objects.filter(url=url)
        .values("country")
        .annotate(total=Count("id"))
        .order_by("-total")
    )


def get_most_popular_urls(limit: int = 10):
    """Returns the top N URLs ranked by annotated click count."""
    return URL.objects.annotate(total_clicks=Count("clicks")).order_by("-total_clicks")[
        :limit
    ]


def get_recent_clicks(url: URL, limit: int = 20):
    """Returns the most recent N clicks for a URL ordered by time descending."""
    return (
        Click.objects.filter(url=url)
        .select_related("url")
        .order_by("-clicked_at")[:limit]
    )


def get_clicks_last_n_days(url: URL, days: int = 7):
    """Counts clicks on a URL within the last N days, grouped by country."""
    since = timezone.now() - timedelta(days=days)
    return (
        Click.objects.filter(url=url, clicked_at__gte=since)
        .values("country")
        .annotate(total=Count("id"))
        .order_by("-total")
    )


def get_urls_with_no_clicks():
    """Finds URLs that have never been clicked using annotate + filter."""
    return URL.objects.annotate(total_clicks=Count("clicks")).filter(total_clicks=0)


def get_click_summary_per_url():
    """Returns each URL with total clicks and the timestamp of the last click."""
    return URL.objects.annotate(
        total_clicks=Count("clicks"),
        last_clicked=Max("clicks__clicked_at"),
    ).order_by("-total_clicks")
