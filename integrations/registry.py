"""Central registry for all data source integrations.

This is the SINGLE ACCESS POINT for all integration-related queries.
Do NOT build parallel data structures elsewhere - use registry methods.
"""

from typing import Dict, List, Type, Optional
import logging
import os
from core.database_integration_base import DatabaseIntegration, DatabaseMetadata
from config_loader import config

# Set up logger for this module
logger = logging.getLogger(__name__)

# Import government integrations
from integrations.government.sam_integration import SAMIntegration
from integrations.government.usaspending_integration import USASpendingIntegration
from integrations.government.dvids_integration import DVIDSIntegration
from integrations.government.usajobs_integration import USAJobsIntegration
from integrations.government.fbi_vault import FBIVaultIntegration
from integrations.government.federal_register import FederalRegisterIntegration
from integrations.government.congress_integration import CongressIntegration
from integrations.government.govinfo_integration import GovInfoIntegration
from integrations.government.sec_edgar_integration import SECEdgarIntegration
from integrations.government.fec_integration import FECIntegration

# Import legal integrations
from integrations.legal.courtlistener_integration import CourtListenerIntegration

# Import investigative integrations
from integrations.investigative.icij_offshore_leaks import ICIJOffshoreLeaksIntegration

# ClearanceJobs integration requires Playwright (optional dependency)
try:
    from integrations.government.clearancejobs_integration import ClearanceJobsIntegration
    CLEARANCEJOBS_AVAILABLE = True
except ImportError as e:
    # Optional dependency missing - integration will be unavailable
    logger.debug(f"ClearanceJobs integration unavailable: {e}", exc_info=True)
    CLEARANCEJOBS_AVAILABLE = False

# CREST integrations (Playwright and Selenium versions)
try:
    from integrations.government.crest_integration import CRESTIntegration
    CREST_PLAYWRIGHT_AVAILABLE = True
except ImportError as e:
    # Optional dependency missing - integration will be unavailable
    logger.debug(f"CREST Playwright integration unavailable: {e}", exc_info=True)
    CREST_PLAYWRIGHT_AVAILABLE = False

try:
    from integrations.government.crest_selenium_integration import CRESTSeleniumIntegration
    CREST_SELENIUM_AVAILABLE = True
except ImportError as e:
    # Optional dependency missing - integration will be unavailable
    logger.debug(f"CREST Selenium integration unavailable: {e}", exc_info=True)
    CREST_SELENIUM_AVAILABLE = False

# Import social integrations
from integrations.social.discord_integration import DiscordIntegration
from integrations.social.brave_search_integration import BraveSearchIntegration

# Import news integrations
from integrations.news.newsapi_integration import NewsAPIIntegration

# Import nonprofit integrations
from integrations.nonprofit.propublica_integration import ProPublicaIntegration

# Import archive integrations
from integrations.archive.wayback_integration import WaybackMachineIntegration

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

