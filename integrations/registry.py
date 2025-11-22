"""Central registry for all data source integrations."""

from typing import Dict, List, Type, Optional
from core.database_integration_base import DatabaseIntegration
from config_loader import config

# Import government integrations
from integrations.government.sam_integration import SAMIntegration
from integrations.government.dvids_integration import DVIDSIntegration
from integrations.government.usajobs_integration import USAJobsIntegration
from integrations.government.fbi_vault import FBIVaultIntegration
from integrations.government.federal_register import FederalRegisterIntegration
from integrations.government.congress_integration import CongressIntegration

# ClearanceJobs integration requires Playwright (optional dependency)
try:
    from integrations.government.clearancejobs_integration import ClearanceJobsIntegration
    CLEARANCEJOBS_AVAILABLE = True
except ImportError:
    CLEARANCEJOBS_AVAILABLE = False

# CREST integration requires Playwright (optional dependency)
try:
    from integrations.government.crest_integration import CRESTIntegration
    CREST_AVAILABLE = True
except ImportError:
    CREST_AVAILABLE = False

# Import social integrations
from integrations.social.discord_integration import DiscordIntegration
from integrations.social.brave_search_integration import BraveSearchIntegration

# Twitter integration requires twitterexplorer_sigint (not yet installed)
try:
    from integrations.social.twitter_integration import TwitterIntegration
    TWITTER_AVAILABLE = True
except ImportError:
    TWITTER_AVAILABLE = False

# Reddit integration requires PRAW (installed)
try:
    from integrations.social.reddit_integration import RedditIntegration
    REDDIT_AVAILABLE = True
except ImportError:
    REDDIT_AVAILABLE = False


