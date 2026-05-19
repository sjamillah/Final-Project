"""Tests for users.selectors and users.services."""

import pytest

from apps.users.models import User
from apps.users.selectors import get_user_by_email, get_user_by_username
from apps.users.services import create_user, update_user_tier


@pytest.mark.django_db
class TestUserSelectors:
    """Tests for user lookup selectors."""

    def test_get_user_by_email_finds_user(self, db):
        """get_user_by_email returns matching user."""
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="Pass123!",
        )

        found = get_user_by_email("test@example.com")

        assert found.pk == user.pk

    def test_get_user_by_email_returns_none_if_not_found(self, db):
        """get_user_by_email returns None for missing email."""
        found = get_user_by_email("notfound@example.com")

        assert found is None

    def test_get_user_by_username_finds_user(self, db):
        """get_user_by_username returns matching user."""
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="Pass123!",
        )

        found = get_user_by_username("testuser")

        assert found.pk == user.pk

    def test_get_user_by_username_returns_none_if_not_found(self, db):
        """get_user_by_username returns None for missing username."""
        found = get_user_by_username("notfound")

        assert found is None


@pytest.mark.django_db
class TestUserServices:
    """Tests for user creation and tier management."""

    def test_create_user_creates_active_user(self, db):
        """create_user creates a new User with correct fields."""
        user = create_user(
            username="newuser",
            email="new@example.com",
            password="Pass123!",
        )

        assert user.pk is not None
        assert user.username == "newuser"
        assert user.email == "new@example.com"
        assert user.is_active is True

    def test_create_user_password_hashed(self, db):
        """create_user stores password as hash, not plaintext."""
        user = create_user(
            username="newuser",
            email="new@example.com",
            password="Pass123!",
        )

        assert user.password != "Pass123!"
        assert user.check_password("Pass123!") is True

    def test_update_user_tier_to_premium(self, db):
        """update_user_tier sets tier and is_premium flag."""
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="Pass123!",
        )
        assert user.is_premium is False

        updated = update_user_tier(user, User.Tier.PREMIUM)

        assert updated.tier == User.Tier.PREMIUM
        assert updated.is_premium is True
        assert User.objects.get(pk=user.pk).is_premium is True

    def test_update_user_tier_to_free(self, db):
        """update_user_tier can reset to free tier."""
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="Pass123!",
            tier=User.Tier.PREMIUM,
        )

        updated = update_user_tier(user, User.Tier.FREE)

        assert updated.tier == User.Tier.FREE
        assert updated.is_premium is False

    def test_update_user_tier_to_admin(self, db):
        """update_user_tier sets admin tier and is_premium flag."""
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="Pass123!",
        )

        updated = update_user_tier(user, User.Tier.ADMIN)

        assert updated.tier == User.Tier.ADMIN
        assert updated.is_premium is False
