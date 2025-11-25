#!/usr/bin/env python3
"""
Shared HTTP client utilities for integrations.

Provides async-compatible HTTP request functions with:
- Automatic async wrapping of synchronous requests
- Configurable timeouts and retries
- Standard error handling and logging
- User-Agent management
- Response validation

Usage:
    from core.http_client import http_get, http_post, HttpClientError

    # Simple GET request
    data = await http_get("https://api.example.com/data", params={"q": "test"})

    # With custom headers and timeout
    data = await http_get(
        "https://api.example.com/data",
        headers={"Authorization": "Bearer token"},
        timeout=30
    )

    # With retries
    data = await http_get(
        "https://api.example.com/data",
        max_retries=3,
        retry_delay=1.0
    )
"""

import asyncio
import logging
from typing import Dict, Optional, Any, Union
from dataclasses import dataclass
from functools import partial

import requests
from requests.exceptions import RequestException, Timeout, HTTPError

logger = logging.getLogger(__name__)

# Default configuration
DEFAULT_TIMEOUT = 30  # seconds
DEFAULT_USER_AGENT = "SIGINT_Platform/1.0"
DEFAULT_MAX_RETRIES = 0
DEFAULT_RETRY_DELAY = 1.0  # seconds


@dataclass
class HttpResponse:
    """Standardized HTTP response wrapper."""
    success: bool
    status_code: int
    data: Optional[Any] = None
    text: Optional[str] = None
    error: Optional[str] = None
    headers: Optional[Dict[str, str]] = None

    def json(self) -> Any:
        """Return parsed JSON data."""
        return self.data

    def raise_for_status(self) -> None:
        """Raise HttpClientError if request failed."""
        if not self.success:
            raise HttpClientError(self.error or f"HTTP {self.status_code}", self.status_code)


class HttpClientError(Exception):
    """Custom exception for HTTP client errors."""

    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code
        self.message = message


def _build_headers(
    headers: Optional[Dict[str, str]] = None,
    user_agent: Optional[str] = None,
    api_key: Optional[str] = None,
    api_key_header: str = "Authorization"
) -> Dict[str, str]:
    """Build request headers with defaults."""
    result = {"User-Agent": user_agent or DEFAULT_USER_AGENT}

    if headers:
        result.update(headers)

    if api_key:
        # Don't override if already set in headers
        if api_key_header not in result:
            result[api_key_header] = api_key

    return result


def _sync_get(
    url: str,
    params: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
    timeout: int = DEFAULT_TIMEOUT,
    parse_json: bool = True
) -> HttpResponse:
    """Synchronous GET request (internal use)."""
    try:
        response = requests.get(url, params=params, headers=headers, timeout=timeout)
        response.raise_for_status()

        data = None
        text = response.text
        if parse_json:
            try:
                data = response.json()
            except ValueError:
                pass  # Not JSON, leave data as None

        return HttpResponse(
            success=True,
            status_code=response.status_code,
            data=data,
            text=text,
            headers=dict(response.headers)
        )

    except Timeout as e:
        logger.warning(f"HTTP GET timeout: {url} ({timeout}s)")
        return HttpResponse(
            success=False,
            status_code=0,
            error=f"Request timed out after {timeout}s"
        )

    except HTTPError as e:
        status_code = e.response.status_code if e.response is not None else 0
        logger.warning(f"HTTP GET error: {url} -> {status_code}")
        return HttpResponse(
            success=False,
            status_code=status_code,
            error=str(e),
            text=e.response.text if e.response is not None else None
        )

    except RequestException as e:
        logger.error(f"HTTP GET failed: {url} -> {e}")
        return HttpResponse(
            success=False,
            status_code=0,
            error=str(e)
        )


def _sync_post(
    url: str,
    data: Optional[Dict[str, Any]] = None,
    json_data: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
    timeout: int = DEFAULT_TIMEOUT,
    parse_json: bool = True
) -> HttpResponse:
    """Synchronous POST request (internal use)."""
    try:
        response = requests.post(
            url,
            data=data,
            json=json_data,
            headers=headers,
            timeout=timeout
        )
        response.raise_for_status()

        resp_data = None
        text = response.text
        if parse_json:
            try:
                resp_data = response.json()
            except ValueError:
                pass

        return HttpResponse(
            success=True,
            status_code=response.status_code,
            data=resp_data,
            text=text,
            headers=dict(response.headers)
        )

    except Timeout as e:
        logger.warning(f"HTTP POST timeout: {url} ({timeout}s)")
        return HttpResponse(
            success=False,
            status_code=0,
            error=f"Request timed out after {timeout}s"
        )

    except HTTPError as e:
        status_code = e.response.status_code if e.response else 0
        logger.warning(f"HTTP POST error: {url} -> {status_code}")
        return HttpResponse(
            success=False,
            status_code=status_code,
            error=str(e),
            text=e.response.text if e.response else None
        )

    except RequestException as e:
        logger.error(f"HTTP POST failed: {url} -> {e}")
        return HttpResponse(
            success=False,
            status_code=0,
            error=str(e)
        )


