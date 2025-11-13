# Codex Recommendations - Implementation Plan

**Date**: 2025-11-13
**Status**: Ready for implementation
**Context**: Codex provided clarifications for all 4 recommendations

---

## Implementation Order (By Complexity)

### 1. Document Prompt Neutrality ✅ TRIVIAL (5 minutes)
**File**: Add note to test documentation
**Action**: Clarify contractor-focused prompt is test-specific only
**Risk**: NONE
**Status**: Can do immediately

### 2. Per-Integration Limits ✅ SIMPLE (30 minutes)
**Files**: config_default.yaml, deep_research.py, config_loader.py
**Action**: Wire integration_limits config section
**Risk**: LOW
**Status**: Ready to implement

### 3. Entity Filtering Redesign ⚠️ COMPLEX (2-3 hours)
**Files**: deep_research.py (delete lines 493-529, add synthesis-time LLM call), new prompt template
**Action**: Remove Python filter, add synthesis-time LLM filtering
**Risk**: MEDIUM (affects entity graph, report quality)
**Status**: Design analysis needed (see below)

### 4. LLM Pagination Control ⚠️ MODERATE (2 hours)
**Files**: Query reformulation prompts, param_hints schema
**Action**: Add Twitter max_pages/search_type hints
**Risk**: LOW-MEDIUM (prompt complexity, limited applicability)
**Status**: Ready to implement with logging

---

## Task #1: Document Prompt Neutrality

**File**: `tests/test_clearancejobs_contractor_focused.py` or create `tests/README.md`

**Change**: Add docstring or comment clarifying contractor bias is intentional for this test

```python
# tests/test_clearancejobs_contractor_focused.py (line 30)

"""
Test ClearanceJobs integration with contractor-focused query.

NOTE: This test uses a contractor-specific query intentionally to validate
ClearanceJobs integration behavior with focused queries. The default deep
research flow uses neutral queries (see test_gemini_deep_research.py).
"""
```

**Validation**: No runtime validation needed (documentation only)

**Status**: ✅ APPROVED - Can implement immediately

---

## Task #2: Per-Integration Limits

### Step 1: Add Config Section

**File**: `config_default.yaml` (after line 69)

```yaml
# Per-Integration Result Limits
integration_limits:
  clearancejobs: 20      # 20 jobs per call
  usajobs: 100           # USAJobs API supports 100/page
  brave_search: 20       # Free tier limit
  sam: 10                # SAM.gov can be slow
  dvids: 50              # DVIDS max is 50
  twitter: 20            # Default Twitter limit
  reddit: 20             # Default Reddit limit
  discord: 20            # Default Discord limit
  # Default: use execution.default_result_limit if not specified
```

### Step 2: Add Config Loader Method

**File**: `config_loader.py` (add new method after line 277)

```python
def get_integration_limit(self, integration_name: str) -> int:
    """Get result limit for specific integration.

    Args:
        integration_name: Name of integration (e.g., 'usajobs', 'clearancejobs')

    Returns:
        Result limit for this integration, or default_result_limit if not specified
    """
    integration_limits = self._config.get('integration_limits', {})
    return integration_limits.get(
        integration_name.lower(),
        self.execution_config.get('default_result_limit', 20)
    )
```

### Step 3: Update MCP Tool Calls

**File**: `research/deep_research.py`

**Change 1: Line 585** (MCP tool calls)
```python
# BEFORE:
limit=10,

# AFTER:
limit=config.get_integration_limit(tool),
```

**Change 2: Line 1084** (Brave Search)
```python
# BEFORE:
web_results = await self._search_brave(task.query, max_results=20)

# AFTER:
brave_limit = config.get_integration_limit('brave_search')
web_results = await self._search_brave(task.query, max_results=brave_limit)
```

**Change 3: Import config** (top of file)
```python
from config_loader import ConfigLoader

# In DeepResearchEngine.__init__:
self.config = ConfigLoader()
```

### Step 4: Update Config Default

**File**: `config_default.yaml` (line 61)

