#!/usr/bin/env python3
"""
Unit tests for RecursiveResearchAgent core logic.

Tests critical methods in isolation without API calls.

Run: pytest tests/unit/test_recursive_agent.py -v
"""

import pytest
from pathlib import Path
import sys
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from research.recursive_agent import (
    RecursiveResearchAgent,
    Evidence,
    GoalContext,
    Constraints,
    GoalStatus,
    ResearchRun
)


@pytest.fixture
def agent():
    """Create agent with test constraints."""
    return RecursiveResearchAgent(
        constraints=Constraints(
            max_depth=2,
            max_time_seconds=60,
            max_goals=10
        )
    )


@pytest.fixture
def context():
    """Create mock goal context."""
    return GoalContext(
        original_objective="Test objective",
        available_sources=[
            {"id": "test_source", "name": "Test Source", "description": "Test"}
        ],
        constraints=Constraints(),
        start_time=datetime.now(),
        research_run=ResearchRun()
    )


class TestUnfixableErrorDetection:
    """Test error pattern detection for query reformulation."""

    def test_timeout_errors_are_unfixable(self, agent):
        """Timeout errors should be detected as unfixable."""
        errors = [
            "ReadTimeoutError: HTTPSConnectionPool read timed out",
            "Connection timeout after 60 seconds",
            "The handshake operation timed out",
            "Request timed out",
        ]

        for error in errors:
            # Get unfixable patterns from config
            raw_config = agent.config.get_raw_config()
            patterns = raw_config.get('research', {}).get('error_handling', {}).get('unfixable_error_patterns', [])

            error_lower = error.lower()
            is_unfixable = any(term.lower() in error_lower for term in patterns)

            assert is_unfixable, f"Should detect timeout as unfixable: {error}"

    def test_rate_limit_errors_are_unfixable(self, agent):
        """Rate limit errors should be detected as unfixable."""
        errors = [
            "HTTP 429: Too Many Requests",
            "Rate limit exceeded",
            "Daily quota exceeded",
            "Throttling request",
        ]

        for error in errors:
            raw_config = agent.config.get_raw_config()
            patterns = raw_config.get('research', {}).get('error_handling', {}).get('unfixable_error_patterns', [])

            error_lower = error.lower()
            is_unfixable = any(term.lower() in error_lower for term in patterns)

            assert is_unfixable, f"Should detect rate limit as unfixable: {error}"

    def test_validation_errors_are_fixable(self, agent):
        """Validation errors (422) should be fixable via reformulation."""
        errors = [
            "HTTP 422: Parameter 'keywords' must be at least 3 characters",
            "Invalid parameter value",
            "Validation failed",
        ]

        for error in errors:
            raw_config = agent.config.get_raw_config()
            patterns = raw_config.get('research', {}).get('error_handling', {}).get('unfixable_error_patterns', [])

            error_lower = error.lower()
            is_unfixable = any(term.lower() in error_lower for term in patterns)

            assert not is_unfixable, f"Should attempt reformulation for: {error}"


class TestConstraintsValidation:
    """Test Constraints dataclass and validation."""

    def test_default_constraints(self):
        """Default constraints should have sensible values."""
        constraints = Constraints()

        assert constraints.max_depth == 15
        assert constraints.max_time_seconds == 1800  # 30 min
        assert constraints.max_cost_dollars == 5.0
        assert constraints.max_goals == 50

    def test_custom_constraints(self):
        """Custom constraints should override defaults."""
        constraints = Constraints(
            max_depth=3,
            max_time_seconds=120,
            max_cost_dollars=1.0,
            max_goals=5
        )

        assert constraints.max_depth == 3
        assert constraints.max_time_seconds == 120
        assert constraints.max_cost_dollars == 1.0
        assert constraints.max_goals == 5


class TestGoalContext:
    """Test GoalContext state management."""

    def test_context_initialization(self, context):
        """Context should initialize with required fields."""
        assert context.original_objective == "Test objective"
        assert len(context.available_sources) == 1
        assert context.depth == 0
        assert context.cost_incurred == 0.0

    def test_cost_tracking(self, context):
        """Should track cost correctly."""
        # Cost is tracked via cost_incurred field
        assert context.cost_incurred == 0.0

        # Can update cost
        context.cost_incurred += 0.01
        assert context.cost_incurred == 0.01

    def test_with_parent(self, context):
        """with_parent() should create new context with incremented depth and goal stack."""
        child_context = context.with_parent("Parent goal")

        assert child_context.depth == 1
        assert "Parent goal" in child_context.goal_stack
        assert len(child_context.goal_stack) == 1
        assert child_context.original_objective == context.original_objective

    def test_with_evidence(self, context):
        """with_evidence() should add evidence to accumulated_evidence."""
        evidence = Evidence(
            source_id="test",
            title="Test",
            url="https://example.com",
            snippet="Test snippet"
        )

        child_context = context.with_evidence([evidence])

        assert len(child_context.accumulated_evidence) == 1
        assert child_context.accumulated_evidence[0].title == "Test"


