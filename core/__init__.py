"""
Core utilities for the SIGINT research platform.

This package provides shared infrastructure used across integrations:
- http_client: Async HTTP client with retry and timeout handling
- rate_limiter: Rate limiting with circuit breaker pattern
- prompt_loader: Jinja2 template rendering for LLM prompts
- database_integration_base: Base classes for data source integrations
"""

from core.http_client import (
    http_get,
    http_post,
    http_get_json,
    http_post_json,
    HttpResponse,
    HttpClientError,
)
from core.rate_limiter import (
    RateLimiter,
    RateLimitExceeded,
    rate_limiter,
    with_rate_limit,
)

__all__ = [
    # HTTP Client
    "http_get",
    "http_post",
    "http_get_json",
    "http_post_json",
    "HttpResponse",
    "HttpClientError",
    # Rate Limiter
    "RateLimiter",
    "RateLimitExceeded",
    "rate_limiter",
    "with_rate_limit",
]
