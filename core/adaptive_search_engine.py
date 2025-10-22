"""Adaptive search engine following Mozart pattern.

This module implements iterative, autonomous search that refines itself:
1. Broad initial search
2. Analyze top results for entities
3. Targeted follow-up searches
4. Quality check & iterate if needed
"""

from typing import List, Dict, Optional
from dataclasses import dataclass
import logging
from llm_utils import acompletion
import json

logger = logging.getLogger(__name__)


@dataclass
class SearchPhase:
    """Results from one search phase."""
    phase_num: int
    query: str
    results: List[Dict]
    entities_extracted: List[str]
    quality_score: float


@dataclass
class AdaptiveSearchResult:
    """Complete adaptive search results."""
    initial_query: str
    phases: List[SearchPhase]
    total_results: int
    unique_results: int
    entities_discovered: List[str]
    quality_metrics: Dict
    iterations: int
    results: List[Dict] = None  # NEW: Actual result objects for synthesis

    def __post_init__(self):
        if self.results is None:
            self.results = []


class AdaptiveSearchEngine:
    """
    Autonomous search that iterates and refines itself.

    Based on Mozart's adaptive discovery pattern:
    1. Broad initial search
    2. Analyze top results for entities
    3. Targeted follow-up searches
    4. Quality check & retry if needed

    Example:
        from core.adaptive_search_engine import AdaptiveSearchEngine
        from core.parallel_executor import ParallelExecutor

        engine = AdaptiveSearchEngine(
            parallel_executor=ParallelExecutor(),
            phase1_count=15,
            max_iterations=3
        )

        result = await engine.adaptive_search("FISA Section 702")
        print(f"Found {result.total_results} results in {result.iterations} phases")
        print(f"Discovered entities: {result.entities_discovered}")
    """

    def __init__(
        self,
        parallel_executor,  # ParallelExecutor instance
        phase1_count: int = 15,      # Initial broad results
        analyze_top_n: int = 5,       # Analyze top 5 for entities
        phase2_queries: int = 4,      # Follow-up searches per iteration
        phase2_per_query: int = 10,   # Results per follow-up
        max_iterations: int = 3,      # Max refinement iterations
        min_quality: float = 0.6,     # Min quality score to stop
    ):
        """
        Initialize the adaptive search engine.

        Args:
            parallel_executor: ParallelExecutor instance for running searches
            phase1_count: Number of results in initial broad search
            analyze_top_n: How many top results to analyze for entities
            phase2_queries: How many entity-based searches per iteration
            phase2_per_query: Results per entity search
            max_iterations: Maximum refinement cycles
            min_quality: Quality threshold to stop searching (0-1)
        """
        self.executor = parallel_executor
        self.phase1_count = phase1_count
        self.analyze_top_n = analyze_top_n
        self.phase2_queries = phase2_queries
        self.phase2_per_query = phase2_per_query
        self.max_iterations = max_iterations
        self.min_quality = min_quality

    async def adaptive_search(
        self,
        initial_query: str,
        databases: List = None,
        api_keys: Dict[str, str] = None
    ) -> AdaptiveSearchResult:
        """
        Execute adaptive search with iterative refinement.

        Args:
            initial_query: Starting search query (e.g., "FISA Section 702")
            databases: List of database integrations to search (defaults to all)
            api_keys: API keys dict for databases

        Returns:
            Complete search results with all phases

        Example:
            result = await engine.adaptive_search(
                "FISA Section 702",
                databases=[sam_db, dvids_db],
                api_keys={"sam": "key123"}
            )
        """
        phases = []
        all_results = []
        seen_urls = set()

        logger.info(f"Starting adaptive search: '{initial_query}'")

        # Phase 1: Broad initial search
        logger.info(f"Phase 1: Broad search ({self.phase1_count} results per database)")
        phase1_results = await self._search_phase(
            query=initial_query,
            limit=self.phase1_count,
            databases=databases,
            api_keys=api_keys
        )

        phase1_unique = self._deduplicate(phase1_results, seen_urls)
        all_results.extend(phase1_unique)

        # Analyze top results for entities
        entities = await self._extract_entities(
            phase1_unique[:self.analyze_top_n],
            initial_query
        )

        phases.append(SearchPhase(
            phase_num=1,
            query=initial_query,
            results=phase1_unique,
            entities_extracted=entities,
            quality_score=self._calculate_quality(phase1_unique)
        ))

        logger.info(f"Phase 1 complete: {len(phase1_unique)} results, extracted {len(entities)} entities")

        # Phase 2+: Iterative refinement
        iteration = 1
        current_entities = entities

        while iteration <= self.max_iterations:
            logger.info(f"Iteration {iteration}: Targeted searches for {len(current_entities[:self.phase2_queries])} entities")

            iteration_results = []

            # Search for each extracted entity
            for entity in current_entities[:self.phase2_queries]:
                refined_query = f"{initial_query} AND {entity}"
                logger.info(f"  Searching: {refined_query}")

                entity_results = await self._search_phase(
                    query=refined_query,
                    limit=self.phase2_per_query,
                    databases=databases,
                    api_keys=api_keys
                )

                unique_entity_results = self._deduplicate(entity_results, seen_urls)
                iteration_results.extend(unique_entity_results)

            all_results.extend(iteration_results)

            # Analyze new results for more entities
            if iteration_results:
                new_entities = await self._extract_entities(
                    iteration_results[:self.analyze_top_n],
                    initial_query
                )
            else:
                new_entities = []

            quality = self._calculate_quality(all_results)

            phases.append(SearchPhase(
                phase_num=iteration + 1,
                query=f"{initial_query} (targeted)",
                results=iteration_results,
                entities_extracted=new_entities,
                quality_score=quality
            ))

            logger.info(f"Iteration {iteration} complete: {len(iteration_results)} new results, quality: {quality:.2f}")

            # Stopping conditions
            if quality >= self.min_quality:
                logger.info(f"Quality threshold reached ({quality:.2f} >= {self.min_quality})")
                break

            if not new_entities:
                logger.info("No new entities discovered, stopping")
                break

            if iteration >= self.max_iterations:
                logger.info(f"Max iterations reached ({self.max_iterations})")
                break

            # Continue with newly discovered entities
            current_entities = new_entities
            iteration += 1

        # Collect all discovered entities
        all_entities = []
        for phase in phases:
            all_entities.extend(phase.entities_extracted)
        all_entities = list(set(all_entities))  # Deduplicate

        # Calculate final quality metrics
        quality_metrics = self._comprehensive_quality_check(all_results, all_entities)

        result = AdaptiveSearchResult(
            initial_query=initial_query,
            phases=phases,
            total_results=len(all_results),
            unique_results=len(seen_urls),
            entities_discovered=all_entities,
            quality_metrics=quality_metrics,
            iterations=len(phases),
            results=all_results  # NEW: Pass actual result objects for synthesis
        )

        logger.info(f"Adaptive search complete: {result.total_results} results, {result.iterations} phases, quality: {quality_metrics['overall_quality']:.2f}")

        return result

    async def _search_phase(
        self,
        query: str,
        limit: int,
        databases: Optional[List] = None,
        api_keys: Optional[Dict[str, str]] = None
    ) -> List[Dict]:
        """
        Execute single search phase across databases.

        Args:
            query: Search query
            limit: Results per database
            databases: Database integrations to search
            api_keys: API keys for databases

        Returns:
            List of result dictionaries
        """
        # Use ParallelExecutor.execute_all method
        # This returns a dict of {db_id: QueryResult}
        result_dict = await self.executor.execute_all(
            research_question=query,
            databases=databases or [],
            api_keys=api_keys or {},
            limit=limit
        )

        # Flatten results into single list
        all_results = []
        for db_id, query_result in result_dict.items():
            if query_result.success and query_result.results:
                all_results.extend(query_result.results)

        return all_results

    def _deduplicate(
        self,
        results: List[Dict],
        seen_urls: set
    ) -> List[Dict]:
        """
        Remove duplicate URLs, update seen set.

        Args:
            results: List of result dictionaries
            seen_urls: Set of URLs already seen (modified in place)

        Returns:
            List of unique results
        """
        unique = []
        for result in results:
            url = result.get('url', '')
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique.append(result)
        return unique

    async def _extract_entities(
        self,
        results: List[Dict],
        original_query: str
    ) -> List[str]:
        """
        Extract key entities from results for follow-up searches.

        Uses LLM to analyze results and find:
        - Related programs
        - Organizations
        - People
        - Concepts
        - Legal frameworks

        Args:
            results: List of search results
            original_query: Original search query for context

        Returns:
            List of entity strings
        """
        if not results:
            return []

        # Build analysis prompt
        results_text = "\n\n".join([
            f"**{r.get('title', 'Untitled')}**\n{r.get('description', '')}"
            for r in results[:5]  # Top 5
        ])

        prompt = f"""You are analyzing search results to discover related entities for deeper investigation.

Original query: "{original_query}"

Top results found:
{results_text}

Your task: Extract 3-5 key entities mentioned in these results that would make good follow-up searches.

Focus on:
- Related programs or operations
- Organizations or agencies involved
- Key people or officials
- Specific legal frameworks or policies
- Technical systems or capabilities

Return ONLY entities that are:
1. Directly related to the original query
2. Specific enough to search (not vague concepts)
3. Likely to find government documents

Return as JSON array of strings:
["entity1", "entity2", "entity3", ...]
"""

        try:
            response = await acompletion(
                model="gpt-5-mini",
                messages=[{"role": "user", "content": prompt}],
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "strict": True,
                        "name": "entity_extraction",
                        "schema": {
                            "type": "object",
                            "properties": {
                                "entities": {
                                    "type": "array",
                                    "items": {"type": "string"}
                                }
                            },
                            "required": ["entities"],
                            "additionalProperties": False
                        }
                    }
                }
            )

            result = json.loads(response.choices[0].message.content)
            entities = result.get("entities", [])

            logger.info(f"Extracted {len(entities)} entities: {entities}")
            return entities

        except Exception as e:
            logger.error(f"Entity extraction failed: {e}")
            return []

    def _calculate_quality(self, results: List[Dict]) -> float:
        """
        Calculate quality score for results.

        Factors:
        - Source diversity (more sources = better)
        - Result count (more = better, up to a point)
        - Relevance scores if available

        Args:
            results: List of search results

        Returns:
            Quality score from 0.0 to 1.0
        """
        if not results:
            return 0.0

        # Source diversity
        sources = set(r.get('source', 'unknown') for r in results)
        diversity_score = min(len(sources) / 4.0, 1.0)  # 4+ sources = max score

        # Result count (diminishing returns after 30)
        count_score = min(len(results) / 30.0, 1.0)

        # Average relevance if available
        relevances = [r.get('relevance_score', 5) for r in results if 'relevance_score' in r]
        if relevances:
            relevance_score = sum(relevances) / len(relevances) / 10.0
        else:
            relevance_score = 0.5  # Neutral

        # Weighted average
        quality = (diversity_score * 0.4) + (count_score * 0.3) + (relevance_score * 0.3)

        return quality

    def _comprehensive_quality_check(
        self,
        all_results: List[Dict],
        entities: List[str]
    ) -> Dict:
        """
        Mozart-style quality metrics.

        Args:
            all_results: All search results
            entities: All discovered entities

        Returns:
            Dictionary with quality metrics and warnings
        """
        if not all_results:
            return {
                "overall_quality": 0.0,
                "source_diversity": 0.0,
                "entity_discovery": 0,
                "warnings": ["No results found"]
            }

        # Source diversity
        sources = [r.get('source') for r in all_results]
        source_counts = {}
        for source in sources:
            source_counts[source] = source_counts.get(source, 0) + 1

        diversity = len(source_counts) / max(len(sources), 1)

        # Check for source dominance (Mozart pattern)
        max_source_pct = max(source_counts.values()) / len(sources) if sources else 0

        warnings = []
        if max_source_pct > 0.3:
            dominant_source = max(source_counts, key=source_counts.get)
            warnings.append(f"{dominant_source} dominates results ({max_source_pct:.0%})")

        if diversity < 0.5:
            warnings.append(f"Low source diversity ({diversity:.0%})")

        if len(entities) < 3:
            warnings.append(f"Few entities discovered ({len(entities)})")

        overall_quality = self._calculate_quality(all_results)

        return {
            "overall_quality": overall_quality,
            "source_diversity": diversity,
            "entity_discovery": len(entities),
            "result_count": len(all_results),
            "source_breakdown": source_counts,
            "warnings": warnings
        }
