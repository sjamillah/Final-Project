import secrets
import string

from django.db import IntegrityError, transaction

from .models import URL
from .exceptions import UniqueCodeError

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
    raise UniqueCodeError("Failed to generate a unique short code. Try again.")


def create_short_url(original_url: str) -> URL:
    # Try to return existing or create atomically using manager helper.
    last_exc = None
    for _ in range(MAX_RETRIES):
        code = _generate_code()
        try:
            with transaction.atomic():
                obj, created = URL.objects.get_or_create(
                    original_url=original_url, defaults={"short_code": code}
                )
                return obj
        except IntegrityError as exc:
            # possible race on short_code unique constraint — try again
            last_exc = exc
            continue

    raise UniqueCodeError(
        "Failed to create a unique short code after retries."
    ) from last_exc


def get_url_by_code(short_code: str) -> URL | None:
    return URL.objects.filter(short_code=short_code).first()
