# Adaptive Search Integration: Mozart → sam_gov

**Date**: 2025-10-20
**Focus**: Iterative, autonomous search that thinks and refines itself
**NOT**: Multi-LLM optimization (you already have litellm, keep gpt-5-mini for everything)

---

## What You Really Want

You want Mozart's **adaptive discovery loop**:

1. **Initial broad search** → Get initial results
2. **Analyze what was found** → Extract entities, patterns, gaps
3. **Refine and search again** → Target specific entities/gaps
4. **Keep iterating** → Until quality threshold met or max iterations reached
5. **Self-evaluate** → Did I find good stuff? Should I search more?

This is different from your current system which:
- Takes keywords → searches once → returns results
- No iteration, no self-reflection, no adaptive refinement

---

## Mozart's Adaptive Discovery (How It Actually Works)

### Phase 1: Broad Initial Search
```python
# From Mozart config.py
adaptive_phase1_count: int = 15  # Get 15 initial sources
```

**What happens**:
- Query: "FISA Section 702"
- Perplexity API: Returns 15 broad sources
- Brave Search: Adds web results
- **No filtering yet** - cast wide net

### Phase 2: Analyze Top Results
```python
adaptive_analysis_sources: int = 5  # Analyze top 5 deeply
```

**What happens**:
- Take top 5 results from Phase 1
- LLM analyzes them: "What entities/programs/people are mentioned?"
- Extract: ["NSA", "Prism program", "FISA court", "Edward Snowden", "Stellar Wind"]

### Phase 3: Targeted Follow-up Searches
```python
adaptive_phase2_queries: int = 4       # Do 4 targeted searches
adaptive_phase2_per_query: int = 10    # Get 10 sources each
```

**What happens**:
- For each extracted entity, search specifically:
  - "FISA Section 702 AND NSA"
  - "FISA Section 702 AND Prism program"
  - "FISA Section 702 AND FISA court"
  - "FISA Section 702 AND Edward Snowden"
- Each returns 10 more focused sources
- Total: 15 (phase 1) + 40 (phase 2) = 55 sources

### Phase 4: Quality Check & Retry
```python
min_source_utilization: float = 0.50   # Expect >=50% sources to be useful
max_single_source_pct: float = 0.15    # No source >15% of citations
citation_diversity_retry: bool = True  # Retry if imbalanced
```

**What happens**:
- Check: Did we use >=50% of sources?
- Check: Is one source dominating?
- If quality issues: **Go back to Phase 3 with different queries**
- Keep iterating until quality threshold met or max iterations

---

## Your Current System vs Adaptive

### Current (Boolean Monitor)
```python
# monitoring/boolean_monitor.py
keywords = ["FISA", "Section 702", "NSA surveillance"]
results = await parallel_executor.search_all_sources(keywords)
# Done. No iteration, no refinement.
```

**Problems**:
- Misses related entities (Prism, Stellar Wind, etc.)
- Doesn't adapt if results poor
- Can't discover connections (FISA → NSA → Prism)
- One-shot search, no intelligence

### Adaptive (What You Want)
```python
# monitoring/adaptive_monitor.py
initial_query = "FISA Section 702"

# Phase 1: Broad search
results_p1 = await search(initial_query)

# Phase 2: Analyze & extract entities
entities = await llm.extract_entities(results_p1[:5])
# Returns: ["NSA", "Prism", "FISA court", "Snowden", "Stellar Wind"]

# Phase 3: Targeted searches for each entity
for entity in entities:
    refined_query = f"{initial_query} AND {entity}"
    results_p3 = await search(refined_query)

# Phase 4: Check quality
if not quality_check_passed(all_results):
    # Iterate again with different approach
    entities_v2 = await llm.extract_different_angle(all_results)
    # ... repeat
```

**Benefits**:
- Discovers connections automatically
- Adapts based on what's found
- Keeps searching until quality threshold
- Autonomous and intelligent

---

## Integration Plan (Focused on Adaptive Search)

### Week 1: Build Adaptive Search Engine

**Goal**: Core adaptive loop that iterates and refines

**File**: `core/adaptive_search_engine.py`

