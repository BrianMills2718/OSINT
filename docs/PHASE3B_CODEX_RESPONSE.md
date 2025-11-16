# Phase 3B: Response to Codex's Implementation Concerns

**Date**: 2025-11-15
**Purpose**: Address Codex's 10 key uncertainties with concrete implementation decisions
**Status**: Investigation complete - Ready for implementation

---

## EXECUTIVE SUMMARY

Codex identified 10 critical uncertainties. All have been investigated and resolved with concrete decisions:

**Key Decisions**:
1. **Execution Path**: New method `_execute_hypothesis()` called from within `_execute_task_with_retry()`
2. **Source Mapping**: Build `DISPLAY_TO_TOOL_MAP` for reverse lookup
3. **Phase 2 Integration**: Hypothesis sources take precedence, Phase 2 disabled during hypothesis execution
4. **Budget Policy**: No per-hypothesis retries, parallel execution, use existing task timeout
5. **Coverage**: Defer to Phase 3C (don't implement coverage assessment yet)
6. **Result Attribution**: Use `hypothesis_id` tag in flat results array
7. **Prompts**: Create `hypothesis_query_generation.j2` template
8. **Telemetry**: Add 3 new event types to execution logger
9. **Testing**: 2 new tests (enabled execution, backward compatibility)
10. **Config**: Add `mode: "execution"`, reuse existing safety valves

**Implementation Estimate**: 8-10 hours (architecture: 5h, prompts: 1h, testing: 2h, telemetry: 1h, documentation: 1h)

---

## CONCERN #1: Execution Path & API Surface

### Codex's Question
> "research/deep_research.py (lines 1146-1390) still runs the legacy _execute_task_with_retry() pipeline. Phase 3B needs a second path (_execute_task_with_hypotheses() + _execute_hypothesis()) but nothing references task.hypotheses after generation except when persisting/reporting."

### Investigation

**Current Flow** (Phase 3A):
```python
async def _execute_task_with_retry(task):
    while retry_count <= max_retries:
        selected_sources = await _select_relevant_sources(task.query)
        mcp_results = await _search_mcp_tools_selected(task.query, selected_sources)
        web_results = await _search_brave(task.query)
        all_results = mcp_results + web_results
        should_accept, relevant_indices, should_continue = await _validate_result_relevance(all_results)
        if should_accept:
            task.accumulated_results.extend(filtered_results)
            break  # Success
```

**Decision**: Expand within `_execute_task_with_retry()` - NOT a separate method

**Proposed Flow** (Phase 3B):
```python
async def _execute_task_with_retry(task):
    # NORMAL SEARCH (existing code - lines 1157-1340)
    while retry_count <= max_retries:
        # ... existing source selection, search, filter logic ...
        if should_accept:
            task.accumulated_results.extend(filtered_results)
            break

    # HYPOTHESIS EXECUTION (NEW - insert after line 1340, before entity extraction)
    if self.hypothesis_branching_enabled and task.hypotheses:
        if self.hypothesis_mode == "execution":  # Not just "planning"
            await self._execute_hypotheses(task)

    # ENTITY EXTRACTION (existing code - line 414+)
    if task.accumulated_results:
        entities = await self._extract_entities(task.accumulated_results)
```

**New Method** (insert around line 1340):
```python
async def _execute_hypotheses(self, task: ResearchTask) -> None:
    """
    Execute all hypotheses for a task in parallel.

    Phase 3B: Hypothesis Execution
    - Generates query per hypothesis using hypothesis.search_strategy.signals
    - Searches using hypothesis.search_strategy.sources (no source selection LLM call)
    - Tags results with hypothesis_id for attribution
    - Appends to task.accumulated_results

    Args:
        task: ResearchTask with task.hypotheses populated
    """
    hypotheses = task.hypotheses.get("hypotheses", [])
    if not hypotheses:
        return

    print(f"\n🔬 Executing {len(hypotheses)} hypotheses for Task {task.id}...")

    # Execute all hypotheses in parallel
    hypothesis_tasks = [
        self._execute_hypothesis(task, hyp)
        for hyp in hypotheses
    ]
    await asyncio.gather(*hypothesis_tasks, return_exceptions=True)

    print(f"✓ Hypothesis execution complete for Task {task.id}")


async def _execute_hypothesis(self, task: ResearchTask, hypothesis: Dict) -> None:
    """
    Execute a single hypothesis: generate query, search sources, filter, tag results.

    Args:
        task: Parent ResearchTask
        hypothesis: Hypothesis dict with id, statement, search_strategy, etc.
    """
    hyp_id = hypothesis["id"]
    hyp_statement = hypothesis["statement"]

    try:
        # Step 1: Generate hypothesis-specific query
        query = await self._generate_hypothesis_query(
            task_query=task.query,
            hypothesis_statement=hyp_statement,
            signals=hypothesis["search_strategy"]["signals"],
            expected_entities=hypothesis["search_strategy"]["expected_entities"]
        )

        # Step 2: Map display names to tool names
        display_sources = hypothesis["search_strategy"]["sources"]
        tool_sources = self._map_hypothesis_sources(display_sources)

        # Step 3: Search using hypothesis sources
        mcp_results = await self._search_mcp_tools_selected(
            query,
            tool_sources,
            limit=config.default_result_limit,
            task_id=task.id,
            attempt=task.retry_count,
            param_adjustments=None  # No param hints for hypotheses
        )

        # Step 4: Validate relevance (using hypothesis context)
        should_accept, reason, relevant_indices, _, _, _ = await self._validate_result_relevance(
            task_query=query,
            research_question=self.original_question,
            sample_results=mcp_results,
            hypothesis_context=hyp_statement  # NEW: Pass hypothesis context
        )

        # Step 5: Filter and tag results
        filtered_results = [mcp_results[i] for i in relevant_indices]
        tagged_results = [
            {**r, "hypothesis_id": hyp_id}
            for r in filtered_results
        ]

        # Step 6: Append to task results
        task.accumulated_results.extend(tagged_results)

        # Step 7: Log success
        print(f"  ✓ Hypothesis {hyp_id}: {len(tagged_results)} results")
        if self.logger:
            self.logger.log_hypothesis_executed(
                task_id=task.id,
                hypothesis_id=hyp_id,
                query=query,
                sources=display_sources,
                results_found=len(mcp_results),
                results_kept=len(tagged_results)
            )

    except Exception as e:
        # Continue on failure (don't kill task)
        print(f"  ⚠️  Hypothesis {hyp_id} failed: {type(e).__name__}: {e}")
        if self.logger:
            self.logger.log_hypothesis_failed(
                task_id=task.id,
                hypothesis_id=hyp_id,
                error=str(e)
            )
```

**Key Design Decisions**:
1. **No separate execution path**: Hypotheses execute AFTER normal search within same task
2. **Reuse existing methods**: `_search_mcp_tools_selected()`, `_validate_result_relevance()`
3. **Single-shot execution**: No per-hypothesis retry loop (keep it simple)
4. **Parallel execution**: All hypotheses run concurrently via `asyncio.gather()`

---

## CONCERN #2: Source Mapping Ambiguity

### Codex's Question
> "Hypotheses store human-readable names ('USAJobs', 'Twitter') in search_strategy.sources. We need a deterministic map back to tool IDs (search_usajobs, search_twitter) and to flag invalid entries."

### Investigation

**Current State**:
- Tool names: `search_usajobs`, `search_twitter`, `search_reddit`
- Display names: `USAJobs`, `Twitter`, `Reddit`
- Mapping exists: `self.tool_name_to_display = {"search_usajobs": "USAJobs", ...}`

**Problem**: Need REVERSE mapping (display → tool)

**Solution**: Build reverse map at initialization

**Code** (add to `__init__()` around line 200):
```python
# Build reverse map: display name → tool name
self.display_to_tool_map = {
    display: tool_name
    for tool_name, display in self.tool_name_to_display.items()
}
```

**Validation Method** (new helper):
```python
def _map_hypothesis_sources(self, display_sources: List[str]) -> List[str]:
    """
    Map hypothesis display names to tool names, with validation.

    Args:
        display_sources: List of human-readable source names from hypothesis

    Returns:
        List of tool names (MCP function names)

    Raises:
        ValueError: If any source name is invalid
    """
    tool_sources = []
    invalid_sources = []

    for display_name in display_sources:
        tool_name = self.display_to_tool_map.get(display_name)
        if tool_name:
            tool_sources.append(tool_name)
        else:
            invalid_sources.append(display_name)

    if invalid_sources:
        # Log warning but continue (don't fail entire hypothesis)
        logging.warning(f"Invalid source names in hypothesis: {invalid_sources}")
        print(f"⚠️  Skipping invalid sources: {', '.join(invalid_sources)}")

    return tool_sources
```

**Example**:
```python
# Hypothesis says: ["USAJobs", "Twitter", "InvalidSource"]
# Maps to: ["search_usajobs", "search_twitter"]
# Logs warning: "Skipping invalid sources: InvalidSource"
```

**Decision**: Build reverse map at init, validate on use, log warnings for invalid sources

---

## CONCERN #3: Integration with Phase 2 Features

### Codex's Question
> "Phase 2 re-selection and param hints currently operate per task/attempt. When hypotheses provide explicit source lists, do we still allow _select_relevant_sources() to override them on retries?"

### Investigation

**Phase 2 Features**:
1. **Source Re-Selection**: LLM adjusts sources on retry based on performance
2. **Param Hints**: LLM suggests source-specific parameters (e.g., Twitter `search_type: "Top"`)

**Conflict**:
- Phase 2: LLM decides sources dynamically (drop Brave, add ClearanceJobs)
- Phase 3B: Hypothesis pre-specifies sources (["USAJobs", "Twitter"])

**Decision**: Hypotheses take precedence, Phase 2 disabled during hypothesis execution

**Rationale**:
- Hypothesis quality depends on testing SPECIFIC source combination
- Changing sources mid-execution defeats hypothesis validation
- Phase 2 still runs for normal task search (before hypotheses)

**Implementation**:
```python
async def _execute_hypothesis(self, task, hypothesis):
    # ...

    # NO source re-selection for hypotheses
    # Use hypothesis.search_strategy.sources directly
    display_sources = hypothesis["search_strategy"]["sources"]
    tool_sources = self._map_hypothesis_sources(display_sources)

    # NO param hints for hypotheses (single-shot, no retry)
    mcp_results = await self._search_mcp_tools_selected(
        query,
        tool_sources,
        limit=config.default_result_limit,
        task_id=task.id,
        attempt=task.retry_count,
        param_adjustments=None  # Explicitly None
    )
```

**Tradeoff**: Lose Phase 2 benefits during hypothesis execution, but gain hypothesis fidelity

---

## CONCERN #4: Budget & Sequencing Policy

### Codex's Question
> "The doc proposes sequential exploration with priority order, but there's no implementation detail for: (1) how many results constitute 'enough', (2) how hypothesis retries interact with task retries, (3) how to honor max_concurrent_tasks"

### Investigation

**Question 1: How many results is "enough"?**
- **Decision**: No stopping criteria (execute all hypotheses)
- **Rationale**: User sets `max_hypotheses_per_task` ceiling upfront, walks away
- **Design philosophy**: "Full autonomous execution, no mid-run decisions"

**Question 2: Hypothesis retries vs task retries?**
- **Decision**: No per-hypothesis retries (single-shot execution)
- **Rationale**: Keeps complexity low, avoids nested retry loops
- **Retry budget**: Only task-level retries (existing max_retries_per_task)

**Question 3: max_concurrent_tasks interaction?**
- **Current**: 3 tasks run in parallel (asyncio.gather in batch)
- **With hypotheses**: Each task internally runs 3 hypotheses in parallel
- **Total parallelism**: 3 tasks × 3 hypotheses = 9 concurrent searches (no change to task concurrency)

**Sequencing Policy**:
```python
# Sequential order:
# 1. Normal task search (with retries, Phase 2 adjustments)
# 2. Hypothesis execution (all in parallel, no retries)
# 3. Entity extraction (once, from all accumulated results)

async def _execute_task_with_retry(task):
    # Step 1: Normal search (existing retry loop)
    while retry_count <= max_retries:
        # ... normal search with retries ...
        if should_accept:
            break

    # Step 2: Hypothesis execution (no retry, parallel)
    if hypothesis_mode == "execution":
        await self._execute_hypotheses(task)  # All hypotheses in parallel

    # Step 3: Entity extraction (once, from normal + hypothesis results)
    entities = await self._extract_entities(task.accumulated_results)
```

**Timeouts**:
- Task-level timeout: existing `max_time_minutes` × 60 (applies to entire task)
- Hypothesis-level timeout: None (inherits from task timeout)
- Per-search timeout: existing 30s (in `_search_mcp_tools_selected`)

**Decision**: Simple sequential policy (normal → hypotheses → entities), no per-hypothesis retries, parallel hypothesis execution

---

## CONCERN #5: Coverage Assessment Inputs

### Codex's Question
> "Phase 3B requires capturing per-hypothesis metrics (results kept, sources tried, entities found) to hand to Phase 3C coverage prompt. Right now we only store aggregate task stats."

### Investigation

**Phase 3C (Coverage Assessment)**: NOT in scope for Phase 3B

**Decision**: Store per-hypothesis metrics in metadata, but don't use them yet

**Data Structure** (extend `metadata.json`):
```json
{
  "hypotheses_by_task": {
    "0": {
      "hypotheses": [...],  // Existing (hypothesis definitions)
      "execution_results": {  // NEW: Per-hypothesis execution metrics
        "1": {
          "query_generated": "GS-2210 official OPM classification standards",
          "sources_searched": ["Brave Search", "USAJobs"],
          "results_found": 15,
          "results_kept": 12,
          "execution_time_ms": 3420,
          "status": "success",
          "error": null
        },
        "2": {
          "query_generated": "GS-2210 job postings cybersecurity network analysis",
          "sources_searched": ["USAJobs", "ClearanceJobs"],
          "results_found": 8,
          "results_kept": 5,
          "execution_time_ms": 2150,
          "status": "success",
          "error": null
        }
      }
    }
  }
}
```

**Implementation** (in `_save_research_output()`):
```python
# Build execution_results from logger
if self.hypothesis_branching_enabled and self.hypothesis_mode == "execution":
    for task in (self.completed_tasks + self.failed_tasks):
        if task.hypotheses:
            # Extract per-hypothesis metrics from execution log
            execution_results = self._build_hypothesis_metrics(task.id)
            metadata["hypotheses_by_task"][task.id]["execution_results"] = execution_results
```

**Decision**: Capture metrics now, defer coverage assessment to Phase 3C

---

## CONCERN #6: Result Aggregation & Deduplication

### Codex's Question
> "With multiple hypotheses, dedup has to span hypotheses while still letting the report attribute findings back to the hypothesis that surfaced them. Decide whether we maintain results_by_hypothesis and merge later or push everything into existing arrays (losing attribution)."

### Investigation

**Current Deduplication** (Phase 3A):
- Happens at synthesis (after all tasks complete)
- Uses URL/title matching across all `accumulated_results`
- No hypothesis attribution

**Decision**: Use `hypothesis_id` tag + multi-attribution during dedup

**Storage** (no change to existing structure):
```python
task.accumulated_results = [
    {"title": "X", "url": "...", "source": "USAJobs", "hypothesis_id": 1},
    {"title": "Y", "url": "...", "source": "USAJobs", "hypothesis_id": 2},
    {"title": "Z", "url": "...", "source": "USAJobs"}  # From normal search (no hypothesis_id)
]
```

**Deduplication Logic** (modify `_save_research_output()` around line 2270):
```python
def _deduplicate_with_attribution(results: List[Dict]) -> List[Dict]:
    """
    Deduplicate results while preserving multi-hypothesis attribution.

    If same result found by multiple hypotheses, keep single copy with
    hypothesis_ids=[1,2,3] array.
    """
    seen = {}  # key: (url or title) → result dict

    for result in results:
        key = result.get("url") or result.get("title")
        if not key:
            continue

        if key in seen:
            # Duplicate - merge hypothesis_ids
            existing_hyp = seen[key].get("hypothesis_ids", [])
            if "hypothesis_id" in seen[key] and seen[key]["hypothesis_id"] not in existing_hyp:
                existing_hyp.append(seen[key]["hypothesis_id"])
                del seen[key]["hypothesis_id"]  # Replace with array
                seen[key]["hypothesis_ids"] = existing_hyp

            new_hyp = result.get("hypothesis_id")
            if new_hyp and new_hyp not in existing_hyp:
                existing_hyp.append(new_hyp)
        else:
            # First occurrence
            seen[key] = result.copy()
            if "hypothesis_id" in seen[key]:
                # Convert to array for consistency
                seen[key]["hypothesis_ids"] = [seen[key]["hypothesis_id"]]
                del seen[key]["hypothesis_id"]

    return list(seen.values())
```

**Report Format**:
```markdown
## Key Findings

**Finding 1**: GS-2210 series covers IT management roles
- Validated by: Hypotheses 1, 2 (high confidence - multiple pathways found same result)
- Source: OPM.gov official documentation

**Finding 2**: Cybersecurity roles frequently classified as GS-2210
- Found by: Hypothesis 2 only
- Source: USAJobs postings analysis
```

**Decision**: Tag with `hypothesis_id`, convert to `hypothesis_ids` array during dedup, show multi-validation in report

---

## CONCERN #7: Prompt Inventory

### Codex's Question
> "We'll need at least one new template for hypothesis-specific query reformulation. Today _select_relevant_sources and _reformulate_for_relevance assume a single task query."

### Investigation

**New Prompt Needed**: `hypothesis_query_generation.j2`

**Template** (create at `prompts/deep_research/hypothesis_query_generation.j2`):
```jinja2
{#
Hypothesis Query Generation - Phase 3B
Generates a search query tailored to a specific hypothesis

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
- Incorporate key signals from the list above
- Target the expected entities
- Keep it concise (3-10 words ideal)
- Use natural language (not just keyword mashing)

**Examples**:
- Good: "GS-2210 official OPM classification standards"
- Good: "federal cybersecurity jobs TS/SCI clearance requirements"
- Bad: "GS-2210 OPM federal government jobs classification" (too generic)
- Bad: "cybersecurity" (too broad, misses signals)

**Output Format** (JSON):
```json
{
  "query": "Your search query here"
}
```

Generate the query now.
```

**Method** (new in `deep_research.py`):
```python
async def _generate_hypothesis_query(
    self,
    task_query: str,
    hypothesis_statement: str,
    signals: List[str],
    expected_entities: List[str]
) -> str:
    """
    Generate search query for a specific hypothesis.

    Phase 3B: Hypothesis Execution

    Args:
        task_query: Parent task query
        hypothesis_statement: What this hypothesis is looking for
        signals: Keywords/patterns from hypothesis.search_strategy.signals
        expected_entities: Entities from hypothesis.search_strategy.expected_entities

    Returns:
        Search query string
    """
    prompt = render_prompt(
        "deep_research/hypothesis_query_generation.j2",
        task_query=task_query,
        hypothesis_statement=hypothesis_statement,
        signals=signals,
        expected_entities=expected_entities
    )

    schema = {
        "type": "object",
        "properties": {
            "query": {"type": "string"}
        },
        "required": ["query"]
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

**Modification to Relevance Validation** (optional - pass hypothesis context):
```python
# In _validate_result_relevance(), add optional parameter:
async def _validate_result_relevance(
    self,
    task_query: str,
    research_question: str,
    sample_results: List[Dict],
    hypothesis_context: Optional[str] = None  # NEW
) -> Tuple[...]:

    # Pass to prompt if present
    prompt = render_prompt(
        "deep_research/relevance_evaluation.j2",
        research_question=research_question,
        task_query=task_query,
        results=sample_results,
        hypothesis_context=hypothesis_context  # NEW: Helps LLM understand context
    )
```

**Decision**: Create `hypothesis_query_generation.j2`, add `_generate_hypothesis_query()` method, optionally pass hypothesis context to relevance evaluation

---

## CONCERN #8: Telemetry & UX

### Codex's Question
> "Execution logs currently record source_selection, query_reformulation, task_completed. We need new event types for hypothesis_started, hypothesis_completed, hypothesis_skipped, and coverage decisions."

### Investigation

**New Event Types Needed**:
1. `hypothesis_execution_started`
2. `hypothesis_executed` (success)
3. `hypothesis_failed` (error)

**Implementation** (add to `utils/execution_logger.py`):
```python
def log_hypothesis_execution_started(self, task_id: int, hypothesis_id: int, hypothesis_statement: str):
    """Log start of hypothesis execution."""
    self._write_event({
        "event": "hypothesis_execution_started",
        "task_id": task_id,
        "hypothesis_id": hypothesis_id,
        "hypothesis_statement": hypothesis_statement,
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
    """Log successful hypothesis execution."""
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

def log_hypothesis_failed(self, task_id: int, hypothesis_id: int, error: str):
    """Log failed hypothesis execution."""
    self._write_event({
        "event": "hypothesis_failed",
        "task_id": task_id,
        "hypothesis_id": hypothesis_id,
        "error": error,
        "timestamp": datetime.now().isoformat()
    })
```

**Console Output**:
```
🔬 Executing 3 hypotheses for Task 0...
  ✓ Hypothesis 1: 12 results (15 found, 12 kept)
  ✓ Hypothesis 2: 5 results (8 found, 5 kept)
  ⚠️  Hypothesis 3 failed: TimeoutError: ClearanceJobs search timed out
✓ Hypothesis execution complete for Task 0
```

**Decision**: Add 3 new event types to execution logger, keep console output concise (one line per hypothesis)

---

## CONCERN #9: Testing Footprint

### Codex's Question
> "We'll have to add at least two new automated tests: (1) Enabled sequential execution, (2) Backward compatibility. These tests don't exist yet."

### Investigation

**Test 1: Execution Mode Enabled** (new file `tests/test_phase3b_execution.py`):
```python
#!/usr/bin/env python3
"""
Phase 3B: Hypothesis Execution Test

Validates:
- Hypotheses are executed (not just generated)
- Results are tagged with hypothesis_id
- Metadata contains execution_results per hypothesis
- Report contains hypothesis-attributed findings
"""

async def test_phase3b_execution():
    research = SimpleDeepResearch(
        max_tasks=2,
        max_retries_per_task=1,
        max_time_minutes=5,
        hypothesis_branching_enabled=True,
        hypothesis_mode="execution"  # NEW: Triggers execution
    )

    result = await research.research("What cybersecurity jobs require TS/SCI clearance?")

    # Validation 1: Hypotheses executed
    assert result['tasks_executed'] > 0

    # Validation 2: Results have hypothesis_id tags
    output_dir = Path(result['output_directory'])
    results_file = output_dir / "results.json"
    with open(results_file) as f:
        results_data = json.load(f)

    hypothesis_tagged = [r for r in results_data['results'] if 'hypothesis_id' in r or 'hypothesis_ids' in r]
    assert len(hypothesis_tagged) > 0, "No results tagged with hypothesis_id"

    # Validation 3: Metadata contains execution_results
    metadata_file = output_dir / "metadata.json"
    with open(metadata_file) as f:
        metadata = json.load(f)

    assert "hypotheses_by_task" in metadata
    for task_id, task_data in metadata["hypotheses_by_task"].items():
        assert "execution_results" in task_data, f"Task {task_id} missing execution_results"
        assert len(task_data["execution_results"]) > 0

    # Validation 4: Report contains hypothesis findings
    report_file = output_dir / "report.md"
    with open(report_file) as f:
        report_text = f.read()

    assert "Hypothesis" in report_text, "Report missing hypothesis attribution"

    print("[PASS] Phase 3B execution validated")
```

**Test 2: Backward Compatibility** (modify existing `tests/test_phase3a_integration.py`):
```python
# Add validation that disabled mode still works
def test_phase3a_disabled_mode():
    """Verify hypothesis_mode='off' doesn't break anything."""
    research = SimpleDeepResearch(
        max_tasks=2,
        hypothesis_branching_enabled=False  # Disabled
    )

    result = await research.research("What is the GS-2210 job series?")

    # Should work exactly like Phase 0 (no hypotheses)
    assert result['tasks_executed'] > 0
    assert 'hypotheses_by_task' not in result  # No hypotheses generated
```

**Decision**: Add 2 new tests (execution validation, backward compatibility), estimated 2-3 hours

---

## CONCERN #10: Config Knobs Still TBD

### Codex's Question
> "The doc references potential options (hypothesis_mode, exploration_mode, budget ceilings). Only enabled and max_hypotheses_per_task are implemented. If we don't add explicit controls, cost explosion becomes reality with no safety valve."

### Investigation

**Current Config** (Phase 3A):
```yaml
hypothesis_branching:
  enabled: true
  max_hypotheses_per_task: 5
```

**Proposed Phase 3B Config**:
```yaml
hypothesis_branching:
  mode: "execution"  # off | planning | execution
  max_hypotheses_per_task: 5  # Ceiling on hypothesis count
  # All other controls use existing safety valves:
  # - max_retries_per_task (existing)
  # - max_time_minutes (existing)
  # - default_result_limit (existing, per-integration)
```

**Safety Valves** (already exist, no new config needed):
1. **max_hypotheses_per_task**: Limits hypothesis count (already implemented)
2. **max_time_minutes**: Task timeout (already enforced at batch level)
3. **max_retries_per_task**: No per-hypothesis retries (use existing task-level budget)
4. **default_result_limit**: Limits results per search (already per-integration)
5. **max_concurrent_tasks**: Limits parallel tasks (already enforced)

**No New Config Needed**:
- `max_hypothesis_retries`: Not needed (single-shot execution)
- `hypothesis_execution_timeout`: Not needed (use task timeout)
- `exploration_mode`: Not needed (always parallel)

**Backward Compatibility** (auto-upgrade from Phase 3A):
```python
# In __init__():
raw_config = config.get_raw_config()
hyp_config = raw_config.get("research", {}).get("hypothesis_branching", {})

# Handle legacy "enabled: true" (Phase 3A)
if "enabled" in hyp_config and "mode" not in hyp_config:
    if hyp_config["enabled"]:
        self.hypothesis_mode = "planning"  # Legacy behavior
        logging.warning("⚠️  hypothesis_branching.enabled is deprecated, use mode: 'planning'")
    else:
        self.hypothesis_mode = "off"
else:
    # New "mode" config (Phase 3B)
    self.hypothesis_mode = hyp_config.get("mode", "off")  # off | planning | execution
```

**Decision**: Add `mode` config (off|planning|execution), reuse existing safety valves, auto-upgrade legacy config

---

## IMPLEMENTATION PLAN

### Phase 3B Implementation Steps (8-10 hours)

**Step 1: Data Structures** (30 min)
- [ ] Add `self.display_to_tool_map` in `__init__()`
- [ ] Add `hypothesis_mode` config reading with auto-upgrade
- [ ] Update `ResearchTask` (no changes needed - already has `hypotheses` field)

**Step 2: Core Methods** (3-4 hours)
- [ ] Create `_execute_hypotheses(task)` - parallel execution loop
- [ ] Create `_execute_hypothesis(task, hypothesis)` - single hypothesis execution
- [ ] Create `_generate_hypothesis_query()` - query generation
- [ ] Create `_map_hypothesis_sources()` - source name validation

**Step 3: Integration** (1 hour)
- [ ] Modify `_execute_task_with_retry()` to call `_execute_hypotheses()` after normal search
- [ ] Modify `_validate_result_relevance()` to accept optional `hypothesis_context` parameter

**Step 4: Prompts** (1 hour)
- [ ] Create `prompts/deep_research/hypothesis_query_generation.j2`
- [ ] Optionally update `prompts/deep_research/relevance_evaluation.j2` to use hypothesis context

**Step 5: Telemetry** (1 hour)
- [ ] Add 3 new logger methods to `utils/execution_logger.py`
- [ ] Add logging calls in `_execute_hypothesis()`
- [ ] Build `execution_results` in `_save_research_output()`

**Step 6: Deduplication** (30 min)
- [ ] Create `_deduplicate_with_attribution()` helper
- [ ] Modify `_save_research_output()` to use multi-attribution dedup

**Step 7: Testing** (2-3 hours)
- [ ] Create `tests/test_phase3b_execution.py`
- [ ] Modify `tests/test_phase3a_integration.py` (add backward compat check)
- [ ] Run both tests, verify all assertions pass

**Step 8: Documentation** (1 hour)
- [ ] Update `CLAUDE.md` with Phase 3B status
- [ ] Update `STATUS.md` with validation results
- [ ] Update `config_default.yaml` with `mode` parameter

**Total**: 8-10 hours

---

## RISK ASSESSMENT

### High Risk (Mitigated)
- ✅ **Cost explosion**: Mitigated by `max_hypotheses_per_task` ceiling + no retries
- ✅ **Complex control flow**: Mitigated by simple sequential design (normal → hypotheses)
- ✅ **Source mapping errors**: Mitigated by validation + warning logs

### Medium Risk (Acceptable)
- ⚠️ **Runtime increase**: 2x expected, but user sets timeout ceiling upfront
- ⚠️ **Report length**: 2x expected, but structured/collapsible
- ⚠️ **Hypothesis overlap**: Allowed, LLM should minimize via prompt guidance

### Low Risk (Not Concerned)
- ✅ **Memory footprint**: 480KB vs 120KB (negligible)
- ✅ **API rate limits**: Circuit breaker already handles
- ✅ **Backward compatibility**: Auto-upgrade handles legacy config
- ✅ **Testing footprint**: 2 new tests (manageable)

---

## FINAL RECOMMENDATION

✅ **PROCEED with Phase 3B implementation**

**All 10 Codex concerns resolved**:
1. ✅ Execution path defined (expand within task, new `_execute_hypotheses()` method)
2. ✅ Source mapping solved (reverse map + validation)
3. ✅ Phase 2 integration decided (hypothesis sources take precedence)
4. ✅ Budget policy clear (no per-hypothesis retries, parallel execution, existing timeouts)
5. ✅ Coverage assessment deferred to Phase 3C (capture metrics, don't use yet)
6. ✅ Result attribution solved (`hypothesis_id` tag + multi-attribution dedup)
7. ✅ Prompts defined (`hypothesis_query_generation.j2` template)
8. ✅ Telemetry specified (3 new event types)
9. ✅ Testing plan ready (2 new tests)
10. ✅ Config minimal (`mode` parameter + auto-upgrade)

**Implementation estimate**: 8-10 hours
**Cost increase**: 1.4x (with optimizations)
**Runtime increase**: 2x (acceptable for quality gain)

**Next step**: Begin implementation following the 8-step plan above.
