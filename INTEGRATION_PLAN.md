# Integration Plan: UFO Wiki Techniques → SigInt Platform

**Date**: 2025-10-20
**Purpose**: Integrate valuable Mozart/Wikibase patterns into sam_gov monitoring platform
**Scope**: 4 key techniques + optional Wikibase integration

---

## Executive Summary

**What we're integrating**:
1. Multi-LLM pipeline (cost optimization + speed)
2. Quality control metrics (prevent false positives)
3. API caching strategy (speed + cost savings)
4. Adaptive discovery (better results)

**What we're NOT integrating** (yet):
- Docker complexity (overkill for current scale)
- Full Wikibase stack (only if we add knowledge graph)

**Timeline**: 2-4 weeks part-time
**Estimated cost reduction**: 40-60% on LLM costs
**Performance improvement**: 2-3x faster searches

---

## Phase 1: Multi-LLM Pipeline (Week 1)

### Current State
```python
# sam_gov uses GPT-5-mini for everything
from llm_utils import acompletion

# Query generation
query = await acompletion(model="gpt-5-mini", messages=[...])

# Relevance scoring
score = await acompletion(model="gpt-5-mini", messages=[...])

# Summary generation
summary = await acompletion(model="gpt-5-mini", messages=[...])
```

**Cost**: ~$0.10-0.30 per monitor run
**Speed**: 30-60 seconds total

### Target State (Mozart Pattern)
```python
# Use different LLMs for different tasks
from utils.llm_pipeline import LLMPipeline

pipeline = LLMPipeline()

# Fast/cheap for simple tasks
query = await pipeline.generate_query(
    model="gpt-5-nano",  # Cheapest
    task="boolean_query"
)

# Good at structured extraction
entities = await pipeline.extract(
    model="gemini-2.5-flash",  # Free tier
    task="entity_extraction",
    data=results
)

# Expensive but high quality for final analysis
summary = await pipeline.synthesize(
    model="claude-sonnet-4",  # Best quality
    task="relevance_scoring",
    data=entities
)
```

**Expected cost**: ~$0.04-0.12 per monitor run (60% reduction)
**Expected speed**: 15-30 seconds (2x faster)

### Implementation Plan

**Step 1: Create LLM Pipeline Utility**

File: `utils/llm_pipeline.py`
```python
"""Multi-LLM pipeline following Mozart pattern."""

from typing import Literal, Dict, Any
from llm_utils import acompletion
import google.generativeai as genai
from anthropic import AsyncAnthropic

TaskType = Literal["query_generation", "entity_extraction", "relevance_scoring", "summarization"]

class LLMPipeline:
    """Route tasks to optimal LLM based on cost/quality tradeoffs."""

    def __init__(self):
        self.anthropic = AsyncAnthropic()
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

        # Task → Model mapping (Mozart pattern)
        self.routing = {
            "query_generation": "gpt-5-nano",      # Simple, cheap
            "entity_extraction": "gemini-2.5-flash",  # Free, good at structured data
            "relevance_scoring": "claude-sonnet-4",   # Expensive, high quality
            "summarization": "gemini-2.5-flash",   # Free, good enough
        }

    async def execute(self, task: TaskType, prompt: str, **kwargs) -> str:
        """Route task to optimal model."""
        model = self.routing[task]

        if model.startswith("gemini"):
            return await self._gemini(model, prompt, **kwargs)
        elif model.startswith("claude"):
            return await self._claude(model, prompt, **kwargs)
        else:
            return await self._openai(model, prompt, **kwargs)

    async def _gemini(self, model: str, prompt: str, **kwargs):
        """Execute via Gemini (free tier)."""
        model = genai.GenerativeModel(model)
        response = await model.generate_content_async(prompt)
        return response.text

    async def _claude(self, model: str, prompt: str, **kwargs):
        """Execute via Claude (high quality)."""
        message = await self.anthropic.messages.create(
            model=model,
            max_tokens=kwargs.get("max_tokens", 1000),
            messages=[{"role": "user", "content": prompt}]
        )
        return message.content[0].text

    async def _openai(self, model: str, prompt: str, **kwargs):
        """Execute via OpenAI (existing pattern)."""
        response = await acompletion(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            **kwargs
        )
        return response.choices[0].message.content
```

