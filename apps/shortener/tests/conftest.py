import pytest
from django.utils import timezone
from datetime import timedelta

from apps.shortener.models import Click, Tag, URL, User


@pytest.fixture
def user(db):
    return User.objects.create_user(
        username="testuser",
        email="test@example.com",
        password="testpass123",
    )


@pytest.fixture
def premium_user(db):
    return User.objects.create_user(
        username="premiumuser",
        email="premium@example.com",
        password="testpass123",
        is_premium=True,
        tier=User.Tier.PREMIUM,
    )


@pytest.fixture
def tag(db):
    tag_obj, _ = Tag.objects.get_or_create(name="Marketing")
    return tag_obj


@pytest.fixture
def tag_social(db):
    tag_obj, _ = Tag.objects.get_or_create(name="Social")
    return tag_obj


@pytest.fixture
def url(db, user):
    return URL.objects.create(
        original_url="https://example.com",
        short_code="abc123",
        owner=user,
    )


@pytest.fixture
def url_no_owner(db):
    return URL.objects.create(
        original_url="https://no-owner.com",
        short_code="noown1",
    )


@pytest.fixture
def url_inactive(db, user):
    return URL.objects.create(
        original_url="https://inactive.com",
        short_code="inact1",
        owner=user,
        is_active=False,
    )


@pytest.fixture
def url_expired(db, user):
    return URL.objects.create(
        original_url="https://expired.com",
        short_code="expir1",
        owner=user,
        expires_at=timezone.now() - timedelta(days=1),
    )


@pytest.fixture
def url_future_expiry(db, user):
    return URL.objects.create(
        original_url="https://future.com",
        short_code="futur1",
        owner=user,
        expires_at=timezone.now() + timedelta(days=7),
    )


@pytest.fixture
def click(db, url):
    return Click.objects.create(
        url=url,
        ip_address="192.168.1.1",
        country="Rwanda",
        city="Kigali",
        user_agent="Mozilla/5.0",
    )


@pytest.fixture
def multiple_clicks(db, url):
    clicks = []
    countries = ["Rwanda", "Rwanda", "Kenya", "Uganda", None]
    for country in countries:
        clicks.append(
            Click.objects.create(
                url=url,
                ip_address="192.168.1.1",
                country=country,
            )
        )
    return clicks
