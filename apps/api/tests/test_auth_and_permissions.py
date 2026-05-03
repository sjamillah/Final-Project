import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.shortener.models import User, URL


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def admin_user(db):
    return User.objects.create_user(
        username="admin",
        email="admin@example.com",
        password="SecureAdminPass123",
        is_staff=True,
        tier=User.Tier.ADMIN,
    )


@pytest.fixture
def premium_user(db):
    user = User.objects.create_user(
        username="premium",
        email="premium@example.com",
        password="SecurePremiumPass123",
        is_premium=True,
        tier=User.Tier.PREMIUM,
    )
    return user


@pytest.fixture
def free_user(db):
    return User.objects.create_user(
        username="freeuser",
        email="free@example.com",
        password="SecureFreePass123",
        is_premium=False,
        tier=User.Tier.FREE,
    )


@pytest.fixture
def free_user_with_10_urls(db, free_user):
    """Create a free user with 10 active URLs (at the limit)."""
    for i in range(10):
        URL.objects.create(
            original_url=f"https://example{i}.com",
            short_code=f"abc{i:03d}",
            owner=free_user,
            is_active=True,
        )
    return free_user


@pytest.fixture
def auth_client_free(client, free_user):
    """APIClient authenticated as a free user."""
    refresh = RefreshToken.for_user(free_user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return client, free_user


@pytest.fixture
def auth_client_premium(client, premium_user):
    """APIClient authenticated as a premium user."""
    refresh = RefreshToken.for_user(premium_user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return client, premium_user


@pytest.mark.django_db
class TestRegister:
    """Registration endpoint tests."""

    def test_register_with_valid_data(self, client):
        response = client.post(
            "/api/v1/auth/register/",
            {
                "username": "newuser",
                "email": "newuser@example.com",
                "password": "SecurePassword123",
                "password_confirm": "SecurePassword123",
            },
        )
        assert response.status_code == 201
        assert "tokens" in response.data
        assert "user" in response.data
        assert response.data["user"]["email"] == "newuser@example.com"
        assert User.objects.filter(email="newuser@example.com").exists()

    def test_register_with_duplicate_email(self, client, free_user):
        response = client.post(
            "/api/v1/auth/register/",
            {
                "username": "anotheruser",
                "email": free_user.email,
                "password": "SecurePassword123",
                "password_confirm": "SecurePassword123",
            },
        )
        assert response.status_code == 400
        assert "email" in response.data

    def test_register_with_password_mismatch(self, client):
        response = client.post(
            "/api/v1/auth/register/",
            {
                "username": "newuser",
                "email": "newuser@example.com",
                "password": "SecurePassword123",
                "password_confirm": "DifferentPassword456",
            },
        )
        assert response.status_code == 400
        assert "password" in response.data

    def test_register_with_weak_password(self, client):
        """Password too short should fail."""
        response = client.post(
            "/api/v1/auth/register/",
            {
                "username": "newuser",
                "email": "newuser@example.com",
                "password": "short",
                "password_confirm": "short",
            },
        )
        assert response.status_code == 400

    def test_register_with_missing_fields(self, client):
        response = client.post("/api/v1/auth/register/", {})
        assert response.status_code == 400
        assert "username" in response.data or "email" in response.data


@pytest.mark.django_db
class TestLogin:
    """Login endpoint tests."""

    def test_login_with_correct_credentials(self, client, free_user):
        response = client.post(
            "/api/v1/auth/login/",
            {
                "email": free_user.email,
                "password": "SecureFreePass123",
            },
        )
        assert response.status_code == 200
        assert "tokens" in response.data
        assert "access" in response.data["tokens"]
        assert "refresh" in response.data["tokens"]
        assert response.data["user"]["email"] == free_user.email

    def test_login_with_wrong_password(self, client, free_user):
        response = client.post(
            "/api/v1/auth/login/",
            {
                "email": free_user.email,
                "password": "WrongPassword",
            },
        )
        assert response.status_code == 400

    def test_login_with_nonexistent_email(self, client):
        response = client.post(
            "/api/v1/auth/login/",
            {
                "email": "nonexistent@example.com",
                "password": "SomePassword123",
            },
        )
        assert response.status_code == 400

    def test_login_with_inactive_account(self, client, db):
        """Inactive user should not be able to login."""
        user = User.objects.create_user(
            username="inactive",
            email="inactive@example.com",
            password="SecurePass123",
            is_active=False,
        )
        response = client.post(
            "/api/v1/auth/login/",
            {
                "email": user.email,
                "password": "SecurePass123",
            },
        )
        assert response.status_code == 400


@pytest.mark.django_db
class TestLogout:
    """Logout endpoint tests."""

    def test_logout_with_valid_token(self, client, free_user):
        refresh = RefreshToken.for_user(free_user)
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
        response = client.post(
            "/api/v1/auth/logout/",
            {"refresh": str(refresh)},
        )
        assert response.status_code == 204

    def test_logout_without_authentication(self, client):
        response = client.post("/api/v1/auth/logout/", {})
        assert response.status_code == 401


@pytest.mark.django_db
class TestURLEndpointProtection:
    """Test that URL endpoints require authentication."""

    def test_unauthenticated_cannot_get_urls(self, client):
        response = client.get("/api/v1/urls/")
        assert response.status_code == 401

    def test_unauthenticated_cannot_post_urls(self, client):
        response = client.post(
            "/api/v1/urls/",
            {"original_url": "https://example.com"},
        )
        assert response.status_code == 401

    def test_authenticated_can_get_urls(self, auth_client_free):
        client, user = auth_client_free
        response = client.get("/api/v1/urls/")
        assert response.status_code == 200
        assert isinstance(response.data, list)

    def test_authenticated_can_post_urls(self, auth_client_free):
        client, user = auth_client_free
        response = client.post(
            "/api/v1/urls/",
            {"original_url": "https://example.com"},
        )
        assert response.status_code == 201
        assert response.data["original_url"] == "https://example.com"


@pytest.mark.django_db
class TestFreeTierLimits:
    """Test free tier URL limit enforcement."""

    def test_free_user_with_10_urls_cannot_create(
        self, auth_client_free, free_user_with_10_urls
    ):
        client, user = auth_client_free
        response = client.post(
            "/api/v1/urls/",
            {"original_url": "https://eleventh.com"},
        )
        assert response.status_code == 403
        assert "limit" in response.data["detail"].lower()

    def test_premium_user_can_exceed_10_urls(self, auth_client_premium, db):
        client, user = auth_client_premium
        # Create 11 URLs to test no limit
        for i in range(11):
            response = client.post(
                "/api/v1/urls/",
                {"original_url": f"https://example{i}.com"},
            )
            assert response.status_code == 201
        assert URL.objects.filter(owner=user, is_active=True).count() == 11

    def test_free_user_cannot_use_custom_alias(self, auth_client_free):
        client, user = auth_client_free
        response = client.post(
            "/api/v1/urls/",
            {
                "original_url": "https://example.com",
                "custom_alias": "myalias",
            },
        )
        assert response.status_code == 403
        assert "premium" in response.data["detail"].lower()

    def test_premium_user_can_use_custom_alias(self, auth_client_premium):
        client, user = auth_client_premium
        response = client.post(
            "/api/v1/urls/",
            {
                "original_url": "https://example.com",
                "custom_alias": "myalias",
            },
        )
        assert response.status_code == 201
        assert response.data["custom_alias"] == "myalias"


@pytest.mark.django_db
class TestOwnershipPermissions:
    """Test URL ownership and permission enforcement."""

    def test_owner_can_patch_their_url(self, auth_client_free, free_user):
        client, user = auth_client_free
        url = URL.objects.create(
            original_url="https://example.com",
            short_code="abc123",
            owner=user,
        )
        response = client.patch(
            f"/api/v1/urls/{url.short_code}/",
            {"title": "Updated Title"},
        )
        assert response.status_code == 200
        assert response.data["title"] == "Updated Title"

    def test_non_owner_cannot_patch_url(
        self, auth_client_free, free_user, premium_user
    ):
        client, user = auth_client_free
        url = URL.objects.create(
            original_url="https://example.com",
            short_code="abc123",
            owner=premium_user,
        )
        response = client.patch(
            f"/api/v1/urls/{url.short_code}/",
            {"title": "Hacked Title"},
        )
        assert response.status_code == 403

    def test_owner_can_delete_their_url(self, auth_client_free, free_user):
        client, user = auth_client_free
        url = URL.objects.create(
            original_url="https://example.com",
            short_code="abc123",
            owner=user,
        )
        response = client.delete(f"/api/v1/urls/{url.short_code}/")
        assert response.status_code == 204
        url.refresh_from_db()
        assert url.is_active is False

    def test_non_owner_cannot_delete_url(
        self, auth_client_free, free_user, premium_user
    ):
        client, user = auth_client_free
        url = URL.objects.create(
            original_url="https://example.com",
            short_code="abc123",
            owner=premium_user,
        )
        response = client.delete(f"/api/v1/urls/{url.short_code}/")
        assert response.status_code == 403

    def test_owner_can_get_their_url(self, auth_client_free, free_user):
        client, user = auth_client_free
        url = URL.objects.create(
            original_url="https://example.com",
            short_code="abc123",
            owner=user,
        )
        response = client.get(f"/api/v1/urls/{url.short_code}/")
        assert response.status_code == 200

    def test_non_owner_cannot_get_others_url(
        self, auth_client_free, free_user, premium_user
    ):
        client, user = auth_client_free
        url = URL.objects.create(
            original_url="https://example.com",
            short_code="abc123",
            owner=premium_user,
        )
        response = client.get(f"/api/v1/urls/{url.short_code}/")
        assert response.status_code == 403


@pytest.mark.django_db
class TestAnalyticsPermissions:
    """Test analytics endpoint access control."""

    def test_free_user_cannot_access_analytics(self, auth_client_free, free_user):
        client, user = auth_client_free
        url = URL.objects.create(
            original_url="https://example.com",
            short_code="abc123",
            owner=user,
        )
        response = client.get(f"/api/v1/urls/{url.short_code}/analytics/")
        assert response.status_code == 403

    def test_premium_user_can_access_own_analytics(
        self, auth_client_premium, premium_user
    ):
        client, user = auth_client_premium
        url = URL.objects.create(
            original_url="https://example.com",
            short_code="abc123",
            owner=user,
        )
        response = client.get(f"/api/v1/urls/{url.short_code}/analytics/")
        assert response.status_code == 200
        assert "total_clicks" in response.data
        assert "clicks_by_country" in response.data

    def test_premium_user_cannot_access_others_analytics(
        self, auth_client_premium, premium_user, free_user
    ):
        client, user = auth_client_premium
        url = URL.objects.create(
            original_url="https://example.com",
            short_code="abc123",
            owner=free_user,
        )
        response = client.get(f"/api/v1/urls/{url.short_code}/analytics/")
        assert response.status_code == 403

    def test_admin_can_access_any_analytics(self, client, admin_user, premium_user):
        """Admin should be able to view analytics for any URL."""
        refresh = RefreshToken.for_user(admin_user)
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
        url = URL.objects.create(
            original_url="https://example.com",
            short_code="abc123",
            owner=premium_user,
        )
        response = client.get(f"/api/v1/urls/{url.short_code}/analytics/")
        assert response.status_code == 200


@pytest.mark.django_db
class TestRedirectPublicAccess:
    """Test that redirect endpoint is public and does not require auth."""

    def test_unauthenticated_can_redirect(self, client, free_user):
        url = URL.objects.create(
            original_url="https://example.com",
            short_code="abc123",
            owner=free_user,
        )
        response = client.get(f"/{url.short_code}/", follow=False)
        assert response.status_code == 302
        assert response["Location"] == "https://example.com"

    def test_redirect_by_custom_alias(self, client, premium_user):
        url = URL.objects.create(
            original_url="https://example.com",
            short_code="abc123",
            custom_alias="myalias",
            owner=premium_user,
        )
        response = client.get(f"/{url.custom_alias}/", follow=False)
        assert response.status_code == 302
        assert response["Location"] == "https://example.com"

    def test_redirect_returns_404_for_nonexistent(self, client):
        response = client.get("/nonexistent/")
        assert response.status_code == 404

    def test_redirect_returns_404_for_inactive(self, client, free_user):
        url = URL.objects.create(
            original_url="https://example.com",
            short_code="abc123",
            owner=free_user,
            is_active=False,
        )
        response = client.get(f"/{url.short_code}/")
        assert response.status_code == 404
