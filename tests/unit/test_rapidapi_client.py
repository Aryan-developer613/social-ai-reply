"""Tests for the shared RapidAPIClient — guards the get()/post() consolidation
(both now share one _request() core with retry + circuit-breaker + throttle)."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.infrastructure.platforms import rapidapi_client as rapidapi_module
from app.services.infrastructure.platforms.rapidapi_client import RapidAPIClient, RapidAPIError


@pytest.fixture(autouse=True)
def _reset_module_state():
    rapidapi_module._request_timestamps.clear()
    rapidapi_module._circuit_broken_hosts.clear()
    yield
    rapidapi_module._request_timestamps.clear()
    rapidapi_module._circuit_broken_hosts.clear()


def _mock_response(status_code: int, json_body: dict | None = None):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_body or {"ok": True}
    resp.text = "error body"
    return resp


class TestGetAndPostShareTheSameCore:
    def test_get_returns_json_on_200(self):
        async def _run():
            client = RapidAPIClient("example.p.rapidapi.com", api_key="k")
            with patch("httpx.AsyncClient") as mock_client_cls:
                mock_http = AsyncMock()
                mock_http.request.return_value = _mock_response(200, {"data": [1, 2]})
                mock_client_cls.return_value.__aenter__.return_value = mock_http
                result = await client.get("/search", params={"q": "x"})
            assert result == {"data": [1, 2]}
            assert mock_http.request.call_args.args[0] == "GET"

        asyncio.run(_run())

    def test_post_returns_json_on_200_and_sends_body(self):
        async def _run():
            client = RapidAPIClient("example.p.rapidapi.com", api_key="k")
            with patch("httpx.AsyncClient") as mock_client_cls:
                mock_http = AsyncMock()
                mock_http.request.return_value = _mock_response(200, {"data": "posted"})
                mock_client_cls.return_value.__aenter__.return_value = mock_http
                result = await client.post("/search/search", json_body={"query": "x"})
            assert result == {"data": "posted"}
            assert mock_http.request.call_args.args[0] == "POST"
            assert mock_http.request.call_args.kwargs["json"] == {"query": "x"}

        asyncio.run(_run())

    def test_extra_headers_merged_with_auth_headers(self):
        async def _run():
            client = RapidAPIClient("example.p.rapidapi.com", api_key="k")
            with patch("httpx.AsyncClient") as mock_client_cls:
                mock_http = AsyncMock()
                mock_http.request.return_value = _mock_response(200)
                mock_client_cls.return_value.__aenter__.return_value = mock_http
                await client.get("/search", extra_headers={"Content-Type": "application/json"})
            headers = mock_http.request.call_args.kwargs["headers"]
            assert headers["Content-Type"] == "application/json"
            assert headers["x-rapidapi-key"] == "k"

        asyncio.run(_run())


class TestClientErrorNoRetry:
    def test_404_raises_immediately_without_retry(self):
        async def _run():
            client = RapidAPIClient("example.p.rapidapi.com", api_key="k")
            with patch("httpx.AsyncClient") as mock_client_cls:
                mock_http = AsyncMock()
                mock_http.request.return_value = _mock_response(404)
                mock_client_cls.return_value.__aenter__.return_value = mock_http
                with pytest.raises(RapidAPIError):
                    await client.get("/missing")
            assert mock_http.request.call_count == 1

        asyncio.run(_run())


class TestCircuitBreaker:
    def test_429_exhausts_retries_then_trips_circuit_for_next_call(self):
        async def _run():
            client = RapidAPIClient("example.p.rapidapi.com", api_key="k")
            with (
                patch("httpx.AsyncClient") as mock_client_cls,
                patch("asyncio.sleep", new=AsyncMock()),
            ):
                mock_http = AsyncMock()
                mock_http.request.return_value = _mock_response(429)
                mock_client_cls.return_value.__aenter__.return_value = mock_http

                with pytest.raises(RapidAPIError):
                    await client.get("/search")

                # Circuit now open — next call fails fast without any HTTP request.
                mock_http.request.reset_mock()
                with pytest.raises(RapidAPIError, match="circuit breaker"):
                    await client.get("/search")
                assert mock_http.request.call_count == 0

        asyncio.run(_run())