class IntegrationRegistry:
    """
    Registry for all available database integrations.

    Supports:
    - Lazy instantiation (classes stored, not instances)
    - Feature flags (config-driven enable/disable)
    - Import isolation (individual integration failures don't crash registry)
    """

    def __init__(self):
        self._integration_classes: Dict[str, Type[DatabaseIntegration]] = {}
        self._cached_instances: Dict[str, DatabaseIntegration] = {}
        self._register_defaults()

    def _register_defaults(self):
        """
        Register all built-in integrations with import isolation.

        Each integration is registered in a try/except block so that:
        - Import failures don't crash the entire registry
        - Failures are logged for debugging
        - Other integrations continue to work
        """
        # Government sources
        self._try_register("sam", SAMIntegration)
        self._try_register("dvids", DVIDSIntegration)
        self._try_register("usajobs", USAJobsIntegration)
        if CLEARANCEJOBS_AVAILABLE:
            self._try_register("clearancejobs", ClearanceJobsIntegration)
        if CREST_AVAILABLE:
            self._try_register("crest", CRESTIntegration)
        self._try_register("fbi_vault", FBIVaultIntegration)
        self._try_register("federal_register", FederalRegisterIntegration)
        self._try_register("congress", CongressIntegration)

        # Social media sources
        self._try_register("discord", DiscordIntegration)
        if TWITTER_AVAILABLE:
            self._try_register("twitter", TwitterIntegration)
        if REDDIT_AVAILABLE:
            self._try_register("reddit", RedditIntegration)

        # Web search
        self._try_register("brave_search", BraveSearchIntegration)

        # Future social media sources (Phase 3)
        # self._try_register("telegram", TelegramIntegration)

    def _try_register(self, integration_id: str, integration_class: Type[DatabaseIntegration]):
        """
        Try to register an integration, catching and logging any errors.

        Args:
            integration_id: Integration ID
            integration_class: Integration class

        Returns:
            None (errors are logged but don't crash)
        """
        try:
            self.register(integration_id, integration_class)
        except Exception as e:
            print(f"Warning: Failed to register {integration_id}: {e}")
            # Don't crash - let other integrations continue

    def register(self, integration_id: str, integration_class: Type[DatabaseIntegration]):
        """
        Register a new integration class.

        Args:
            integration_id: Unique ID for this integration (must match metadata.id)
            integration_class: The integration class (NOT an instance)
        """
        self._integration_classes[integration_id] = integration_class

    def is_enabled(self, integration_id: str) -> bool:
        """
        Check if an integration is enabled via feature flags.

        Args:
            integration_id: Integration ID to check

        Returns:
            True if enabled in config, False if disabled or config missing
        """
        try:
            db_config = config.get_database_config(integration_id)
            return db_config.get("enabled", True)  # Default to enabled if not specified
        except Exception:
            # If config doesn't exist or fails to load, default to enabled
            return True

    def get(self, integration_id: str) -> Type[DatabaseIntegration]:
        """
        Get an integration class by ID.

        Args:
            integration_id: Integration ID

        Returns:
            Integration class (NOT instance)

        Raises:
            ValueError: If integration not found
        """
        if integration_id not in self._integration_classes:
            raise ValueError(f"Unknown integration: {integration_id}")
        return self._integration_classes[integration_id]

    def get_instance(self, integration_id: str) -> Optional[DatabaseIntegration]:
        """
        Get an integration instance (lazy instantiation + caching).

        Args:
            integration_id: Integration ID

        Returns:
            Integration instance, or None if disabled or unavailable
        """
        # Check feature flag
        if not self.is_enabled(integration_id):
            return None

        # Return cached instance if available
        if integration_id in self._cached_instances:
            return self._cached_instances[integration_id]

        # Lazy instantiation
        try:
            integration_class = self.get(integration_id)
            instance = integration_class()
            self._cached_instances[integration_id] = instance
            return instance
        except Exception as e:
            # Log error but don't crash
            print(f"Warning: Failed to instantiate {integration_id}: {e}")
            return None

    def get_all(self) -> Dict[str, Type[DatabaseIntegration]]:
        """Get all registered integration classes (NOT instances)."""
        return self._integration_classes.copy()

    def get_all_enabled(self) -> Dict[str, DatabaseIntegration]:
        """
        Get all enabled integration instances.

        Returns:
            Dict of integration_id -> instance for all enabled integrations
        """
        enabled = {}
        for integration_id in self._integration_classes.keys():
            instance = self.get_instance(integration_id)
            if instance is not None:
                enabled[integration_id] = instance
        return enabled

    def get_by_category(self, category: str) -> List[Type[DatabaseIntegration]]:
        """
        Get all integration classes in a specific category.

        Args:
            category: Category name

        Returns:
            List of integration classes (NOT instances)
        """
        result = []
        for integration_class in self._integration_classes.values():
            # Create temporary instance to check category
            temp_instance = integration_class()
            if temp_instance.metadata.category == category:
                result.append(integration_class)
        return result

    def list_ids(self) -> List[str]:
        """List all registered integration IDs."""
        return list(self._integration_classes.keys())

    def list_enabled_ids(self) -> List[str]:
        """List IDs of all enabled integrations."""
        return [
            integration_id
            for integration_id in self._integration_classes.keys()
            if self.is_enabled(integration_id)
        ]

    def list_categories(self) -> List[str]:
        """List all unique categories."""
        categories = set()
        for integration_class in self._integration_classes.values():
            temp_instance = integration_class()
            # Convert enum to string for sorting
            categories.add(temp_instance.metadata.category.value)
        return sorted(categories)

    def get_status(self) -> Dict[str, Dict[str, any]]:
        """
        Get status of all integrations (for debugging/UI).

        Returns:
            Dict of integration_id -> {
                "registered": bool,
                "enabled": bool,
                "available": bool (can instantiate),
                "reason": str (if unavailable)
            }
        """
        status = {}
        for integration_id in self._integration_classes.keys():
            enabled = self.is_enabled(integration_id)

            # Try to instantiate to check availability
            available = False
            reason = None
            if enabled:
                try:
                    instance = self.get_instance(integration_id)
                    available = instance is not None
                    if not available:
                        reason = "Instantiation failed"
                except Exception as e:
                    reason = str(e)
            else:
                reason = "Disabled in config"

            status[integration_id] = {
                "registered": True,
                "enabled": enabled,
                "available": available,
                "reason": reason
            }

        return status


# Global registry instance
registry = IntegrationRegistry()
