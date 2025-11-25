#!/usr/bin/env python3
"""
Tests for the shared HTTP client utility.

Unit tests use mocking for reliability.
Integration tests (marked with @pytest.mark.integration) use real endpoints.
"""

import pytest
import asyncio
import sys
import os
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.http_client import (
    http_get,
    http_post,
    http_get_json,
    http_post_json,
    HttpResponse,
    HttpClientError,
    _build_headers,
    _sync_get,
    _sync_post,
    DEFAULT_USER_AGENT,
)


class TestBuildHeaders:
    """Test header building utility."""

    def test_default_user_agent(self) -> None:
        """Should include default user agent."""
        headers = _build_headers()
        assert headers["User-Agent"] == DEFAULT_USER_AGENT

    def test_custom_user_agent(self) -> None:
        """Should use custom user agent."""
        headers = _build_headers(user_agent="CustomAgent/1.0")
        assert headers["User-Agent"] == "CustomAgent/1.0"

    def test_merge_headers(self) -> None:
        """Should merge custom headers."""
        headers = _build_headers(headers={"X-Custom": "value"})
        assert headers["X-Custom"] == "value"
        assert "User-Agent" in headers

    def test_api_key(self) -> None:
        """Should add API key to headers."""
        headers = _build_headers(api_key="test-key")
        assert headers["Authorization"] == "test-key"

    def test_custom_api_key_header(self) -> None:
        """Should use custom API key header name."""
        headers = _build_headers(api_key="test-key", api_key_header="X-Api-Key")
        assert headers["X-Api-Key"] == "test-key"

    def test_dont_override_existing_api_key(self) -> None:
        """Should not override existing API key header."""
        headers = _build_headers(
            headers={"Authorization": "existing"},
            api_key="new-key"
        )
        assert headers["Authorization"] == "existing"


class TestHttpResponse:
    """Test HttpResponse dataclass."""

    def test_success_response(self) -> None:
        """Should create successful response."""
        response = HttpResponse(
            success=True,
            status_code=200,
            data={"key": "value"}
        )
        assert response.success
        assert response.status_code == 200
        assert response.json() == {"key": "value"}

    def test_error_response(self) -> None:
        """Should create error response."""
        response = HttpResponse(
            success=False,
            status_code=404,
            error="Not found"
        )
        assert not response.success
        assert response.error == "Not found"

    def test_raise_for_status_success(self) -> None:
        """Should not raise for successful response."""
        response = HttpResponse(success=True, status_code=200)
        response.raise_for_status()  # Should not raise

    def test_raise_for_status_error(self) -> None:
        """Should raise for error response."""
        response = HttpResponse(success=False, status_code=404, error="Not found")
        with pytest.raises(HttpClientError) as exc_info:
            response.raise_for_status()
        assert exc_info.value.status_code == 404


class TestHttpClientError:
    """Test HttpClientError exception."""

    def test_error_message(self) -> None:
        """Should store error message."""
        error = HttpClientError("Test error", 500)
        assert str(error) == "Test error"
        assert error.message == "Test error"
        assert error.status_code == 500

    def test_error_without_status(self) -> None:
        """Should work without status code."""
        error = HttpClientError("Test error")
        assert error.status_code is None


