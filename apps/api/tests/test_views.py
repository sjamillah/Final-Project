import pytest
from unittest.mock import patch
from rest_framework.test import APIClient

from apps.shortener.models import Click


@pytest.fixture
def client():
    return APIClient()


@pytest.mark.django_db
class TestURLCreateView:

    def test_creates_short_url(self, client):
        response = client.post(
            "/api/urls/",
            {"original_url": "https://example.com/create"},
            format="json",
        )
        assert response.status_code == 201
        assert "short_code" in response.data
        assert "original_url" in response.data
        assert "created_at" in response.data

    def test_returns_existing_for_duplicate(self, client):
        payload = {"original_url": "https://example.com/dup"}
        r1 = client.post("/api/urls/", payload, format="json")
        r2 = client.post("/api/urls/", payload, format="json")
        assert r1.status_code == 201
        assert r2.status_code == 201
        assert r1.data["short_code"] == r2.data["short_code"]

    def test_invalid_url_returns_400(self, client):
        response = client.post(
            "/api/urls/",
            {"original_url": "not-a-url"},
            format="json",
        )
        assert response.status_code == 400
        assert "original_url" in response.data

    def test_missing_url_returns_400(self, client):
        response = client.post("/api/urls/", {}, format="json")
        assert response.status_code == 400

    def test_short_code_length(self, client):
        response = client.post(
            "/api/urls/",
            {"original_url": "https://example.com/length"},
            format="json",
        )
        assert response.status_code == 201
        assert len(response.data["short_code"]) == 6

    def test_only_post_allowed(self, client):
        response = client.get("/api/urls/")
        assert response.status_code == 405


@pytest.mark.django_db
class TestURLRedirectView:

    def test_redirects_to_original_url(self, client, url):
        response = client.get(f"/{url.short_code}/")
        assert response.status_code == 302
        assert response["Location"] == url.original_url

    def test_invalid_code_returns_404(self, client):
        response = client.get("/xxxxxx/")
        assert response.status_code == 404

    def test_inactive_code_returns_404(self, client, url_inactive):
        response = client.get(f"/{url_inactive.short_code}/")
        assert response.status_code == 404

    def test_expired_code_returns_410(self, client, url_expired):
        response = client.get(f"/{url_expired.short_code}/")
        assert response.status_code == 410

    def test_redirect_correct_location(self, client, db):
        from apps.shortener.services import create_short_url

        created = create_short_url("https://redirect-target.com")
        response = client.get(f"/{created.short_code}/")
        assert response["Location"] == "https://redirect-target.com"

    def test_redirect_creates_click_record(self, client, url):
        assert Click.objects.filter(url=url).count() == 0
        response = client.get(
            f"/{url.short_code}/",
            HTTP_USER_AGENT="pytest-agent",
            HTTP_REFERER="https://source.example.com",
            REMOTE_ADDR="10.10.10.10",
        )
        assert response.status_code == 302
        click = Click.objects.get(url=url)
        assert click.user_agent == "pytest-agent"
        assert click.referrer == "https://source.example.com"
        assert click.ip_address == "10.10.10.10"

    def test_redirect_increments_click_count(self, client, url):
        assert url.click_count == 0
        client.get(f"/{url.short_code}/")
        url.refresh_from_db()
        assert url.click_count == 1

    def test_redirect_still_works_when_click_tracking_fails(self, client, url):
        with patch("apps.api.v1.views.create_click_for_url", side_effect=Exception):
            response = client.get(f"/{url.short_code}/")
        assert response.status_code == 302
        assert response["Location"] == url.original_url
