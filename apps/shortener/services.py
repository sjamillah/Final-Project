import secrets
import string
from typing import Optional

from django.db import IntegrityError, transaction
from django.db.models import F, Q
from django.utils import timezone

from apps.shortener.models import Tag, URL, Click

ALPHABET = string.ascii_letters + string.digits
CODE_LENGTH = 6
MAX_RETRIES = 10
FREE_URL_LIMIT = 10


def _is_premium_or_admin(user) -> bool:
    """Check if user is premium or admin. Centralized tier check."""
    if not user:
        return False
    return getattr(user, "is_premium", False) or (
        getattr(user, "tier", None) == getattr(user, "Tier", None).ADMIN
    )


def _generate_code() -> str:
    return "".join(secrets.choice(ALPHABET) for _ in range(CODE_LENGTH))


def check_url_limit(user) -> None:
    """
    Raises ValueError if a free user has reached their active URL limit.
    Premium and admin users are exempt.
    """
    if _is_premium_or_admin(user):
        return

    if user:
        active_count = URL.objects.filter(owner=user, is_active=True).count()
    else:
        active_count = URL.objects.filter(owner__isnull=True, is_active=True).count()

    if active_count >= FREE_URL_LIMIT:
        raise ValueError(
            f"Free users can only have {FREE_URL_LIMIT} active URLs. "
            "Upgrade to Premium for unlimited URLs."
        )


def check_custom_alias_permission(user, custom_alias: str | None) -> None:
    """
    Raises ValueError if a free or anonymous user attempts to use a custom alias.
    """
    if not custom_alias:
        return
    if not _is_premium_or_admin(user):
        raise ValueError(
            "Custom aliases are a Premium feature. Upgrade to use vanity URLs."
        )


def resolve_short_code(custom_alias: str | None) -> str:
    """
    Returns custom_alias if provided, otherwise generates a unique short code.
    """
    if custom_alias:
        return custom_alias

    for _ in range(MAX_RETRIES):
        code = _generate_code()
        if not URL.objects.filter(short_code=code).exists():
            return code

    raise RuntimeError(
        f"Could not generate a unique short code after {MAX_RETRIES} attempts."
    )


def get_or_create_tags(tag_names: list[str]) -> list[Tag]:
    """
    Fetches or creates Tag objects for the given list of names.
    Returns a list of Tag instances.
    """
    tags = []
    for name in tag_names:
        tag, _ = Tag.objects.get_or_create(name=name.strip())
        tags.append(tag)
    return tags


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
    Core service for creating a shortened URL.
    Enforces tier limits and custom alias permissions.

    This function is idempotent for duplicate `original_url` submissions: if a
    matching active URL already exists (either owned by the same user or an
    anonymous URL), the existing instance is returned.
    """
    # Support both `owner=` (tests) and `user=` (older callers).
    user = owner if owner is not None else user

    check_url_limit(user)
    check_custom_alias_permission(user, custom_alias)

    # If an active URL for this original URL already exists, return it.
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
        raise ValueError("This custom alias is already taken.")

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
        except IntegrityError as e:
            # If short_code collided, try a new code and retry.
            if "short_code" in str(e):
                short_code = _generate_code()
                continue
            # On original-url owner unique constraint, try to fetch existing.
            existing = (
                URL.objects.filter(original_url=original_url)
                .filter(Q(owner=user) | Q(owner__isnull=True))
                .first()
            )
            if existing:
                return existing
            raise
    else:
        raise RuntimeError("Failed to create URL after multiple retries.")

    if tag_names:
        tags = get_or_create_tags(tag_names)
        url.tags.set(tags)

    return url


def get_url_by_code(short_code: str) -> URL | None:
    """
    Looks up a URL by short_code or custom_alias.
    Returns None if not found or inactive.
    """
    url = (
        URL.objects.filter(short_code=short_code, is_active=True).first()
    ) or URL.objects.filter(custom_alias=short_code, is_active=True).first()

    if url and url.expires_at and url.expires_at < timezone.now():
        return None

    return url


def update_url(url: URL, validated_data: dict, user) -> URL:
    """
    Updates a URL instance. Enforces custom alias permissions on update.
    """
    custom_alias = validated_data.get("custom_alias")
    check_custom_alias_permission(user, custom_alias)

    if custom_alias:
        alias_qs = URL.objects.filter(custom_alias=custom_alias) | URL.objects.filter(
            short_code=custom_alias
        )
        if alias_qs.exclude(pk=url.pk).exists():
            raise ValueError("This custom alias is already taken.")

    tag_names = validated_data.pop("tags", None)

    for field, value in validated_data.items():
        setattr(url, field, value)
    url.save()

    if tag_names is not None:
        tags = get_or_create_tags(tag_names)
        url.tags.set(tags)

    return url


def deactivate_url(url: URL) -> URL:
    """
    Soft deletes a URL by setting is_active=False.
    """
    url.is_active = False
    url.save(update_fields=["is_active"])
    return url


def build_click_metadata(meta: dict) -> dict:
    """Extract minimal click metadata from WSGI `request.META` mapping.

    Returns a simple object with attribute access (for tests and callers).
    Honors the `TRUST_PROXY_HEADERS` setting.
    """
    from types import SimpleNamespace
    from django.conf import settings

    xff = meta.get("HTTP_X_FORWARDED_FOR")
    ip = None
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
    metadata: dict | None = None,
    ip_address: str | None = None,
    meta: dict | None = None,
) -> Click:
    """Create a Click row and increment the parent URL's click_count.

    Backwards-compatible: callers can pass `ip_address=` or a `meta`/`metadata` dict
    (typically `request.META`). If none provided, creates a Click with
    null metadata fields.
    """
    # Prefer explicit ip_address, then meta/metadata dict, then metadata arg.
    data_obj = None
    if ip_address is not None:
        # build a small object with attribute access
        from types import SimpleNamespace

        data_obj = SimpleNamespace(
            ip_address=ip_address, user_agent=None, referrer=None
        )
    else:
        if metadata:
            if isinstance(metadata, dict):
                data_obj = build_click_metadata(metadata)
            elif hasattr(metadata, "ip_address"):
                data_obj = metadata
            elif hasattr(metadata, "get"):
                # Mapping-like
                data_obj = build_click_metadata(metadata)
            else:
                # Fallback: attempt to coerce to mapping
                try:
                    data_obj = build_click_metadata(dict(metadata))
                except Exception:
                    data_obj = None
        elif meta:
            if isinstance(meta, dict):
                data_obj = build_click_metadata(meta)
            elif hasattr(meta, "ip_address"):
                data_obj = meta
            else:
                try:
                    data_obj = build_click_metadata(dict(meta))
                except Exception:
                    data_obj = None

    if data_obj is None:
        # empty object
        from types import SimpleNamespace

        data_obj = SimpleNamespace(ip_address=None, user_agent=None, referrer=None)

    click = Click.objects.create(
        url=url,
        ip_address=data_obj.ip_address,
        user_agent=data_obj.user_agent,
        referrer=data_obj.referrer,
    )
    URL.objects.filter(pk=url.pk).update(click_count=F("click_count") + 1)
    return click