class TestSyncGet:
    """Test _sync_get function with mocking."""

    @patch('core.http_client.requests.get')
    def test_successful_get(self, mock_get: MagicMock) -> None:
        """Should return successful response."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '{"key": "value"}'
        mock_response.json.return_value = {"key": "value"}
        mock_response.headers = {"Content-Type": "application/json"}
        mock_get.return_value = mock_response

        response = _sync_get("https://api.example.com/data")

        assert response.success
        assert response.status_code == 200
        assert response.data == {"key": "value"}

    @patch('core.http_client.requests.get')
    def test_timeout_handling(self, mock_get: MagicMock) -> None:
        """Should handle timeout gracefully."""
        from requests.exceptions import Timeout
        mock_get.side_effect = Timeout("Connection timed out")

        response = _sync_get("https://api.example.com/data", timeout=5)

        assert not response.success
        assert response.status_code == 0
        assert "timed out" in response.error.lower()

    @patch('core.http_client.requests.get')
    def test_http_error_handling(self, mock_get: MagicMock) -> None:
        """Should handle HTTP errors."""
        from requests.exceptions import HTTPError
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.text = "Not Found"
        mock_response.raise_for_status.side_effect = HTTPError(response=mock_response)
        mock_get.return_value = mock_response

        response = _sync_get("https://api.example.com/data")

        assert not response.success
        assert response.status_code == 404


class TestSyncPost:
    """Test _sync_post function with mocking."""

    @patch('core.http_client.requests.post')
    def test_successful_post(self, mock_post: MagicMock) -> None:
        """Should return successful response."""
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.text = '{"id": 123}'
        mock_response.json.return_value = {"id": 123}
        mock_response.headers = {"Content-Type": "application/json"}
        mock_post.return_value = mock_response

        response = _sync_post(
            "https://api.example.com/data",
            json_data={"name": "test"}
        )

        assert response.success
        assert response.status_code == 201
        assert response.data == {"id": 123}


class TestHttpGetAsync:
    """Test http_get async function."""

    @pytest.mark.asyncio
    @patch('core.http_client._sync_get')
    async def test_async_get_success(self, mock_sync_get: MagicMock) -> None:
        """Should wrap sync get in async."""
        mock_sync_get.return_value = HttpResponse(
            success=True,
            status_code=200,
            data={"result": "ok"}
        )

        response = await http_get("https://api.example.com/data")

        assert response.success
        assert response.data == {"result": "ok"}

    @pytest.mark.asyncio
    @patch('core.http_client._sync_get')
    async def test_async_get_with_retry(self, mock_sync_get: MagicMock) -> None:
        """Should retry on retryable status codes."""
        # First call fails with 503, second succeeds
        mock_sync_get.side_effect = [
            HttpResponse(success=False, status_code=503, error="Service Unavailable"),
            HttpResponse(success=True, status_code=200, data={"result": "ok"})
        ]

        response = await http_get(
            "https://api.example.com/data",
            max_retries=1,
            retry_delay=0.1
        )

        assert response.success
        assert mock_sync_get.call_count == 2

    @pytest.mark.asyncio
    @patch('core.http_client._sync_get')
    async def test_async_get_no_retry_on_404(self, mock_sync_get: MagicMock) -> None:
        """Should not retry on 404."""
        mock_sync_get.return_value = HttpResponse(
            success=False,
            status_code=404,
            error="Not Found"
        )

        response = await http_get(
            "https://api.example.com/data",
            max_retries=3
        )

        assert not response.success
        assert mock_sync_get.call_count == 1  # No retries


class TestHttpGetJson:
    """Test http_get_json convenience function."""

    @pytest.mark.asyncio
    @patch('core.http_client._sync_get')
    async def test_json_get_success(self, mock_sync_get: MagicMock) -> None:
        """Should return parsed JSON."""
        mock_sync_get.return_value = HttpResponse(
            success=True,
            status_code=200,
            data={"key": "value"}
        )

        data = await http_get_json("https://api.example.com/data")

        assert data == {"key": "value"}

    @pytest.mark.asyncio
    @patch('core.http_client._sync_get')
    async def test_json_get_error(self, mock_sync_get: MagicMock) -> None:
        """Should raise on error."""
        mock_sync_get.return_value = HttpResponse(
            success=False,
            status_code=500,
            error="Server Error"
        )

        with pytest.raises(HttpClientError) as exc_info:
            await http_get_json("https://api.example.com/data")

        assert exc_info.value.status_code == 500

    @pytest.mark.asyncio
    @patch('core.http_client._sync_get')
    async def test_json_get_non_json_response(self, mock_sync_get: MagicMock) -> None:
        """Should raise if response is not JSON."""
        mock_sync_get.return_value = HttpResponse(
            success=True,
            status_code=200,
            data=None,  # Not JSON
            text="Plain text"
        )

        with pytest.raises(HttpClientError) as exc_info:
            await http_get_json("https://api.example.com/data")

        assert "not valid JSON" in str(exc_info.value)


class TestHttpPostJson:
    """Test http_post_json convenience function."""

    @pytest.mark.asyncio
    @patch('core.http_client._sync_post')
    async def test_json_post_success(self, mock_sync_post: MagicMock) -> None:
        """Should return parsed JSON."""
        mock_sync_post.return_value = HttpResponse(
            success=True,
            status_code=201,
            data={"id": 123}
        )

        data = await http_post_json(
            "https://api.example.com/data",
            json_data={"name": "test"}
        )

        assert data == {"id": 123}


# Optional integration tests (require network)
@pytest.mark.integration
class TestHttpClientIntegration:
    """Integration tests using real HTTP endpoints.

    These tests hit external services and may fail due to network issues.
    They are marked with pytest.mark.integration for selective running.
    """

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_real_get_request(self) -> None:
        """Test with real HTTP endpoint (may fail if httpbin.org is down)."""
        response = await http_get(
            "https://httpbin.org/get",
            params={"test": "value"},
            timeout=30
        )
        # Skip assertion if service is unavailable (503, 502, etc.)
        if response.status_code in (502, 503, 504):
            pytest.skip(f"httpbin.org returned {response.status_code} - service temporarily unavailable")
        assert response.success
        assert response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "not integration"])
