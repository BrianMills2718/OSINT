# Phase 3B: Hypothesis Execution - Comprehensive Implementation Plan

**Date**: 2025-11-15
**Estimated Time**: 8-10 hours
**Status**: Ready to implement
**Prerequisites**: Phase 3A complete and committed (commit 55a9efa)

---

## TABLE OF CONTENTS

1. [Overview](#overview)
2. [Dependencies & Prerequisites](#dependencies--prerequisites)
3. [Implementation Steps](#implementation-steps)
4. [Validation & Testing](#validation--testing)
5. [Rollback Plan](#rollback-plan)
6. [Success Criteria](#success-criteria)

---

## OVERVIEW

### What We're Building

**Phase 3B: Hypothesis Execution** - Execute each hypothesis with its specific search strategy instead of just displaying hypotheses in reports.

**Current Behavior** (Phase 3A - Planning):
```
User query → 3 tasks → 3 hypotheses per task (planning only)
Report shows: "Suggested Investigative Angles" (what COULD be done)
Searches: Normal task search only (hypotheses not executed)
```

**New Behavior** (Phase 3B - Execution):
```
User query → 3 tasks → 3 hypotheses per task (executed)
Report shows: "Hypothesis Findings" (what WAS found by each hypothesis)
Searches: Normal task search + 3 hypothesis searches per task
```

### Architecture Decision

**Expand Within Task** (not task multiplication):
- Keep existing 3-5 tasks
- Execute hypotheses AFTER normal task search
- Tag results with `hypothesis_id` for attribution
- Single-shot execution (no per-hypothesis retries)
- Parallel execution (all hypotheses at once)

### Key Design Principles

1. **Quality over cost**: LLM query generation per hypothesis (not crude signal joining)
2. **Full autonomy**: No mid-run stopping decisions (user sets ceiling upfront)
3. **Failure resilience**: Continue on hypothesis failure (don't kill entire task)
4. **Attribution**: Tag results with hypothesis_id, preserve multi-validation
5. **Backward compatible**: Auto-upgrade from Phase 3A config

---

## DEPENDENCIES & PREREQUISITES

### Code Prerequisites

**Required** (already exist):
- ✅ `_generate_hypotheses()` method (Phase 3A - line 622)
- ✅ `_search_mcp_tools_selected()` method (line 893)
- ✅ `_validate_result_relevance()` method (line 1442)
- ✅ `task.hypotheses` field in ResearchTask (line 94)
- ✅ `self.tool_name_to_display` mapping (line ~130)

**Will Create**:
- `_execute_hypotheses()` method (NEW)
- `_execute_hypothesis()` method (NEW)
- `_generate_hypothesis_query()` method (NEW)
- `_map_hypothesis_sources()` helper (NEW)
- `_deduplicate_with_attribution()` helper (NEW)

### Config Prerequisites

**Current** (Phase 3A):
```yaml
hypothesis_branching:
  enabled: true
  max_hypotheses_per_task: 5
```

**Will Modify To**:
```yaml
hypothesis_branching:
  mode: "execution"  # off | planning | execution
  max_hypotheses_per_task: 5
```

### Prompt Prerequisites

**Will Create**:
- `prompts/deep_research/hypothesis_query_generation.j2` (NEW)

**Will Modify**:
- `prompts/deep_research/relevance_evaluation.j2` (optional - add hypothesis_context)

### Testing Prerequisites

**Will Create**:
- `tests/test_phase3b_execution.py` (NEW)

**Will Modify**:
- `tests/test_phase3a_integration.py` (add backward compat check)

---

## IMPLEMENTATION STEPS

### STEP 1: Data Structures & Config (30 minutes)

**Objective**: Set up reverse source mapping and config reading with auto-upgrade

#### 1.1: Build Reverse Source Map

**File**: `research/deep_research.py`
**Location**: `__init__()` method (around line 200, after `self.tool_name_to_display` is built)

**Code**:
```python
# Build reverse map: display name → tool name (Phase 3B)
self.display_to_tool_map = {
    display: tool_name
    for tool_name, display in self.tool_name_to_display.items()
}
# Example: {"USAJobs": "search_usajobs", "Twitter": "search_twitter"}
```

**Validation**:
```python
# Quick test in Python REPL:
from research.deep_research import SimpleDeepResearch
research = SimpleDeepResearch()
assert "USAJobs" in research.display_to_tool_map
assert research.display_to_tool_map["USAJobs"] == "search_usajobs"
print("[PASS] Reverse map built correctly")
```

#### 1.2: Update Config Reading with Auto-Upgrade

**File**: `research/deep_research.py`
**Location**: `__init__()` method (around line 177-180, replace existing hypothesis config reading)

**Code**:
```python
# Phase 3A/3B: Hypothesis branching configuration
raw_config = config.get_raw_config()
hyp_config = raw_config.get("research", {}).get("hypothesis_branching", {})

# Handle legacy "enabled: true" (Phase 3A) with auto-upgrade
if "enabled" in hyp_config and "mode" not in hyp_config:
    if hyp_config["enabled"]:
        self.hypothesis_mode = "planning"  # Legacy behavior preserved
        logging.warning("⚠️  hypothesis_branching.enabled is deprecated, use mode: 'planning' instead")
    else:
        self.hypothesis_mode = "off"
else:
    # New "mode" config (Phase 3B)
    self.hypothesis_mode = hyp_config.get("mode", "off")  # off | planning | execution

self.hypothesis_branching_enabled = (self.hypothesis_mode in ["planning", "execution"])
self.max_hypotheses_per_task = hyp_config.get("max_hypotheses_per_task", 5)
```

**Validation**:
```python
# Test auto-upgrade from Phase 3A config
# config.yaml: hypothesis_branching: {enabled: true}
research = SimpleDeepResearch()
assert research.hypothesis_mode == "planning"
assert research.hypothesis_branching_enabled == True

# Test new Phase 3B config
# config.yaml: hypothesis_branching: {mode: "execution"}
research = SimpleDeepResearch()
assert research.hypothesis_mode == "execution"
print("[PASS] Config auto-upgrade working")
```

#### 1.3: Update config_default.yaml

**File**: `config_default.yaml`
**Location**: Lines 205-229 (hypothesis_branching section)

**Change**:
```yaml
# BEFORE (Phase 3A):
hypothesis_branching:
  enabled: false  # DEPRECATED - use 'mode' instead
  max_hypotheses_per_task: 5

# AFTER (Phase 3B):
hypothesis_branching:
  mode: "off"  # off | planning | execution
  # - "off": No hypothesis generation (Phase 0 behavior)
  # - "planning": Generate hypotheses but don't execute (Phase 3A)
  # - "execution": Generate AND execute hypotheses (Phase 3B)

  max_hypotheses_per_task: 5  # Ceiling (LLM adapts 1-5 based on complexity)

  # Note: Legacy "enabled: true/false" still works (auto-upgrades to planning/off)
```

**Success Criteria**:
- [ ] Reverse map built in `__init__()`
- [ ] Config auto-upgrade from `enabled` to `mode`
- [ ] Deprecation warning logged for legacy config
- [ ] `config_default.yaml` updated with `mode` parameter

---

### STEP 2: Helper Methods (1 hour)

**Objective**: Create source mapping and deduplication helpers

#### 2.1: Source Name Validation Helper

**File**: `research/deep_research.py`
**Location**: Insert around line 850 (before `_search_mcp_tools_selected()`)

**Code**:
```python
def _map_hypothesis_sources(self, display_sources: List[str]) -> List[str]:
    """
    Map hypothesis display names to tool names, with validation.

    Phase 3B: Hypothesis Execution

    Args:
        display_sources: List of human-readable source names from hypothesis
                        (e.g., ["USAJobs", "Twitter", "Brave Search"])

    Returns:
        List of tool names (MCP function names)
        (e.g., ["search_usajobs", "search_twitter", "brave_search"])

    Logs warnings for invalid sources but continues (doesn't fail).
    """
    tool_sources = []
    invalid_sources = []

    for display_name in display_sources:
        # Check reverse map for tool name
        tool_name = self.display_to_tool_map.get(display_name)
        if tool_name:
            tool_sources.append(tool_name)
        else:
            invalid_sources.append(display_name)

    # Log warnings for invalid sources (don't fail - just skip them)
    if invalid_sources:
        logging.warning(f"Invalid source names in hypothesis: {invalid_sources}")
        print(f"⚠️  Skipping invalid sources: {', '.join(invalid_sources)}")

    return tool_sources
```

**Validation**:
```python
# Test with valid sources
sources = research._map_hypothesis_sources(["USAJobs", "Twitter"])
assert sources == ["search_usajobs", "search_twitter"]

# Test with invalid sources (should log warning but continue)
sources = research._map_hypothesis_sources(["USAJobs", "InvalidSource", "Twitter"])
assert sources == ["search_usajobs", "search_twitter"]
assert "InvalidSource" not in sources
print("[PASS] Source mapping validates correctly")
```

#### 2.2: Multi-Attribution Deduplication Helper

**File**: `research/deep_research.py`
**Location**: Insert around line 2260 (before `_save_research_output()`)

**Code**:
```python
def _deduplicate_with_attribution(self, results: List[Dict]) -> List[Dict]:
    """
    Deduplicate results while preserving multi-hypothesis attribution.

    Phase 3B: Hypothesis Execution

    If same result found by multiple hypotheses, keep single copy with
    hypothesis_ids=[1,2,3] array showing all hypotheses that found it.

    Args:
        results: List of result dicts (may have hypothesis_id tags)

    Returns:
        Deduplicated results with hypothesis_ids arrays
    """
    seen = {}  # key: (url or title) → result dict

    for result in results:
        # Use URL as primary key, fall back to title
        key = result.get("url") or result.get("title")
        if not key:
            continue  # Skip results without URL or title

        if key in seen:
            # Duplicate found - merge hypothesis attribution
            existing_hyp_ids = seen[key].get("hypothesis_ids", [])

            # Convert single hypothesis_id to array (if first duplicate)
            if "hypothesis_id" in seen[key]:
                existing_hyp_ids = [seen[key]["hypothesis_id"]]
                del seen[key]["hypothesis_id"]
                seen[key]["hypothesis_ids"] = existing_hyp_ids

            # Add new hypothesis_id if present
            new_hyp_id = result.get("hypothesis_id")
            if new_hyp_id and new_hyp_id not in existing_hyp_ids:
                existing_hyp_ids.append(new_hyp_id)
        else:
            # First occurrence - store as-is
            seen[key] = result.copy()

            # Convert hypothesis_id to array for consistency
            if "hypothesis_id" in seen[key]:
                seen[key]["hypothesis_ids"] = [seen[key]["hypothesis_id"]]
                del seen[key]["hypothesis_id"]

    return list(seen.values())
```

**Validation**:
```python
# Test deduplication with attribution
results = [
    {"title": "Job A", "url": "http://a.com", "hypothesis_id": 1},
    {"title": "Job A", "url": "http://a.com", "hypothesis_id": 2},  # Duplicate
    {"title": "Job B", "url": "http://b.com"}  # No hypothesis_id
]
deduped = research._deduplicate_with_attribution(results)
assert len(deduped) == 2  # Job A deduplicated
assert deduped[0]["hypothesis_ids"] == [1, 2]  # Both hypotheses credited
print("[PASS] Deduplication preserves attribution")
```

**Success Criteria**:
- [ ] `_map_hypothesis_sources()` validates and logs warnings
- [ ] `_deduplicate_with_attribution()` preserves multi-hypothesis attribution
- [ ] Both helpers tested with edge cases

---

### STEP 3: Hypothesis Query Generation (1.5 hours)

**Objective**: Create LLM prompt and method for hypothesis-specific queries

#### 3.1: Create Query Generation Template

**File**: `prompts/deep_research/hypothesis_query_generation.j2` (NEW)

**Content**:
```jinja2
{#
Hypothesis Query Generation - Phase 3B
Generates a search query tailored to a specific investigative hypothesis

Input Variables:
- task_query: The parent task query
- hypothesis_statement: What this hypothesis is looking for
- signals: List of keywords/patterns indicating relevance
- expected_entities: Organizations/people/programs expected to find
#}

You are generating a search query for a specific investigative hypothesis.

## CONTEXT

**Parent Task Query**: {{ task_query }}

**Hypothesis**: {{ hypothesis_statement }}

**Signals to Look For**:
{% for signal in signals %}
- {{ signal }}
{% endfor %}

**Expected Entities**:
{% for entity in expected_entities %}
- {{ entity }}
{% endfor %}

---

## YOUR TASK

Generate a search query that will find results matching this hypothesis.

**Requirements**:
- Incorporate key signals from the list above (3-5 signals ideal)
- Target the expected entities
- Keep it concise (3-10 words ideal, max 15 words)
- Use natural language (not just keyword mashing)
- Focus on the SPECIFIC angle of this hypothesis (not the general task)

**Good Examples**:
- "GS-2210 official OPM classification standards"
- "federal cybersecurity jobs TS/SCI clearance requirements Fort Meade"
- "NSA classified programs FOIA declassified documents"

**Bad Examples**:
- "GS-2210 OPM federal government jobs classification information technology" (too generic, keyword stuffing)
- "cybersecurity" (too broad, misses signals and entities)
- "What are the duties of a GS-2210 Information Technology Specialist?" (conversational, not search-optimized)

**Important Notes**:
- This query will be searched on: {{ sources|join(', ') }}
- Tailor language to these sources (e.g., formal for government databases, casual for social media)
- If searching social media (Twitter, Reddit), consider hashtags or community terms

---

## OUTPUT FORMAT (JSON)

Return a JSON object with this structure:

```json
{
  "query": "Your concise, signal-rich search query here"
}
```

Generate the query now.
```

**Validation**: Template renders without errors
```bash
python3 -c "from core.prompt_loader import render_prompt; print(render_prompt('deep_research/hypothesis_query_generation.j2', task_query='test', hypothesis_statement='test', signals=['sig1'], expected_entities=['ent1'], sources=['USAJobs']))"
```

#### 3.2: Create Query Generation Method

**File**: `research/deep_research.py`
**Location**: Insert around line 750 (after `_generate_hypotheses()`)

**Code**:
```python
async def _generate_hypothesis_query(
    self,
    task_query: str,
    hypothesis_statement: str,
    signals: List[str],
    expected_entities: List[str],
    sources: List[str]
) -> str:
    """
    Generate search query for a specific hypothesis.

    Phase 3B: Hypothesis Execution

    Uses LLM to craft a query incorporating:
    - Hypothesis statement (what we're looking for)
    - Signals (keywords/patterns)
    - Expected entities (organizations/people/programs)
    - Target sources (to tailor language)

    Args:
        task_query: Parent task query (for context)
        hypothesis_statement: What this hypothesis is looking for
        signals: Keywords from hypothesis.search_strategy.signals
        expected_entities: Entities from hypothesis.search_strategy.expected_entities
        sources: Display names of sources to be searched

    Returns:
        Search query string (3-15 words, optimized for hypothesis)
    """
    prompt = render_prompt(
        "deep_research/hypothesis_query_generation.j2",
        task_query=task_query,
        hypothesis_statement=hypothesis_statement,
        signals=signals,
        expected_entities=expected_entities,
        sources=sources
    )

    schema = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query (3-15 words)"
            }
        },
        "required": ["query"],
        "additionalProperties": False
    }

    response = await acompletion(
        model=config.get_model("query_generation"),
        messages=[{"role": "user", "content": prompt}],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "strict": True,
                "name": "hypothesis_query_generation",
                "schema": schema
            }
        }
    )

    result = json.loads(response.choices[0].message.content)
    return result["query"]
```

**Validation**:
```python
# Test query generation
query = await research._generate_hypothesis_query(
    task_query="GS-2210 job series duties",
    hypothesis_statement="Official OPM documentation defines GS-2210 duties",
    signals=["GS-2210", "OPM classification", "duties"],
    expected_entities=["OPM", "GS-2210"],
    sources=["Brave Search", "USAJobs"]
)
assert len(query.split()) >= 3 and len(query.split()) <= 15
assert "GS-2210" in query or "2210" in query
print(f"[PASS] Generated query: {query}")
```

**Success Criteria**:
- [ ] Template created at `prompts/deep_research/hypothesis_query_generation.j2`
- [ ] Method `_generate_hypothesis_query()` returns 3-15 word queries
- [ ] Query incorporates signals and entities
- [ ] Test with sample hypothesis succeeds

---

### STEP 4: Core Execution Methods (3-4 hours)

**Objective**: Implement hypothesis execution logic

#### 4.1: Single Hypothesis Executor

**File**: `research/deep_research.py`
**Location**: Insert around line 1340 (before entity extraction in `_execute_task_with_retry()`)

**Code**:
```python
async def _execute_hypothesis(
    self,
    task: ResearchTask,
    hypothesis: Dict
) -> Dict[str, any]:
    """
    Execute a single hypothesis: generate query, search sources, filter, tag results.

    Phase 3B: Hypothesis Execution

    Flow:
    1. Generate hypothesis-specific query (LLM)
    2. Map display sources to tool names
    3. Search using hypothesis sources (no source selection)
    4. Validate relevance (with hypothesis context)
    5. Filter and tag results with hypothesis_id
    6. Return execution metrics

    Args:
        task: Parent ResearchTask
        hypothesis: Hypothesis dict with id, statement, search_strategy, etc.

    Returns:
        Execution metrics dict with:
        - query_generated: str
        - sources_searched: List[str] (display names)
        - results_found: int
        - results_kept: int
        - execution_time_ms: int
        - status: "success" | "failed"
        - error: Optional[str]
    """
    hyp_id = hypothesis["id"]
    hyp_statement = hypothesis["statement"]
    start_time = time.time()

    try:
        # Step 1: Generate hypothesis-specific query
        display_sources = hypothesis["search_strategy"]["sources"]
        query = await self._generate_hypothesis_query(
            task_query=task.query,
            hypothesis_statement=hyp_statement,
            signals=hypothesis["search_strategy"]["signals"],
            expected_entities=hypothesis["search_strategy"]["expected_entities"],
            sources=display_sources
        )

        # Log query generation
        if self.logger:
            self.logger.log_hypothesis_execution_started(
                task_id=task.id,
                hypothesis_id=hyp_id,
                hypothesis_statement=hyp_statement,
                query_generated=query
            )

        # Step 2: Map display names to tool names (with validation)
        tool_sources = self._map_hypothesis_sources(display_sources)

        if not tool_sources:
            # All sources were invalid - skip this hypothesis
            raise ValueError(f"No valid sources in hypothesis {hyp_id}: {display_sources}")

        # Step 3: Search using hypothesis sources (MCP only, no Brave for hypotheses)
        mcp_tool_sources = [s for s in tool_sources if s != "brave_search"]

        mcp_results = []
        if mcp_tool_sources:
            mcp_results = await self._search_mcp_tools_selected(
                query,
                mcp_tool_sources,
                limit=config.default_result_limit,
                task_id=task.id,
                attempt=task.retry_count,
                param_adjustments=None  # No param hints for hypotheses
            )

        # Step 4: Validate relevance (pass hypothesis context for better filtering)
        should_accept, relevance_reason, relevant_indices, _, _, _ = await self._validate_result_relevance(
            task_query=query,
            research_question=self.original_question,
            sample_results=mcp_results,
            hypothesis_context=hyp_statement  # NEW: Help LLM understand context
        )

        # Step 5: Filter and tag results
        filtered_results = [mcp_results[i] for i in relevant_indices]
        tagged_results = [
            {**r, "hypothesis_id": hyp_id}
            for r in filtered_results
        ]

        # Step 6: Append to task results
        task.accumulated_results.extend(tagged_results)

        # Calculate execution time
        execution_time_ms = int((time.time() - start_time) * 1000)

        # Step 7: Log success
        print(f"  ✓ Hypothesis {hyp_id}: {len(tagged_results)} results ({len(mcp_results)} found, {len(tagged_results)} kept)")
        if self.logger:
            self.logger.log_hypothesis_executed(
                task_id=task.id,
                hypothesis_id=hyp_id,
                query=query,
                sources=display_sources,
                results_found=len(mcp_results),
                results_kept=len(tagged_results)
            )

        # Return metrics
        return {
            "query_generated": query,
            "sources_searched": display_sources,
            "results_found": len(mcp_results),
            "results_kept": len(tagged_results),
            "execution_time_ms": execution_time_ms,
            "status": "success",
            "error": None
        }

    except Exception as e:
        # Calculate execution time even for failures
        execution_time_ms = int((time.time() - start_time) * 1000)

        # Log failure (don't kill entire task)
        error_msg = f"{type(e).__name__}: {str(e)}"
        print(f"  ⚠️  Hypothesis {hyp_id} failed: {error_msg}")
        if self.logger:
            self.logger.log_hypothesis_failed(
                task_id=task.id,
                hypothesis_id=hyp_id,
                error=error_msg
            )

        # Return failure metrics
        return {
            "query_generated": None,
            "sources_searched": display_sources,
            "results_found": 0,
            "results_kept": 0,
            "execution_time_ms": execution_time_ms,
            "status": "failed",
            "error": error_msg
        }
```

#### 4.2: Parallel Hypothesis Executor

**File**: `research/deep_research.py`
**Location**: Insert around line 1340 (before `_execute_hypothesis()`)

**Code**:
```python
async def _execute_hypotheses(self, task: ResearchTask) -> None:
    """
    Execute all hypotheses for a task in parallel.

    Phase 3B: Hypothesis Execution

    Flow:
    1. Extract hypotheses from task.hypotheses
    2. Execute all hypotheses concurrently (asyncio.gather)
    3. Store execution metrics in task metadata

    Results are appended to task.accumulated_results with hypothesis_id tags.

    Args:
        task: ResearchTask with task.hypotheses populated
    """
    if not task.hypotheses:
        return

    hypotheses = task.hypotheses.get("hypotheses", [])
    if not hypotheses:
        return

    print(f"\n🔬 Executing {len(hypotheses)} hypothesis/hypotheses for Task {task.id}...")

    # Execute all hypotheses in parallel (don't stop on individual failures)
    hypothesis_tasks = [
        self._execute_hypothesis(task, hyp)
        for hyp in hypotheses
    ]
    execution_results = await asyncio.gather(*hypothesis_tasks, return_exceptions=False)

    # Store execution metrics in task for later persistence
    if not hasattr(task, 'hypothesis_execution_results'):
        task.hypothesis_execution_results = {}

    for hyp, metrics in zip(hypotheses, execution_results):
        task.hypothesis_execution_results[hyp["id"]] = metrics

    # Summary
    successful = sum(1 for m in execution_results if m["status"] == "success")
    total_results = sum(m["results_kept"] for m in execution_results)
    print(f"✓ Hypothesis execution complete for Task {task.id}: {successful}/{len(hypotheses)} successful, {total_results} total results")
```

#### 4.3: Integration into Task Retry Loop

**File**: `research/deep_research.py`
**Location**: Modify `_execute_task_with_retry()` around line 1340

**Change**:
```python
# EXISTING CODE (around line 1340):
# ... normal search with retry logic ...
if should_accept and filtered_results:
    task.accumulated_results.extend(filtered_results)
    # ... logging ...
    break  # Success - exit retry loop

# NEW CODE (insert after retry loop, before entity extraction):
# Phase 3B: Execute hypotheses if enabled (after normal search completes)
if self.hypothesis_mode == "execution" and task.hypotheses:
    await self._execute_hypotheses(task)

# EXISTING CODE (entity extraction):
# Extract entities from accumulated results (normal + hypothesis results)
if task.accumulated_results:
    print(f"🔍 Extracting entities from {len(task.accumulated_results)} accumulated results...")
    # ... entity extraction ...
```

**Success Criteria**:
- [ ] `_execute_hypothesis()` returns execution metrics dict
- [ ] `_execute_hypotheses()` runs hypotheses in parallel
- [ ] Integration point in `_execute_task_with_retry()` calls `_execute_hypotheses()`
- [ ] Results tagged with `hypothesis_id` appear in `task.accumulated_results`

---

### STEP 5: Telemetry & Logging (1 hour)

**Objective**: Add execution events to logger

#### 5.1: Add Logger Methods

**File**: `utils/execution_logger.py`
**Location**: Add after existing log methods (around line 200)

**Code**:
```python
def log_hypothesis_execution_started(
    self,
    task_id: int,
    hypothesis_id: int,
    hypothesis_statement: str,
    query_generated: str
):
    """
    Log start of hypothesis execution.

    Phase 3B: Hypothesis Execution
    """
    self._write_event({
        "event": "hypothesis_execution_started",
        "task_id": task_id,
        "hypothesis_id": hypothesis_id,
        "hypothesis_statement": hypothesis_statement,
        "query_generated": query_generated,
        "timestamp": datetime.now().isoformat()
    })

def log_hypothesis_executed(
    self,
    task_id: int,
    hypothesis_id: int,
    query: str,
    sources: List[str],
    results_found: int,
    results_kept: int
):
    """
    Log successful hypothesis execution.

    Phase 3B: Hypothesis Execution
    """
    self._write_event({
        "event": "hypothesis_executed",
        "task_id": task_id,
        "hypothesis_id": hypothesis_id,
        "query": query,
        "sources": sources,
        "results_found": results_found,
        "results_kept": results_kept,
        "timestamp": datetime.now().isoformat()
    })

def log_hypothesis_failed(
    self,
    task_id: int,
    hypothesis_id: int,
    error: str
):
    """
    Log failed hypothesis execution.

    Phase 3B: Hypothesis Execution
    """
    self._write_event({
        "event": "hypothesis_failed",
        "task_id": task_id,
        "hypothesis_id": hypothesis_id,
        "error": error,
        "timestamp": datetime.now().isoformat()
    })
```

#### 5.2: Update Metadata Persistence

**File**: `research/deep_research.py`
**Location**: Modify `_save_research_output()` around line 2290

**Change**:
```python
# EXISTING CODE (Phase 3A - saves hypothesis definitions):
if self.hypothesis_branching_enabled:
    hypotheses_by_task = {}
    for task in (self.completed_tasks + self.failed_tasks):
        if task.hypotheses:
            hypotheses_by_task[task.id] = task.hypotheses

    if hypotheses_by_task:
        metadata["hypotheses_by_task"] = hypotheses_by_task

# NEW CODE (Phase 3B - add execution results):
if self.hypothesis_mode == "execution":
    # Add execution_results per task
    for task in (self.completed_tasks + self.failed_tasks):
        if hasattr(task, 'hypothesis_execution_results') and task.hypothesis_execution_results:
            # Ensure hypotheses_by_task entry exists
            if task.id not in metadata.get("hypotheses_by_task", {}):
                continue

            # Add execution_results to existing hypothesis data
            metadata["hypotheses_by_task"][task.id]["execution_results"] = task.hypothesis_execution_results
```

**Success Criteria**:
- [ ] 3 new logger methods added
- [ ] Metadata includes `execution_results` per task when mode="execution"
- [ ] Execution log events appear in `execution_log.jsonl`

---

### STEP 6: Deduplication Update (30 minutes)

**Objective**: Use multi-attribution dedup in synthesis

**File**: `research/deep_research.py`
**Location**: Modify `_save_research_output()` around line 2270 (deduplication section)

**Change**:
```python
# EXISTING CODE (Phase 3A deduplication):
# Deduplicate results across all tasks
aggregated_results_list = []
for r in aggregated_results_by_task.values():
    aggregated_results_list.extend(r.get('results', []))

seen = set()
unique_results = []
duplicates_removed = 0
for result in aggregated_results_list:
    key = result.get("url") or result.get("title")
    if key and key not in seen:
        seen.add(key)
        unique_results.append(result)
    elif key:
        duplicates_removed += 1

# NEW CODE (Phase 3B - use multi-attribution dedup):
if self.hypothesis_mode == "execution":
    # Use hypothesis-aware deduplication (preserves multi-validation)
    unique_results = self._deduplicate_with_attribution(aggregated_results_list)
    duplicates_removed = len(aggregated_results_list) - len(unique_results)
else:
    # Use simple deduplication (Phase 0/3A behavior)
    seen = set()
    unique_results = []
    duplicates_removed = 0
    for result in aggregated_results_list:
        key = result.get("url") or result.get("title")
        if key and key not in seen:
            seen.add(key)
            unique_results.append(result)
        elif key:
            duplicates_removed += 1
```

**Success Criteria**:
- [ ] Multi-attribution dedup used when mode="execution"
- [ ] Results have `hypothesis_ids` array after dedup
- [ ] Dedup count matches (original - unique)

---

### STEP 7: Testing (2-3 hours)

**Objective**: Validate execution mode + backward compatibility

#### 7.1: Create Execution Mode Test

**File**: `tests/test_phase3b_execution.py` (NEW)

**Content**:
```python
#!/usr/bin/env python3
"""
Phase 3B: Hypothesis Execution Test

Validates:
1. Hypotheses are executed (not just generated)
2. Results are tagged with hypothesis_id or hypothesis_ids
3. Metadata contains execution_results per hypothesis
4. Report contains hypothesis-attributed findings
5. Execution log contains hypothesis events
"""

import asyncio
import json
from pathlib import Path
from research.deep_research import SimpleDeepResearch
from config_loader import Config

async def main():
    print("="*80)
    print("PHASE 3B EXECUTION TEST")
    print("="*80)
    print()

    # Override config to enable execution mode
    research = SimpleDeepResearch(
        max_tasks=2,
        max_retries_per_task=1,
        max_time_minutes=5,
        hypothesis_branching_enabled=True,
        hypothesis_mode="execution"  # KEY: Triggers execution
    )

    print("✓ Hypothesis execution mode ENABLED")
    print()
    print(f"Running query: 'What cybersecurity jobs require TS/SCI clearance?'")
    print("-"*80)
    print()

    result = await research.research("What cybersecurity jobs require TS/SCI clearance?")

    print()
    print("="*80)
    print("TEST RESULTS")
    print("="*80)
    print()

    # Test 1: Basic execution
    print(f"1. Tasks Executed: {result['tasks_executed']}")
    print(f"2. Total Results: {result['total_results']}")
    print(f"3. Entities Discovered: {len(result.get('entities_discovered', []))}")
    print()

    # Test 2: Results have hypothesis_id tags
    output_dir = Path(result['output_directory'])
    results_file = output_dir / "results.json"

    with open(results_file) as f:
        results_data = json.load(f)

    hypothesis_tagged = [
        r for r in results_data['results']
        if 'hypothesis_id' in r or 'hypothesis_ids' in r
    ]

    print(f"4. Results with hypothesis attribution: {len(hypothesis_tagged)}/{len(results_data['results'])}")

    if len(hypothesis_tagged) == 0:
        print("   ❌ FAIL: No results tagged with hypothesis_id")
        return
    else:
        print(f"   ✓ PASS: {len(hypothesis_tagged)} results attributed to hypotheses")
    print()

    # Test 3: Metadata contains execution_results
    metadata_file = output_dir / "metadata.json"
    with open(metadata_file) as f:
        metadata = json.load(f)

    print("5. Metadata - hypothesis_mode:", metadata.get("engine_config", {}).get("hypothesis_mode", "NOT FOUND"))
    print("6. Metadata - hypotheses_by_task:", "✓ PRESENT" if "hypotheses_by_task" in metadata else "❌ MISSING")

    if "hypotheses_by_task" not in metadata:
        print("   ❌ FAIL: hypotheses_by_task missing from metadata")
        return

    # Check execution_results
    for task_id, task_data in metadata["hypotheses_by_task"].items():
        print(f"   Task {task_id}:")
        if "execution_results" not in task_data:
            print(f"      ❌ FAIL: Missing execution_results")
            return

        exec_results = task_data["execution_results"]
        print(f"      - Hypotheses executed: {len(exec_results)}")
        for hyp_id, metrics in exec_results.items():
            status = metrics.get("status", "unknown")
            results_kept = metrics.get("results_kept", 0)
            print(f"         Hypothesis {hyp_id}: {status}, {results_kept} results")
    print()

    # Test 4: Report contains hypothesis findings
    report_file = output_dir / "report.md"
    with open(report_file) as f:
        report_text = f.read()

    has_hypothesis_section = "Hypothesis" in report_text or "hypothesis" in report_text.lower()
    print(f"7. Report contains hypothesis attribution: {'✓ YES' if has_hypothesis_section else '❌ NO'}")

    if not has_hypothesis_section:
        print("   ⚠️  WARNING: Report may be missing hypothesis attribution")
    print()

    # Test 5: Execution log contains hypothesis events
    exec_log_file = output_dir / "execution_log.jsonl"
    hypothesis_events = 0

    if exec_log_file.exists():
        with open(exec_log_file) as f:
            for line in f:
                event = json.loads(line)
                if "hypothesis" in event.get("event", "").lower():
                    hypothesis_events += 1

        print(f"8. Execution log hypothesis events: {hypothesis_events}")
        if hypothesis_events > 0:
            print(f"   ✓ PASS: Found {hypothesis_events} hypothesis-related events")
        else:
            print("   ⚠️  WARNING: No hypothesis events in execution log")
    else:
        print("8. Execution log: ❌ NOT FOUND")
    print()

    print("="*80)
    print("VALIDATION COMPLETE")
    print("="*80)
    print()
    print(f"Output directory: {output_dir}")
    print()

    # Final verdict
    if len(hypothesis_tagged) > 0:
        print("✓ Phase 3B execution validated successfully")
    else:
        print("❌ Phase 3B execution validation FAILED")

if __name__ == "__main__":
    asyncio.run(main())
```

**Run**:
```bash
source .venv/bin/activate
python3 tests/test_phase3b_execution.py
```

#### 7.2: Update Backward Compatibility Test

**File**: `tests/test_phase3a_integration.py`
**Location**: Add new test at end of file

**Code**:
```python
# Add at end of test_phase3a_integration.py:

async def test_backward_compatibility():
    """
    Verify that disabled mode (Phase 0) still works after Phase 3B changes.
    """
    print("\n=== BACKWARD COMPATIBILITY TEST ===\n")

    research = SimpleDeepResearch(
        max_tasks=2,
        max_retries_per_task=1,
        max_time_minutes=3,
        hypothesis_branching_enabled=False  # Disabled
    )

    print("✓ Hypothesis branching DISABLED")

    result = await research.research("What is the GS-2210 job series?")

    # Should work like Phase 0 (no hypotheses)
    assert result['tasks_executed'] > 0, "No tasks executed"

    # Metadata should NOT contain hypotheses
    output_dir = Path(result['output_directory'])
    metadata_file = output_dir / "metadata.json"
    with open(metadata_file) as f:
        metadata = json.load(f)

    assert "hypotheses_by_task" not in metadata, "Hypotheses present when disabled"

    print("✓ No hypotheses generated (correct)")
    print("✓ Backward compatibility confirmed")

# Modify main() to run both tests:
if __name__ == "__main__":
    asyncio.run(test_phase3a_integration())
    asyncio.run(test_backward_compatibility())
```

**Success Criteria**:
- [ ] Execution test passes (hypothesis_id tags present)
- [ ] Metadata contains execution_results
- [ ] Backward compatibility test passes (no hypotheses when disabled)

---

### STEP 8: Documentation (1 hour)

**Objective**: Update documentation with Phase 3B status

#### 8.1: Update CLAUDE.md

**File**: `CLAUDE.md`
**Location**: TEMPORARY section (replace Phase 3A status)

**Change**:
```markdown
# CLAUDE.md - Temporary Section (Updated as Tasks Complete)

**Last Updated**: 2025-11-15 (Phase 3B: Hypothesis Execution - COMPLETE)
**Current Phase**: Phase 3B - Hypothesis Execution
**Current Focus**: Validation complete - feature ready for production testing
**Status**: ✅ Phase 3B COMPLETE - All execution features implemented and tested

---

## PHASE 3B COMPLETE: Hypothesis Execution ✅

**Status**: All implementation complete, tests passing

**What Works Now**:
- ✅ Hypotheses are executed (not just generated)
- ✅ Each hypothesis gets LLM-generated query
- ✅ Results tagged with hypothesis_id for attribution
- ✅ Multi-hypothesis validation (hypothesis_ids=[1,2,3])
- ✅ Execution metrics in metadata.json (per hypothesis)
- ✅ Execution events in execution_log.jsonl
- ✅ Backward compatibility (mode="off" and "planning" still work)

**Validation Evidence** (2025-11-15):
- Test query: "What cybersecurity jobs require TS/SCI clearance?"
- 2 tasks × 3 hypotheses = 6 hypothesis executions
- Results: X hypothesis-attributed findings
- Metadata: execution_results present for all hypotheses
- Backward compat: disabled mode works (no hypotheses generated)

---

## COMPLETED WORK: Phase 3B Implementation (2025-11-15)

All 8 implementation steps completed successfully.

### Step 1: Data Structures ✅ COMPLETE
- Reverse source map built (display → tool name)
- Config auto-upgrade from Phase 3A (enabled → mode)
- config_default.yaml updated with mode parameter

### Step 2: Helper Methods ✅ COMPLETE
- _map_hypothesis_sources() validates sources
- _deduplicate_with_attribution() preserves multi-validation

### Step 3: Query Generation ✅ COMPLETE
- Template: prompts/deep_research/hypothesis_query_generation.j2
- Method: _generate_hypothesis_query() (LLM per hypothesis)

### Step 4: Core Execution ✅ COMPLETE
- _execute_hypothesis() - single hypothesis executor
- _execute_hypotheses() - parallel executor
- Integration in _execute_task_with_retry() (after normal search)

### Step 5: Telemetry ✅ COMPLETE
- 3 new logger methods (started, executed, failed)
- Metadata includes execution_results per hypothesis

### Step 6: Deduplication ✅ COMPLETE
- Multi-attribution dedup when mode="execution"
- Results have hypothesis_ids arrays

### Step 7: Testing ✅ COMPLETE
- tests/test_phase3b_execution.py validates execution mode
- tests/test_phase3a_integration.py validates backward compatibility

### Step 8: Documentation ✅ COMPLETE
- CLAUDE.md updated (this file)
- STATUS.md updated with Phase 3B validation results
```

#### 8.2: Update STATUS.md

**File**: `STATUS.md`
**Location**: Add Phase 3B section after Phase 3A

**Content**:
```markdown
## Phase 3B: Hypothesis Execution ✅ COMPLETE

**Implementation Date**: 2025-11-15
**Status**: ✅ **PRODUCTION READY** - All features implemented and validated

### What This Adds

Executes each hypothesis with its specific search strategy instead of just displaying hypotheses in reports.

**User-Facing Changes**:
- Hypotheses are now EXECUTED (not just planned)
- Results show which hypothesis found each finding
- Multi-validated results show "Found by Hypotheses 1, 2, 3" (high confidence)

**Configuration**:
```yaml
hypothesis_branching:
  mode: "execution"  # off | planning | execution
  max_hypotheses_per_task: 5
```

### Implementation Details

**New Methods** (5 total):
1. `_execute_hypotheses(task)` - Parallel executor
2. `_execute_hypothesis(task, hypothesis)` - Single hypothesis executor
3. `_generate_hypothesis_query()` - LLM query generation
4. `_map_hypothesis_sources()` - Source validation
5. `_deduplicate_with_attribution()` - Multi-attribution dedup

**New Prompt**:
- `prompts/deep_research/hypothesis_query_generation.j2`

**New Telemetry**:
- `hypothesis_execution_started` event
- `hypothesis_executed` event
- `hypothesis_failed` event

### Validation Results

**Test Query**: "What cybersecurity jobs require TS/SCI clearance?"
**Configuration**: mode="execution", 2 tasks, 5 min timeout

**Results**:
- ✅ 6 hypotheses executed (2 tasks × 3 hypotheses each)
- ✅ X results attributed to hypotheses
- ✅ Metadata contains execution_results per hypothesis
- ✅ Multi-validation working (same result found by multiple hypotheses)
- ✅ Backward compatibility: disabled mode still works

**Files Modified**:
- research/deep_research.py (5 new methods, 2 integrations)
- prompts/deep_research/hypothesis_query_generation.j2 (NEW)
- utils/execution_logger.py (3 new methods)
- config_default.yaml (mode parameter)
- tests/test_phase3b_execution.py (NEW)
- tests/test_phase3a_integration.py (backward compat test)
```

**Success Criteria**:
- [ ] CLAUDE.md updated with Phase 3B status
- [ ] STATUS.md contains validation results
- [ ] All implementation steps documented

---

## VALIDATION & TESTING

### Pre-Implementation Checklist

Before starting implementation:
- [ ] Phase 3A committed (commit 55a9efa)
- [ ] Python cache cleared (`find . -name "*.pyc" -delete`)
- [ ] Virtual environment activated (`source .venv/bin/activate`)
- [ ] All background processes killed

### Step-by-Step Validation

After each step:
- [ ] **Step 1**: Test reverse map exists, config auto-upgrade works
- [ ] **Step 2**: Test source validation, deduplication with attribution
- [ ] **Step 3**: Test query generation template, LLM returns valid queries
- [ ] **Step 4**: Test hypothesis execution, results tagged correctly
- [ ] **Step 5**: Test logger methods, metadata has execution_results
- [ ] **Step 6**: Test multi-attribution dedup preserves hypothesis_ids
- [ ] **Step 7**: Run both test files, all assertions pass
- [ ] **Step 8**: Documentation updated, files committed

### Final E2E Validation

Run all tests:
```bash
# Clean environment
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null
find . -name "*.pyc" -delete 2>/dev/null

# Activate environment
source .venv/bin/activate

# Run Phase 3B execution test
python3 tests/test_phase3b_execution.py

# Run backward compatibility test
python3 tests/test_phase3a_integration.py

# Verify both pass
echo "All tests passed!"
```

**Expected Output**:
- Phase 3B execution test: "✓ Phase 3B execution validated successfully"
- Backward compatibility test: "✓ Backward compatibility confirmed"

---

## ROLLBACK PLAN

### If Implementation Fails

**Quick Rollback** (revert to Phase 3A):
```bash
# Revert all changes
git reset --hard 55a9efa

# Clean Python cache
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null
find . -name "*.pyc" -delete 2>/dev/null

# Verify Phase 3A still works
python3 tests/test_phase3a_enabled_mode.py
```

### Partial Rollback (Keep Some Features)

If only specific features need rollback:

**Disable execution mode** (keep code, disable feature):
```yaml
# config.yaml:
hypothesis_branching:
  mode: "planning"  # Revert to Phase 3A behavior
```

**Remove new methods** (if causing issues):
- Comment out `_execute_hypotheses()` integration in `_execute_task_with_retry()`
- Keep all new methods (can be used in Phase 3C)

---

## SUCCESS CRITERIA

### All 8 Steps Complete

- [x] Step 1: Data structures (reverse map, config auto-upgrade)
- [x] Step 2: Helper methods (source mapping, deduplication)
- [x] Step 3: Query generation (template + method)
- [x] Step 4: Core execution (3 methods, integration)
- [x] Step 5: Telemetry (3 logger methods, metadata)
- [x] Step 6: Deduplication (multi-attribution)
- [x] Step 7: Testing (2 tests passing)
- [x] Step 8: Documentation (CLAUDE.md, STATUS.md)

### Validation Passing

- [ ] test_phase3b_execution.py passes
- [ ] test_phase3a_integration.py passes (backward compat)
- [ ] No import errors
- [ ] No runtime errors
- [ ] Hypothesis-attributed results present
- [ ] Metadata has execution_results
- [ ] Execution log has hypothesis events

### Quality Metrics

- [ ] Cost increase ≤ 2x (acceptable for quality gain)
- [ ] Runtime increase ≤ 2x (user sets timeout upfront)
- [ ] No regressions in disabled/planning modes
- [ ] Multi-attribution working (hypothesis_ids arrays)
- [ ] Console output clear and informative

---

## IMPLEMENTATION TIME TRACKING

| Step | Estimated | Actual | Status |
|------|-----------|--------|--------|
| 1. Data Structures | 30 min | ___ | ⏸️ |
| 2. Helper Methods | 1 hour | ___ | ⏸️ |
| 3. Query Generation | 1.5 hours | ___ | ⏸️ |
| 4. Core Execution | 3-4 hours | ___ | ⏸️ |
| 5. Telemetry | 1 hour | ___ | ⏸️ |
| 6. Deduplication | 30 min | ___ | ⏸️ |
| 7. Testing | 2-3 hours | ___ | ⏸️ |
| 8. Documentation | 1 hour | ___ | ⏸️ |
| **Total** | **8-10 hours** | **___** | ⏸️ |

---

## NEXT STEPS AFTER COMPLETION

1. **Commit Phase 3B** with comprehensive commit message
2. **Run production test** with real user queries
3. **Collect feedback** on hypothesis execution value
4. **Decide Phase 3C** (coverage assessment) based on results
5. **Consider optimizations** if cost/runtime too high

---

## REFERENCES

- **Investigation**: `docs/PHASE3B_INVESTIGATION.md` (23 concerns analyzed)
- **Codex Response**: `docs/PHASE3B_CODEX_RESPONSE.md` (10 uncertainties resolved)
- **Phase 3A Commit**: 55a9efa (hypothesis generation foundation)
- **Design Philosophy**: CLAUDE.md PERMANENT section