```yaml
# BEFORE:
default_result_limit: 10

# AFTER:
default_result_limit: 20        # Increased from 10 per Codex recommendation
```

### Validation

**Test**: Run `tests/test_gemini_deep_research.py` and verify:
- USAJobs returns up to 100 results (not capped at 10)
- ClearanceJobs returns up to 20 results
- Brave Search uses config value (not hardcoded 20)

**Expected Log Output**:
```
🔍 Searching USAJobs with limit=100...
🔍 Searching ClearanceJobs with limit=20...
🔍 Searching Brave Search with limit=20...
```

**Status**: ✅ APPROVED - Ready to implement

---

## Task #3: Entity Filtering Redesign

### Current Architecture Analysis

**Stage 1: Per-Task Extraction** (line 414, called 3 times in test)
```python
entities_found = await self._extract_entities(
    research_question=self.original_question,
    task_query=task.query,
    results=task.accumulated_results
)
task.entities_found = entities_found
await self._update_entity_graph(entities_found)
```

**Stage 2: Cross-Task Python Filter** (lines 493-529, WILL BE DELETED)
- Filters with META_TERMS_BLACKLIST
- Requires 2+ task appearances
- Operates on aggregated entity set

**Stage 3: Synthesis** (line 1983, WHERE NEW LLM CALL GOES)
```python
async def _synthesize_report(self, original_question: str) -> str:
    # Collect all results...

    # Compile entity relationships (currently uses filtered entities)
    relationship_summary = []
    for entity, related in list(self.entity_graph.items()):
        relationship_summary.append(f"- {entity}: {', '.join(related)}")
```

### Codex's Approach

**Quote**: "pass the entire aggregated entity list into a final LLM prompt at synthesis time and let it decide what to keep/drop (with rationale)"

**Implementation Location**: In `_synthesize_report()` after line 1983, BEFORE building relationship_summary

### Implementation Design

**Step 1: Aggregate All Entities** (new code after line 1983)

```python
# Aggregate all entities from completed tasks (BEFORE filtering)
all_entities_raw = set()
entity_sources = {}  # Track which tasks found each entity

for task in self.completed_tasks:
    for entity in task.entities_found:
        entity_lower = entity.strip().lower()
        all_entities_raw.add(entity_lower)

        if entity_lower not in entity_sources:
            entity_sources[entity_lower] = []
        entity_sources[entity_lower].append(task.id)

# Count task occurrences for each entity
entity_task_counts = {
    entity: len(sources)
    for entity, sources in entity_sources.items()
}
```

**Step 2: Create Synthesis-Time Entity Filter Prompt**

**New File**: `prompts/deep_research/entity_synthesis_filter.j2`

```jinja2
You are filtering entities for a final research report.

RESEARCH QUESTION:
{{ research_question }}

COMPLETED TASKS:
{% for task in completed_tasks %}
Task {{ task.id }}: {{ task.query }}
  Results: {{ task.accumulated_results|length }}
  Entities found: {{ task.entities_found|join(', ') }}
{% endfor %}

ALL ENTITIES DISCOVERED ({{ all_entities|length }} total):
{% for entity, count in entity_task_counts.items() %}
- "{{ entity }}" (found in {{ count }} task{{ 's' if count > 1 else '' }})
{% endfor %}

TASK: Filter this entity list to keep ONLY entities that are:
1. Relevant to the research question
2. Specific and informative (not generic meta-terms like "job", "cybersecurity" alone)
3. Useful for a final research report

FILTERING GUIDANCE:
- KEEP: Specific entities (e.g., "IT Specialist (Cybersecurity)", "2210 Series", "DHS")
- KEEP: Entities appearing in multiple tasks (higher confidence)
- REMOVE: Generic meta-terms (e.g., "job", "clearance", "government" by themselves)
- REMOVE: Entities unrelated to research question
- KEEP: Domain-specific terms even if generic in other contexts (e.g., "TS/SCI" is specific in clearance context)

Return a JSON object with:
{
  "kept_entities": ["entity1", "entity2", ...],
  "removed_entities": ["entity3", "entity4", ...],
  "rationale": "Brief explanation of filtering decisions"
}
```

