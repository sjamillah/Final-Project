import pytest
from unittest.mock import patch
from django.db import IntegrityError
from django.test import override_settings

from apps.shortener.models import Click, URL
from apps.shortener.services import (
    _generate_code,
    build_click_metadata,
    create_click_for_url,
    create_short_url,
)
from apps.shortener.selectors import get_url_by_code


@pytest.mark.django_db
class TestGenerateCode:

    def test_returns_string(self):
        code = _generate_code()
        assert isinstance(code, str)

    def test_correct_length(self):
        code = _generate_code()
        assert len(code) == 6

    def test_alphanumeric_only(self):
        for _ in range(20):
            code = _generate_code()
            assert code.isalnum()

    def test_generates_unique_values(self):
        codes = {_generate_code() for _ in range(50)}
        assert len(codes) > 1


@pytest.mark.django_db
class TestCreateShortUrl:

    def test_creates_new_url(self, db):
        result = create_short_url("https://example.com/new")
        assert result.pk is not None
        assert result.original_url == "https://example.com/new"
        assert len(result.short_code) == 6

    def test_returns_existing_for_duplicate(self, db):
        first = create_short_url("https://example.com/dup")
        second = create_short_url("https://example.com/dup")
        assert first.pk == second.pk
        assert URL.objects.filter(original_url="https://example.com/dup").count() == 1

    def test_returns_existing_for_same_owner(self, db, user):
        first = create_short_url("https://example.com/owned-dup", owner=user)
        second = create_short_url("https://example.com/owned-dup", owner=user)
        assert first.pk == second.pk

    def test_different_owner_gets_different_url(self, db, user, premium_user):
        first = create_short_url("https://example.com/shared", owner=user)
        second = create_short_url("https://example.com/shared", owner=premium_user)
        assert first.pk != second.pk

    def test_retries_on_integrity_error_then_succeeds(self, db):
        with patch("apps.shortener.services.URL.objects.create") as mock_create:
            mock_create.side_effect = [
                IntegrityError(
                    "duplicate key value violates unique constraint urls_short_code"
                ),
                URL(original_url="https://example.com/retry", short_code="ret123"),
            ]
            result = create_short_url("https://example.com/retry")
            assert result.short_code == "ret123"
            assert mock_create.call_count == 2

    def test_raises_for_unexpected_integrity_error(self, db):
        with patch("apps.shortener.services.URL.objects.create") as mock_create:
            mock_create.side_effect = IntegrityError("other constraint failure")
            with pytest.raises(IntegrityError):
                create_short_url("https://example.com/fail")

    def test_different_urls_get_different_codes(self, db):
        first = create_short_url("https://example.com/one")
        second = create_short_url("https://example.com/two")
        assert first.short_code != second.short_code

    def test_returns_url_instance(self, db):
        result = create_short_url("https://example.com/typed")
        assert isinstance(result, URL)

    def test_short_code_is_stored(self, db):
        result = create_short_url("https://example.com/stored")
        from_db = URL.objects.get(pk=result.pk)
        assert from_db.short_code == result.short_code


@pytest.mark.django_db
class TestCreateClickForUrl:

    def test_creates_click_entry(self, url):
        click = create_click_for_url(url=url, ip_address="127.0.0.1")
        assert isinstance(click, Click)
        assert click.url_id == url.pk
        assert click.ip_address == "127.0.0.1"

    def test_increments_click_count(self, url):
        assert url.click_count == 0
        create_click_for_url(url=url)
        url.refresh_from_db()
        assert url.click_count == 1


class TestBuildClickMetadata:

    @override_settings(TRUST_PROXY_HEADERS=False)
    def test_uses_remote_addr_when_proxy_headers_not_trusted(self):
        data = build_click_metadata(
            {
                "HTTP_X_FORWARDED_FOR": "1.1.1.1, 2.2.2.2",
                "REMOTE_ADDR": "9.9.9.9",
            }
        )
        assert data.ip_address == "9.9.9.9"

    @override_settings(TRUST_PROXY_HEADERS=True)
    def test_uses_forwarded_for_when_proxy_headers_trusted(self):
        data = build_click_metadata(
            {
                "HTTP_X_FORWARDED_FOR": "1.1.1.1, 2.2.2.2",
                "REMOTE_ADDR": "9.9.9.9",
            }
        )
        assert data.ip_address == "1.1.1.1"


@pytest.mark.django_db
class TestCheckUrlLimit:
    """Tests for free tier URL limit enforcement."""

    def test_free_user_reaches_limit_raises_error(self, db):
        from apps.users.models import User
        from apps.shortener.services import check_url_limit

        user = User.objects.create_user(
            username="freeuser",
            email="free@test.com",
            password="Pass123!",
        )
        # Create 10 active URLs
        for i in range(10):
            URL.objects.create(
                owner=user,
                original_url=f"https://example.com/{i}",
                short_code=f"code{i:02d}",
                is_active=True,
            )

        from apps.shortener.exceptions import URLLimitExceeded

        with pytest.raises(URLLimitExceeded, match="Free users can only have"):
            check_url_limit(user)

    def test_premium_user_no_limit(self, db):
        from apps.users.models import User
        from apps.shortener.services import check_url_limit

        user = User.objects.create_user(
            username="premiumuser",
            email="premium@test.com",
            password="Pass123!",
            tier=User.Tier.PREMIUM,
        )
        # Create 15 URLs (exceeds free limit)
        for i in range(15):
            URL.objects.create(
                owner=user,
                original_url=f"https://example.com/{i}",
                short_code=f"code{i:02d}",
                is_active=True,
            )

        # Should not raise
        check_url_limit(user)


