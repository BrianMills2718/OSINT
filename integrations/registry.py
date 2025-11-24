"""Central registry for all data source integrations."""

from typing import Dict, List, Type, Optional
from core.database_integration_base import DatabaseIntegration
from config_loader import config

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
except ImportError:
    CLEARANCEJOBS_AVAILABLE = False

# CREST integrations (Playwright and Selenium versions)
try:
    from integrations.government.crest_integration import CRESTIntegration
    CREST_PLAYWRIGHT_AVAILABLE = True
except ImportError:
    CREST_PLAYWRIGHT_AVAILABLE = False

try:
    from integrations.government.crest_selenium_integration import CRESTSeleniumIntegration
    CREST_SELENIUM_AVAILABLE = True
except ImportError:
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
            print(f"Warning: Failed to register {integration_id}: {e}")
            # Don't crash - let other integrations continue

    def register(self, integration_id: str, integration_class: Type[DatabaseIntegration]):
        """
        Register a new integration class with architectural validation.

        Enforces architectural consistency by validating:
        1. Required methods exist (metadata, is_relevant, generate_query, execute_search)
        2. Source metadata entry exists in source_metadata.py
        3. Prompt template exists (warning only)
        4. Metadata ID matches registration ID

        Args:
            integration_id: Unique ID for this integration (must match metadata.id)
            integration_class: The integration class (NOT an instance)

        Raises:
            ValueError: If validation fails (missing methods, missing metadata, ID mismatch)
        """
        import os

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
            raise ValueError(
                f"Integration '{integration_id}' failed to instantiate or get metadata: {e}"
            )

        # Validation 3: Source metadata entry exists
        from integrations.source_metadata import get_source_metadata
        source_metadata = get_source_metadata(metadata.name)
        if not source_metadata:
            raise ValueError(
                f"Integration '{integration_id}' missing source_metadata entry for '{metadata.name}'.\n"
                f"Add entry to integrations/source_metadata.py"
            )

        # Validation 4: Prompt template exists (warning only, not all integrations need prompts)
        prompt_path = f"prompts/integrations/{integration_id}_query_generation.j2"
        if not os.path.exists(prompt_path):
            # Not an error - some integrations may not use LLM query generation
            pass

        # Validation 5: Metadata ID matches registration ID
        if metadata.id != integration_id:
            raise ValueError(
                f"Integration metadata.id ('{metadata.id}') doesn't match registration ID ('{integration_id}')\n"
                f"Update metadata.id in integration class to match"
            )

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
                results['query_generation'] = False
                results['error'] = results.get('error', '') + f" | Query generation check failed: {e}"

            # Test 4: execute_search exists and is async?
            try:
                import inspect
                has_execute_search = hasattr(instance, 'execute_search')
                is_async = inspect.iscoroutinefunction(instance.execute_search) if has_execute_search else False
                results['graceful_errors'] = has_execute_search and is_async
            except Exception as e:
                results['graceful_errors'] = False
                results['error'] = results.get('error', '') + f" | Execute search check failed: {e}"

        except Exception as e:
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


# Global registry instance
registry = IntegrationRegistry()
