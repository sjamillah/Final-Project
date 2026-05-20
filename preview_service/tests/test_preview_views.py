import pytest
from rest_framework.test import APIClient


@pytest.fixture
def client():
    return APIClient()


@pytest.mark.django_db
@pytest.mark.urls("preview_service.urls")
class TestPreviewEndpoint:

    def test_preview_endpoint_returns_metadata(self, client, monkeypatch):
        from preview_service import views

        monkeypatch.setattr(
            views,
            "_fetch_preview",
            lambda url: {
                "title": "Example Title",
                "description": "Example Description",
                "favicon": "https://example.com/favicon.ico",
            },
        )

        response = client.post(
            "/api/preview/",
            {"url": "https://example.com"},
            format="json",
        )

        assert response.status_code == 200
        assert response.data["title"] == "Example Title"
        assert response.data["description"] == "Example Description"
        assert response.data["favicon"] == "https://example.com/favicon.ico"
