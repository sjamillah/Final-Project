import pytest
from rest_framework_simplejwt.tokens import RefreshToken


@pytest.fixture
def authenticated_client(client, db):
    """Returns a client with JWT authentication headers."""
    from apps.users.models import User

    user = User.objects.create_user(
        username="testuser",
        email="test@example.com",
        password="TestPass123",
    )
    refresh = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return client


@pytest.mark.django_db
class TestURLCreateView:

    def test_creates_short_url(self, authenticated_client):
        response = authenticated_client.post(
            "/api/v1/urls/",
            {"original_url": "https://example.com/create"},
            format="json",
        )
        assert response.status_code == 201
        assert "short_code" in response.data
        assert "original_url" in response.data
        assert "created_at" in response.data

    def test_returns_existing_for_duplicate(self, authenticated_client):
        payload = {"original_url": "https://example.com/dup"}
        r1 = authenticated_client.post("/api/v1/urls/", payload, format="json")
        r2 = authenticated_client.post("/api/v1/urls/", payload, format="json")
        assert r1.status_code == 201
        assert r2.status_code == 201
        assert r1.data["short_code"] == r2.data["short_code"]

    def test_invalid_url_returns_400(self, authenticated_client):
        response = authenticated_client.post(
            "/api/v1/urls/",
            {"original_url": "not-a-url"},
            format="json",
        )
        assert response.status_code == 400
        assert "original_url" in response.data

    def test_missing_url_returns_400(self, authenticated_client):
        response = authenticated_client.post("/api/v1/urls/", {}, format="json")
        assert response.status_code == 400

    def test_short_code_length(self, authenticated_client):
        response = authenticated_client.post(
            "/api/v1/urls/",
            {"original_url": "https://example.com/length"},
            format="json",
        )
        assert response.status_code == 201
        assert len(response.data["short_code"]) == 6

    def test_get_lists_user_urls(self, authenticated_client):
        # POST a URL first
        authenticated_client.post(
            "/api/v1/urls/",
            {"original_url": "https://example.com/list"},
            format="json",
        )
        # GET should list user's URLs
        response = authenticated_client.get("/api/v1/urls/")
        assert response.status_code == 200
        assert "results" in response.data  # paginated response


@pytest.mark.django_db
class TestURLRedirectView:

    def test_redirects_to_original_url(self, client, url):
        response = client.get(f"/{url.short_code}/")
        assert response.status_code == 302
        assert response["Location"] == url.original_url

    def test_invalid_code_returns_404(self, client):
        response = client.get("/xxxxxx/")
        assert response.status_code == 404

    def test_redirect_correct_location(self, client, db):
        from apps.shortener.services import create_short_url

        created = create_short_url("https://redirect-target.com")
        response = client.get(f"/{created.short_code}/")
        assert response["Location"] == "https://redirect-target.com"
