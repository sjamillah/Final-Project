import secrets
import string

from .models import URL

ALPHABET = string.ascii_letters + string.digits
CODE_LENGTH = 6
MAX_RETRIES = 5


def _generate_code() -> str:
    return "".join(secrets.choice(ALPHABET) for _ in range(CODE_LENGTH))


def _unique_code() -> str:
    for _ in range(MAX_RETRIES):
        code = _generate_code()
        if not URL.objects.filter(short_code=code).exists():
            return code
    raise RuntimeError("Failed to generate a unique short code. Try again.")


def create_short_url(original_url: str) -> URL:
    existing = URL.objects.filter(original_url=original_url).first()
    if existing:
        return existing

    code = _unique_code()
    return URL.objects.create(original_url=original_url, short_code=code)


def get_url_by_code(short_code: str) -> URL | None:
    return URL.objects.filter(short_code=short_code).first()