async def http_get(
    url: str,
    params: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
    timeout: int = DEFAULT_TIMEOUT,
    user_agent: Optional[str] = None,
    api_key: Optional[str] = None,
    api_key_header: str = "Authorization",
    parse_json: bool = True,
    max_retries: int = DEFAULT_MAX_RETRIES,
    retry_delay: float = DEFAULT_RETRY_DELAY,
    retry_on_status: Optional[list] = None
) -> HttpResponse:
    """
    Async-compatible HTTP GET request.

    Wraps synchronous requests in an executor for async compatibility.
    Includes automatic retry logic for transient failures.

    Args:
        url: Request URL
        params: Query parameters
        headers: Additional headers (merged with defaults)
        timeout: Request timeout in seconds
        user_agent: Custom User-Agent header
        api_key: API key to include in headers
        api_key_header: Header name for API key (default: Authorization)
        parse_json: Whether to parse response as JSON
        max_retries: Number of retries on failure (default: 0)
        retry_delay: Seconds between retries (default: 1.0)
        retry_on_status: HTTP status codes to retry on (default: [429, 500, 502, 503, 504])

    Returns:
        HttpResponse with success status, data, and metadata

    Example:
        response = await http_get(
            "https://api.example.com/data",
            params={"q": "test"},
            api_key="my-key",
            max_retries=3
        )
        if response.success:
            print(response.data)
    """
    if retry_on_status is None:
        retry_on_status = [429, 500, 502, 503, 504]

    full_headers = _build_headers(headers, user_agent, api_key, api_key_header)

    loop = asyncio.get_event_loop()
    attempt = 0

    while True:
        response = await loop.run_in_executor(
            None,
            partial(_sync_get, url, params, full_headers, timeout, parse_json)
        )

        # Success or non-retryable error
        if response.success or response.status_code not in retry_on_status:
            return response

        # Check if we should retry
        attempt += 1
        if attempt > max_retries:
            return response

        # Log retry
        logger.info(f"HTTP GET retry {attempt}/{max_retries}: {url} (status {response.status_code})")
        await asyncio.sleep(retry_delay * attempt)  # Exponential backoff


async def http_post(
    url: str,
    data: Optional[Dict[str, Any]] = None,
    json_data: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
    timeout: int = DEFAULT_TIMEOUT,
    user_agent: Optional[str] = None,
    api_key: Optional[str] = None,
    api_key_header: str = "Authorization",
    parse_json: bool = True,
    max_retries: int = DEFAULT_MAX_RETRIES,
    retry_delay: float = DEFAULT_RETRY_DELAY,
    retry_on_status: Optional[list] = None
) -> HttpResponse:
    """
    Async-compatible HTTP POST request.

    Args:
        url: Request URL
        data: Form data to send
        json_data: JSON data to send (sets Content-Type automatically)
        headers: Additional headers
        timeout: Request timeout in seconds
        user_agent: Custom User-Agent header
        api_key: API key to include in headers
        api_key_header: Header name for API key
        parse_json: Whether to parse response as JSON
        max_retries: Number of retries on failure
        retry_delay: Seconds between retries
        retry_on_status: HTTP status codes to retry on

    Returns:
        HttpResponse with success status, data, and metadata
    """
    if retry_on_status is None:
        retry_on_status = [429, 500, 502, 503, 504]

    full_headers = _build_headers(headers, user_agent, api_key, api_key_header)

    loop = asyncio.get_event_loop()
    attempt = 0

    while True:
        response = await loop.run_in_executor(
            None,
            partial(_sync_post, url, data, json_data, full_headers, timeout, parse_json)
        )

        if response.success or response.status_code not in retry_on_status:
            return response

        attempt += 1
        if attempt > max_retries:
            return response

        logger.info(f"HTTP POST retry {attempt}/{max_retries}: {url} (status {response.status_code})")
        await asyncio.sleep(retry_delay * attempt)


async def http_get_json(
    url: str,
    params: Optional[Dict[str, Any]] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Convenience function for GET requests expecting JSON response.

    Raises HttpClientError if request fails or response is not valid JSON.

    Args:
        url: Request URL
        params: Query parameters
        **kwargs: Additional arguments passed to http_get()

    Returns:
        Parsed JSON response

    Raises:
        HttpClientError: If request fails or response is not JSON
    """
    response = await http_get(url, params=params, parse_json=True, **kwargs)

    if not response.success:
        raise HttpClientError(response.error or "Request failed", response.status_code)

    if response.data is None:
        raise HttpClientError("Response is not valid JSON", response.status_code)

    return response.data


async def http_post_json(
    url: str,
    json_data: Dict[str, Any],
    **kwargs
) -> Dict[str, Any]:
    """
    Convenience function for POST requests with JSON body expecting JSON response.

    Args:
        url: Request URL
        json_data: JSON data to send
        **kwargs: Additional arguments passed to http_post()

    Returns:
        Parsed JSON response

    Raises:
        HttpClientError: If request fails or response is not JSON
    """
    response = await http_post(url, json_data=json_data, parse_json=True, **kwargs)

    if not response.success:
        raise HttpClientError(response.error or "Request failed", response.status_code)

    if response.data is None:
        raise HttpClientError("Response is not valid JSON", response.status_code)

    return response.data