```python
"""Adaptive search engine following Mozart pattern."""

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

class AdaptiveSearchEngine:
    """
    Autonomous search that iterates and refines itself.

    Based on Mozart's adaptive discovery pattern:
    1. Broad initial search
    2. Analyze top results for entities
    3. Targeted follow-up searches
    4. Quality check & retry if needed
    """

    def __init__(
        self,
        parallel_executor,  # Your existing ParallelExecutor
        phase1_count: int = 15,      # Initial broad results
        analyze_top_n: int = 5,       # Analyze top 5 for entities
        phase2_queries: int = 4,      # Follow-up searches per iteration
        phase2_per_query: int = 10,   # Results per follow-up
        max_iterations: int = 3,      # Max refinement iterations
        min_quality: float = 0.6,     # Min quality score to stop
    ):
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
        sources: List[str] = None
    ) -> AdaptiveSearchResult:
        """
        Execute adaptive search with iterative refinement.

        Args:
            initial_query: Starting search query (e.g., "FISA Section 702")
            sources: Which sources to search (defaults to all)

        Returns:
            Complete search results with all phases
        """
        phases = []
        all_results = []
        seen_urls = set()

        logger.info(f"Starting adaptive search: '{initial_query}'")

        # Phase 1: Broad initial search
        logger.info(f"Phase 1: Broad search ({self.phase1_count} results)")
        phase1_results = await self._search_phase(
            query=initial_query,
            limit=self.phase1_count,
            sources=sources
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
                    sources=sources
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
            iterations=len(phases)
        )

        logger.info(f"Adaptive search complete: {result.total_results} results, {result.iterations} phases, quality: {quality_metrics['overall_quality']:.2f}")

        return result

    async def _search_phase(
        self,
        query: str,
        limit: int,
        sources: Optional[List[str]] = None
    ) -> List[Dict]:
        """Execute single search phase across sources."""
        # Use your existing parallel executor
        results = await self.executor.execute_parallel_search(
            research_question=query,
            limit=limit,
            specific_sources=sources
        )
        return results

    def _deduplicate(
        self,
        results: List[Dict],
        seen_urls: set
    ) -> List[Dict]:
        """Remove duplicate URLs, update seen set."""
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
        """Mozart-style quality metrics."""
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
```

---

### Week 2: Integrate with Boolean Monitor

**Goal**: Replace static keyword search with adaptive search

**File**: `monitoring/adaptive_boolean_monitor.py`

```python
"""Boolean monitor with adaptive search."""

from monitoring.boolean_monitor import BooleanMonitor
from core.adaptive_search_engine import AdaptiveSearchEngine, AdaptiveSearchResult
from core.parallel_executor import ParallelExecutor
import logging

logger = logging.getLogger(__name__)

class AdaptiveBooleanMonitor(BooleanMonitor):
    """Boolean monitor that uses adaptive search instead of static keywords."""

    def __init__(self, config_path: str):
        super().__init__(config_path)

        # Create adaptive search engine
        self.adaptive_engine = AdaptiveSearchEngine(
            parallel_executor=ParallelExecutor(),
            phase1_count=15,         # Configurable
            analyze_top_n=5,
            phase2_queries=4,
            phase2_per_query=10,
            max_iterations=3,
            min_quality=0.6
        )

        # Track adaptive history
        self.search_history = []

    async def execute_search(self, keywords: List[str]) -> List[Dict]:
        """
        Execute adaptive search instead of simple keyword search.

        For each keyword, run adaptive search that iterates and refines.
        """
        all_results = []

        for keyword in keywords:
            logger.info(f"Starting adaptive search for: {keyword}")

            # Run adaptive search (autonomous iteration)
            adaptive_result = await self.adaptive_engine.adaptive_search(
                initial_query=keyword,
                sources=self.config.sources  # Use configured sources
            )

            # Log what was discovered
            logger.info(f"Adaptive search complete for '{keyword}':")
            logger.info(f"  - {adaptive_result.total_results} results")
            logger.info(f"  - {adaptive_result.iterations} phases")
            logger.info(f"  - {len(adaptive_result.entities_discovered)} entities discovered")
            logger.info(f"  - Quality: {adaptive_result.quality_metrics['overall_quality']:.2f}")

            # Add all phase results
            for phase in adaptive_result.phases:
                all_results.extend(phase.results)

            # Store search history for analysis
            self.search_history.append({
                'keyword': keyword,
                'adaptive_result': adaptive_result,
                'timestamp': datetime.now()
            })

        return all_results

    async def send_alert(self, new_results: List[Dict], **kwargs):
        """Enhanced alert with adaptive search insights."""

        # Include adaptive search insights in email
        adaptive_insights = self._build_adaptive_insights()

        await super().send_alert(
            new_results,
            adaptive_insights=adaptive_insights,
            **kwargs
        )

    def _build_adaptive_insights(self) -> Dict:
        """Build insights from adaptive search history."""
        if not self.search_history:
            return {}

        # Aggregate across all keyword searches
        total_phases = sum(
            s['adaptive_result'].iterations
            for s in self.search_history
        )

        all_entities = []
        for s in self.search_history:
            all_entities.extend(s['adaptive_result'].entities_discovered)
        unique_entities = list(set(all_entities))

        avg_quality = sum(
            s['adaptive_result'].quality_metrics['overall_quality']
            for s in self.search_history
        ) / len(self.search_history)

        return {
            'keywords_searched': len(self.search_history),
            'total_phases_executed': total_phases,
            'entities_discovered': unique_entities,
            'average_quality': avg_quality,
            'search_details': [
                {
                    'keyword': s['keyword'],
                    'iterations': s['adaptive_result'].iterations,
                    'results_found': s['adaptive_result'].total_results,
                    'quality': s['adaptive_result'].quality_metrics['overall_quality']
                }
                for s in self.search_history
            ]
        }
```

