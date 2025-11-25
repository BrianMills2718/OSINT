#!/usr/bin/env python3
"""
Tests for pydantic configuration schema validation.

Tests validate_config(), AppConfig model, and config_loader integration.
"""

import pytest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config_schema import (
    AppConfig,
    validate_config,
    get_default_config,
    LLMConfig,
    ExecutionConfig,
    TimeoutsConfig,
    ResearchConfig,
    DeepResearchConfig,
    HypothesisBranchingConfig,
)
from pydantic import ValidationError


class TestDefaultConfig:
    """Test default configuration generation."""

    def test_get_default_config(self) -> None:
        """Default config should be valid."""
        config = get_default_config()
        assert config is not None
        assert isinstance(config, AppConfig)

    def test_default_llm_model(self) -> None:
        """Default model should be set."""
        config = get_default_config()
        assert config.llm.default_model == "gemini/gemini-2.5-flash"

    def test_default_execution_settings(self) -> None:
        """Default execution settings should be sensible."""
        config = get_default_config()
        assert config.execution.max_concurrent == 10
        assert config.execution.max_refinements == 2
        assert config.execution.default_result_limit == 20

    def test_default_timeouts(self) -> None:
        """Default timeouts should be set."""
        config = get_default_config()
        assert config.timeouts.api_request == 30
        assert config.timeouts.llm_request == 180
        assert config.timeouts.total_search == 300


class TestValidConfig:
    """Test valid configuration parsing."""

    def test_minimal_config(self) -> None:
        """Minimal config with defaults should be valid."""
        config = validate_config({})
        assert config is not None

    def test_full_config(self) -> None:
        """Full config with all sections should be valid."""
        config_dict = {
            "llm": {
                "default_model": "gpt-4o",
                "temporal_context": {"enabled": True, "format": "structured"},
            },
            "execution": {
                "max_concurrent": 5,
                "max_refinements": 3,
            },
            "timeouts": {
                "api_request": 60,
                "llm_request": 240,
            },
            "cost_management": {
                "max_cost_per_query": 1.0,
                "track_costs": True,
            },
            "research": {
                "deep_research": {
                    "max_tasks": 20,
                    "max_time_minutes": 60,
                },
                "hypothesis_branching": {
                    "mode": "execution",
                    "max_hypotheses_per_task": 5,
                    "max_hypotheses_to_execute": 3,
                },
            },
        }
        config = validate_config(config_dict)
        assert config.llm.default_model == "gpt-4o"
        assert config.execution.max_concurrent == 5
        assert config.timeouts.api_request == 60
        assert config.research.deep_research.max_tasks == 20


class TestInvalidConfig:
    """Test invalid configuration rejection."""

    def test_negative_max_concurrent(self) -> None:
        """Negative max_concurrent should be rejected."""
        config_dict = {"execution": {"max_concurrent": -1}}
        with pytest.raises(ValidationError) as exc_info:
            validate_config(config_dict)
        assert "max_concurrent" in str(exc_info.value)

    def test_zero_max_concurrent(self) -> None:
        """Zero max_concurrent should be rejected."""
        config_dict = {"execution": {"max_concurrent": 0}}
        with pytest.raises(ValidationError) as exc_info:
            validate_config(config_dict)
        assert "max_concurrent" in str(exc_info.value)

    def test_negative_timeout(self) -> None:
        """Negative timeout should be rejected."""
        config_dict = {"timeouts": {"api_request": -5}}
        with pytest.raises(ValidationError) as exc_info:
            validate_config(config_dict)
        assert "api_request" in str(exc_info.value)

    def test_invalid_temperature(self) -> None:
        """Temperature > 2.0 should be rejected."""
        config_dict = {
            "llm": {
                "query_generation": {"temperature": 3.0}
            }
        }
        with pytest.raises(ValidationError) as exc_info:
            validate_config(config_dict)
        assert "temperature" in str(exc_info.value)

    def test_invalid_hypothesis_mode(self) -> None:
        """Invalid hypothesis mode should be rejected."""
        config_dict = {
            "research": {
                "hypothesis_branching": {"mode": "invalid_mode"}
            }
        }
        with pytest.raises(ValidationError) as exc_info:
            validate_config(config_dict)
        assert "mode" in str(exc_info.value)

    def test_invalid_log_level(self) -> None:
        """Invalid log level should be rejected."""
        config_dict = {"logging": {"level": "TRACE"}}
        with pytest.raises(ValidationError) as exc_info:
            validate_config(config_dict)
        assert "level" in str(exc_info.value)

    def test_negative_cost(self) -> None:
        """Negative max cost should be rejected."""
        config_dict = {"cost_management": {"max_cost_per_query": -1.0}}
        with pytest.raises(ValidationError) as exc_info:
            validate_config(config_dict)
        assert "max_cost_per_query" in str(exc_info.value)


class TestCrossFieldValidation:
    """Test cross-field validation constraints."""

    def test_task_timeout_vs_llm_timeout(self) -> None:
        """Task timeout must be >= LLM timeout."""
        config_dict = {
            "timeouts": {"llm_request": 300},  # 5 minutes
            "research": {
                "deep_research": {"task_timeout_seconds": 60}  # 1 minute - too short
            }
        }
        with pytest.raises(ValidationError) as exc_info:
            validate_config(config_dict)
        assert "task_timeout_seconds" in str(exc_info.value)

    def test_hypothesis_execute_vs_generate_limit(self) -> None:
        """Max hypotheses to execute cannot exceed max to generate."""
        config_dict = {
            "research": {
                "hypothesis_branching": {
                    "max_hypotheses_per_task": 3,
                    "max_hypotheses_to_execute": 5,  # Too high
                }
            }
        }
        with pytest.raises(ValidationError) as exc_info:
            validate_config(config_dict)
        assert "max_hypotheses_to_execute" in str(exc_info.value)


class TestIntegrationLimits:
    """Test integration limits validation."""

    def test_valid_integration_limits(self) -> None:
        """Valid integration limits should be accepted."""
        config_dict = {
            "integration_limits": {
                "sam": 10,
                "usajobs": 100,
                "twitter": 20,
            }
        }
        config = validate_config(config_dict)
        assert config.integration_limits["sam"] == 10
        assert config.integration_limits["usajobs"] == 100

    def test_zero_integration_limit(self) -> None:
        """Zero integration limit should be rejected."""
        config_dict = {"integration_limits": {"sam": 0}}
        with pytest.raises(ValidationError) as exc_info:
            validate_config(config_dict)
        assert "sam" in str(exc_info.value)

    def test_excessive_integration_limit(self) -> None:
        """Excessive integration limit should be rejected."""
        config_dict = {"integration_limits": {"sam": 5000}}
        with pytest.raises(ValidationError) as exc_info:
            validate_config(config_dict)
        assert "sam" in str(exc_info.value)


class TestConfigLoaderIntegration:
    """Test config_loader.py integration with pydantic schema."""

    def test_config_singleton_loads(self) -> None:
        """Config singleton should load successfully."""
        from config_loader import config
        assert config is not None
        assert config._config is not None

    def test_validated_property(self) -> None:
        """Validated property should return AppConfig."""
        from config_loader import config
        validated = config.validated
        assert isinstance(validated, AppConfig)

    def test_validated_type_safety(self) -> None:
        """Validated config should provide type-safe access."""
        from config_loader import config
        # These should all work with IDE autocomplete
        assert isinstance(config.validated.llm.default_model, str)
        assert isinstance(config.validated.execution.max_concurrent, int)
        assert isinstance(config.validated.timeouts.llm_request, int)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