**Step 2: Update Boolean Monitor**

File: `monitoring/boolean_monitor.py`
```python
from utils.llm_pipeline import LLMPipeline

class BooleanMonitor:
    def __init__(self, config_path: str):
        # ... existing code ...
        self.llm = LLMPipeline()  # NEW

    async def score_relevance(self, result: Dict, keywords: List[str]) -> int:
        """Score using Claude Sonnet (high quality)."""
        prompt = f"""Score relevance 0-10 for this result.
        Keywords: {keywords}
        Title: {result['title']}
        Description: {result['description']}
        """

        # Use Claude for quality-critical task
        score_text = await self.llm.execute(
            task="relevance_scoring",
            prompt=prompt
        )
        return int(score_text.strip())

    async def extract_entities(self, results: List[Dict]) -> Dict:
        """Extract entities using Gemini (free, good at extraction)."""
        prompt = f"""Extract key entities from these results:
        {json.dumps(results[:5])}

        Return JSON:
        {{
            "people": [...],
            "organizations": [...],
            "programs": [...],
            "locations": [...]
        }}
        """

        # Use Gemini for structured extraction
        entities_json = await self.llm.execute(
            task="entity_extraction",
            prompt=prompt
        )
        return json.loads(entities_json)
```

**Step 3: Add API Keys**

File: `.env`
```bash
# Existing
OPENAI_API_KEY=sk-...

# New
GEMINI_API_KEY=AIzaSy...        # Free tier: 50 requests/day
ANTHROPIC_API_KEY=sk-ant-...    # $15-20/month usage-based
```

**Testing**:
```bash
# Test multi-LLM pipeline
python3 -c "
import asyncio
from utils.llm_pipeline import LLMPipeline

async def test():
    llm = LLMPipeline()

    # Test Gemini (free)
    entities = await llm.execute('entity_extraction', 'Extract from: FISA Section 702')
    print(f'Gemini: {entities}')

    # Test Claude (quality)
    score = await llm.execute('relevance_scoring', 'Score: NSA surveillance')
    print(f'Claude: {score}')

asyncio.run(test())
"
```

**Success Criteria**:
- [ ] Multi-LLM pipeline working
- [ ] 40%+ cost reduction vs all-GPT-5
- [ ] Quality maintained (relevance scores accurate)
- [ ] Speed improved 2x

---

## Phase 2: Quality Control Metrics (Week 2)

### Current State
```python
# Basic relevance filtering (≥6 threshold)
if relevance_score >= 6:
    alert_results.append(result)
```

**Problem**: No metrics on monitor health, source diversity, or result quality

### Target State (Mozart Pattern)
```python
# Comprehensive quality metrics
class QualityMetrics:
    min_source_utilization: float = 0.50      # ≥50% of sources used
    max_single_source_dominance: float = 0.30  # No source >30% of results
    min_results_per_keyword: int = 2          # Each keyword finds ≥2 results
    citation_diversity_retry: bool = True     # Retry if imbalanced

    def check(self, results: List[Dict]) -> QualityReport:
        """Validate result quality."""
        # Check source diversity
        # Check keyword distribution
        # Check relevance score distribution
        # Return pass/fail + recommendations
```

### Implementation Plan

**Step 1: Create Quality Metrics Module**