# Telegram integration requires Telethon
try:
    from integrations.social.telegram_integration import TelegramIntegration
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False


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
        self._try_register("usaspending", USASpendingIntegration)
        self._try_register("dvids", DVIDSIntegration)
        self._try_register("usajobs", USAJobsIntegration)
        if CLEARANCEJOBS_AVAILABLE:
            self._try_register("clearancejobs", ClearanceJobsIntegration)

        # CREST - Selenium only (Playwright version blocked by Akamai Bot Manager)
        if CREST_SELENIUM_AVAILABLE:
            self._try_register("crest_selenium", CRESTSeleniumIntegration)

        self._try_register("fbi_vault", FBIVaultIntegration)
        self._try_register("federal_register", FederalRegisterIntegration)
        self._try_register("congress", CongressIntegration)
        self._try_register("govinfo", GovInfoIntegration)
        self._try_register("sec_edgar", SECEdgarIntegration)
        self._try_register("fec", FECIntegration)

        # Legal sources
        self._try_register("courtlistener", CourtListenerIntegration)

        # Investigative sources
        self._try_register("icij_offshore_leaks", ICIJOffshoreLeaksIntegration)

        # Social media sources
        self._try_register("discord", DiscordIntegration)
        if TWITTER_AVAILABLE:
            self._try_register("twitter", TwitterIntegration)
        if REDDIT_AVAILABLE:
            self._try_register("reddit", RedditIntegration)
        if TELEGRAM_AVAILABLE:
            self._try_register("telegram", TelegramIntegration)

        # Web search & news
        self._try_register("brave_search", BraveSearchIntegration)
        self._try_register("newsapi", NewsAPIIntegration)

        # Nonprofit sources
        self._try_register("propublica", ProPublicaIntegration)

        # Archive sources
        self._try_register("wayback_machine", WaybackMachineIntegration)

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
            # Registration failed - log but don't crash
            logger.warning(f"Failed to register {integration_id}: {e}", exc_info=True)
            print(f"Warning: Failed to register {integration_id}: {e}")
            # Don't crash - let other integrations continue

    def register(self, integration_id: str, integration_class: Type[DatabaseIntegration]):
        """
        Register a new integration class with architectural validation.

        Enforces architectural consistency by validating:
        1. Required methods exist (metadata, is_relevant, generate_query, execute_search)
        2. Can instantiate and get metadata
        3. Metadata ID matches registration ID
        4. Prompt template exists (warning only)

        Args:
            integration_id: Unique ID for this integration (must match metadata.id)
            integration_class: The integration class (NOT an instance)

        Raises:
            ValueError: If validation fails (missing methods, missing metadata, ID mismatch)
        """
        # Validation 1: Required methods exist
        required_methods = ['metadata', 'is_relevant', 'generate_query', 'execute_search']
        missing_methods = [m for m in required_methods if not hasattr(integration_class, m)]
        if missing_methods:
            raise ValueError(
                f"Integration '{integration_id}' missing required methods: {missing_methods}\n"
                f"All integrations must implement: {required_methods}"
            )

        # Validation 2: Can instantiate and get metadata
        try:
            temp_instance = integration_class()
            metadata = temp_instance.metadata
        except Exception as e:
            # Metadata validation failed - log and re-raise
            logger.error(f"Integration '{integration_id}' failed to instantiate or get metadata: {e}", exc_info=True)
            raise ValueError(
                f"Integration '{integration_id}' failed to instantiate or get metadata: {e}"
            )

        # Validation 3: Metadata ID matches registration ID
        if metadata.id != integration_id:
            raise ValueError(
                f"Integration metadata.id ('{metadata.id}') doesn't match registration ID ('{integration_id}')\n"
                f"Update metadata.id in integration class to match"
            )

        # Validation 4: Prompt template exists (warning only, not all integrations need prompts)
        prompt_path = f"prompts/integrations/{integration_id}_query_generation.j2"
        if not os.path.exists(prompt_path):
            # Not an error - some integrations may not use LLM query generation
            pass

        # All validations passed - register it
        self._integration_classes[integration_id] = integration_class
        # Success message removed to avoid spam during startup

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
            # Instantiation failed - log and return None
            logger.warning(f"Failed to instantiate {integration_id}: {e}", exc_info=True)
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
                    # Availability check failed
                    logger.debug(f"Availability check failed for {integration_id}: {e}", exc_info=True)
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

    def validate_integration(self, integration_id: str) -> Dict[str, any]:
        """
        Run smoke tests on a registered integration.

        Tests:
        1. Can instantiate?
        2. Metadata is valid?
        3. generate_query returns valid structure?
        4. execute_search handles errors gracefully?

        Args:
            integration_id: Integration ID to validate

        Returns:
            Dict with test results:
            {
                "instantiation": bool,
                "metadata_valid": bool,
                "query_generation": bool,
                "graceful_errors": bool,
                "error": str (if any test failed with exception)
            }
        """
        results = {}

        try:
            # Test 1: Can instantiate?
            instance = self.get_instance(integration_id)
            results['instantiation'] = instance is not None

            if not instance:
                results['metadata_valid'] = False
                results['query_generation'] = False
                results['graceful_errors'] = False
                return results

            # Test 2: Metadata valid?
            try:
                metadata = instance.metadata
                results['metadata_valid'] = bool(
                    metadata.name and
                    metadata.id and
                    metadata.category
                )
            except Exception as e:
                # Metadata validation failed during structural check
                logger.warning(f"Metadata validation failed for {integration_id}: {e}", exc_info=True)
                results['metadata_valid'] = False
                results['error'] = f"Metadata validation failed: {e}"

            # Test 3: generate_query returns valid structure?
            # Note: This is async, but we're doing a basic check here
            # Full validation would require actually calling it
            try:
                import inspect
                has_generate_query = hasattr(instance, 'generate_query')
                is_async = inspect.iscoroutinefunction(instance.generate_query) if has_generate_query else False
                results['query_generation'] = has_generate_query and is_async
            except Exception as e:
                # Query generation check failed
                logger.debug(f"Query generation check failed for {integration_id}: {e}", exc_info=True)
                results['query_generation'] = False
                results['error'] = results.get('error', '') + f" | Query generation check failed: {e}"

            # Test 4: execute_search exists and is async?
            try:
                import inspect
                has_execute_search = hasattr(instance, 'execute_search')
                is_async = inspect.iscoroutinefunction(instance.execute_search) if has_execute_search else False
                results['graceful_errors'] = has_execute_search and is_async
            except Exception as e:
                # Execute search check failed
                logger.debug(f"Execute search check failed for {integration_id}: {e}", exc_info=True)
                results['graceful_errors'] = False
                results['error'] = results.get('error', '') + f" | Execute search check failed: {e}"

        except Exception as e:
            # Overall validation failed - log and record error
            logger.error(f"Structural validation failed for {integration_id}: {e}", exc_info=True)
            results['error'] = str(e)
            # Fill in any missing results
            for key in ['instantiation', 'metadata_valid', 'query_generation', 'graceful_errors']:
                if key not in results:
                    results[key] = False

        return results

    def validate_all(self) -> Dict[str, Dict[str, any]]:
        """
        Run smoke tests on ALL registered integrations.

        Returns:
            Dict of integration_id -> validation results
            {
                "integration_id": {
                    "instantiation": bool,
                    "metadata_valid": bool,
                    "query_generation": bool,
                    "graceful_errors": bool,
                    "error": str (if any)
                }
            }
        """
        results = {}
        for integration_id in self._integration_classes:
            results[integration_id] = self.validate_integration(integration_id)
        return results

    def print_validation_report(self, results: Dict[str, Dict[str, any]] = None):
        """
        Print a human-readable validation report.

        Args:
            results: Optional validation results from validate_all().
                    If not provided, will run validate_all() first.
        """
        if results is None:
            results = self.validate_all()

        print("\n" + "="*80)
        print("INTEGRATION VALIDATION REPORT")
        print("="*80)

        total_integrations = len(results)
        passed_count = 0

        for integration_id, tests in sorted(results.items()):
            # Count passed tests
            test_results = [v for k, v in tests.items() if k != 'error' and isinstance(v, bool)]
            passed = sum(test_results)
            total = len(test_results)

            if passed == total:
                status = "[PASS]"
                passed_count += 1
            elif passed > 0:
                status = "[PARTIAL]"
            else:
                status = "[FAIL]"

            print(f"\n{status} {integration_id}: {passed}/{total} tests passed")

            # Show individual test results
            if passed < total or 'error' in tests:
                for test_name, result in tests.items():
                    if test_name == 'error':
                        print(f"  ❌ Error: {result}")
                    elif not result:
                        print(f"  ❌ {test_name}: FAIL")

        print("\n" + "="*80)
        print(f"SUMMARY: {passed_count}/{total_integrations} integrations passed all tests")
        print("="*80)


    # ==========================================================================
    # HELPER METHODS - Single access point for all source-related queries
    # Use these instead of building parallel data structures in other modules
    # ==========================================================================

    def get_metadata(self, integration_id: str) -> Optional[DatabaseMetadata]:
        """
        Get complete metadata for an integration.

        This is the SINGLE SOURCE OF TRUTH for all source configuration.

        Args:
            integration_id: Integration ID (e.g., "sam", "govinfo")

        Returns:
            DatabaseMetadata or None if not found/not enabled
        """
        instance = self.get_instance(integration_id)
        if instance:
            return instance.metadata
        return None

    def get_display_name(self, integration_id: str) -> str:
        """
        Get human-readable display name for an integration.

        Args:
            integration_id: Integration ID (e.g., "sam")

        Returns:
            Display name (e.g., "SAM.gov") or integration_id if not found
        """
        metadata = self.get_metadata(integration_id)
        return metadata.name if metadata else integration_id

    def get_all_metadata(self) -> Dict[str, DatabaseMetadata]:
        """
        Get metadata for all enabled integrations.

        Returns:
            Dict of integration_id -> DatabaseMetadata
        """
        result = {}
        for integration_id in self._integration_classes:
            metadata = self.get_metadata(integration_id)
            if metadata:
                result[integration_id] = metadata
        return result

    def normalize_source_name(self, name: str) -> Optional[str]:
        """
        Normalize any source name variation to canonical integration_id.

        Handles:
        - Integration IDs: "sam" -> "sam"
        - Display names: "SAM.gov" -> "sam"
        - Case variations: "GOVINFO" -> "govinfo"
        - Common suffixes: "USASpending.gov" -> "usaspending"

        This is the ONE function that should be used for all LLM output
        normalization. Do NOT implement normalization elsewhere.

        Args:
            name: Source name from LLM or user (any format)

        Returns:
            Canonical integration_id or None if no match found
        """
        if not name:
            return None

        # Build lookup maps on first call (cached via instance)
        if not hasattr(self, '_name_lookup_cache'):
            self._name_lookup_cache = {}
            self._display_to_id_cache = {}

            for integration_id in self._integration_classes:
                metadata = self.get_metadata(integration_id)
                if metadata:
                    # Map integration_id -> itself
                    self._name_lookup_cache[integration_id.lower()] = integration_id
                    # Map display_name -> integration_id
                    self._display_to_id_cache[metadata.name.lower()] = integration_id

        # 1. Try exact match on integration_id
        name_lower = name.lower()
        if name_lower in self._name_lookup_cache:
            return self._name_lookup_cache[name_lower]

        # 2. Try exact match on display name
        if name_lower in self._display_to_id_cache:
            return self._display_to_id_cache[name_lower]

        # 3. Handle search_ prefix (legacy tool naming convention)
        if name_lower.startswith("search_"):
            base = name_lower[7:]  # Remove "search_" prefix
            if base in self._name_lookup_cache:
                return self._name_lookup_cache[base]

        # 4. Try removing common suffixes (.gov, .com, .org)
        for suffix in [".gov", ".com", ".org"]:
            if name_lower.endswith(suffix):
                base = name_lower[:-len(suffix)]
                if base in self._name_lookup_cache:
                    return self._name_lookup_cache[base]
                if base in self._display_to_id_cache:
                    return self._display_to_id_cache[base]

        # 5. Try fuzzy match (contains)
        for display_lower, integration_id in self._display_to_id_cache.items():
            if display_lower in name_lower or name_lower in display_lower:
                return integration_id

        return None

    def get_api_key(self, integration_id: str) -> Optional[str]:
        """
        Get API key for an integration from environment.

        Uses the api_key_env_var field from DatabaseMetadata.

        Args:
            integration_id: Integration ID

        Returns:
            API key string or None if not required/not found
        """
        metadata = self.get_metadata(integration_id)
        if not metadata or not metadata.requires_api_key:
            return None

        env_var = metadata.api_key_env_var
        if not env_var:
            # Fallback to convention: INTEGRATION_ID_API_KEY
            env_var = f"{integration_id.upper()}_API_KEY"

        return os.getenv(env_var)

    def get_api_key_status(self) -> Dict[str, Dict[str, any]]:
        """
        Get API key status for all integrations (for debugging/UI).

        Returns:
            Dict of integration_id -> {
                "requires_key": bool,
                "env_var": str,
                "has_key": bool
            }
        """
        status = {}
        for integration_id in self._integration_classes:
            metadata = self.get_metadata(integration_id)
            if metadata:
                env_var = metadata.api_key_env_var or f"{integration_id.upper()}_API_KEY"
                status[integration_id] = {
                    "requires_key": metadata.requires_api_key,
                    "env_var": env_var if metadata.requires_api_key else None,
                    "has_key": bool(os.getenv(env_var)) if metadata.requires_api_key else True
                }
        return status

    def clear_caches(self):
        """Clear all internal caches (useful after dynamic registration)."""
        self._cached_instances.clear()
        if hasattr(self, '_name_lookup_cache'):
            del self._name_lookup_cache
        if hasattr(self, '_display_to_id_cache'):
            del self._display_to_id_cache


# Global registry instance
registry = IntegrationRegistry()