**Step 3: Call LLM Filter in Synthesis**

```python
# In _synthesize_report(), after aggregating entities

# Filter entities via LLM
filter_prompt = render_prompt(
    "deep_research/entity_synthesis_filter.j2",
    research_question=original_question,
    completed_tasks=[{
        'id': t.id,
        'query': t.query,
        'accumulated_results': t.accumulated_results,
        'entities_found': t.entities_found
    } for t in self.completed_tasks],
    all_entities=list(all_entities_raw),
    entity_task_counts=entity_task_counts
)

filter_response = await acompletion(
    model=config.llm_config['strategic_coordinator'],
    messages=[{"role": "user", "content": filter_prompt}],
    response_format={
        "type": "json_schema",
        "json_schema": {
            "name": "entity_filter",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {
                    "kept_entities": {"type": "array", "items": {"type": "string"}},
                    "removed_entities": {"type": "array", "items": {"type": "string"}},
                    "rationale": {"type": "string"}
                },
                "required": ["kept_entities", "removed_entities", "rationale"],
                "additionalProperties": False
            }
        }
    }
)

filter_result = json.loads(filter_response.choices[0].message.content)
kept_entities = set(e.lower() for e in filter_result['kept_entities'])

# Log filtering decision
entities_removed = len(all_entities_raw) - len(kept_entities)
if entities_removed > 0:
    logging.info(f"Entity synthesis filtering: Removed {entities_removed} entities ({len(all_entities_raw)} → {len(kept_entities)})")
    logging.info(f"Rationale: {filter_result['rationale']}")
    print(f"🔍 Entity filtering (synthesis): Removed {entities_removed} entities")
    print(f"   Rationale: {filter_result['rationale']}")
```

**Step 4: Update Entity Graph for Report**

```python
# Filter entity_graph to only include kept entities
filtered_entity_graph = {
    entity: related
    for entity, related in self.entity_graph.items()
    if entity.lower() in kept_entities
}

# Build relationship summary from filtered graph
relationship_summary = []
for entity, related in filtered_entity_graph.items():
    # Only include relationships where both entities are kept
    kept_related = [r for r in related if r.lower() in kept_entities]
    if kept_related:
        relationship_summary.append(f"- {entity}: connected to {', '.join(kept_related)}")
```

**Step 5: Delete Old Python Filter**

**File**: `research/deep_research.py` (lines 493-529)

**Action**: Delete entire block (META_TERMS_BLACKLIST + filtering logic)

### Critical Design Questions

**Q1: Should we update self.entity_graph permanently or just for reporting?**

