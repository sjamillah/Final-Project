from .models import URL


def url_exists(short_code: str) -> bool:
    return bool(URL.objects.get_by_code(short_code))


def get_all_urls() -> list[URL]:
    return list(URL.objects.order_by("-created_at"))
