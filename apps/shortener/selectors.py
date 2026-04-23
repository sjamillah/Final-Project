from django.db.models import Prefetch  # pyright: ignore[reportMissingModuleSource]

from .models import Click, URL

# Basic fetches


def get_urls_with_owner():
    """Single query using JOIN. Avoids N+1 when accessing url.owner.*"""
    return URL.objects.select_related("owner").all()


def get_urls_with_tags():
    """Two queries total regardless of row count. Avoids N+1 on url.tags.all()"""
    return URL.objects.prefetch_related("tags").all()


def get_urls_full():
    """Three queries total: URLs + owners (JOIN) + tags + clicks (prefetch)."""
    return (
        URL.objects.select_related("owner")
        .prefetch_related("tags")
        .prefetch_related(
            Prefetch("clicks", queryset=Click.objects.order_by("-clicked_at"))
        )
    )


# Scoped fetches


def get_active_urls_with_owner():
    """Active URLs only, owner resolved in the same query."""
    return URL.objects.active().select_related("owner")


def get_popular_urls_with_tags(threshold=100):
    """Popular URLs with tags prefetched. Safe to iterate and call .tags.all()"""
    return URL.objects.popular(threshold=threshold).prefetch_related("tags")


def get_url_by_code_with_owner(short_code: str) -> URL | None:
    """Single URL lookup by short_code. Resolves owner in the same query."""
    return URL.objects.select_related("owner").filter(short_code=short_code).first()


def get_urls_for_user(user):
    """All URLs belonging to a user. Tags prefetched for safe iteration."""
    return (
        URL.objects.filter(owner=user).prefetch_related("tags").order_by("-created_at")
    )
