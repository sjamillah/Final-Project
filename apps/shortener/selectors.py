from .models import URL


def url_exists(short_code: str) -> bool:
    return URL.objects.filter(short_code=short_code).exists()


def get_all_urls() -> list[URL]:
    return URL.objects.order_by("-created_at")
