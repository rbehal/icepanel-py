from unittest.mock import Mock

import pytest

from icepanel.client import HttpResponse, IcePanelClient
from icepanel.errors import IcePanelError


def _response(status_code: int, payload: str, headers: dict | None = None) -> HttpResponse:
    return HttpResponse(
        status_code=status_code,
        headers=headers or {},
        text=payload,
        url="https://example.com",
    )


def test_resource_request_builds_url_and_returns_json(monkeypatch: pytest.MonkeyPatch) -> None:
    client = IcePanelClient(api_key="test-key", base_url="https://example.com", api_version="v1")
    response = _response(200, "{\"items\": [\"diagram\"]}", {"Content-Type": "application/json"})
    request_mock = Mock(return_value=response)
    monkeypatch.setattr(client, "_send", request_mock)

    data = client.diagrams.list()

    assert data == {"items": ["diagram"]}
    request_mock.assert_called_once()
    assert request_mock.call_args.kwargs["url"] == "https://example.com/v1/diagrams"
    assert request_mock.call_args.kwargs["headers"]["Authorization"] == "Bearer test-key"


def test_request_raw_returns_headers(monkeypatch: pytest.MonkeyPatch) -> None:
    client = IcePanelClient(base_url="https://example.com", api_version="v1")
    response = _response(200, "{\"ok\": true}", {"Content-Type": "application/json", "X-My-Header": "value"})
    request_mock = Mock(return_value=response)
    monkeypatch.setattr(client, "_send", request_mock)

    data, raw_response = client.request_raw("GET", "model/objects")

    assert data == {"ok": True}
    assert raw_response.headers.get("X-My-Header") == "value"


def test_request_raises_on_error_response(monkeypatch: pytest.MonkeyPatch) -> None:
    client = IcePanelClient(base_url="https://example.com", api_version="v1")
    response = _response(404, "{\"error\": \"not found\"}", {"Content-Type": "application/json"})
    request_mock = Mock(return_value=response)
    monkeypatch.setattr(client, "_send", request_mock)

    with pytest.raises(IcePanelError) as exc_info:
        client.tags.list()

    assert exc_info.value.status_code == 404
    assert exc_info.value.body == {"error": "not found"}


def test_request_retries_on_retryable_status(monkeypatch: pytest.MonkeyPatch) -> None:
    client = IcePanelClient(base_url="https://example.com", api_version="v1", max_retries=1)
    response_error = _response(500, "{\"error\": \"server\"}", {"Content-Type": "application/json"})
    response_ok = _response(200, "{\"items\": []}", {"Content-Type": "application/json"})
    request_mock = Mock(side_effect=[response_error, response_ok])
    monkeypatch.setattr(client, "_send", request_mock)

    data = client.comments.list()

    assert data == {"items": []}
    assert request_mock.call_count == 2
