#!/usr/bin/env python3
"""
Tests for the rate limiting abstraction.
"""

import pytest
import asyncio
import sys
import os
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.rate_limiter import (
    RateLimiter,
    RateLimitExceeded,
    SourceRateState,
    with_rate_limit,
)


class TestSourceRateState:
    """Test SourceRateState dataclass."""

    def test_initial_state(self) -> None:
        """Should initialize with default values."""
        state = SourceRateState(name="TestSource")
        assert state.name == "TestSource"
        assert not state.is_blocked
        assert state.blocked_until is None
        assert state.consecutive_429s == 0

    def test_reset_block(self) -> None:
        """Should reset blocked state."""
        state = SourceRateState(name="TestSource")
        state.is_blocked = True
        state.blocked_until = datetime.now()
        state.consecutive_429s = 3

        state.reset_block()

        assert not state.is_blocked
        assert state.blocked_until is None
        assert state.consecutive_429s == 0


class TestRateLimiter:
    """Test RateLimiter class."""

    def test_init(self) -> None:
        """Should initialize with empty state."""
        limiter = RateLimiter()
        assert limiter.get_blocked_sources() == set()
        assert limiter.get_stats().total_requests == 0

    def test_is_available_new_source(self) -> None:
        """New sources should be available."""
        limiter = RateLimiter()
        assert limiter.is_available("NewSource")

    def test_record_success(self) -> None:
        """Should track successful requests."""
        limiter = RateLimiter()
        limiter.record_success("TestSource")
        limiter.record_success("TestSource")

        stats = limiter.get_source_stats("TestSource")
        assert stats["total_requests"] == 2
        assert stats["consecutive_429s"] == 0

    @patch('core.rate_limiter.config')
    def test_record_rate_limit_no_circuit_breaker(self, mock_config: MagicMock) -> None:
        """Should track 429 without blocking if circuit breaker disabled."""
        mock_config.get_rate_limit_config.return_value = {
            "use_circuit_breaker": False,
            "cooldown_minutes": 60,
            "is_critical": True
        }

        limiter = RateLimiter()
        limiter.record_rate_limit("CriticalSource")

        assert limiter.is_available("CriticalSource")
        stats = limiter.get_source_stats("CriticalSource")
        assert stats["total_429s"] == 1

    @patch('core.rate_limiter.config')
    def test_record_rate_limit_with_circuit_breaker(self, mock_config: MagicMock) -> None:
        """Should block source when circuit breaker is enabled."""
        mock_config.get_rate_limit_config.return_value = {
            "use_circuit_breaker": True,
            "cooldown_minutes": 60,
            "is_critical": False
        }

        limiter = RateLimiter()
        limiter.record_rate_limit("SAM.gov")

        assert not limiter.is_available("SAM.gov")
        assert "SAM.gov" in limiter.get_blocked_sources()

    @patch('core.rate_limiter.config')
    def test_block_expiry(self, mock_config: MagicMock) -> None:
        """Should unblock source after cooldown expires."""
        mock_config.get_rate_limit_config.return_value = {
            "use_circuit_breaker": True,
            "cooldown_minutes": 1,  # 1 minute cooldown
            "is_critical": False
        }

        limiter = RateLimiter()
        limiter.record_rate_limit("TestSource")

        # Manually set blocked_until to the past
        state = limiter._get_source_state("TestSource")
        state.blocked_until = datetime.now() - timedelta(minutes=1)

        assert limiter.is_available("TestSource")
        assert "TestSource" not in limiter.get_blocked_sources()

    def test_unblock_source(self) -> None:
        """Should manually unblock source."""
        limiter = RateLimiter()
        state = limiter._get_source_state("TestSource")
        state.is_blocked = True
        state.blocked_until = datetime.now() + timedelta(hours=1)
        limiter._stats.blocked_sources.add("TestSource")

        limiter.unblock_source("TestSource")

        assert limiter.is_available("TestSource")
        assert "TestSource" not in limiter.get_blocked_sources()

    def test_get_backoff_delay(self) -> None:
        """Should calculate exponential backoff."""
        limiter = RateLimiter()
        state = limiter._get_source_state("TestSource")

        # No failures = no delay
        assert limiter.get_backoff_delay("TestSource") == 0.0

        # 1 failure = base delay
        state.consecutive_429s = 1
        assert limiter.get_backoff_delay("TestSource", base_delay=1.0) == 1.0

        # 2 failures = 2x
        state.consecutive_429s = 2
        assert limiter.get_backoff_delay("TestSource", base_delay=1.0) == 2.0

        # 3 failures = 4x
        state.consecutive_429s = 3
        assert limiter.get_backoff_delay("TestSource", base_delay=1.0) == 4.0

        # Should cap at 60 seconds
        state.consecutive_429s = 10
        assert limiter.get_backoff_delay("TestSource", base_delay=1.0) == 60.0

    def test_reset(self) -> None:
        """Should reset all state."""
        limiter = RateLimiter()
        limiter.record_success("Source1")
        limiter.record_success("Source2")
        limiter._stats.blocked_sources.add("Source1")

        limiter.reset()

        assert limiter.get_stats().total_requests == 0
        assert limiter.get_blocked_sources() == set()


