import pytest
from django.utils import timezone

from apps.shortener.models import Click, Tag, URL, User


@pytest.mark.django_db
class TestUserModel:

    def test_create_user(self, user):
        assert user.pk is not None
        assert user.username == "testuser"
        assert user.tier == User.Tier.FREE
        assert user.is_premium is False

    def test_premium_user(self, premium_user):
        assert premium_user.is_premium is True
        assert premium_user.tier == User.Tier.PREMIUM

    def test_tier_choices(self):
        assert User.Tier.FREE == "free"
        assert User.Tier.PREMIUM == "premium"
        assert User.Tier.ADMIN == "admin"

    def test_email_is_unique(self, db):
        from django.db import IntegrityError

        User.objects.create_user(
            username="user-one",
            email="unique@example.com",
            password="pass12345",
        )

        with pytest.raises(IntegrityError):
            User.objects.create_user(
                username="user-two",
                email="unique@example.com",
                password="pass12345",
            )

    def test_str(self, user):
        assert str(user) == "testuser"

    def test_db_table(self):
        assert User._meta.db_table == "users"

    def test_default_tier_is_free(self, db):
        user = User.objects.create_user(username="newuser", password="pass")
        assert user.tier == User.Tier.FREE


@pytest.mark.django_db
class TestTagModel:

    def test_create_tag(self, tag):
        assert tag.pk is not None
        assert tag.name == "Marketing"

    def test_str(self, tag):
        assert str(tag) == "Marketing"

    def test_db_table(self):
        assert Tag._meta.db_table == "tags"

    def test_name_is_unique(self, tag):
        from django.db import IntegrityError

        with pytest.raises(IntegrityError):
            Tag.objects.create(name="Marketing")


@pytest.mark.django_db
class TestURLModel:

    def test_create_url(self, url):
        assert url.pk is not None
        assert url.original_url == "https://example.com"
        assert url.short_code == "abc123"
        assert url.is_active is True
        assert url.click_count == 0
        assert url.expires_at is None

    def test_optional_metadata_fields_default_to_none(self, db, user):
        url = URL.objects.create(
            original_url="https://metadata.example.com",
            short_code="meta01",
            owner=user,
        )
        assert url.custom_alias is None
        assert url.title is None
        assert url.description is None
        assert url.favicon is None

    def test_optional_metadata_fields_can_be_saved(self, db, user):
        url = URL.objects.create(
            original_url="https://metadata.example.com/with-fields",
            short_code="meta02",
            owner=user,
            custom_alias="docs",
            title="Marketing Landing Page",
            description="Primary campaign landing page",
            favicon="https://example.com/favicon.ico",
        )
        assert url.custom_alias == "docs"
        assert url.title == "Marketing Landing Page"
        assert url.description == "Primary campaign landing page"
        assert url.favicon == "https://example.com/favicon.ico"

    def test_str(self, url):
        assert str(url) == "abc123 -> https://example.com"

    def test_db_table(self):
        assert URL._meta.db_table == "urls"

    def test_short_code_is_unique(self, url, db):
        from django.db import IntegrityError

        with pytest.raises(IntegrityError):
            URL.objects.create(
                original_url="https://other.com",
                short_code="abc123",
            )

    def test_owner_nullable(self, url_no_owner):
        assert url_no_owner.owner is None

    def test_owner_cascade_delete(self, url, user):
        url_id = url.pk
        user.delete()
        assert not URL.objects.filter(pk=url_id).exists()

    def test_tags_many_to_many(self, url, tag, tag_social):
        url.tags.add(tag, tag_social)
        assert url.tags.count() == 2

    def test_created_at_auto_set(self, url):
        assert url.created_at is not None
        assert url.created_at <= timezone.now()


@pytest.mark.django_db
class TestClickModel:

    def test_create_click(self, click):
        assert click.pk is not None
        assert click.ip_address == "192.168.1.1"
        assert click.country == "Rwanda"
        assert click.city == "Kigali"

    def test_str(self, click):
        assert "abc123" in str(click)

    def test_db_table(self):
        assert Click._meta.db_table == "clicks"

    def test_cascade_delete_with_url(self, click, url):
        click_id = click.pk
        url.delete()
        assert not Click.objects.filter(pk=click_id).exists()

    def test_optional_fields_nullable(self, db, url):
        click = Click.objects.create(url=url)
        assert click.ip_address is None
        assert click.country is None
        assert click.city is None
        assert click.referrer is None
        assert click.user_agent is None

    def test_clicked_at_auto_set(self, click):
        assert click.clicked_at is not None
        assert click.clicked_at <= timezone.now()
