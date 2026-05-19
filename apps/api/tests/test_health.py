import pytest
from rest_framework.test import APIClient


@pytest.fixture
def client():
    return APIClient()


@pytest.mark.django_db
class TestHealthEndpoint:

    def test_root_health_endpoint_is_available(self, client):
        response = client.get("/health/")
        assert response.status_code in {200, 503}
        assert "status" in response.data

    def test_returns_status_field(self, client):
        response = client.get("/api/v1/health/")
        assert "status" in response.data

    def test_returns_checks_field(self, client):
        response = client.get("/api/v1/health/")
        assert "checks" in response.data
        assert "db" in response.data["checks"]
        assert "redis" in response.data["checks"]

    def test_db_check_passes(self, client):
        response = client.get("/api/v1/health/")
        assert response.data["checks"]["db"] == "ok"

    def test_no_authentication_required(self, client):
        response = client.get("/api/v1/health/")
        assert response.status_code != 401

    def test_status_ok_when_db_reachable(self, client):
        response = client.get("/api/v1/health/")
        # DB is always reachable in test environment; Redis uses LocMemCache.
        assert response.data["status"] == "ok"
        assert response.status_code == 200