class TestResearchRun:
    """Test ResearchRun global evidence index."""

    def test_research_run_initialization(self):
        """ResearchRun should initialize with empty index."""
        run = ResearchRun()

        assert len(run.index) == 0
        assert len(run.evidence_store) == 0
        assert run.lock is not None

    def test_max_index_items_configurable(self):
        """Max index items should be configurable."""
        run = ResearchRun(max_index_items_for_selection=100)

        assert run.max_index_items_for_selection == 100


class TestAgentInitialization:
    """Test agent setup and configuration."""

    def test_agent_initializes_with_defaults(self):
        """Agent should initialize with default constraints."""
        agent = RecursiveResearchAgent()

        assert agent.constraints.max_depth == 15
        assert agent.constraints.max_time_seconds == 1800
        assert agent.output_dir.name.startswith("2025")  # Timestamped

    def test_agent_initializes_with_custom_constraints(self):
        """Agent should accept custom constraints."""
        constraints = Constraints(max_depth=5, max_time_seconds=300)
        agent = RecursiveResearchAgent(constraints=constraints)

        assert agent.constraints.max_depth == 5
        assert agent.constraints.max_time_seconds == 300

    def test_agent_has_config_reference(self):
        """Agent should have config reference for error handling."""
        agent = RecursiveResearchAgent()

        assert hasattr(agent, 'config')
        assert agent.config is not None


class TestEvidenceDataClass:
    """Test Evidence dataclass and factory methods."""

    def test_evidence_from_dict(self):
        """Evidence.from_dict() should create Evidence from search result."""
        result_dict = {
            "title": "Test Title",
            "url": "https://example.com",
            "snippet": "Test snippet",
            "date": "2025-01-01",
            "metadata": {"key": "value"}
        }

        evidence = Evidence.from_dict(result_dict, source_id="test_source")

        assert evidence.title == "Test Title"
        assert evidence.url == "https://example.com"
        assert evidence.content == "Test snippet"  # content property
        assert evidence.snippet == "Test snippet"  # snippet field
        assert evidence.source == "test_source"    # source property
        assert evidence.source_id == "test_source" # source_id field
        assert evidence.metadata["key"] == "value"

    def test_evidence_handles_missing_fields(self):
        """Evidence should handle missing optional fields gracefully."""
        result_dict = {
            "title": "Test Title",
            "snippet": "",  # Required field
        }

        evidence = Evidence.from_dict(result_dict, source_id="test")

        assert evidence.title == "Test Title"
        assert evidence.url is None or evidence.url == ""
        assert evidence.content == ""  # From snippet
        assert evidence.date is None

    def test_evidence_direct_construction(self):
        """Evidence can be constructed directly with required fields."""
        evidence = Evidence(
            source_id="test",
            title="Test Title",
            url="https://example.com",
            snippet="Test snippet"
        )

        assert evidence.title == "Test Title"
        assert evidence.source_id == "test"
        assert evidence.content == "Test snippet"


class TestGoalStatusEnum:
    """Test GoalStatus enum values."""

    def test_all_status_values_exist(self):
        """All expected status values should be defined."""
        expected = ["PENDING", "IN_PROGRESS", "COMPLETED", "FAILED", "CONSTRAINED", "CYCLE_DETECTED"]

        actual = [status.name for status in GoalStatus]

        for expected_status in expected:
            assert expected_status in actual, f"Missing status: {expected_status}"


# Note: Integration tests for _filter_results, _decompose_goal, etc. require
# LLM calls and are better suited for integration tests. These unit tests
# focus on data structures, configuration, and pure logic functions.


class TestConfigurationLoading:
    """Test that configuration loads correctly."""

    def test_unfixable_error_patterns_load_from_config(self, agent):
        """Error patterns should load from config."""
        raw_config = agent.config.get_raw_config()
        patterns = raw_config.get('research', {}).get('error_handling', {}).get('unfixable_error_patterns', [])

        # Should have rate limit patterns
        assert any("rate limit" in p.lower() for p in patterns)

        # Should have timeout patterns
        assert any("timeout" in p.lower() for p in patterns)

        # Should have at least 10 patterns
        assert len(patterns) >= 10

    def test_constraints_load_from_config(self, agent):
        """Constraints should be accessible."""
        assert agent.constraints.max_depth > 0
        assert agent.constraints.max_time_seconds > 0
        assert agent.constraints.max_cost_dollars > 0


if __name__ == "__main__":
    # Allow running directly: python tests/unit/test_recursive_agent.py
    pytest.main([__file__, "-v"])