class TestRateLimiterAsync:
    """Test async rate limiter functionality."""

    @pytest.mark.asyncio
    async def test_acquire_success(self) -> None:
        """Should allow request and record success."""
        limiter = RateLimiter()

        async with limiter.acquire("TestSource") as acquired:
            assert acquired

        assert limiter.get_source_stats("TestSource")["total_requests"] == 1

    @pytest.mark.asyncio
    @patch('core.rate_limiter.config')
    async def test_acquire_blocked(self, mock_config: MagicMock) -> None:
        """Should raise when source is blocked."""
        mock_config.get_rate_limit_config.return_value = {
            "use_circuit_breaker": True,
            "cooldown_minutes": 60,
            "is_critical": False
        }

        limiter = RateLimiter()
        limiter.record_rate_limit("BlockedSource")

        with pytest.raises(RateLimitExceeded) as exc_info:
            async with limiter.acquire("BlockedSource"):
                pass

        assert exc_info.value.source == "BlockedSource"

    @pytest.mark.asyncio
    @patch('core.rate_limiter.config')
    async def test_acquire_blocked_no_raise(self, mock_config: MagicMock) -> None:
        """Should return False when blocked if raise_if_blocked=False."""
        mock_config.get_rate_limit_config.return_value = {
            "use_circuit_breaker": True,
            "cooldown_minutes": 60,
            "is_critical": False
        }

        limiter = RateLimiter()
        limiter.record_rate_limit("BlockedSource")

        async with limiter.acquire("BlockedSource", raise_if_blocked=False) as acquired:
            assert not acquired

    @pytest.mark.asyncio
    async def test_wait_if_needed(self) -> None:
        """Should enforce per-second rate limiting."""
        limiter = RateLimiter()

        # First request - no wait
        start = asyncio.get_event_loop().time()
        await limiter.wait_if_needed("TestSource", requests_per_second=10)
        first_elapsed = asyncio.get_event_loop().time() - start

        # Second request - should wait ~0.1s (1/10 per second)
        start = asyncio.get_event_loop().time()
        await limiter.wait_if_needed("TestSource", requests_per_second=10)
        second_elapsed = asyncio.get_event_loop().time() - start

        assert first_elapsed < 0.05  # First should be instant
        assert second_elapsed >= 0.08  # Second should wait ~0.1s (with some tolerance)


class TestWithRateLimitDecorator:
    """Test the @with_rate_limit decorator."""

    @pytest.mark.asyncio
    async def test_decorator_success(self) -> None:
        """Should allow decorated function to execute."""
        call_count = 0

        @with_rate_limit("TestSource")
        async def my_function():
            nonlocal call_count
            call_count += 1
            return "success"

        result = await my_function()

        assert result == "success"
        assert call_count == 1


class TestRateLimitExceeded:
    """Test RateLimitExceeded exception."""

    def test_exception_attributes(self) -> None:
        """Should store source and retry_after."""
        exc = RateLimitExceeded("TestSource", "Rate limit hit", retry_after=60.0)

        assert exc.source == "TestSource"
        assert exc.message == "Rate limit hit"
        assert exc.retry_after == 60.0
        assert str(exc) == "Rate limit hit"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
