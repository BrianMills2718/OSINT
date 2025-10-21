"""Central registry for all data source integrations."""

from typing import Dict, List, Type
from core.database_integration_base import DatabaseIntegration

# Import government integrations
from integrations.government.sam_integration import SAMIntegration
from integrations.government.dvids_integration import DVIDSIntegration
from integrations.government.usajobs_integration import USAJobsIntegration
from integrations.government.clearancejobs_integration import ClearanceJobsIntegration
from integrations.government.fbi_vault import FBIVaultIntegration

# Import social integrations
from integrations.social.discord_integration import DiscordIntegration
from integrations.social.twitter_integration import TwitterIntegration

# Future social integrations
# from integrations.social.reddit_integration import RedditIntegration


class IntegrationRegistry:
    """Registry for all available database integrations."""

    def __init__(self):
        self._integrations: Dict[str, Type[DatabaseIntegration]] = {}
        self._register_defaults()

    def _register_defaults(self):
        """Register all built-in integrations."""
        # Government sources
        self.register(SAMIntegration)
        self.register(DVIDSIntegration)
        self.register(USAJobsIntegration)
        self.register(ClearanceJobsIntegration)
        self.register(FBIVaultIntegration)

        # Social media sources
        self.register(DiscordIntegration)
        self.register(TwitterIntegration)

        # Future social media sources (Phase 3)
        # self.register(RedditIntegration)
        # self.register(TelegramIntegration)

    def register(self, integration_class: Type[DatabaseIntegration]):
        """Register a new integration class."""
        # Create temporary instance to get metadata
        temp_instance = integration_class()
        integration_id = temp_instance.metadata.id
        self._integrations[integration_id] = integration_class

    def get(self, integration_id: str) -> Type[DatabaseIntegration]:
        """Get an integration class by ID."""
        if integration_id not in self._integrations:
            raise ValueError(f"Unknown integration: {integration_id}")
        return self._integrations[integration_id]

    def get_all(self) -> Dict[str, Type[DatabaseIntegration]]:
        """Get all registered integrations."""
        return self._integrations.copy()

    def get_by_category(self, category: str) -> List[Type[DatabaseIntegration]]:
        """Get all integrations in a specific category."""
        result = []
        for integration_class in self._integrations.values():
            temp_instance = integration_class()
            if temp_instance.metadata.category == category:
                result.append(integration_class)
        return result

    def list_ids(self) -> List[str]:
        """List all registered integration IDs."""
        return list(self._integrations.keys())

    def list_categories(self) -> List[str]:
        """List all unique categories."""
        categories = set()
        for integration_class in self._integrations.values():
            temp_instance = integration_class()
            # Convert enum to string for sorting
            categories.add(temp_instance.metadata.category.value)
        return sorted(categories)


# Global registry instance
registry = IntegrationRegistry()
