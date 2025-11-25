#!/usr/bin/env python3
"""
Pydantic schema models for configuration validation.

Provides type-safe configuration with validation, defaults, and documentation.
Used by config_loader.py to validate config.yaml and config_default.yaml.
"""

from typing import Dict, List, Optional, Any, Literal
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict


# ============================================================================
# LLM Configuration Models
# ============================================================================

class TemporalContextConfig(BaseModel):
    """Configuration for temporal context injection into LLM prompts."""
    enabled: bool = Field(default=True, description="Enable temporal context injection")
    format: Literal["structured", "simple", "minimal"] = Field(
        default="structured",
        description="Format: structured (detailed), simple (one line), minimal (just date)"
    )


class OperationModelConfig(BaseModel):
    """Configuration for a specific LLM operation (query_generation, analysis, etc.)."""
    model: Optional[str] = Field(default=None, description="Model override for this operation")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="Temperature (0-2)")
    max_tokens: int = Field(default=500, gt=0, description="Maximum tokens for response")


class LLMConfig(BaseModel):
    """LLM configuration section."""
    default_model: str = Field(
        default="gemini/gemini-2.5-flash",
        description="Default model for all operations"
    )
    temporal_context: TemporalContextConfig = Field(default_factory=TemporalContextConfig)

    # Operation-specific configurations
    query_generation: Optional[OperationModelConfig] = None
    refinement: Optional[OperationModelConfig] = None
    analysis: Optional[OperationModelConfig] = None
    synthesis: Optional[OperationModelConfig] = None
    code_generation: Optional[OperationModelConfig] = None


# ============================================================================
# Execution Configuration
# ============================================================================

class ExecutionConfig(BaseModel):
    """Execution configuration section."""
    max_concurrent: int = Field(default=10, ge=1, le=50, description="Max parallel API calls")
    max_refinements: int = Field(default=2, ge=0, le=10, description="Max query refinement iterations")
    default_result_limit: int = Field(default=20, ge=1, le=500, description="Default results per database")
    enable_adaptive_analysis: bool = Field(default=True, description="Enable Ditto-style code generation")
    enable_auto_refinement: bool = Field(default=True, description="Enable automatic query refinement")


# ============================================================================
# Timeout Configuration
# ============================================================================

class TimeoutsConfig(BaseModel):
    """Timeout configuration section (all values in seconds)."""
    api_request: int = Field(default=30, ge=1, le=300, description="HTTP request timeout")
    llm_request: int = Field(default=180, ge=30, le=600, description="LLM API call timeout")
    code_execution: int = Field(default=30, ge=1, le=120, description="Generated code execution timeout")
    total_search: int = Field(default=300, ge=60, le=3600, description="Total search timeout")


# ============================================================================
# Database Configuration
# ============================================================================

class DatabaseConfig(BaseModel):
    """Configuration for a specific database/integration."""
    enabled: bool = Field(default=True, description="Whether this database is enabled")
    timeout: int = Field(default=30, ge=1, le=300, description="Request timeout in seconds")

    # Optional fields that vary by database
    default_date_range_days: Optional[int] = Field(default=None, ge=1, le=365)
    results_per_page: Optional[int] = Field(default=None, ge=1, le=500)
    origin: Optional[str] = Field(default=None, description="API origin domain")
    requires_puppeteer: Optional[bool] = Field(default=None)
    default_congress: Optional[int] = Field(default=None, ge=1, le=200)
    default_limit: Optional[int] = Field(default=None, ge=1, le=500)
    max_results_per_query: Optional[int] = Field(default=None, ge=1, le=1000)
    rate_limit_per_second: Optional[int] = Field(default=None, ge=1, le=100)
    rate_limit_daily: Optional[int] = Field(default=None, ge=1, le=10000)
    max_age_days: Optional[int] = Field(default=None, ge=1, le=365)
    max_snapshots_per_url: Optional[int] = Field(default=None, ge=1, le=100)

    # Credential placeholders (actual values from .env)
    user_email: Optional[str] = Field(default=None)
    api_key: Optional[str] = Field(default=None)
    client_id: Optional[str] = Field(default=None)
    client_secret: Optional[str] = Field(default=None)
    username: Optional[str] = Field(default=None)
    password: Optional[str] = Field(default=None)
    user_agent: Optional[str] = Field(default=None)

    model_config = ConfigDict(extra="allow")  # Allow additional fields for future database-specific options