File: `monitoring/quality_metrics.py`
```python
"""Quality control metrics following Mozart pattern."""

from dataclasses import dataclass
from typing import List, Dict
from collections import Counter

@dataclass
class QualityReport:
    """Quality metrics for monitor run."""
    passed: bool
    warnings: List[str]
    metrics: Dict[str, float]
    recommendations: List[str]

class QualityMetrics:
    """Validate monitor result quality."""

    def __init__(self):
        # Thresholds (Mozart pattern)
        self.min_source_utilization = 0.50      # ≥50% of sources return results
        self.max_single_source_dominance = 0.30  # No source >30% of results
        self.min_results_per_keyword = 2         # Each keyword ≥2 results
        self.min_relevance_avg = 7.0             # Avg relevance ≥7
        self.max_duplicate_pct = 0.15            # ≤15% duplicates

    def check(self, results: List[Dict], keywords: List[str], sources: List[str]) -> QualityReport:
        """Comprehensive quality check."""
        warnings = []
        recommendations = []

        # 1. Source diversity
        source_counts = Counter([r['source'] for r in results])
        total = len(results)

        for source, count in source_counts.items():
            pct = count / total
            if pct > self.max_single_source_dominance:
                warnings.append(f"{source} dominates results ({pct:.0%})")
                recommendations.append(f"Adjust {source} queries or add more sources")

        # 2. Source utilization
        sources_used = len(source_counts)
        utilization = sources_used / len(sources)
        if utilization < self.min_source_utilization:
            warnings.append(f"Low source utilization ({utilization:.0%})")
            recommendations.append("Check API connectivity or query relevance")

        # 3. Keyword coverage
        keyword_counts = Counter()
        for r in results:
            for kw in r.get('matched_keywords', []):
                keyword_counts[kw] += 1

        for kw in keywords:
            count = keyword_counts.get(kw, 0)
            if count < self.min_results_per_keyword:
                warnings.append(f"Keyword '{kw}' only found {count} results")
                recommendations.append(f"Consider broader query for '{kw}'")

        # 4. Relevance quality
        if results:
            avg_relevance = sum(r.get('relevance_score', 0) for r in results) / len(results)
            if avg_relevance < self.min_relevance_avg:
                warnings.append(f"Low average relevance ({avg_relevance:.1f}/10)")
                recommendations.append("Refine keywords or adjust scoring threshold")

        # 5. Duplicate detection
        urls = [r['url'] for r in results]
        duplicates = len(urls) - len(set(urls))
        dup_pct = duplicates / len(urls) if urls else 0
        if dup_pct > self.max_duplicate_pct:
            warnings.append(f"High duplicate rate ({dup_pct:.0%})")
            recommendations.append("Check deduplication logic")

        return QualityReport(
            passed=len(warnings) == 0,
            warnings=warnings,
            metrics={
                "source_utilization": utilization,
                "avg_relevance": avg_relevance if results else 0,
                "duplicate_pct": dup_pct,
                "results_per_keyword": sum(keyword_counts.values()) / len(keywords) if keywords else 0
            },
            recommendations=recommendations
        )
```

**Step 2: Integrate with Monitor**

File: `monitoring/boolean_monitor.py`
```python
from monitoring.quality_metrics import QualityMetrics, QualityReport

class BooleanMonitor:
    def __init__(self, config_path: str):
        # ... existing code ...
        self.quality = QualityMetrics()  # NEW

    async def run(self):
        """Execute monitor with quality checks."""
        results = await self.execute_search(self.config.keywords)
        new_results = self.check_for_new_results(results)

        # NEW: Quality check
        report = self.quality.check(
            results=new_results,
            keywords=self.config.keywords,
            sources=self.get_active_sources()
        )

        # Log quality metrics
        logger.info(f"Quality metrics: {report.metrics}")

        if not report.passed:
            logger.warning(f"Quality warnings: {report.warnings}")

            # Include in email alert
            self.quality_warnings = report.warnings
            self.quality_recommendations = report.recommendations

        # Send alert with quality report
        await self.send_alert(new_results, quality_report=report)
```

**Step 3: Update Email Template**

File: `monitoring/email_template.html` (add section)
```html
<!-- NEW: Quality Report Section -->
{% if quality_report and quality_report.warnings %}
<div style="background: #fff3cd; padding: 15px; margin: 20px 0; border-radius: 5px;">
    <h3>⚠️ Quality Warnings</h3>
    <ul>
    {% for warning in quality_report.warnings %}
        <li>{{ warning }}</li>
    {% endfor %}
    </ul>

    <h4>Recommendations:</h4>
    <ul>
    {% for rec in quality_report.recommendations %}
        <li>{{ rec }}</li>
    {% endfor %}
    </ul>
</div>
{% endif %}

<!-- Quality Metrics -->
<div style="background: #f8f9fa; padding: 10px; margin: 10px 0;">
    <strong>Metrics:</strong>
    Source Utilization: {{ "%.0f"|format(quality_report.metrics.source_utilization * 100) }}% |
    Avg Relevance: {{ "%.1f"|format(quality_report.metrics.avg_relevance) }}/10 |
    Results/Keyword: {{ "%.1f"|format(quality_report.metrics.results_per_keyword) }}
</div>
```

