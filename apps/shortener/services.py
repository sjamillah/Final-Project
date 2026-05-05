from dataclasses import dataclass
import secrets
import string
from collections.abc import Mapping

from django.conf import settings
from django.db import IntegrityError, transaction
from django.db.models import F

from .models import Click, URL, User
from .exceptions import UniqueCodeError


@dataclass(frozen=True, slots=True)
class ClickMetadata:
    ip_address: str | None
    user_agent: str | None
    referrer: str | None

    @staticmethod
    def _first_forwarded_ip(forwarded_for: str) -> str | None:
        first_ip = forwarded_for.split(",")[0].strip()
        return first_ip or None

    @classmethod
    def from_request_meta(cls, meta: Mapping[str, str]) -> "ClickMetadata":
        forwarded_for = meta.get("HTTP_X_FORWARDED_FOR", "")
        trust_proxy_headers = getattr(settings, "TRUST_PROXY_HEADERS", False)

        ip_address = None
        if trust_proxy_headers and forwarded_for:
            ip_address = cls._first_forwarded_ip(forwarded_for)
        if not ip_address:
            ip_address = meta.get("REMOTE_ADDR")

        return cls(
            ip_address=ip_address,
            user_agent=meta.get("HTTP_USER_AGENT"),
            referrer=meta.get("HTTP_REFERER"),
        )


logger = logging.getLogger(__name__)

ALPHABET = string.ascii_letters + string.digits
CODE_LENGTH = 6
MAX_RETRIES = 5

SHORT_CODE_ERROR_HINT = "short_code"
OWNER_ORIGINAL_CONSTRAINT_NAMES = {
    "uniq_owner_original_url",
    "uniq_anon_original_url",
}


def _generate_code() -> str:
    return "".join(secrets.choice(ALPHABET) for _ in range(CODE_LENGTH))


def _unique_code() -> str:
    for _ in range(MAX_RETRIES):
        code = _generate_code()
        if not URL.objects.filter(short_code=code).exists():
            return code
    raise UniqueCodeError("Failed to generate a unique short code. Try again.")


def _get_existing_url_for_owner(original_url: str, owner: User | None) -> URL | None:
    if owner is None:
        return URL.objects.filter(original_url=original_url, owner__isnull=True).first()
    return URL.objects.filter(original_url=original_url, owner=owner).first()


def _extract_constraint_name(exc: IntegrityError) -> str | None:
    cause = getattr(exc, "__cause__", None)
    diag = getattr(cause, "diag", None)
    return getattr(diag, "constraint_name", None)


def _is_short_code_integrity_error(exc: IntegrityError) -> bool:
    constraint_name = _extract_constraint_name(exc)
    if constraint_name:
        return SHORT_CODE_ERROR_HINT in constraint_name
    return SHORT_CODE_ERROR_HINT in str(exc)


def _is_owner_original_integrity_error(exc: IntegrityError) -> bool:
    constraint_name = _extract_constraint_name(exc)
    if constraint_name:
        return constraint_name in OWNER_ORIGINAL_CONSTRAINT_NAMES
    error_text = str(exc)
    return "owner" in error_text and "original_url" in error_text


def create_short_url(original_url: str, owner: User | None = None) -> URL:
    # ACID: this write path is wrapped in atomic transactions and retries only on
    # short-code uniqueness collisions.
    for _ in range(MAX_RETRIES):
        existing = _get_existing_url_for_owner(original_url=original_url, owner=owner)
        if existing:
            return existing

        try:
            with transaction.atomic():
                return URL.objects.create(
                    original_url=original_url,
                    short_code=_generate_code(),
                    owner=owner,
                )
        except IntegrityError as exc:
            if _is_owner_original_integrity_error(exc):
                existing = _get_existing_url_for_owner(
                    original_url=original_url,
                    owner=owner,
                )
                if existing:
                    return existing
                raise

            if _is_short_code_integrity_error(exc):
                continue

            raise

    raise UniqueCodeError("Failed to generate a unique short code. Try again.")


def build_click_metadata(meta: Mapping[str, str]) -> ClickMetadata:
    return ClickMetadata.from_request_meta(meta)


def create_click_for_url(
    url: URL,
    *,
    metadata: ClickMetadata | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
    country: str | None = None,
    city: str | None = None,
    referrer: str | None = None,
) -> Click:
    if metadata is not None:
        ip_address = metadata.ip_address
        user_agent = metadata.user_agent
        referrer = metadata.referrer

    with transaction.atomic():
        click = Click.objects.create(
            url=url,
            ip_address=ip_address,
            user_agent=user_agent,
            country=country,
            city=city,
            referrer=referrer,
        )
        URL.objects.filter(pk=url.pk).update(click_count=F("click_count") + 1)
    return click


def get_url_by_code(short_code: str) -> URL | None:
    # Compatibility wrapper retained for callers still importing from services.
    from .selectors import get_url_by_code as selector_get_url_by_code

    return selector_get_url_by_code(short_code)