**Option A**: Update self.entity_graph (permanent change)
- Pro: Consistent state after synthesis
- Con: Loses information (can't go back)

**Option B**: Create filtered copy for report only
- Pro: Preserves raw data
- Con: entity_graph contains unfiltered entities

**Recommendation**: **Option B** - Create `filtered_entity_graph` for report, keep `self.entity_graph` intact for debugging

**Q2: What happens to relationships when parent entity is filtered?**

**Answer**: Only include relationships where BOTH entities are kept (see Step 4 implementation)

**Q3: Should we log which entities were removed and why?**

**Answer**: YES - Log count + LLM's rationale for transparency

**Q4: Does this preserve multi-task confirmation benefit?**

**Answer**: YES - We pass `entity_task_counts` to LLM, which can use it for confidence scoring. The prompt explicitly says "KEEP: Entities appearing in multiple tasks (higher confidence)"

### Validation Plan

**Test 1: Run test_polish_validation.py**
- Expected: Entities filtered at synthesis time (not during per-task extraction)
- Expected: LLM rationale logged explaining filtering decisions
- Expected: Final entity count similar to current (16-20 entities for cybersecurity query)

**Test 2: Run test_clearancejobs_contractor_focused.py**
- Expected: Contractor-specific entities kept (e.g., "Northrop Grumman", "Lockheed Martin")
- Expected: Generic meta-terms removed (e.g., "defense contractor", "job")
- Expected: Clearance levels kept (e.g., "TS/SCI with polygraph")

**Success Criteria**:
- [ ] Lines 493-529 deleted from deep_research.py
- [ ] New prompt template created (entity_synthesis_filter.j2)
- [ ] LLM filtering call added to _synthesize_report()
- [ ] Filtering happens AFTER all tasks complete (not per-task)
- [ ] LLM rationale logged for transparency
- [ ] Entity relationships preserved (only kept entities in report)
- [ ] Test results similar to current quality (16-20 entities for cyber query)

**Estimated Time**: 2-3 hours (prompt design + integration + testing)

**Risk**: MEDIUM
- Could filter too aggressively (lose important entities)
- Could filter too conservatively (keep junk)
- LLM reasoning quality unknown

**Mitigation**: Log LLM rationale, run multiple test queries, compare before/after entity quality

**Status**: ⚠️ DESIGN COMPLETE - Ready for implementation

---

## Task #4: LLM Pagination Control

### Codex's Clarification

**Quote**: "implement it where the API already supports it (Twitter's max_pages/search_type). For sources without native paging (ClearanceJobs, Brave), note that we can't do 'next page' until we extend the scraper/API. (Just document that limitation for now.)"

### Implementation Design

**Step 1: Extend param_hints Schema**

**File**: `prompts/deep_research/query_reformulation_relevance.j2` (after existing param_hints examples)

**Add Twitter Example**:
```jinja2
AVAILABLE PARAM_HINTS BY SOURCE:

Reddit:
- time_filter: "hour" | "day" | "week" | "month" | "year" | "all"
  Example: {"reddit": {"time_filter": "week"}} → find recent discussions

USAJobs:
- keywords: ["keyword1", "keyword2"]
  Example: {"usajobs": {"keywords": ["remote", "cleared"]}} → filter jobs

Twitter (NEW):
- search_type: "Top" | "Latest" | "People"
  - "Top": Popular tweets (most engagement)
  - "Latest": Recent tweets (chronological)
  - "People": Tweets from specific accounts
- max_pages: 1-5 (default: 1)
  - Higher pages = more results but slower
  Example: {"twitter": {"search_type": "Top", "max_pages": 2}} → find popular tweets with more coverage

LIMITATIONS:
- ClearanceJobs: No pagination support (scraper limitation)
- Brave Search: No pagination support (API limitation)
- For these sources, use query reformulation only
```

**Step 2: Update Twitter Integration to Accept param_hints**

**File**: `integrations/social/twitter_integration.py` (modify execute_search signature)

```python
async def execute_search(
    self,
    params: Dict[str, Any],
    api_key: str,
    limit: int = 10,
    param_hints: Optional[Dict[str, Any]] = None  # NEW PARAMETER
) -> QueryResult:
    """Execute Twitter search with optional param_hints."""

    # Extract search_type and max_pages from param_hints
    search_type = "Top"  # Default
    max_pages = 1        # Default

    if param_hints:
        search_type = param_hints.get('search_type', 'Top')
        max_pages = param_hints.get('max_pages', 1)

    # Validate search_type
    if search_type not in ["Top", "Latest", "People"]:
        logging.warning(f"Invalid search_type '{search_type}', using 'Top'")
        search_type = "Top"

    # Validate max_pages
    max_pages = max(1, min(max_pages, 5))  # Clamp to 1-5

    # Rest of implementation uses search_type and max_pages...
```

**Step 3: Add Usage Logging**

**File**: `research/execution_logger.py` (add new method)

```python
def log_param_hints_usage(
    self,
    task_id: int,
    attempt: int,
    source: str,
    hints_used: Dict[str, Any],
    results_before: int,
    results_after: int
):
    """Log param_hints usage for effectiveness measurement.

    Args:
        task_id: Task identifier
        attempt: Retry attempt number
        source: Source name (e.g., 'twitter', 'reddit')
        hints_used: Actual param_hints applied
        results_before: Result count from previous attempt (if any)
        results_after: Result count with hints applied
    """
    self.logger.info({
        'event': 'param_hints_used',
        'task_id': task_id,
        'attempt': attempt,
        'source': source,
        'hints': hints_used,
        'results_before': results_before,
        'results_after': results_after,
        'effectiveness': 'improved' if results_after > results_before else 'no_improvement'
    })
```

**Step 4: Call Logger When Hints Used**

**File**: `research/deep_research.py` (in _execute_task_with_retry, after MCP call)

```python
# After MCP search completes (around line 700)
if param_adjustments and self.logger:
    for source, hints in param_adjustments.items():
        # Find results for this source
        source_results = [r for r in all_results if r.get('source') == source]

        self.logger.log_param_hints_usage(
            task_id=task.id,
            attempt=task.retry_count,
            source=source,
            hints_used=hints,
            results_before=task.previous_attempt_count if hasattr(task, 'previous_attempt_count') else 0,
            results_after=len(source_results)
        )
```

**Step 5: Document Limitations**

**File**: `prompts/deep_research/query_reformulation_relevance.j2` (add note in LIMITATIONS section)

```jinja2
IMPORTANT LIMITATIONS:
- ClearanceJobs: No pagination support (scraper-based, cannot request "page 2")
- Brave Search: No pagination support (API does not support paging)
- For these sources, only query reformulation is available (cannot adjust search_type, max_pages, etc.)
```

### Validation Plan

**Test 1: Verify Twitter Accepts param_hints**
```python
# In tests/test_twitter_param_hints.py
result = await twitter_integration.execute_search(
    params={'query': 'cybersecurity jobs'},
    api_key=api_key,
    param_hints={'search_type': 'Top', 'max_pages': 2}
)
assert result.success
assert result.metadata.get('search_type') == 'Top'
assert result.metadata.get('max_pages') == 2
```

**Test 2: Verify LLM Uses param_hints on Retry**
```python
# Run deep research with max_retries=2
# Expected: On retry, LLM suggests {"twitter": {"search_type": "Latest"}} if "Top" didn't work
```

**Test 3: Verify Logging Works**
```bash
# Run deep research, check execution_log.jsonl
grep "param_hints_used" execution_log.jsonl
# Expected: Entries showing hints used + effectiveness
```

### Success Criteria

- [ ] Twitter integration accepts param_hints parameter
- [ ] Query reformulation prompt includes Twitter examples
- [ ] LLM can suggest search_type/max_pages adjustments
- [ ] Logging captures param_hints usage for analysis
- [ ] Limitations documented for ClearanceJobs/Brave
- [ ] Invalid hints validated and logged

**Estimated Time**: 2 hours (prompt update + integration change + logging + testing)

**Risk**: LOW-MEDIUM
- Prompt complexity (LLM must understand Twitter-specific options)
- Limited applicability (only helps when retrying same source)
- Unclear if hints actually improve quality (need data)

**Mitigation**: Add logging to measure effectiveness, can remove feature later if data shows no benefit

**Status**: ✅ APPROVED - Ready to implement with logging

---

## Implementation Summary

| Task | Complexity | Time | Risk | Status |
|------|-----------|------|------|--------|
| #1: Document Neutrality | Trivial | 5 min | NONE | ✅ Ready |
| #2: Per-Integration Limits | Simple | 30 min | LOW | ✅ Ready |
| #3: Entity Filtering | Complex | 2-3 hrs | MEDIUM | ⚠️ Design complete |
| #4: Pagination Control | Moderate | 2 hrs | LOW-MED | ✅ Ready |

**Total Estimated Time**: 4.5-5.5 hours

**Recommended Order**:
1. #1 (5 min) - Trivial documentation
2. #2 (30 min) - Simple config wiring
3. #4 (2 hrs) - Moderate complexity with logging
4. #3 (2-3 hrs) - Most complex, test last

**Final Validation**: Run test_clearancejobs_contractor_focused.py after all changes to verify combined behavior

---

**END OF IMPLEMENTATION PLAN**