**Testing**:
```bash
# Test quality metrics
python3 -c "
from monitoring.quality_metrics import QualityMetrics

qm = QualityMetrics()

# Simulate imbalanced results (one source dominates)
results = [
    {'source': 'SAM.gov', 'url': 'url1', 'matched_keywords': ['FISA'], 'relevance_score': 8},
    {'source': 'SAM.gov', 'url': 'url2', 'matched_keywords': ['FISA'], 'relevance_score': 7},
    {'source': 'SAM.gov', 'url': 'url3', 'matched_keywords': ['NSA'], 'relevance_score': 9},
    {'source': 'DVIDS', 'url': 'url4', 'matched_keywords': ['Section 702'], 'relevance_score': 6},
]

report = qm.check(results, keywords=['FISA', 'NSA', 'Section 702'], sources=['SAM.gov', 'DVIDS', 'USAJobs'])
print(f'Passed: {report.passed}')
print(f'Warnings: {report.warnings}')
print(f'Metrics: {report.metrics}')
"
```

**Success Criteria**:
- [ ] Quality metrics working
- [ ] Warnings shown in email alerts
- [ ] Catches imbalanced sources
- [ ] Detects low keyword coverage

---

## Phase 3: API Caching Strategy (Week 3)

### Current State
```python
# No caching - every monitor run hits APIs fresh
results = await database_integration.execute_search(query)
```

**Problem**: Wastes API calls, slow, expensive

### Target State (Mozart Pattern)
```python
# 7-day cache for search results
cache_key = hashlib.sha256(query.encode()).hexdigest()

if cache.exists(cache_key) and cache.age(cache_key) < CACHE_TTL:
    return cache.get(cache_key)
else:
    results = await database_integration.execute_search(query)
    cache.set(cache_key, results, ttl=CACHE_TTL)
    return results
```

### Implementation Plan

**Step 1: Create Cache Utility**

File: `utils/search_cache.py`
```python
"""Search result caching following Mozart pattern."""

import json
import hashlib
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

class SearchCache:
    """Cache search results to avoid redundant API calls."""

    def __init__(self, cache_dir: str = ".cache/searches", ttl_hours: int = 168):  # 7 days
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.ttl = timedelta(hours=ttl_hours)

    def _get_cache_path(self, cache_key: str) -> Path:
        """Get cache file path for key."""
        return self.cache_dir / f"{cache_key}.json"

    def _generate_key(self, source: str, query: Dict) -> str:
        """Generate cache key from source + query."""
        key_str = f"{source}:{json.dumps(query, sort_keys=True)}"
        return hashlib.sha256(key_str.encode()).hexdigest()

    def get(self, source: str, query: Dict) -> Optional[Dict]:
        """Get cached results if fresh."""
        cache_key = self._generate_key(source, query)
        cache_path = self._get_cache_path(cache_key)

        if not cache_path.exists():
            return None

        # Check age
        mtime = datetime.fromtimestamp(cache_path.stat().st_mtime)
        age = datetime.now() - mtime

        if age > self.ttl:
            # Expired, delete
            cache_path.unlink()
            return None

        # Load and return
        with cache_path.open('r') as f:
            cached = json.load(f)
            cached['_from_cache'] = True
            cached['_cache_age_hours'] = age.total_seconds() / 3600
            return cached

    def set(self, source: str, query: Dict, results: Dict) -> None:
        """Cache results."""
        cache_key = self._generate_key(source, query)
        cache_path = self._get_cache_path(cache_key)

        with cache_path.open('w') as f:
            json.dump({
                'source': source,
                'query': query,
                'results': results,
                'cached_at': datetime.now().isoformat()
            }, f, indent=2)

    def clear_old(self) -> int:
        """Clear expired cache entries."""
        cleared = 0
        for cache_file in self.cache_dir.glob("*.json"):
            mtime = datetime.fromtimestamp(cache_file.stat().st_mtime)
            age = datetime.now() - mtime
            if age > self.ttl:
                cache_file.unlink()
                cleared += 1
        return cleared
```

**Step 2: Integrate with Database Base Class**

