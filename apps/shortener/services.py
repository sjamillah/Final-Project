import secrets
import string
from types import SimpleNamespace
from typing import Optional

from django.conf import settings
from django.db import IntegrityError, transaction
from django.db.models import F, Q

from apps.shortener.cache import invalidate_redirect_cache
from apps.shortener.exceptions import (
    AliasAlreadyTaken,
    PremiumFeatureRequired,
    UniqueCodeError,
    URLLimitExceeded,
)
from apps.shortener.models import Click, Tag, URL

ALPHABET = string.ascii_letters + string.digits
CODE_LENGTH = 6
MAX_RETRIES = 10
FREE_URL_LIMIT = 10


def _is_premium_or_admin(user) -> bool:
    if not user:
        return False
    return getattr(user, "is_premium", False) or (
        getattr(user, "tier", None) == getattr(user, "Tier", None).ADMIN
    )


def _generate_code() -> str:
    return "".join(secrets.choice(ALPHABET) for _ in range(CODE_LENGTH))


def check_url_limit(user) -> None:
    """Raises URLLimitExceeded when a free user has reached their active URL cap."""
    if _is_premium_or_admin(user):
        return

    active_count = (
        URL.objects.filter(owner=user, is_active=True).count()
        if user
        else URL.objects.filter(owner__isnull=True, is_active=True).count()
    )

    if active_count >= FREE_URL_LIMIT:
        raise URLLimitExceeded(
            f"Free users can only have {FREE_URL_LIMIT} active URLs. "
            "Upgrade to Premium for unlimited URLs."
        )


def check_custom_alias_permission(user, custom_alias: str | None) -> None:
    """Raises PremiumFeatureRequired when a free user attempts to use a custom alias."""
    if not custom_alias:
        return
    if not _is_premium_or_admin(user):
        raise PremiumFeatureRequired(
            "Custom aliases are a Premium feature. Upgrade to use vanity URLs."
        )


def resolve_short_code(custom_alias: str | None) -> str:
    """Returns custom_alias if provided, otherwise generates a collision-free short code."""
    if custom_alias:
        return custom_alias

    for _ in range(MAX_RETRIES):
        code = _generate_code()
        if not URL.objects.filter(short_code=code).exists():
            return code

    raise UniqueCodeError(
        f"Could not generate a unique short code after {MAX_RETRIES} attempts."
    )


def get_or_create_tags(tag_names: list[str]) -> list[Tag]:
    return [Tag.objects.get_or_create(name=name.strip())[0] for name in tag_names]


def create_short_url(
    original_url: str,
    owner: Optional[object] = None,
    user: Optional[object] = None,
    custom_alias: Optional[str] = None,
    title: Optional[str] = None,
    expires_at=None,
    tag_names: Optional[list[str]] = None,
) -> URL:
    """
    Create a shortened URL, enforcing tier limits and alias permissions.
    Idempotent: returns the existing URL if the same original_url already exists
    for the same owner.
    """
    user = owner if owner is not None else user

    check_url_limit(user)
    check_custom_alias_permission(user, custom_alias)

    existing = (
        URL.objects.filter(original_url=original_url)
        .filter(Q(owner=user) | Q(owner__isnull=True))
        .first()
    )
    if existing and existing.is_active:
        return existing

    if custom_alias and (
        URL.objects.filter(custom_alias=custom_alias).exists()
        or URL.objects.filter(short_code=custom_alias).exists()
    ):
        raise AliasAlreadyTaken("This custom alias is already taken.")

    short_code = resolve_short_code(custom_alias)

    for _ in range(MAX_RETRIES):
        try:
            with transaction.atomic():
                url = URL.objects.create(
                    original_url=original_url,
                    short_code=short_code,
                    custom_alias=custom_alias,
                    title=title,
                    expires_at=expires_at,
                    owner=user,
                )
            break
        except IntegrityError as exc:
            if "short_code" in str(exc):
                short_code = _generate_code()
                continue
            existing = (
                URL.objects.filter(original_url=original_url)
                .filter(Q(owner=user) | Q(owner__isnull=True))
                .first()
            )
            if existing:
                return existing
            raise
    else:
        raise UniqueCodeError("Failed to create URL after multiple retries.")

    if tag_names:
        url.tags.set(get_or_create_tags(tag_names))

    return url


def update_url(url: URL, validated_data: dict, user) -> URL:
    """Update a URL. Enforces alias permissions and invalidates the redirect cache."""
    custom_alias = validated_data.get("custom_alias")
    check_custom_alias_permission(user, custom_alias)

    if custom_alias:
        conflict = (
            URL.objects.filter(custom_alias=custom_alias)
            | URL.objects.filter(short_code=custom_alias)
        ).exclude(pk=url.pk)
        if conflict.exists():
            raise AliasAlreadyTaken("This custom alias is already taken.")

    tag_names = validated_data.pop("tags", None)

    for field, value in validated_data.items():
        setattr(url, field, value)
    url.save()

    invalidate_redirect_cache(url.short_code, url.custom_alias)

    if tag_names is not None:
        url.tags.set(get_or_create_tags(tag_names))

    return url


def deactivate_url(url: URL) -> URL:
    """Soft-delete a URL and evict it from the redirect cache."""
    url.is_active = False
    url.save(update_fields=["is_active"])
    invalidate_redirect_cache(url.short_code, url.custom_alias)
    return url


def build_click_metadata(meta: dict) -> SimpleNamespace:
    """Extract click metadata from WSGI request.META. Honors TRUST_PROXY_HEADERS."""
    xff = meta.get("HTTP_X_FORWARDED_FOR")
    if getattr(settings, "TRUST_PROXY_HEADERS", False) and xff:
        ip = xff.split(",")[0].strip()
    else:
        ip = meta.get("REMOTE_ADDR")

    return SimpleNamespace(
        ip_address=ip,
        user_agent=meta.get("HTTP_USER_AGENT"),
        referrer=meta.get("HTTP_REFERER"),
    )


def create_click_for_url(
    url: URL,
    ip_address: str | None = None,
    user_agent: str | None = None,
    referrer: str | None = None,
) -> Click:
    """
    Atomically create a Click row and increment the parent URL's click_count.
    Both writes succeed or both are rolled back (ACID).
    """
    with transaction.atomic():
        click = Click.objects.create(
            url=url,
            ip_address=ip_address,
            user_agent=user_agent,
            referrer=referrer,
        )
        URL.objects.filter(pk=url.pk).update(click_count=F("click_count") + 1)
    return click
