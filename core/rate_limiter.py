#!/usr/bin/env python3
"""
Rate limiting abstraction for API integrations.

Provides:
- Circuit breaker pattern for sources with strict rate limits
- Per-second rate limiting (token bucket algorithm)
- Exponential backoff for 429 errors
- Integration with config.yaml rate limiting settings

Usage:
    from core.rate_limiter import RateLimiter, RateLimitExceeded

    # Create rate limiter (typically one per application)
    limiter = RateLimiter()

    # Check if source is available
    if limiter.is_available("SAM.gov"):
        try:
            result = await make_request()
        except RateLimitExceeded:
            limiter.record_rate_limit("SAM.gov")

    # With automatic handling
    async with limiter.acquire("SEC EDGAR", requests_per_second=10):
        result = await make_request()
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Optional, Set, Any
from dataclasses import dataclass, field
from contextlib import asynccontextmanager

from config_loader import config

logger = logging.getLogger(__name__)


class RateLimitExceeded(Exception):
    """Raised when rate limit is exceeded."""

    def __init__(
        self,
        source: str,
        message: str = "Rate limit exceeded",
        retry_after: Optional[float] = None
    ):
        super().__init__(message)
        self.source = source
        self.message = message
        self.retry_after = retry_after


@dataclass
class SourceRateState:
    """Tracks rate limiting state for a single source."""
    name: str
    is_blocked: bool = False
    blocked_until: Optional[datetime] = None
    consecutive_429s: int = 0
    last_request_time: float = 0.0
    request_count_this_second: int = 0
    total_requests: int = 0
    total_429s: int = 0

    def reset_block(self) -> None:
        """Reset blocked state."""
        self.is_blocked = False
        self.blocked_until = None
        self.consecutive_429s = 0


@dataclass
class RateLimiterStats:
    """Statistics for rate limiter."""
    total_requests: int = 0
    total_429s: int = 0
    blocked_sources: Set[str] = field(default_factory=set)
    requests_by_source: Dict[str, int] = field(default_factory=dict)


class RateLimiter:
    """
    Centralized rate limiting manager for all API sources.

    Features:
    - Circuit breaker: Block sources after 429 errors
    - Per-second limiting: Token bucket for APIs with per-second limits
    - Exponential backoff: Increasing delays after consecutive failures
    - Config integration: Uses config.yaml for source-specific settings

    Example:
        limiter = RateLimiter()

        # Simple check
        if limiter.is_available("SAM.gov"):
            try:
                result = await api_call()
            except HTTPError as e:
                if e.response.status_code == 429:
                    limiter.record_rate_limit("SAM.gov")

        # With automatic per-second limiting
        async with limiter.acquire("SEC EDGAR", requests_per_second=10):
            result = await api_call()
    """

    def __init__(self) -> None:
        """Initialize rate limiter with empty state."""
        self._sources: Dict[str, SourceRateState] = {}
        self._stats = RateLimiterStats()
        self._lock = asyncio.Lock()

    def _get_source_state(self, source: str) -> SourceRateState:
        """Get or create state for a source."""
        if source not in self._sources:
            self._sources[source] = SourceRateState(name=source)
        return self._sources[source]

    def _get_source_config(self, source: str) -> Dict[str, Any]:
        """Get rate limiting config for source."""
        return config.get_rate_limit_config(source)

    def is_available(self, source: str) -> bool:
        """
        Check if a source is available for requests.

        Returns False if source is blocked due to rate limiting.

        Args:
            source: Source name (e.g., "SAM.gov", "USAJobs")

        Returns:
            True if source can accept requests, False if blocked
        """
        state = self._get_source_state(source)

        # Check if block has expired
        if state.is_blocked:
            if state.blocked_until and datetime.now() >= state.blocked_until:
                logger.info(f"Rate limit cooldown expired for {source}")
                state.reset_block()
                self._stats.blocked_sources.discard(source)
            else:
                return False

        return True

    def record_rate_limit(
        self,
        source: str,
        status_code: int = 429,
        retry_after: Optional[float] = None
    ) -> None:
        """
        Record that a source returned a rate limit error.

        Implements circuit breaker pattern: After receiving 429,
        the source may be blocked for a cooldown period.

        Args:
            source: Source name
            status_code: HTTP status code (usually 429)
            retry_after: Seconds to wait (from Retry-After header)
        """
        state = self._get_source_state(source)
        source_config = self._get_source_config(source)

        state.consecutive_429s += 1
        state.total_429s += 1
        self._stats.total_429s += 1

        logger.warning(
            f"Rate limit hit for {source} (429 #{state.consecutive_429s})"
        )

        # Apply circuit breaker if configured
        if source_config.get("use_circuit_breaker", False):
            cooldown_minutes = source_config.get("cooldown_minutes", 60)

            # Use retry_after if provided, otherwise use config cooldown
            if retry_after:
                cooldown_seconds = retry_after
            else:
                cooldown_seconds = cooldown_minutes * 60

            state.is_blocked = True
            state.blocked_until = datetime.now() + timedelta(seconds=cooldown_seconds)
            self._stats.blocked_sources.add(source)

            logger.warning(
                f"Circuit breaker activated for {source}: "
                f"blocked until {state.blocked_until.isoformat()}"
            )

    def record_success(self, source: str) -> None:
        """
        Record a successful request.

        Resets consecutive failure counter.

        Args:
            source: Source name
        """
        state = self._get_source_state(source)
        state.consecutive_429s = 0
        state.total_requests += 1
        self._stats.total_requests += 1
        self._stats.requests_by_source[source] = (
            self._stats.requests_by_source.get(source, 0) + 1
        )

    def get_backoff_delay(self, source: str, base_delay: float = 1.0) -> float:
        """
        Get exponential backoff delay for a source.

        Delay increases with consecutive 429 errors:
        - 0 failures: 0s (no delay)
        - 1 failure: base_delay (e.g., 1s)
        - 2 failures: base_delay * 2 (e.g., 2s)
        - 3 failures: base_delay * 4 (e.g., 4s)
        - Max: 60 seconds

        Args:
            source: Source name
            base_delay: Base delay in seconds (default: 1.0)

        Returns:
            Delay in seconds
        """
        state = self._get_source_state(source)

        if state.consecutive_429s == 0:
            return 0.0

        delay = base_delay * (2 ** (state.consecutive_429s - 1))
        return min(delay, 60.0)  # Cap at 60 seconds

    async def wait_if_needed(
        self,
        source: str,
        requests_per_second: Optional[float] = None
    ) -> None:
        """
        Wait if necessary to respect rate limits.

        For sources with per-second limits (like SEC EDGAR's 10/sec),
        this enforces spacing between requests.

        Args:
            source: Source name
            requests_per_second: Max requests per second (None = no limit)
        """
        if requests_per_second is None:
            return

        state = self._get_source_state(source)
        current_time = time.time()
        min_interval = 1.0 / requests_per_second

        # Calculate time since last request
        elapsed = current_time - state.last_request_time

        if elapsed < min_interval:
            wait_time = min_interval - elapsed
            logger.debug(f"Rate limiting {source}: waiting {wait_time:.3f}s")
            await asyncio.sleep(wait_time)

        state.last_request_time = time.time()

    @asynccontextmanager
    async def acquire(
        self,
        source: str,
        requests_per_second: Optional[float] = None,
        raise_if_blocked: bool = True
    ):
        """
        Context manager for rate-limited requests.

        Handles:
        - Checking source availability
        - Per-second rate limiting
        - Recording success/failure

        Args:
            source: Source name
            requests_per_second: Max requests per second (None = no limit)
            raise_if_blocked: Whether to raise if source is blocked

        Raises:
            RateLimitExceeded: If source is blocked and raise_if_blocked=True

        Example:
            async with limiter.acquire("SEC EDGAR", requests_per_second=10):
                result = await api_call()
        """
        # Check availability
        if not self.is_available(source):
            if raise_if_blocked:
                state = self._get_source_state(source)
                retry_after = None
                if state.blocked_until:
                    retry_after = (state.blocked_until - datetime.now()).total_seconds()
                raise RateLimitExceeded(
                    source,
                    f"{source} is rate limited (circuit breaker active)",
                    retry_after
                )
            else:
                yield False
                return

        # Apply per-second limiting
        async with self._lock:
            await self.wait_if_needed(source, requests_per_second)

        try:
            yield True
            self.record_success(source)
        except RateLimitExceeded:
            # Re-raise but also record
            self.record_rate_limit(source)
            raise

    def unblock_source(self, source: str) -> None:
        """
        Manually unblock a source.

        Useful for testing or when you know the rate limit has reset.

        Args:
            source: Source name
        """
        state = self._get_source_state(source)
        state.reset_block()
        self._stats.blocked_sources.discard(source)
        logger.info(f"Manually unblocked {source}")

    def get_blocked_sources(self) -> Set[str]:
        """Get set of currently blocked source names."""
        # Refresh blocked status
        for source in list(self._stats.blocked_sources):
            self.is_available(source)  # This checks and clears expired blocks
        return self._stats.blocked_sources.copy()

    def get_stats(self) -> RateLimiterStats:
        """Get rate limiter statistics."""
        return self._stats

    def get_source_stats(self, source: str) -> Dict[str, Any]:
        """
        Get statistics for a specific source.

        Args:
            source: Source name

        Returns:
            Dict with source statistics
        """
        state = self._get_source_state(source)
        return {
            "name": source,
            "is_blocked": state.is_blocked,
            "blocked_until": state.blocked_until.isoformat() if state.blocked_until else None,
            "consecutive_429s": state.consecutive_429s,
            "total_requests": state.total_requests,
            "total_429s": state.total_429s,
        }

    def reset(self) -> None:
        """Reset all rate limiter state."""
        self._sources.clear()
        self._stats = RateLimiterStats()
        logger.info("Rate limiter reset")


# Global singleton instance
rate_limiter = RateLimiter()


def with_rate_limit(
    source: str,
    requests_per_second: Optional[float] = None
):
    """
    Decorator for rate-limited async functions.

    Args:
        source: Source name for rate limiting
        requests_per_second: Max requests per second

    Example:
        @with_rate_limit("SEC EDGAR", requests_per_second=10)
        async def fetch_filing(cik: str):
            return await http_get(f"https://sec.gov/cgi-bin/browse-edgar?CIK={cik}")
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            async with rate_limiter.acquire(source, requests_per_second):
                return await func(*args, **kwargs)
        return wrapper
    return decorator
