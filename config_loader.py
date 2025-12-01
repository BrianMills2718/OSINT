#!/usr/bin/env python3
"""
Configuration loader for AI Research System.

Provides centralized configuration management with:
- YAML file loading
- Environment variable overrides
- Pydantic schema validation
- Singleton pattern
- LiteLLM provider flexibility
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, List
import logging

from config_schema import AppConfig, validate_config
from pydantic import ValidationError


class Config:
    """
    Singleton configuration manager.

    Loads configuration from:
    1. config_default.yaml (bundled defaults)
    2. config.yaml (user overrides, optional)
    3. Environment variables (highest priority)

    Usage:
        from config_loader import config

        # Get model for specific operation
        model = config.get_model("query_generation")

        # Get model parameters
        params = config.get_model_params("analysis")

        # Get timeout
        timeout = config.get_timeout("api_request")

        # Get database config
        db_config = config.get_database_config("sam")
    """

    _instance = None
    _config = None
    _validated_config: Optional[AppConfig] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Config, cls).__new__(cls)
            cls._instance._load_config()
        return cls._instance

    def _load_config(self):
        """Load configuration from files and environment."""
        # Find config directory
        config_dir = Path(__file__).parent

        # Load default config
        default_config_path = config_dir / "config_default.yaml"
        if not default_config_path.exists():
            raise FileNotFoundError(f"Default config not found: {default_config_path}")

        with open(default_config_path, 'r') as f:
            self._config = yaml.safe_load(f)

        # Load user config (optional)
        user_config_path = config_dir / "config.yaml"
        if user_config_path.exists():
            with open(user_config_path, 'r') as f:
                user_config = yaml.safe_load(f)
                self._deep_merge(self._config, user_config)

        # Apply environment variable overrides
        self._apply_env_overrides()

        # Validate config
        self._validate()

    def _deep_merge(self, base: Dict, override: Dict):
        """Deep merge override dict into base dict."""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value

    def _apply_env_overrides(self):
        """Apply environment variable overrides."""
        # LLM model overrides
        if os.getenv("RESEARCH_LLM_MODEL"):
            self._config["llm"]["default_model"] = os.getenv("RESEARCH_LLM_MODEL")

        # Execution overrides
        if os.getenv("RESEARCH_MAX_CONCURRENT"):
            self._config["execution"]["max_concurrent"] = int(os.getenv("RESEARCH_MAX_CONCURRENT"))

        if os.getenv("RESEARCH_MAX_REFINEMENTS"):
            self._config["execution"]["max_refinements"] = int(os.getenv("RESEARCH_MAX_REFINEMENTS"))

        # Timeout overrides
        if os.getenv("RESEARCH_TIMEOUT"):
            self._config["timeouts"]["total_search"] = int(os.getenv("RESEARCH_TIMEOUT"))

    def _validate(self) -> None:
        """
        Validate configuration using pydantic schema.

        Raises:
            ValueError: If validation fails with human-readable error message
        """
        try:
            # Validate against pydantic schema
            self._validated_config = validate_config(self._config)
        except ValidationError as e:
            # Convert pydantic errors to human-readable format
            errors = []
            for error in e.errors():
                field_path = ".".join(str(p) for p in error["loc"])
                msg = error["msg"]
                errors.append(f"  - {field_path}: {msg}")
            error_summary = "\n".join(errors)
            raise ValueError(f"Configuration validation failed:\n{error_summary}") from e

    # ========================================================================
    # LLM Configuration
    # ========================================================================

    def get_model(self, operation: str) -> str:
        """
        Get model name for specific operation.

        Args:
            operation: Operation type (query_generation, refinement, analysis,
                      synthesis, code_generation)

        Returns:
            Model name (e.g., "gpt-5-mini", "claude-3-5-sonnet-20241022")
        """
        operation_config = self._config["llm"].get(operation, {})

        # Return operation-specific model if specified
        if isinstance(operation_config, dict) and "model" in operation_config:
            return operation_config["model"]

        # Fall back to default model
        return self._config["llm"]["default_model"]

    def get_model_params(self, operation: str) -> Dict[str, Any]:
        """
        Get all parameters for a model operation.

        Args:
            operation: Operation type

        Returns:
            Dict with model, temperature, max_tokens, etc.
        """
        operation_config = self._config["llm"].get(operation, {})

        if isinstance(operation_config, dict):
            params = operation_config.copy()
            # Ensure model is set
            if "model" not in params:
                params["model"] = self._config["llm"]["default_model"]
            return params

        # Fallback to just model
        return {"model": self._config["llm"]["default_model"]}

    # ========================================================================
    # Execution Configuration
    # ========================================================================

    @property
    def max_concurrent(self) -> int:
        """Maximum number of concurrent API calls."""
        return self._config["execution"]["max_concurrent"]

    @property
    def max_refinements(self) -> int:
        """Maximum number of query refinement iterations."""
        return self._config["execution"]["max_refinements"]

    @property
    def default_result_limit(self) -> int:
        """Default number of results per database."""
        return self._config["execution"]["default_result_limit"]

    @property
    def enable_adaptive_analysis(self) -> bool:
        """Whether adaptive code-based analysis is enabled."""
        return self._config["execution"]["enable_adaptive_analysis"]

    @property
    def enable_auto_refinement(self) -> bool:
        """Whether automatic query refinement is enabled."""
        return self._config["execution"]["enable_auto_refinement"]

    # ========================================================================
    # Timeout Configuration
    # ========================================================================

    def get_timeout(self, timeout_type: str) -> int:
        """
        Get timeout value in seconds.

        Args:
            timeout_type: Type of timeout (api_request, llm_request,
                         code_execution, total_search)

        Returns:
            Timeout in seconds
        """
        return self._config["timeouts"].get(timeout_type, 30)

    # ========================================================================
    # Database Configuration
    # ========================================================================

    def get_database_config(self, db_id: str) -> Dict[str, Any]:
        """
        Get configuration for specific database.

        Args:
            db_id: Database ID (sam, usajobs, dvids, clearancejobs)

        Returns:
            Database configuration dict
        """
        return self._config["databases"].get(db_id, {"enabled": True, "timeout": 30})

    def is_database_enabled(self, db_id: str) -> bool:
        """Check if database is enabled."""
        db_config = self.get_database_config(db_id)
        return db_config.get("enabled", True)

    # ========================================================================
    # Rate Limiting Configuration
    # ========================================================================

    def get_rate_limit_config(self, source_name: str) -> Dict[str, Any]:
        """
        Get rate limiting configuration for a specific source.

        Priority (highest to lowest):
        1. config.yaml overrides (circuit_breaker_sources, critical_always_retry)
        2. DatabaseMetadata defaults (retry_on_rate_limit_within_session, rate_limit_recovery_seconds)
        3. Hardcoded fallbacks

        Args:
            source_name: Display name of the source (e.g., "SAM.gov", "USAJobs")

        Returns:
            Dict with:
                - use_circuit_breaker (bool): Whether to skip source after 429
                - cooldown_minutes (int): Minutes to keep source blocked
                - cooldown_seconds (int): Seconds to keep source blocked (more precise)
                - is_critical (bool): Whether source should never be skipped
                - retry_within_session (bool): Whether retrying within session is worthwhile

        Example:
            >>> config.get_rate_limit_config("SAM.gov")
            {"use_circuit_breaker": True, "cooldown_seconds": 86400, "retry_within_session": False, ...}

            >>> config.get_rate_limit_config("Brave Search")
            {"use_circuit_breaker": True, "cooldown_seconds": 120, "retry_within_session": True, ...}
        """
        # 1. Try to get per-source metadata from registry (highest priority for recovery time)
        metadata_recovery_seconds = None  # None means "use fallback"
        metadata_retry_within_session = True  # Default: worth retrying

        try:
            from integrations.registry import registry
            metadata = registry.get_metadata_by_display_name(source_name)
            if metadata:
                # Use metadata values if available
                if hasattr(metadata, 'retry_on_rate_limit_within_session'):
                    metadata_retry_within_session = metadata.retry_on_rate_limit_within_session
                if hasattr(metadata, 'rate_limit_recovery_seconds') and metadata.rate_limit_recovery_seconds:
                    metadata_recovery_seconds = metadata.rate_limit_recovery_seconds
        except ImportError:
            pass  # Registry not available, use defaults

        # 2. Get config.yaml overrides
        rate_config = self._config.get("rate_limiting", {})
        circuit_breaker_sources = rate_config.get("circuit_breaker_sources", ["SAM.gov"])
        critical_sources = rate_config.get("critical_always_retry", ["USAJobs"])
        global_cooldown_minutes = rate_config.get("circuit_breaker_cooldown_minutes", None)

        # 3. Determine final cooldown (priority: per-source metadata > global config > default)
        # Per-source metadata takes precedence because it's more accurate for each API
        if metadata_recovery_seconds is not None:
            cooldown_seconds = metadata_recovery_seconds
        elif global_cooldown_minutes is not None:
            cooldown_seconds = global_cooldown_minutes * 60
        else:
            cooldown_seconds = 60 * 60  # Default: 1 hour

        # Determine circuit breaker behavior:
        # - If explicitly in circuit_breaker_sources config.yaml, use that
        # - Otherwise, use metadata: skip circuit breaker if retry_within_session is False
        if source_name in circuit_breaker_sources:
            use_circuit_breaker = True
        else:
            # If metadata says don't retry within session, automatically enable circuit breaker
            use_circuit_breaker = not metadata_retry_within_session

        return {
            "use_circuit_breaker": use_circuit_breaker,
            "cooldown_minutes": cooldown_seconds // 60,  # Backward compatible
            "cooldown_seconds": cooldown_seconds,
            "is_critical": source_name in critical_sources,
            "retry_within_session": metadata_retry_within_session
        }

    def get_integration_limit(self, integration_name: str) -> int:
        """
        Get result limit for specific integration.

        Args:
            integration_name: Name of integration (e.g., 'usajobs', 'clearancejobs', 'twitter')

        Returns:
            Result limit for this integration, or default_result_limit if not specified

        Example:
            >>> config.get_integration_limit('usajobs')
            100  # USAJobs has override

            >>> config.get_integration_limit('twitter')
            20  # Twitter has override

            >>> config.get_integration_limit('some_new_integration')
            20  # Falls back to default_result_limit
        """
        integration_limits = self._config.get('integration_limits', {})
        return integration_limits.get(
            integration_name.lower(),
            self.default_result_limit
        )

    # ========================================================================
    # Provider Fallback (LiteLLM Feature)
    # ========================================================================

    @property
    def default_model(self) -> str:
        """Default LLM model to use for all calls."""
        llm_config = self._config.get("llm", {})
        return llm_config.get("default_model", "gpt-4o-mini")

    @property
    def fallback_enabled(self) -> bool:
        """Whether provider fallback is enabled."""
        llm_config = self._config.get("llm", {})
        fallback_config = llm_config.get("provider_fallback", {})
        return fallback_config.get("enabled", False)

    @property
    def fallback_models(self) -> List[str]:
        """List of fallback models to try if primary fails."""
        llm_config = self._config.get("llm", {})
        fallback_config = llm_config.get("provider_fallback", {})
        return fallback_config.get("fallback_models", [])

    # ========================================================================
    # Cost Management
    # ========================================================================

    @property
    def max_cost_per_query(self) -> float:
        """Maximum cost per query in USD."""
        cost_config = self._config.get("cost_management", {})
        return cost_config.get("max_cost_per_query", 0.50)

    @property
    def track_costs(self) -> bool:
        """Whether to track API costs."""
        cost_config = self._config.get("cost_management", {})
        return cost_config.get("track_costs", True)

    @property
    def warn_on_expensive_queries(self) -> bool:
        """Whether to warn on expensive queries."""
        cost_config = self._config.get("cost_management", {})
        return cost_config.get("warn_on_expensive_queries", True)

    # ========================================================================
    # Logging Configuration
    # ========================================================================

    @property
    def log_level(self) -> str:
        """Logging level (DEBUG, INFO, WARNING, ERROR)."""
        logging_config = self._config.get("logging", {})
        return logging_config.get("level", "INFO")

    @property
    def log_llm_calls(self) -> bool:
        """Whether to log LLM API calls."""
        logging_config = self._config.get("logging", {})
        return logging_config.get("log_llm_calls", True)

    @property
    def log_api_calls(self) -> bool:
        """Whether to log database API calls."""
        logging_config = self._config.get("logging", {})
        return logging_config.get("log_api_calls", True)

    @property
    def log_file(self) -> Optional[str]:
        """Log file path (None for stdout only)."""
        logging_config = self._config.get("logging", {})
        return logging_config.get("log_file")

    # ========================================================================
    # Utility Methods
    # ========================================================================

    def reload(self) -> None:
        """Reload configuration from files."""
        self._load_config()

    def get_raw_config(self) -> Dict[str, Any]:
        """Get raw configuration dict (for debugging)."""
        return self._config.copy()

    @property
    def validated(self) -> AppConfig:
        """
        Get the validated pydantic configuration model.

        Provides type-safe access to all configuration with IDE autocomplete.

        Returns:
            AppConfig: Validated configuration model

        Example:
            >>> config.validated.llm.default_model
            'gemini/gemini-2.5-flash'
            >>> config.validated.research.deep_research.max_tasks
            15
            >>> config.validated.timeouts.llm_request
            180
        """
        if self._validated_config is None:
            raise RuntimeError("Configuration not loaded. Call _load_config() first.")
        return self._validated_config


# Global singleton instance
config = Config()