# ============================================================================
# Rate Limiting Configuration
# ============================================================================

class RateLimitingConfig(BaseModel):
    """Rate limiting configuration section."""
    circuit_breaker_sources: List[str] = Field(
        default_factory=lambda: ["SAM.gov"],
        description="Sources to skip after 429 error"
    )
    critical_always_retry: List[str] = Field(
        default_factory=lambda: ["USAJobs"],
        description="Sources that should never be skipped"
    )
    circuit_breaker_cooldown_minutes: int = Field(
        default=60, ge=1, le=1440,
        description="Minutes to keep source blocked after rate limit"
    )


# ============================================================================
# Provider Fallback Configuration
# ============================================================================

class ProviderFallbackConfig(BaseModel):
    """Provider fallback configuration for LiteLLM."""
    enabled: bool = Field(default=True, description="Enable provider fallback")
    fallback_models: List[str] = Field(
        default_factory=lambda: [
            "gemini/gemini-2.5-flash-lite",
            "gemini/gemini-2.0-flash-exp"
        ],
        description="Fallback models to try if primary fails"
    )


# ============================================================================
# Cost Management Configuration
# ============================================================================

class CostManagementConfig(BaseModel):
    """Cost management configuration section."""
    max_cost_per_query: float = Field(
        default=0.50, ge=0.0, le=100.0,
        description="Maximum cost per query in USD"
    )
    track_costs: bool = Field(default=True, description="Log LLM API costs")
    warn_on_expensive_queries: bool = Field(default=True, description="Warn if query > 50% of max")


# ============================================================================
# Research Configuration (Nested)
# ============================================================================

class DeepResearchConfig(BaseModel):
    """Deep research execution limits."""
    max_tasks: int = Field(default=15, ge=1, le=100, description="Maximum tasks to execute")
    max_retries_per_task: int = Field(default=2, ge=0, le=10, description="Max retries for failed tasks")
    max_time_minutes: int = Field(default=120, ge=1, le=1440, description="Maximum investigation time")
    min_results_per_task: int = Field(default=3, ge=0, le=100, description="Minimum results for success")
    max_concurrent_tasks: int = Field(default=4, ge=1, le=20, description="Max parallel tasks")
    task_timeout_seconds: int = Field(default=1800, ge=60, le=7200, description="Per-task timeout")
    max_follow_ups_per_task: Optional[int] = Field(
        default=None, ge=0, le=20,
        description="Max follow-ups per task (null=unlimited)"
    )


class ManagerAgentConfig(BaseModel):
    """Manager-Agent architecture configuration."""
    enabled: bool = Field(default=True, description="Enable task prioritization")
    saturation_detection: bool = Field(default=True, description="Check for research saturation")
    saturation_check_interval: int = Field(default=3, ge=1, le=20, description="Check every N tasks")
    saturation_confidence_threshold: int = Field(
        default=70, ge=50, le=100,
        description="Stop if saturation confidence >= %"
    )
    allow_saturation_stop: bool = Field(default=True, description="Stop when saturated")
    reprioritize_after_task: bool = Field(default=True, description="Reprioritize after each completion")


class HypothesisBranchingConfig(BaseModel):
    """Hypothesis branching configuration."""
    mode: Literal["off", "planning", "execution"] = Field(
        default="execution",
        description="Operation mode: off/planning/execution"
    )
    max_hypotheses_per_task: int = Field(
        default=5, ge=1, le=10,
        description="Maximum hypotheses to generate per task"
    )
    coverage_mode: bool = Field(
        default=True,
        description="Sequential execution with adaptive stopping"
    )
    max_hypotheses_to_execute: int = Field(
        default=5, ge=1, le=10,
        description="Hard ceiling on hypotheses to execute"
    )


class ModelRolesConfig(BaseModel):
    """Model roles for different research phases."""
    scoping: str = Field(default="gemini/gemini-2.5-flash")
    research: str = Field(default="gemini/gemini-2.5-flash")
    summarization: str = Field(default="gemini/gemini-2.5-flash")
    synthesis: str = Field(default="gemini/gemini-2.5-flash")