File: `core/database_integration_base.py`
```python
from utils.search_cache import SearchCache

class DatabaseIntegration(ABC):
    def __init__(self):
        self.cache = SearchCache()  # NEW

    async def execute_search(self, query_params, api_key, limit=100) -> QueryResult:
        """Execute search with caching."""

        # Check cache first
        cached = self.cache.get(source=self.metadata.name, query=query_params)
        if cached:
            logger.info(f"Cache hit for {self.metadata.name} (age: {cached['_cache_age_hours']:.1f}h)")
            return QueryResult(
                source=self.metadata.name,
                query=query_params,
                results=cached['results'],
                total_results=len(cached['results']),
                from_cache=True
            )

        # Cache miss - execute actual search
        logger.info(f"Cache miss for {self.metadata.name}, executing search")
        result = await self._execute_search_impl(query_params, api_key, limit)

        # Cache result
        self.cache.set(
            source=self.metadata.name,
            query=query_params,
            results=result.dict()
        )

        return result

    @abstractmethod
    async def _execute_search_impl(self, query_params, api_key, limit) -> QueryResult:
        """Actual search implementation (to be overridden)."""
        pass
```

**Step 3: Update Monitor Logging**

File: `monitoring/boolean_monitor.py`
```python
async def execute_search(self, keywords: List[str]) -> List[Dict]:
    """Execute searches with cache tracking."""
    # ... existing parallel search code ...

    # Track cache hits
    cache_hits = sum(1 for r in all_results if r.get('from_cache'))
    cache_rate = cache_hits / len(all_results) if all_results else 0

    logger.info(f"Search complete: {len(all_results)} results, {cache_rate:.0%} from cache")

    # Include in email
    self.cache_stats = {
        'total_queries': len(all_results),
        'cache_hits': cache_hits,
        'cache_rate': cache_rate
    }
```

**Testing**:
```bash
# Test caching
python3 -c "
import asyncio
from utils.search_cache import SearchCache

cache = SearchCache()

# Simulate search
source = 'SAM.gov'
query = {'keywords': 'FISA', 'limit': 10}
results = {'count': 5, 'items': ['result1', 'result2']}

# First call - cache miss
print('First call:')
cached = cache.get(source, query)
print(f'  Cached: {cached is not None}')

# Store
cache.set(source, query, results)

# Second call - cache hit
print('Second call:')
cached = cache.get(source, query)
print(f'  Cached: {cached is not None}')
print(f'  Age: {cached[\"_cache_age_hours\"]:.2f}h')
"
```

**Success Criteria**:
- [ ] Cache working for all integrations
- [ ] 50%+ cache hit rate after first run
- [ ] Search speed 5-10x faster on cached results
- [ ] API costs reduced 50%+

---

## Phase 4: Adaptive Discovery (Week 4)

### Current State
```python
# Static keyword search
keywords = ["FISA", "Section 702", "NSA surveillance"]
results = await search_all_sources(keywords)
```

**Problem**: Misses related entities, limited discovery

### Target State (Mozart Pattern)
```python
# Phase 1: Broad search
initial_results = await search(keywords)

# Phase 2: Extract entities
entities = await llm.extract_entities(initial_results[:5])
# Returns: ["Section 702", "NSA", "FISA court", "Prism program"]

# Phase 3: Targeted searches
for entity in entities:
    refined_results = await search(f"{keyword} AND {entity}")
```

### Implementation Plan

**Step 1: Create Adaptive Discovery Module**