**Update email template** to show adaptive insights:

```html
<!-- Add to monitoring/email_template.html -->

{% if adaptive_insights %}
<div style="background: #e3f2fd; padding: 15px; margin: 20px 0; border-radius: 5px;">
    <h3>🔍 Adaptive Search Insights</h3>

    <p><strong>Search Intelligence:</strong></p>
    <ul>
        <li><strong>Keywords searched:</strong> {{ adaptive_insights.keywords_searched }}</li>
        <li><strong>Search phases executed:</strong> {{ adaptive_insights.total_phases_executed }}</li>
        <li><strong>Average quality:</strong> {{ "%.1f"|format(adaptive_insights.average_quality * 10) }}/10</li>
    </ul>

    {% if adaptive_insights.entities_discovered %}
    <p><strong>Entities Discovered:</strong></p>
    <div style="background: white; padding: 10px; border-radius: 3px;">
        {% for entity in adaptive_insights.entities_discovered[:10] %}
            <span style="background: #64b5f6; color: white; padding: 4px 8px; margin: 2px; border-radius: 3px; display: inline-block;">{{ entity }}</span>
        {% endfor %}
    </div>
    {% endif %}

    <details style="margin-top: 10px;">
        <summary><strong>Search Details</strong> (click to expand)</summary>
        <table style="width: 100%; margin-top: 10px; border-collapse: collapse;">
            <tr style="background: #f5f5f5;">
                <th style="padding: 8px; text-align: left;">Keyword</th>
                <th style="padding: 8px; text-align: left;">Iterations</th>
                <th style="padding: 8px; text-align: left;">Results</th>
                <th style="padding: 8px; text-align: left;">Quality</th>
            </tr>
            {% for detail in adaptive_insights.search_details %}
            <tr>
                <td style="padding: 8px;">{{ detail.keyword }}</td>
                <td style="padding: 8px;">{{ detail.iterations }}</td>
                <td style="padding: 8px;">{{ detail.results_found }}</td>
                <td style="padding: 8px;">{{ "%.1f"|format(detail.quality * 10) }}/10</td>
            </tr>
            {% endfor %}
        </table>
    </details>
</div>
{% endif %}
```

---

### Week 3: Add Web Search Integration

**Goal**: Integrate internet search (Brave/Perplexity) for deeper research

**File**: `integrations/web/brave_search.py`

```python
"""Brave Search integration for web research."""

from core.database_integration_base import DatabaseIntegration, DatabaseMetadata, QueryResult
import httpx
import os
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

class BraveSearchIntegration(DatabaseIntegration):
    """
    Brave Search API integration.

    Free tier: 2,000 queries/month
    Paid: $5/month for 20,000 queries
    """

    @property
    def metadata(self) -> DatabaseMetadata:
        return DatabaseMetadata(
            name="Brave Search",
            description="Web search via Brave Search API",
            source_type="web",
            requires_key=True,
            rate_limit="2000/month (free tier)",
            relevance_keywords=[]  # Relevant for everything
        )

    async def is_relevant(self, research_question: str) -> bool:
        """Always relevant - it's general web search."""
        return True

    async def generate_query(self, research_question: str) -> Optional[Dict]:
        """
        Generate Brave Search query.

        Brave API is simple: just pass the search string.
        """
        return {
            "q": research_question,
            "count": 20,  # Results per page
            "freshness": "py"  # Past year (or "pm" for month, "pw" for week)
        }

    async def execute_search(
        self,
        query_params: Dict,
        api_key: str,
        limit: int = 100
    ) -> QueryResult:
        """Execute Brave Search."""

        url = "https://api.search.brave.com/res/v1/web/search"

        headers = {
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "X-Subscription-Token": api_key
        }

        params = {
            "q": query_params["q"],
            "count": min(query_params.get("count", 20), 20),  # Max 20 per request
            "freshness": query_params.get("freshness", "py")
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=params)
                response.raise_for_status()
                data = response.json()

            # Parse results
            results = []
            for item in data.get("web", {}).get("results", [])[:limit]:
                results.append({
                    "title": item.get("title", ""),
                    "description": item.get("description", ""),
                    "url": item.get("url", ""),
                    "age": item.get("age", ""),  # "1 day ago", etc.
                    "source": "Brave Search"
                })

            logger.info(f"Brave Search returned {len(results)} results")

            return QueryResult(
                source=self.metadata.name,
                query=query_params,
                results=results,
                total_results=len(results),
                metadata={"api": "Brave Search v1"}
            )

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                logger.error("Brave Search rate limit exceeded")
                return QueryResult(
                    source=self.metadata.name,
                    query=query_params,
                    results=[],
                    total_results=0,
                    error="Rate limit exceeded"
                )
            raise
        except Exception as e:
            logger.error(f"Brave Search failed: {e}")
            raise
```

