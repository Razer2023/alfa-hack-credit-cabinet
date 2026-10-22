"""HTTP-клиенты сервисов B и C: формат вызовов и обработка ответов."""

import httpx
import pytest

from app.clients.base import ExternalNotFound, ExternalServiceError, JsonHttpClient


def client_with(handler) -> JsonHttpClient:
    client = JsonHttpClient("scoring", "http://scoring:8000", timeout=1)
    client._http = httpx.Client(base_url="http://scoring:8000", transport=httpx.MockTransport(handler))
    return client


def test_internal_calls_ignore_proxy_env(monkeypatch):
    monkeypatch.setenv("HTTP_PROXY", "http://corporate-proxy:3128")
    client = JsonHttpClient("scoring", "http://scoring:8000", timeout=1)
    assert client._http._trust_env is False


def test_json_response():
    client = client_with(lambda request: httpx.Response(200, json={"code": "EXPRESS"}))
    assert client.request("GET", "/api/v1/products/EXPRESS") == {"code": "EXPRESS"}


def test_not_found_and_errors():
    assert_raises = {404: ExternalNotFound, 422: ExternalServiceError, 503: ExternalServiceError}
    for status, error in assert_raises.items():
        client = client_with(lambda request, s=status: httpx.Response(s, json={}))
        with pytest.raises(error):
            client.request("GET", "/x")


def test_connection_error():
    def broken(request):
        raise httpx.ConnectError("refused")

    with pytest.raises(ExternalServiceError):
        client_with(broken).request("GET", "/x")