File: `monitoring/adaptive_discovery.py`
```python
"""Adaptive discovery following Mozart pattern."""

from typing import List, Dict
from utils.llm_pipeline import LLMPipeline

class AdaptiveDiscovery:
    """Multi-phase search with entity extraction."""

    def __init__(self):
        self.llm = LLMPipeline()
        self.phase1_results = 5      # Analyze top 5 from initial search
        self.phase2_queries = 3      # Generate 3 follow-up queries

    async def discover(self, initial_keywords: List[str], search_fn) -> List[Dict]:
        """Execute adaptive discovery."""
        all_results = []

        # Phase 1: Broad search
        logger.info(f"Phase 1: Searching {len(initial_keywords)} keywords")
        phase1_results = await search_fn(initial_keywords)
        all_results.extend(phase1_results)

        if not phase1_results:
            return all_results

        # Phase 2: Extract entities from top results
        logger.info(f"Phase 2: Analyzing top {self.phase1_results} results")
        top_results = sorted(phase1_results, key=lambda x: x.get('relevance_score', 0), reverse=True)[:self.phase1_results]

        entities = await self._extract_entities(top_results, initial_keywords)
        logger.info(f"Extracted entities: {entities}")

        # Phase 3: Targeted follow-up searches
        logger.info(f"Phase 3: Executing {len(entities[:self.phase2_queries])} targeted searches")
        for entity in entities[:self.phase2_queries]:
            # Combine original keyword with extracted entity
            refined_query = f"{initial_keywords[0]} AND {entity}"
            refined_results = await search_fn([refined_query])
            all_results.extend(refined_results)

        return all_results

    async def _extract_entities(self, results: List[Dict], keywords: List[str]) -> List[str]:
        """Extract key entities for follow-up searches."""
        prompt = f"""Analyze these search results and extract key related entities.

Original keywords: {', '.join(keywords)}

Top results:
{json.dumps([{'title': r['title'], 'description': r.get('description', '')} for r in results], indent=2)}

Extract 3-5 related entities (programs, organizations, people, locations, or concepts) that would refine the search.

Return as JSON list: ["entity1", "entity2", "entity3"]
"""

        entities_json = await self.llm.execute(
            task="entity_extraction",
            prompt=prompt
        )

        entities = json.loads(entities_json)
        return entities
```

**Step 2: Integrate with Monitor (Optional)**

File: `monitoring/boolean_monitor.py`
```python
from monitoring.adaptive_discovery import AdaptiveDiscovery

class BooleanMonitor:
    def __init__(self, config_path: str):
        # ... existing code ...
        self.adaptive = AdaptiveDiscovery()  # NEW
        self.use_adaptive = os.getenv("ADAPTIVE_DISCOVERY", "false").lower() == "true"

    async def execute_search(self, keywords: List[str]) -> List[Dict]:
        """Execute search with optional adaptive discovery."""

        if self.use_adaptive:
            # Adaptive multi-phase search
            logger.info("Using adaptive discovery")
            return await self.adaptive.discover(keywords, self._search_fn)
        else:
            # Standard parallel search
            return await self._standard_search(keywords)

    async def _search_fn(self, keywords: List[str]) -> List[Dict]:
        """Search function for adaptive discovery."""
        return await self._standard_search(keywords)
```

**Step 3: Configuration**

File: `.env`
```bash
# Enable adaptive discovery (optional - adds LLM cost)
ADAPTIVE_DISCOVERY="true"

# Or configure per monitor in YAML:
```

File: `data/monitors/configs/surveillance_fisa_monitor.yaml`
```yaml
name: "Surveillance & FISA Programs"
adaptive_discovery: true  # NEW
adaptive_phase1_results: 5
adaptive_phase2_queries: 3
keywords:
  - "FISA Section 702"
  # ...
```

**Testing**:
```bash
# Test adaptive discovery
python3 -c "
import asyncio
from monitoring.adaptive_discovery import AdaptiveDiscovery

async def mock_search(keywords):
    # Mock search results
    return [
        {'title': 'NSA FISA surveillance', 'description': 'Prism program details', 'relevance_score': 9},
        {'title': 'Section 702 renewal', 'description': 'FISA court approval', 'relevance_score': 8},
    ]

async def test():
    adaptive = AdaptiveDiscovery()
    results = await adaptive.discover(['FISA'], mock_search)
    print(f'Total results: {len(results)}')
    print(f'Phases executed: Initial + follow-ups')

asyncio.run(test())
"
```

**Success Criteria**:
- [ ] Adaptive discovery working
- [ ] Finds 20-30% more relevant results
- [ ] Entity extraction accurate
- [ ] Configurable per monitor

---

## Optional: Wikibase Knowledge Graph (Future)

**Only implement if you want**:
- Collaborative research (3+ people)
- Knowledge graph queries
- Entity relationship tracking

**See separate document**: `SI_UFO_Wiki/INTEGRATION_WITH_SAM_GOV.md`

