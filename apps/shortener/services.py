import logging
import secrets
import string

from django.db import IntegrityError, transaction

from .exceptions import UniqueCodeError
from .models import URL

logger = logging.getLogger(__name__)

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
    last_exc = None
    for _ in range(MAX_RETRIES):
        code = _generate_code()
        try:
            with transaction.atomic():
                obj, _created = URL.objects.get_or_create(
                    original_url=original_url, defaults={"short_code": code}
                )
                logger.info("Resolved short URL for %s", original_url)
                return obj
        except IntegrityError as exc:
            last_exc = exc
            logger.warning(
                "IntegrityError while creating short URL for %s; retrying",
                original_url,
            )
            continue

    logger.error("Failed to create short URL for %s after retries", original_url)
    raise UniqueCodeError(
        "Failed to create a unique short code after retries."
    ) from last_exc


def get_url_by_code(short_code: str) -> URL | None:
    return URL.objects.filter(short_code=short_code).first()
