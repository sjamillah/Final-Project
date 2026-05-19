from apps.shortener import preview_client


class _FakeResponse:
    def __init__(self, payload: dict):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class _FakeClient:
    def __init__(self, response: _FakeResponse):
        self._response = response

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def post(self, url, json=None):
        return self._response


def test_fetch_preview_returns_metadata(monkeypatch):
    payload = {
        "title": "Example Page",
        "description": "Example description",
        "favicon": "https://example.com/favicon.ico",
    }

    monkeypatch.setattr(preview_client, "is_open", lambda domain: False)
    monkeypatch.setattr(preview_client, "record_success", lambda domain: None)
    monkeypatch.setattr(preview_client, "record_failure", lambda domain: None)
    monkeypatch.setattr(
        preview_client.httpx,
        "Client",
        lambda **kwargs: _FakeClient(_FakeResponse(payload)),
    )

    result = preview_client.fetch_preview("https://example.com/page")

    assert result.title == "Example Page"
    assert result.description == "Example description"
    assert result.favicon == "https://example.com/favicon.ico"


def test_fetch_preview_returns_none_when_circuit_is_open(monkeypatch):
    monkeypatch.setattr(preview_client, "is_open", lambda domain: True)

    result = preview_client.fetch_preview("https://example.com/page")

    assert result is None