**Timeline**: 1-2 weeks
**Cost**: $20-40/month (VPS hosting)

---

## Testing & Validation

### Test Plan

**Week 1: Multi-LLM Pipeline**
```bash
# Run single monitor with multi-LLM
python3 monitoring/boolean_monitor.py data/monitors/configs/surveillance_fisa_monitor.yaml

# Compare costs:
# Before: Check OpenAI usage
# After: Check OpenAI + Gemini + Anthropic usage
# Expected: 40-60% cost reduction
```

**Week 2: Quality Metrics**
```bash
# Run monitor, check email for quality report
# Should see:
# - Source utilization %
# - Average relevance score
# - Warnings if imbalanced
```

**Week 3: Caching**
```bash
# Run same monitor twice
# First run: 100% API calls
# Second run: 80%+ cache hits
# Check .cache/searches/ directory
```

**Week 4: Adaptive Discovery**
```bash
# Enable adaptive discovery
# Run monitor
# Check logs for:
# - Phase 1: Initial search
# - Phase 2: Entity extraction
# - Phase 3: Targeted searches
# Should find 20-30% more results
```

### Success Metrics

| Metric | Current | Target | Mozart Baseline |
|--------|---------|--------|-----------------|
| Cost per run | $0.10-0.30 | $0.04-0.12 | $0.10-0.30 |
| Search speed | 30-60s | 15-30s | 2-5 min |
| Cache hit rate | 0% | 50%+ | 7-day cache |
| Results found | Baseline | +20-30% | Adaptive discovery |
| False positives | ~10-20% | <5% | Quality metrics |

---

## Rollout Plan

### Week 1: Multi-LLM (Core Infrastructure)
- Day 1-2: Implement LLMPipeline utility
- Day 3-4: Integrate with BooleanMonitor
- Day 5: Test and measure cost savings
- Day 6-7: Deploy to 1-2 monitors

### Week 2: Quality Metrics (Validation)
- Day 1-2: Implement QualityMetrics module
- Day 3-4: Integrate with email alerts
- Day 5: Test with intentionally imbalanced data
- Day 6-7: Deploy to all monitors

### Week 3: Caching (Performance)
- Day 1-2: Implement SearchCache utility
- Day 3-4: Integrate with database base class
- Day 5: Test cache hit rates
- Day 6-7: Deploy to all integrations

### Week 4: Adaptive Discovery (Enhancement)
- Day 1-2: Implement AdaptiveDiscovery module
- Day 3-4: Integrate with BooleanMonitor (optional flag)
- Day 5: Test with 2-3 monitors
- Day 6-7: Enable for high-value monitors only

---

## Risk Mitigation

**Risk**: New LLM APIs fail
**Mitigation**: Fallback to GPT-5 if Gemini/Claude unavailable

**Risk**: Quality metrics too strict
**Mitigation**: Make thresholds configurable, start lenient

**Risk**: Cache causes stale data
**Mitigation**: Configurable TTL, manual cache clear command

**Risk**: Adaptive discovery too expensive
**Mitigation**: Optional feature, disable by default

**Risk**: Integration breaks existing monitors
**Mitigation**: Feature flags, gradual rollout, extensive testing

---

## Cost Analysis

### Current Costs (All GPT-5)
- Query generation: $0.02/monitor
- Relevance scoring: $0.08/monitor
- Total: $0.10/monitor
- 5 monitors daily: $15/month

### Projected Costs (Multi-LLM)
- Query generation (GPT-5-nano): $0.005/monitor
- Entity extraction (Gemini): $0.00/monitor (free)
- Relevance scoring (Claude): $0.035/monitor
- Total: $0.04/monitor (60% reduction)
- 5 monitors daily: $6/month

### ROI
- Savings: $9/month
- Implementation time: 2-4 weeks
- Payback: Immediate (first month)

---

## Next Steps After Integration

1. **Monitor metrics** for 2 weeks
2. **Tune thresholds** based on real data
3. **Consider Wikibase** if collaborative research needed
4. **Scale up** to more monitors/keywords
5. **Share learnings** with your friend (they might adopt your quality metrics!)

---

**Last Updated**: 2025-10-20
**Status**: Ready for implementation
**Owner**: Brian
**Timeline**: 2-4 weeks part-time
