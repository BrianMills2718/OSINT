#!/usr/bin/env python3
"""
Adaptive Boolean Monitor - Boolean monitoring with iterative refinement.

This extends BooleanMonitor to use AdaptiveSearchEngine for multi-phase
iterative search instead of simple keyword matching.

Key differences vs BooleanMonitor:
- Uses AdaptiveSearchEngine for entity-based refinement
- Multiple search phases per keyword
- Quality-driven iteration
- Entity discovery tracking

Usage:
    monitor = AdaptiveBooleanMonitor("data/monitors/configs/surveillance_fisa_monitor.yaml")
    await monitor.run()
"""

from typing import List, Dict, Optional
from dataclasses import dataclass
import logging
import yaml
from pathlib import Path
import sys

# Add project root to path for imports
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from monitoring.boolean_monitor import BooleanMonitor, MonitorConfig

logger = logging.getLogger('AdaptiveBooleanMonitor')


@dataclass
class AdaptiveConfig:
    """Configuration for adaptive search parameters."""
    phase1_count: int = 15          # Initial broad search results
    analyze_top_n: int = 5           # Analyze top N for entities
    phase2_queries: int = 4          # Follow-up searches per iteration
    phase2_per_query: int = 10       # Results per follow-up search
    max_iterations: int = 3          # Maximum refinement iterations
    min_quality: float = 0.6         # Quality threshold to stop iterating


