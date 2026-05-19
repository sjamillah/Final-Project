import pytest


@pytest.mark.django_db
def test_openapi_schema_includes_short_code_and_request_body(client):
    response = client.get("/api/schema/", HTTP_ACCEPT="application/json")

    assert response.status_code == 200

    schema = response.json()

    create_path = schema["paths"]["/api/v1/urls/"]["post"]
    redirect_path = schema["paths"]["/{short_code}/"]["get"]

    assert create_path["requestBody"]["content"]["application/json"]["schema"]
    assert redirect_path["parameters"][0]["name"] == "short_code"