@pytest.mark.django_db
class TestCheckCustomAliasPermission:
    """Tests for custom alias permission enforcement."""

    def test_free_user_cannot_use_custom_alias(self, db):
        from apps.users.models import User
        from apps.shortener.services import check_custom_alias_permission

        user = User.objects.create_user(
            username="freeuser",
            email="free@test.com",
            password="Pass123!",
        )

        from apps.shortener.exceptions import PremiumFeatureRequired

        with pytest.raises(
            PremiumFeatureRequired, match="Custom aliases are a Premium feature"
        ):
            check_custom_alias_permission(user, "myalias")

    def test_premium_user_can_use_alias(self, db):
        from apps.users.models import User
        from apps.shortener.services import check_custom_alias_permission

        user = User.objects.create_user(
            username="premiumuser",
            email="premium@test.com",
            password="Pass123!",
            tier=User.Tier.PREMIUM,
        )

        # Should not raise
        check_custom_alias_permission(user, "myalias")

    def test_none_alias_allowed(self, db):
        from apps.users.models import User
        from apps.shortener.services import check_custom_alias_permission

        user = User.objects.create_user(
            username="freeuser",
            email="free@test.com",
            password="Pass123!",
        )

        # Should not raise for None
        check_custom_alias_permission(user, None)


@pytest.mark.django_db
class TestGetUrlByCode:
    """Tests for URL lookup by code/alias."""

    def test_finds_by_short_code(self, url):
        found = get_url_by_code(url.short_code)
        assert found.pk == url.pk

    def test_finds_by_custom_alias(self, user):
        url = URL.objects.create(
            owner=user,
            original_url="https://example.com",
            short_code="abc123",
            custom_alias="myalias",
        )

        found = get_url_by_code("myalias")
        assert found.pk == url.pk

    def test_finds_inactive_urls(self, user):
        url = URL.objects.create(
            owner=user,
            original_url="https://example.com",
            short_code="abc123",
            is_active=False,
        )

        found = get_url_by_code("abc123")
        assert found.pk == url.pk

    def test_returns_none_for_not_found(self):
        found = get_url_by_code("notfound")
        assert found is None


@pytest.mark.django_db
class TestUpdateUrl:
    """Tests for URL update operations."""

    def test_updates_title(self, user):
        from apps.shortener.services import update_url

        url = URL.objects.create(
            owner=user,
            original_url="https://example.com",
            short_code="abc123",
            title="Old Title",
        )

        updated = update_url(url, {"title": "New Title"}, user)
        assert updated.title == "New Title"
        assert URL.objects.get(pk=url.pk).title == "New Title"

    def test_update_with_tags(self, user):
        from apps.shortener.services import update_url

        url = URL.objects.create(
            owner=user,
            original_url="https://example.com",
            short_code="abc123",
        )

        updated = update_url(url, {"title": "New", "tags": ["python", "django"]}, user)
        assert {t.name for t in updated.tags.all()} == {"python", "django"}


@pytest.mark.django_db
class TestDeactivateUrl:
    """Tests for soft delete operation."""

    def test_deactivates_url(self, url):
        from apps.shortener.services import deactivate_url

        assert url.is_active is True

        deactivated = deactivate_url(url)

        assert deactivated.is_active is False
        assert URL.objects.get(pk=url.pk).is_active is False


@pytest.mark.django_db
class TestGetOrCreateTags:
    """Tests for tag creation and reuse."""

    def test_creates_new_tags(self):
        from apps.shortener.services import get_or_create_tags
        from apps.shortener.models import Tag

        tags = get_or_create_tags(["unique_python_tag", "unique_django_tag"])

        assert len(tags) == 2
        assert {t.name for t in tags} == {"unique_python_tag", "unique_django_tag"}
        # Verify they exist in DB
        assert Tag.objects.filter(name="unique_python_tag").exists()
        assert Tag.objects.filter(name="unique_django_tag").exists()

    def test_reuses_existing_tags(self):
        from apps.shortener.services import get_or_create_tags
        from apps.shortener.models import Tag

        # Pre-create one tag
        Tag.objects.create(name="unique_reuse_tag")

        # Get or create both (one new, one existing)
        tags = get_or_create_tags(["unique_reuse_tag", "unique_new_tag"])

        assert len(tags) == 2
        assert {t.name for t in tags} == {"unique_reuse_tag", "unique_new_tag"}

    def test_strips_whitespace(self):
        from apps.shortener.services import get_or_create_tags

        tags = get_or_create_tags(["  unique_python_ws  ", "unique_django_ws"])

        assert tags[0].name == "unique_python_ws"
        assert tags[1].name == "unique_django_ws"