class ResearchConfig(BaseModel):
    """Research flow configuration section."""
    deep_research: DeepResearchConfig = Field(default_factory=DeepResearchConfig)
    manager_agent: ManagerAgentConfig = Field(default_factory=ManagerAgentConfig)
    hypothesis_branching: HypothesisBranchingConfig = Field(default_factory=HypothesisBranchingConfig)

    enable_scoping: bool = Field(default=False, description="Enable ScopingAgent")
    enable_supervisor: bool = Field(default=False, description="Enable ResearchSupervisor")
    enable_hitl: bool = Field(default=False, description="Enable Human-in-the-Loop")

    max_subtasks: int = Field(default=5, ge=1, le=20, description="Max sub-questions per brief")
    auto_clarify_threshold: float = Field(
        default=0.7, ge=0.0, le=1.0,
        description="Confidence to skip clarification"
    )

    model_roles: ModelRolesConfig = Field(default_factory=ModelRolesConfig)


# ============================================================================
# Logging Configuration
# ============================================================================

class LoggingConfig(BaseModel):
    """Logging configuration section."""
    level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(
        default="INFO",
        description="Logging level"
    )
    log_llm_calls: bool = Field(default=True, description="Log all LLM API calls")
    log_api_calls: bool = Field(default=True, description="Log all database API calls")
    log_file: Optional[str] = Field(default="research.log", description="Log file path")
    log_to_stdout: bool = Field(default=True, description="Print to console")


# ============================================================================
# Root Configuration Model
# ============================================================================

class AppConfig(BaseModel):
    """
    Root configuration model for the AI Research System.

    Validates all configuration sections with sensible defaults.
    Use this model to validate config.yaml and config_default.yaml.
    """

    llm: LLMConfig = Field(default_factory=LLMConfig)
    execution: ExecutionConfig = Field(default_factory=ExecutionConfig)
    integration_limits: Dict[str, int] = Field(
        default_factory=dict,
        description="Per-integration result limit overrides"
    )
    timeouts: TimeoutsConfig = Field(default_factory=TimeoutsConfig)
    databases: Dict[str, DatabaseConfig] = Field(
        default_factory=dict,
        description="Per-database configuration"
    )
    rate_limiting: RateLimitingConfig = Field(default_factory=RateLimitingConfig)
    provider_fallback: ProviderFallbackConfig = Field(default_factory=ProviderFallbackConfig)
    cost_management: CostManagementConfig = Field(default_factory=CostManagementConfig)
    research: ResearchConfig = Field(default_factory=ResearchConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)

    @field_validator("integration_limits")
    @classmethod
    def validate_integration_limits(cls, v: Dict[str, int]) -> Dict[str, int]:
        """Validate integration limits are positive integers."""
        for name, limit in v.items():
            if limit < 1:
                raise ValueError(f"Integration limit for '{name}' must be >= 1, got {limit}")
            if limit > 1000:
                raise ValueError(f"Integration limit for '{name}' must be <= 1000, got {limit}")
        return v

    @model_validator(mode="after")
    def validate_cross_field_constraints(self) -> "AppConfig":
        """Validate cross-field constraints."""
        # Ensure task timeout is greater than LLM timeout
        if self.research.deep_research.task_timeout_seconds < self.timeouts.llm_request:
            raise ValueError(
                f"task_timeout_seconds ({self.research.deep_research.task_timeout_seconds}) "
                f"must be >= llm_request timeout ({self.timeouts.llm_request})"
            )

        # Ensure max_hypotheses_to_execute <= max_hypotheses_per_task
        hypo = self.research.hypothesis_branching
        if hypo.max_hypotheses_to_execute > hypo.max_hypotheses_per_task:
            raise ValueError(
                f"max_hypotheses_to_execute ({hypo.max_hypotheses_to_execute}) "
                f"cannot exceed max_hypotheses_per_task ({hypo.max_hypotheses_per_task})"
            )

        return self

    model_config = ConfigDict(extra="allow")  # Allow additional fields for forward compatibility


def validate_config(config_dict: Dict[str, Any]) -> AppConfig:
    """
    Validate a configuration dictionary against the schema.

    Args:
        config_dict: Raw configuration dictionary from YAML

    Returns:
        Validated AppConfig instance

    Raises:
        pydantic.ValidationError: If validation fails
    """
    return AppConfig.model_validate(config_dict)


def get_default_config() -> AppConfig:
    """
    Get the default configuration with all defaults applied.

    Returns:
        AppConfig instance with default values
    """
    return AppConfig()