**Register in `integrations/registry.py`**:
```python
from integrations.web.brave_search import BraveSearchIntegration

AVAILABLE_INTEGRATIONS = {
    # ... existing government sources ...
    "brave_search": BraveSearchIntegration,
}
```

**Add to `.env`**:
```bash
# Web search (optional - for adaptive discovery)
BRAVE_SEARCH_API_KEY="your-key-here"  # Get from https://brave.com/search/api/
```

**Enable in monitor config**:
```yaml
# data/monitors/configs/surveillance_fisa_monitor.yaml
name: "Surveillance & FISA Programs"
keywords:
  - "FISA Section 702"
  - "NSA surveillance programs"
sources:
  - sam_gov
  - dvids
  - usajobs
  - federal_register
  - brave_search  # NEW - adds web search
adaptive_search: true  # Enable iterative refinement
adaptive_config:
  phase1_count: 15
  analyze_top_n: 5
  phase2_queries: 4
  max_iterations: 3
  min_quality: 0.6
```

---

## Testing the Adaptive System

### Test 1: Single Keyword Adaptive Search
```bash
python3 -c "
import asyncio
from core.adaptive_search_engine import AdaptiveSearchEngine
from core.parallel_executor import ParallelExecutor

async def test():
    engine = AdaptiveSearchEngine(
        parallel_executor=ParallelExecutor(),
        phase1_count=10,
        phase2_queries=3,
        max_iterations=2
    )

    result = await engine.adaptive_search('FISA Section 702')

    print(f'Total results: {result.total_results}')
    print(f'Phases: {result.iterations}')
    print(f'Entities discovered: {result.entities_discovered}')
    print(f'Quality: {result.quality_metrics[\"overall_quality\"]:.2f}')

    for phase in result.phases:
        print(f'  Phase {phase.phase_num}: {len(phase.results)} results, entities: {phase.entities_extracted}')

asyncio.run(test())
"
```

**Expected output**:
```
Phase 1: Broad search (10 results)
Extracted 5 entities: ['NSA', 'Prism program', 'FISA court', 'Edward Snowden', 'Stellar Wind']
Phase 1 complete: 10 results, extracted 5 entities
Iteration 1: Targeted searches for 3 entities
  Searching: FISA Section 702 AND NSA
  Searching: FISA Section 702 AND Prism program
  Searching: FISA Section 702 AND FISA court
Iteration 1 complete: 24 new results, quality: 0.75
Quality threshold reached (0.75 >= 0.60)
Adaptive search complete: 34 results, 2 phases, quality: 0.75

Total results: 34
Phases: 2
Entities discovered: ['NSA', 'Prism program', 'FISA court', 'Edward Snowden', 'Stellar Wind', 'William Barr', 'FISA Amendments Act']
Quality: 0.75
  Phase 1: 10 results, entities: ['NSA', 'Prism program', 'FISA court', 'Edward Snowden', 'Stellar Wind']
  Phase 2: 24 results, entities: ['William Barr', 'FISA Amendments Act']
```

### Test 2: Adaptive Monitor Run
```bash
# Run adaptive monitor (dry-run, don't send email)
python3 -c "
import asyncio
from monitoring.adaptive_boolean_monitor import AdaptiveBooleanMonitor

async def test():
    monitor = AdaptiveBooleanMonitor('data/monitors/configs/surveillance_fisa_monitor.yaml')
    await monitor.run()

asyncio.run(test())
"
```

**Check logs** for:
- Multiple search phases executed
- Entities extracted between phases
- Quality scores improving
- Warnings if quality thresholds not met

---

## Configuration Options

### Adaptive Search Tuning

**File**: `data/monitors/configs/your_monitor.yaml`