class AdaptiveBooleanMonitor(BooleanMonitor):
    """
    Boolean monitor with adaptive search capabilities.

    Extends BooleanMonitor to use AdaptiveSearchEngine for iterative,
    entity-based refinement of search results.

    Workflow:
    1. Load config (supports adaptive_search flag)
    2. For each keyword:
       a. Run AdaptiveSearchEngine (multi-phase)
       b. Collect all results from all phases
    3. Deduplicate combined results
    4. Check for new results
    5. Filter by relevance
    6. Send alerts
    7. Save results
    """

    def __init__(self, config_path: str):
        """
        Initialize adaptive monitor.

        Args:
            config_path: Path to YAML config file (supports adaptive_search field)
        """
        # Initialize base BooleanMonitor
        super().__init__(config_path)

        # Load adaptive configuration
        self.adaptive_config = self._load_adaptive_config(config_path)
        self.adaptive_enabled = self.adaptive_config is not None

        if self.adaptive_enabled:
            logger.info(f"Adaptive search ENABLED for '{self.config.name}'")
            logger.info(f"  Phase 1 results: {self.adaptive_config.phase1_count}")
            logger.info(f"  Max iterations: {self.adaptive_config.max_iterations}")
            logger.info(f"  Quality threshold: {self.adaptive_config.min_quality}")
        else:
            logger.info(f"Adaptive search DISABLED for '{self.config.name}' (using standard search)")

    def _load_adaptive_config(self, config_path: str) -> Optional[AdaptiveConfig]:
        """
        Load adaptive search configuration from YAML.

        Args:
            config_path: Path to YAML config file

        Returns:
            AdaptiveConfig if adaptive_search enabled, None otherwise
        """
        with open(config_path, 'r') as f:
            config_data = yaml.safe_load(f)

        # Check if adaptive search is enabled
        if not config_data.get('adaptive_search', False):
            return None

        # Get adaptive config section (use defaults if not specified)
        adaptive_data = config_data.get('adaptive_config', {})

        return AdaptiveConfig(
            phase1_count=adaptive_data.get('phase1_count', 15),
            analyze_top_n=adaptive_data.get('analyze_top_n', 5),
            phase2_queries=adaptive_data.get('phase2_queries', 4),
            phase2_per_query=adaptive_data.get('phase2_per_query', 10),
            max_iterations=adaptive_data.get('max_iterations', 3),
            min_quality=adaptive_data.get('min_quality', 0.6)
        )

    async def execute_search(self, keywords: List[str]) -> List[Dict]:
        """
        Execute searches - uses adaptive or standard based on config.

        If adaptive_search enabled:
        - Uses AdaptiveSearchEngine for each keyword
        - Collects all results from all phases
        - Returns combined results

        If adaptive_search disabled:
        - Falls back to parent BooleanMonitor.execute_search()

        Args:
            keywords: List of keywords to search

        Returns:
            List of standardized results from all keywords and phases
        """
        if not self.adaptive_enabled:
            # Fall back to standard parallel search
            logger.info("Using standard search (adaptive disabled)")
            return await super().execute_search(keywords)

        # Use adaptive search
        logger.info(f"Using ADAPTIVE search for {len(keywords)} keywords")

        # Import adaptive search engine
        from core.adaptive_search_engine import AdaptiveSearchEngine
        from core.parallel_executor import ParallelExecutor
        from integrations.registry import registry
        from dotenv import load_dotenv
        import os

        load_dotenv()

        # Initialize AdaptiveSearchEngine
        engine = AdaptiveSearchEngine(
            parallel_executor=ParallelExecutor(),
            phase1_count=self.adaptive_config.phase1_count,
            analyze_top_n=self.adaptive_config.analyze_top_n,
            phase2_queries=self.adaptive_config.phase2_queries,
            phase2_per_query=self.adaptive_config.phase2_per_query,
            max_iterations=self.adaptive_config.max_iterations,
            min_quality=self.adaptive_config.min_quality
        )

        # Load database integrations for configured sources
        databases = []
        api_keys = {}

        for source_id in self.config.sources:
            integration_class = registry.get(source_id)
            if integration_class:
                integration = integration_class()
                databases.append(integration)

                # Get API key if needed
                if integration.metadata.requires_api_key:
                    api_key_var = f"{source_id.upper().replace('-', '_')}_API_KEY"
                    api_key = os.getenv(api_key_var, '')
                    if api_key:
                        api_keys[source_id] = api_key
            else:
                logger.warning(f"Unknown source in config: {source_id}")

        logger.info(f"Loaded {len(databases)} database integrations")

        # Execute adaptive search for each keyword
        all_results = []
        all_entities = []

        for keyword in keywords:
            logger.info(f"\n{'='*60}")
            logger.info(f"ADAPTIVE SEARCH: '{keyword}'")
            logger.info(f"{'='*60}")

            try:
                # Run adaptive search
                adaptive_result = await engine.adaptive_search(
                    initial_query=keyword,
                    databases=databases,
                    api_keys=api_keys
                )

                # Log adaptive search summary
                logger.info(f"\nAdaptive search complete for '{keyword}':")
                logger.info(f"  Total results: {adaptive_result.total_results}")
                logger.info(f"  Unique results: {adaptive_result.unique_results}")
                logger.info(f"  Phases: {adaptive_result.iterations}")
                logger.info(f"  Entities discovered: {len(adaptive_result.entities_discovered)}")
                logger.info(f"  Quality: {adaptive_result.quality_metrics.get('overall_quality', 0):.2f}")

                if adaptive_result.quality_metrics.get('warnings'):
                    logger.info(f"  Warnings: {adaptive_result.quality_metrics['warnings']}")

                # Log entities discovered
                if adaptive_result.entities_discovered:
                    logger.info(f"  Entities: {adaptive_result.entities_discovered[:5]}...")
                    all_entities.extend(adaptive_result.entities_discovered)

                # Collect results from all phases
                for phase in adaptive_result.phases:
                    for result in phase.results:
                        # Add keyword field for tracking
                        result['keyword'] = keyword
                        # Add phase information
                        result['adaptive_phase'] = phase.phase_num
                        result['adaptive_quality'] = phase.quality_score

                        all_results.append(result)

                logger.info(f"Collected {len([r for r in all_results if r['keyword'] == keyword])} results for '{keyword}'")

            except Exception as e:
                logger.error(f"Adaptive search failed for '{keyword}': {str(e)}", exc_info=True)
                # Continue with other keywords even if one fails

        # Log summary
        logger.info(f"\n{'='*60}")
        logger.info(f"ADAPTIVE SEARCH SUMMARY")
        logger.info(f"{'='*60}")
        logger.info(f"Keywords searched: {len(keywords)}")
        logger.info(f"Total results: {len(all_results)}")
        logger.info(f"Unique entities discovered: {len(set(all_entities))}")

        return all_results


# Example usage
async def main():
    """Test the AdaptiveBooleanMonitor with example config."""
    import asyncio
    import sys

    if len(sys.argv) < 2:
        print("Usage: python3 adaptive_boolean_monitor.py <config_path>")
        print("Example: python3 adaptive_boolean_monitor.py data/monitors/configs/surveillance_fisa_monitor.yaml")
        return

    config_path = sys.argv[1]

    # Create adaptive monitor
    monitor = AdaptiveBooleanMonitor(config_path)

    # Run monitor
    await monitor.run()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