```yaml
name: "Your Monitor"
keywords:
  - "keyword1"
  - "keyword2"

# Enable adaptive search
adaptive_search: true

# Adaptive configuration (optional, these are defaults)
adaptive_config:
  phase1_count: 15          # Initial broad results
  analyze_top_n: 5          # Analyze top N for entities
  phase2_queries: 4         # Follow-up searches per iteration
  phase2_per_query: 10      # Results per follow-up search
  max_iterations: 3         # Max refinement cycles
  min_quality: 0.6          # Stop if quality >= this (0-1 scale)

  # Quality thresholds (Mozart pattern)
  min_source_diversity: 0.5   # Require 50%+ sources used
  max_source_dominance: 0.3   # No source >30% of results
```

**Tuning for different use cases**:

**Fast/Cheap** (fewer iterations):
```yaml
adaptive_config:
  phase1_count: 10
  phase2_queries: 2
  max_iterations: 1
  min_quality: 0.5
```

**Deep Research** (thorough investigation):
```yaml
adaptive_config:
  phase1_count: 20
  phase2_queries: 6
  max_iterations: 5
  min_quality: 0.8
```

**Balanced** (default recommended):
```yaml
adaptive_config:
  phase1_count: 15
  phase2_queries: 4
  max_iterations: 3
  min_quality: 0.6
```

---

## What You Get

### Before (Static Keywords)
```
Query: "FISA Section 702"
→ Search SAM.gov, DVIDS, USAJobs once
→ Get 12 results
→ Done
```

**Problems**: Misses Prism, Stellar Wind, related programs

### After (Adaptive Search)
```
Phase 1: "FISA Section 702"
→ Get 15 broad results
→ Analyze top 5: Extract ["NSA", "Prism", "FISA court", "Snowden"]

Phase 2: Targeted searches
→ "FISA Section 702 AND NSA" → 10 results
→ "FISA Section 702 AND Prism" → 10 results
→ "FISA Section 702 AND FISA court" → 10 results
→ Analyze: Extract ["Stellar Wind", "William Barr"]

Phase 3: More targeted searches
→ "FISA Section 702 AND Stellar Wind" → 8 results
→ "FISA Section 702 AND William Barr" → 6 results

Quality check: 0.75 >= 0.60 ✓ Stop

Total: 59 results, 3 phases, discovered 6 related entities
```

**Result**: Found Prism, Stellar Wind, and connections automatically

---

## Integration with Wiki (Future)

Once you have adaptive search working, you can:

1. **Feed discovered entities to knowledge graph**:
   - Adaptive search discovers: ["NSA", "Prism program", "FISA court"]
   - Create Wikibase items for each
   - Link relationships: FISA Section 702 → involves → NSA → operates → Prism

2. **Use knowledge graph to seed searches**:
   - Query Wikibase: "What programs are related to NSA surveillance?"
   - Get: [Prism, Stellar Wind, XKeyscore]
   - Feed back to adaptive search for deeper investigation

3. **Close the loop** (autonomous research cycle):
   ```
   Search → Discover entities → Store in graph → Query graph → Search deeper → ...
   ```

**This is what makes it truly autonomous** - it doesn't just search, it learns and refines continuously.

---

## Summary: What You're Building

**Autonomous Adaptive Research System**:

1. **Iterative Discovery**: Searches → Analyzes → Refines → Searches again
2. **Entity Extraction**: Discovers related programs/people/concepts automatically
3. **Quality-Driven**: Keeps searching until quality threshold met
4. **Self-Evaluating**: Knows when it found good stuff vs when to keep looking
5. **Web + Database**: Combines government databases + web search
6. **Intelligence Growth**: Discovers connections you didn't know to search for

**NOT just**:
- Keyword search (static, one-shot)
- Boolean monitoring (no iteration)
- Manual research (you decide what to search)

**Instead**:
- Autonomous agent that thinks and refines
- Discovers connections automatically
- Keeps searching until confident it found good stuff

---

## Next Steps

1. **Week 1**: Build `AdaptiveSearchEngine` core (iteration logic)
2. **Week 2**: Integrate with `AdaptiveBooleanMonitor` (replace static search)
3. **Week 3**: Add Brave Search (web research capability)
4. **Week 4**: Test with production monitors, tune quality thresholds

**Total time**: 2-4 weeks part-time

**Key files**:
- `core/adaptive_search_engine.py` - Core iteration logic
- `monitoring/adaptive_boolean_monitor.py` - Integration with monitors
- `integrations/web/brave_search.py` - Web search capability

---

**Last Updated**: 2025-10-20
**Focus**: Iterative, autonomous search (NOT multi-LLM optimization)
**Owner**: Brian
