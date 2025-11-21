# Query Saturation - Implementation Plan
**Branch**: `feature/query-level-saturation`
**Created**: 2025-11-21
**Status**: Planning Phase

---

## Vision Statement

**Long-term goal**: Deep research system that investigates like an expert journalist:
1. **Iterative querying** until source is saturated (not one-shot)
2. **Following breadcrumbs** (entities, IDs, references discovered in results)
3. **Verifying claims** (cross-reference, detect contradictions, triangulate)
4. **Researching entities** (auto-investigate key organizations/people discovered)
5. **Learning and adapting** (improve strategies based on what works)

**Philosophy**: Each phase delivers independent value. Can stop after any phase and have a working, improved system.

---

## Phase 0: Baseline Documentation (CURRENT STATE)

**Goal**: Document current system performance as baseline for comparison

**Status**: ✅ COMPLETE (system is working)

**Current Behavior**:
- **Queries per source**: Exactly 1 (no iteration)
- **Research mode**: Single-shot per hypothesis
- **Time**: Predictable (1 query × N sources)
- **Results quality**: Good for simple queries, shallow for complex topics
- **Limitations**: Can't adapt queries, can't explore deep topics, can't follow leads

**Baseline Metrics** (from recent runs):
- Cuba sanctions: 3 tasks, 216 results, 27 entities, 8.4 minutes
- DoD AI contracts 2024: (running now)

**Validation**: ✅ System works, producing useful results

---

## Phase 1: Core Query Saturation

**Duration**: 2.5 weeks (12.5 days)
**Goal**: Enable iterative querying per source until LLM determines saturation
**Value**: 30-50% more results, better coverage of complex topics

### **Scope Definition**

**IN SCOPE** (must deliver):
1. ✅ While loop with LLM saturation decision (not `for i in range(N)`)
2. ✅ Query history tracking per source
3. ✅ User-configurable limits (max_queries_per_source, max_time_per_source_seconds)
4. ✅ Enhanced logging (per-query events with reasoning)
5. ✅ Source metadata for LLM guidance
6. ✅ Parallel source execution (sources in parallel, queries within source sequential)

**OUT OF SCOPE** (defer to later phases):
- ❌ Breadcrumb following (Phase 2)
- ❌ Verification/triangulation (Phase 3)
- ❌ Entity research (Phase 4)
- ❌ Learning metrics (Phase 5)

### **Prerequisites**

- ✅ Current system working (Phase 0 validated)
- ✅ Feature branch created (`feature/query-level-saturation`)
- ✅ Planning docs reviewed and approved

### **Implementation Steps** (Ordered)

#### **Step 1: Configuration Enhancement** (~30 min)
**File**: `research/deep_research.py` (SimpleDeepResearch.__init__)

**Changes**:
```python
def __init__(
    self,
    max_tasks: int = 10,
    max_retries_per_task: int = 2,
    max_time_minutes: int = 120,
    min_results_per_task: int = 5,
    max_concurrent_tasks: int = 3,

    # NEW: Query saturation config
    max_queries_per_source: Dict[str, int] = None,  # {source_name: limit}
    max_time_per_source_seconds: int = 300,  # 5 min default

    progress_callback: Optional[Callable] = None
):
    # ... existing code ...

    # Set defaults for query saturation
    self.max_queries_per_source = max_queries_per_source or {
        'SAM.gov': 10,
        'DVIDS': 5,
        'USAJobs': 5,
        'ClearanceJobs': 5,
        'Twitter': 3,
        'Reddit': 3,
        'Discord': 3,
        'Brave Search': 5
    }
    self.max_time_per_source_seconds = max_time_per_source_seconds
```

**Test**: Verify config loads correctly

---

#### **Step 2: Source Metadata** (~1 hour)
**File**: New file `integrations/source_metadata.py`

**Create**:
```python
from dataclasses import dataclass
from typing import List

@dataclass
class SourceMetadata:
    """Metadata about a data source to guide LLM query generation"""
    name: str
    description: str
    characteristics: Dict[str, Any]  # {"requires_formal_names": True, ...}
    query_strategies: List[str]  # Effective query patterns
    typical_result_count: int  # Expected results per query
    max_queries_recommended: int  # Suggested ceiling

# Define metadata for each source
SOURCE_METADATA = {
    'SAM.gov': SourceMetadata(
        name='SAM.gov',
        description='Federal contract awards and opportunities',
        characteristics={
            'requires_formal_names': True,  # "Department of Defense" not "DoD"
            'date_format': 'YYYY-MM-DD',
            'rich_metadata': True,
            'structured_data': True
        },
        query_strategies=[
            'exact_contract_id',
            'agency_name_keyword_date',
            'naics_code_filter'
        ],
        typical_result_count=50,
        max_queries_recommended=10
    ),
    'DVIDS': SourceMetadata(
        name='DVIDS',
        description='Department of Defense news and media',
        characteristics={
            'news_articles': True,
            'military_focused': True,
            'formal_tone': True
        },
        query_strategies=[
            'keyword_search',
            'unit_name_search',
            'topic_search'
        ],
        typical_result_count=20,
        max_queries_recommended=5
    ),
    # ... more sources
}
```

**Test**: Verify metadata accessible

---

#### **Step 3: Saturation Prompt** (~2 hours)
**File**: New file `prompts/deep_research/source_saturation.j2`

**Create**:
```jinja2
You are deciding whether to continue querying {{ source_name }} or if the source is saturated.

HYPOTHESIS: {{ hypothesis_statement }}
SOURCE: {{ source_name }}
SOURCE CHARACTERISTICS:
{{ source_metadata | tojson(indent=2) }}

QUERY HISTORY:
{% for query_attempt in query_history %}
{{ loop.index }}. Query: "{{ query_attempt.query }}"
   Results: {{ query_attempt.results_total }} total, {{ query_attempt.results_accepted }} accepted, {{ query_attempt.results_rejected }} rejected
   {% if query_attempt.rejection_themes %}
   Rejection themes: {{ query_attempt.rejection_themes | join(', ') }}
   {% endif %}
{% endfor %}

TOTAL RESULTS SO FAR: {{ total_results_accepted }} accepted across {{ query_history | length }} queries

CURRENT GAPS:
{% if information_gaps %}
{% for gap in information_gaps %}
- {{ gap }}
{% endfor %}
{% else %}
No specific gaps identified.
{% endif %}

DECISION FRAMEWORK:

**SATURATED** if:
1. High confidence we've found all relevant information that exists
2. Recent queries yielding only duplicates or off-topic results
3. Information clearly doesn't exist in this source
4. Queries are repeating similar patterns without new results

**CONTINUE** if:
1. Reasonable chance different query formulation could find more
2. Identified gaps that could be addressed with targeted queries
3. Source characteristics suggest more depth available
4. Haven't tried key query strategies yet

SATURATION GUIDANCE:
- Query effectiveness: Are we getting better or worse results?
- Terminology learning: Have we found keywords that work?
- Information existence: Does the info likely exist here?
- Diminishing returns: Are new queries adding value?
- Pattern recognition: If 3+ queries yield no new results → likely saturated
- Quality decline: If results declining in quality → likely saturated
- Duplicate signals: If hitting duplicates repeatedly → likely saturated

Return JSON:
{
    "decision": "SATURATED" or "CONTINUE",
    "reasoning": "2-3 sentences explaining your decision",
    "confidence": 0-100,  // Confidence in this decision
    "existence_confidence": 0-100,  // Confidence information exists in source
    "next_query_suggestion": "If CONTINUE, specific query to try next",
    "next_query_reasoning": "Why this query should work",
    "expected_value": "high" | "medium" | "low",  // Expected value of next query
    "remaining_gaps": [...]  // List of specific info gaps still unaddressed
}

If CONTINUE, provide a SPECIFIC query to try next that targets identified gaps or uses a different strategy.
```

**Test**: Verify template renders correctly

---

#### **Step 3.5: First Query Generation** (~1 hour)
**File**: `research/deep_research.py`

**Add method**:
```python
async def _generate_initial_query(
    self,
    hypothesis: Dict[str, Any],
    source_name: str,
    source_metadata: Dict[str, Any]
) -> str:
    """
    Generate first query from hypothesis (no query history yet).

    This is separate from _generate_next_query_or_stop because:
    - First query has no history to reason from
    - Uses hypothesis statement + source metadata only
    - Simpler prompt without saturation decision

    Returns:
        query: String query to execute
    """
    from core.prompt_loader import render_prompt

    # Use existing hypothesis query generation prompt (or create new one)
    prompt = render_prompt(
        'deep_research/hypothesis_query_generation.j2',
        hypothesis_statement=hypothesis['statement'],
        source_name=source_name,
        source_metadata=source_metadata,
        search_strategy=hypothesis.get('search_strategy', {}),
        information_gaps=hypothesis.get('information_gaps', [])
    )

    response = await acompletion(
        model=self.model,
        messages=[{"role": "user", "content": prompt}],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "initial_query",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "reasoning": {"type": "string"}
                    },
                    "required": ["query", "reasoning"]
                }
            }
        }
    )

    result = json.loads(response.choices[0].message.content)
    return result
```

**Test**: Unit test with sample hypothesis

---

#### **Step 4: Core Saturation Method** (~5 hours)
**File**: `research/deep_research.py`

**Add method**:
```python
async def _execute_source_with_saturation(
    self,
    task_id: int,
    task: Dict[str, Any],
    hypothesis: Dict[str, Any],
    source_name: str
) -> List[Dict[str, Any]]:
    """
    Execute queries against single source until saturated.

    Returns:
        List of accepted results from all queries
    """
    from integrations.source_metadata import SOURCE_METADATA

    query_history = []
    all_results = []
    seen_result_urls = set()  # Track URLs for within-source deduplication
    start_time = time.time()

    # Get source-specific limits
    max_queries = self.max_queries_per_source.get(source_name, 5)
    max_time = self.max_time_per_source_seconds
    source_metadata = SOURCE_METADATA.get(source_name, {})

    # Log saturation start
    self.logger.log_source_saturation_start(
        task_id=task_id,
        hypothesis_id=hypothesis.get('id'),
        source_name=source_name,
        max_queries=max_queries,
        max_time_seconds=max_time
    )

    while True:  # ✅ No hardcoded loop count
        query_num = len(query_history) + 1

        try:
            # FIRST QUERY: Different logic than subsequent queries
            if len(query_history) == 0:
                # Generate initial query from hypothesis (no history yet)
                initial = await self._generate_initial_query(
                    hypothesis=hypothesis,
                    source_name=source_name,
                    source_metadata=source_metadata
                )
                query_decision = {
                    'decision': 'CONTINUE',
                    'reasoning': 'Initial query for hypothesis',
                    'next_query_suggestion': initial['query'],
                    'next_query_reasoning': initial['reasoning'],
                    'confidence': 100,
                    'expected_value': 'high'
                }
            else:
                # SUBSEQUENT QUERIES: Check saturation and generate next query
                query_decision = await self._generate_next_query_or_stop(
                    task=task,
                    hypothesis=hypothesis,
                    source_name=source_name,
                    query_history=query_history,
                    source_metadata=source_metadata,
                    total_results_accepted=len(all_results)
                )

                # Update hypothesis information_gaps dynamically (if provided)
                if 'remaining_gaps' in query_decision:
                    hypothesis['information_gaps'] = query_decision['remaining_gaps']

                # PRIMARY EXIT: LLM says saturated
                if query_decision['decision'] == 'SATURATED':
                    self.logger.log_source_saturation_complete(
                        task_id=task_id,
                        hypothesis_id=hypothesis.get('id'),
                        source_name=source_name,
                        exit_reason='llm_saturated',
                        queries_executed=len(query_history),
                        results_accepted=len(all_results),
                        saturation_reasoning=query_decision['reasoning'],
                        decision_confidence=query_decision.get('confidence', 0)
                    )
                    break

        except Exception as e:
            logger.error(f"Error generating query for {source_name}: {e}")
            self.logger.log_source_saturation_complete(
                task_id=task_id,
                hypothesis_id=hypothesis.get('id'),
                source_name=source_name,
                exit_reason='query_generation_error',
                queries_executed=len(query_history),
                results_accepted=len(all_results),
                saturation_reasoning=f"Query generation failed: {str(e)}"
            )
            break

        # Validate query suggestion exists
        query = query_decision.get('next_query_suggestion', '').strip()
        if not query:
            logger.warning(f"Empty query suggestion from LLM for {source_name}")
            self.logger.log_source_saturation_complete(
                task_id=task_id,
                hypothesis_id=hypothesis.get('id'),
                source_name=source_name,
                exit_reason='empty_query_suggestion',
                queries_executed=len(query_history),
                results_accepted=len(all_results),
                saturation_reasoning="LLM suggested empty query"
            )
            break

        query_reasoning = query_decision.get('next_query_reasoning', '')

        self.logger.log_query_attempt(
            task_id=task_id,
            hypothesis_id=hypothesis.get('id'),
            source_name=source_name,
            query_num=query_num,
            query=query,
            reasoning=query_reasoning,
            expected_value=query_decision.get('expected_value', 'unknown')
        )

        try:
            # Call source API
            results = await self._execute_source_query(
                source_name=source_name,
                query=query,
                task_id=task_id
            )
        except Exception as e:
            logger.error(f"Source query failed for {source_name}: {e}")
            # Track failed attempt and continue
            query_history.append({
                'query': query,
                'reasoning': query_reasoning,
                'results_total': 0,
                'results_accepted': 0,
                'results_rejected': 0,
                'error': str(e),
                'effectiveness': 0
            })
            continue  # Try next query

        # Filter results using EXISTING relevance evaluation
        try:
            filtered = await self._evaluate_source_results(
                task_id=task_id,
                source_name=source_name,
                results=results,
                original_query=task['query'],
                attempt=0  # Not using retry logic here
            )
        except Exception as e:
            logger.error(f"Result filtering failed for {source_name}: {e}")
            query_history.append({
                'query': query,
                'reasoning': query_reasoning,
                'results_total': len(results),
                'results_accepted': 0,
                'results_rejected': len(results),
                'error': str(e),
                'effectiveness': 0
            })
            continue

        # Deduplicate within source (track URLs seen)
        accepted = filtered.get('accepted_results', [])
        new_results = []
        duplicate_count = 0

        for result in accepted:
            result_url = result.get('url', '') or result.get('id', '')
            if result_url and result_url not in seen_result_urls:
                new_results.append(result)
                seen_result_urls.add(result_url)
            else:
                duplicate_count += 1

        all_results.extend(new_results)

        # Track query attempt
        query_history.append({
            'query': query,
            'reasoning': query_reasoning,
            'results_total': len(results),
            'results_accepted': len(new_results),
            'results_rejected': len(results) - len(accepted),
            'results_duplicate': duplicate_count,
            'rejection_themes': filtered.get('rejection_themes', []),
            'effectiveness': len(new_results) / len(results) if results else 0
        })

        # SECONDARY EXIT: User-configured query limit
        if len(query_history) >= max_queries:
            self.logger.log_source_saturation_complete(
                task_id=task_id,
                hypothesis_id=hypothesis.get('id'),
                source_name=source_name,
                exit_reason='max_queries_reached',
                queries_executed=len(query_history),
                results_accepted=len(all_results),
                saturation_reasoning=f"Reached user-configured limit: {max_queries} queries"
            )
            break

        # TERTIARY EXIT: User-configured time limit
        elapsed = time.time() - start_time
        if elapsed > max_time:
            self.logger.log_source_saturation_complete(
                task_id=task_id,
                hypothesis_id=hypothesis.get('id'),
                source_name=source_name,
                exit_reason='time_limit_reached',
                queries_executed=len(query_history),
                results_accepted=len(all_results),
                saturation_reasoning=f"Reached time limit: {max_time}s"
            )
            break

    return all_results
```

**Test**: Unit test with mock source

---

#### **Step 5: Query Decision Method** (~2 hours)
**File**: `research/deep_research.py`

**Add method**:
```python
async def _generate_next_query_or_stop(
    self,
    task: Dict[str, Any],
    hypothesis: Dict[str, Any],
    source_name: str,
    query_history: List[Dict],
    source_metadata: Dict,
    total_results_accepted: int
) -> Dict[str, Any]:
    """
    LLM decides: continue with next query or stop (saturated).

    Returns:
        {
            "decision": "SATURATED" | "CONTINUE",
            "reasoning": "...",
            "confidence": 0-100,
            "next_query_suggestion": "...",  # if CONTINUE
            "next_query_reasoning": "...",   # if CONTINUE
            "expected_value": "high" | "medium" | "low",
            "remaining_gaps": [...]  # Updated list of info gaps
        }
    """
    from core.prompt_loader import render_prompt

    # NOTE: information_gaps should be updated dynamically:
    # - Initial gaps from hypothesis generation
    # - LLM updates "remaining_gaps" field after each query
    # - Caller updates hypothesis['information_gaps'] with remaining_gaps
    # This enables adaptive query generation targeting unaddressed gaps

    # Render saturation prompt
    prompt = render_prompt(
        'deep_research/source_saturation.j2',
        hypothesis_statement=hypothesis['statement'],
        source_name=source_name,
        source_metadata=source_metadata,
        query_history=query_history,
        total_results_accepted=total_results_accepted,
        information_gaps=hypothesis.get('information_gaps', [])
    )

    # LLM decision
    response = await acompletion(
        model=self.model,
        messages=[{"role": "user", "content": prompt}],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "saturation_decision",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "decision": {"type": "string", "enum": ["SATURATED", "CONTINUE"]},
                        "reasoning": {"type": "string"},
                        "confidence": {"type": "integer", "minimum": 0, "maximum": 100},
                        "existence_confidence": {"type": "integer", "minimum": 0, "maximum": 100},
                        "next_query_suggestion": {"type": "string"},
                        "next_query_reasoning": {"type": "string"},
                        "expected_value": {"type": "string", "enum": ["high", "medium", "low"]},
                        "remaining_gaps": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Updated list of information gaps still unaddressed"
                        }
                    },
                    "required": ["decision", "reasoning", "confidence"]
                }
            }
        }
    )

    decision = json.loads(response.choices[0].message.content)
    return decision
```

**Test**: Unit test with sample query history

---

#### **Step 6: Update Hypothesis Execution** (~2 hours)
**File**: `research/deep_research.py`

**Modify `_execute_hypothesis` method**:
```python
async def _execute_hypothesis(
    self,
    task_id: int,
    task: Dict[str, Any],
    hypothesis: Dict[str, Any]
) -> Dict[str, Any]:
    """Execute single hypothesis with query saturation."""

    # Select sources (existing code)
    selected_sources = await self._select_sources_for_task(
        task['query'],
        hypothesis['statement']
    )

    # Execute sources IN PARALLEL with saturation
    # (queries within each source are sequential)
    source_tasks = [
        self._execute_source_with_saturation(
            task_id=task_id,
            task=task,
            hypothesis=hypothesis,
            source_name=source_name
        )
        for source_name in selected_sources
    ]

    # Wait for all sources to complete
    source_results_lists = await asyncio.gather(*source_tasks, return_exceptions=True)

    # Combine results from all sources
    all_results = []
    for source_name, results in zip(selected_sources, source_results_lists):
        if isinstance(results, Exception):
            logger.error(f"Source {source_name} failed: {results}")
            continue
        all_results.extend(results)

    # Deduplicate across sources (existing code)
    unique_results = self._deduplicate_results(all_results)

    # Log hypothesis completion
    self.logger.log_hypothesis_execution_complete(
        task_id=task_id,
        hypothesis_id=hypothesis['id'],
        sources_executed=len(selected_sources),
        total_results=len(unique_results)
    )

    return {
        'hypothesis_id': hypothesis['id'],
        'results': unique_results,
        'sources_executed': selected_sources
    }
```

**Test**: Unit test with mock sources

---

#### **Step 7: Logging Enhancements** (~2 hours)
**File**: `research/execution_logger.py`

**Add methods**:
```python
def log_source_saturation_start(self, task_id, hypothesis_id, source_name,
                                  max_queries, max_time_seconds):
    """Log start of source saturation."""
    self._write_entry(task_id, "source_saturation_start", {
        "hypothesis_id": hypothesis_id,
        "source_name": source_name,
        "max_queries": max_queries,
        "max_time_seconds": max_time_seconds
    })

def log_query_attempt(self, task_id, hypothesis_id, source_name,
                       query_num, query, reasoning, expected_value=None):
    """Log individual query attempt."""
    self._write_entry(task_id, "query_attempt", {
        "hypothesis_id": hypothesis_id,
        "source_name": source_name,
        "query_num": query_num,
        "query": query,
        "reasoning": reasoning,
        "expected_value": expected_value  # high | medium | low
    })

def log_source_saturation_complete(self, task_id, hypothesis_id, source_name,
                                     exit_reason, queries_executed,
                                     results_accepted, saturation_reasoning,
                                     decision_confidence=None):
    """Log completion of source saturation."""
    self._write_entry(task_id, "source_saturation_complete", {
        "hypothesis_id": hypothesis_id,
        "source_name": source_name,
        "exit_reason": exit_reason,  # llm_saturated | max_queries_reached | time_limit_reached | query_generation_error | empty_query_suggestion
        "queries_executed": queries_executed,
        "results_accepted": results_accepted,
        "saturation_reasoning": saturation_reasoning,
        "decision_confidence": decision_confidence  # 0-100 (if LLM saturation)
    })

def log_hypothesis_execution_complete(self, task_id, hypothesis_id,
                                        sources_executed, total_results):
    """Log completion of hypothesis execution."""
    self._write_entry(task_id, "hypothesis_execution_complete", {
        "hypothesis_id": hypothesis_id,
        "sources_executed": sources_executed,
        "total_results": total_results
    })
```

**Test**: Verify logging writes to JSONL

---

#### **Step 8: Integration Testing** (~1 day)

**Test Sequence**:

1. **Unit Tests** (~2 hours)
   ```bash
   # Test saturation decision logic
   pytest tests/test_saturation_decision.py -v

   # Test query generation
   pytest tests/test_query_generation_with_history.py -v

   # Test source execution
   pytest tests/test_source_saturation.py -v
   ```

2. **Single Source Test** (~2 hours)
   ```python
   # Test with SAM.gov only, 1 hypothesis
   # Verify: Multiple queries executed, saturation triggered
   python3 -c "
   from research.deep_research import SimpleDeepResearch
   engine = SimpleDeepResearch(max_queries_per_source={'SAM.gov': 3})
   result = await engine.research('DoD AI contracts 2024')
   print(f'Queries executed: {result}')
   "
   ```

3. **Multi-Source Test** (~2 hours)
   ```python
   # Test with SAM.gov + DVIDS + Brave, 1 hypothesis
   # Verify: Sources execute in parallel, each saturates independently
   ```

4. **E2E Test** (~2 hours)
   ```bash
   # Full research query with multiple tasks, hypotheses, sources
   python3 run_research.py "recent Department of Defense AI contracts 2024"

   # Verify:
   # - Multiple queries per source
   # - Saturation decisions logged
   # - Results quality improved vs baseline
   # - No crashes or timeouts
   ```

---

### **Success Criteria** (Phase 1 Validation Gate)

Must ALL pass to proceed to Phase 2:

- [ ] **Multi-query execution**: System executes 2+ queries per source on at least 70% of sources (not stuck at 1)
- [ ] **LLM intelligence**: LLM stops before hitting max_queries in >70% of sources (indicates adaptive saturation)
- [ ] **Adaptive behavior**: Average queries per source: 3-5 (shows system is neither stopping too early nor hitting limits constantly)
- [ ] **Result quality**: Finds 30%+ more results than baseline (measured on same test query)
- [ ] **Safety limits**: No infinite loops (all sources respect max_queries/max_time)
- [ ] **Performance**: <2x baseline execution time
- [ ] **Logging completeness**: All query attempts logged with reasoning, confidence scores, and expected_value
- [ ] **Parallel execution**: Sources execute in parallel correctly (validate with timing analysis)
- [ ] **Error handling**: System handles source failures gracefully (no crashes from query errors)
- [ ] **Deduplication**: Within-source duplicate tracking prevents result inflation (verify duplicate_count in logs)
- [ ] **E2E test**: Full research query completes successfully with multiple hypotheses

**Validation Process**:
1. Run baseline test (record: result count, execution time, queries per source)
2. Run Phase 1 test (same query)
3. Compare results:
   - 30%+ more results
   - Average 3-5 queries per source (not 1, not max_queries)
   - >70% of sources stopped by LLM (not by limits)
4. Check logs:
   - Verify confidence scores present
   - Verify expected_value present
   - Verify duplicate_count tracked
5. Measure time (<2x baseline)
6. Test error handling (simulate source failure, verify graceful handling)

**If ANY criterion fails**:
- ⛔ **STOP - Do not proceed to Phase 2**
- 🔍 **Debug**: Analyze logs, find root cause
- 🔧 **Fix**: Correct issue
- 🔄 **Re-validate**: Run tests again
- ✅ **Only proceed** when ALL criteria pass

---

### **Rollback Strategy**

**If Phase 1 fails after implementation**:

1. **Revert code changes**:
   ```bash
   git revert HEAD~N  # Revert Phase 1 commits
   ```

2. **Validate baseline still works**:
   ```bash
   python3 run_research.py "test query"
   ```

3. **Analyze what went wrong**:
   - Review logs
   - Identify root cause
   - Document lessons learned

4. **Options**:
   - Fix and retry Phase 1
   - Reduce Phase 1 scope (ultra-minimal)
   - Defer Phase 1 entirely

**Key principle**: System must remain working after any rollback.

---

### **Time Estimate**

**Optimistic**: 2 weeks (if everything works first try)
**Realistic**: 2.5 weeks (expect debugging, iteration)
**Pessimistic**: 3.5 weeks (if major issues discovered)

**Breakdown**:
- Configuration: 0.5 day
- Source metadata: 0.5 day
- Saturation prompt: 0.5 day
- First query generation: 0.5 day (NEW)
- Core method: 1.5 days (increased for dedup + error handling)
- Query decision: 0.5 day
- Integration: 0.5 day
- Logging: 0.5 day (with confidence scores)
- Testing & validation: 2 days (increased for error handling tests)
- Debugging & fixes: 2-3 days (buffer)

**Total**: 12.5 days (2.5 weeks)

---

### **Dependencies**

**Requires**:
- ✅ Current system working (Phase 0)
- ✅ Feature branch created
- ✅ Planning approved

**Provides** (for later phases):
- Query history infrastructure
- Source saturation patterns
- Enhanced logging
- Configuration framework

---

## Phase 2: Breadcrumb Following

**Duration**: 2 weeks
**Goal**: Investigate entities/IDs/references discovered in results
**Value**: 10-20% more context, deeper investigation

### **Prerequisites**

- ✅ Phase 1 validated and working
- ✅ Phase 1 provides query history infrastructure

### **Scope Definition**

**IN SCOPE**:
1. Extract breadcrumbs (entities, contract IDs, org names) from results
2. Prioritize breadcrumbs (high-value first)
3. Execute targeted queries for breadcrumbs
4. User-configurable breadcrumb limits

**OUT OF SCOPE**:
- Verification (Phase 3)
- Entity research (Phase 4)

### **Implementation Steps** (High-Level)

1. Add `_extract_breadcrumbs` method (LLM extracts from results)
2. Add `_prioritize_breadcrumbs` method (LLM ranks by importance)
3. Add `_follow_breadcrumb` method (executes targeted query)
4. Update hypothesis execution to include breadcrumbs
5. Test extraction, prioritization, following
6. E2E validation

### **Success Criteria**

- [ ] Extracts 5-10 breadcrumbs per hypothesis
- [ ] Follows high-value breadcrumbs (contract IDs, key entities)
- [ ] Adds 10-20% more results vs Phase 1
- [ ] Respects breadcrumb limits (no excessive following)
- [ ] E2E test passes

**Validation Gate**: If fails, continue using Phase 1 only (system still works).

### **Time Estimate**

**Realistic**: 2 weeks

---

## Phase 3: Verification & Triangulation

**Duration**: 2 weeks
**Goal**: Cross-reference claims, detect contradictions, flag unverified info
**Value**: Improved reliability, investigative rigor

### **Prerequisites**

- ✅ Phase 1 validated
- ✅ Phase 2 validated (optional but helpful)

### **Scope Definition**

**IN SCOPE**:
1. Verify claims across multiple sources
2. Detect contradictions between sources
3. Flag single-source unverified claims
4. Prefer official sources over social media

**OUT OF SCOPE**:
- Entity research (Phase 4)

### **Success Criteria**

- [ ] Identifies claims needing verification
- [ ] Detects contradictions (dates, amounts, names)
- [ ] Flags unverified claims clearly in report
- [ ] Improves result reliability

**Validation Gate**: If fails, continue using Phases 1-2 (system still works).

### **Time Estimate**

**Realistic**: 2 weeks

---

## Phase 4: Entity Research

**Duration**: 2 weeks
**Goal**: Auto-research key entities discovered during investigation
**Value**: Deeper context, entity profiles

### **Prerequisites**

- ✅ Phases 1-3 validated

### **Scope Definition**

**IN SCOPE**:
1. Identify high-importance entities (LLM decision)
2. Auto-generate entity research tasks
3. Execute entity research (uses Phase 1 saturation)
4. Link entity profiles to original research

**OUT OF SCOPE**:
- Learning metrics (Phase 5)

### **Success Criteria**

- [ ] Identifies 5-10 key entities per research
- [ ] Researches entities automatically
- [ ] Builds entity profiles
- [ ] Links profiles to original research context

**Validation Gate**: If fails, continue using Phases 1-3 (system still works).

### **Time Estimate**

**Realistic**: 2 weeks

---

## Phase 5: Learning & Optimization

**Duration**: 3-4 weeks
**Goal**: System learns and improves over time
**Value**: Continuous improvement, source quality awareness

### **Scope Definition**

**IN SCOPE**:
1. Track source quality over time
2. Learn query patterns that work
3. Adapt strategies based on history
4. Measure improvement trends
5. Source effectiveness scoring

**Success Criteria**

- [ ] Tracks metrics across research runs
- [ ] Identifies improving/declining sources
- [ ] Learns query patterns
- [ ] Adapts strategies automatically

**Time Estimate**

**Realistic**: 3-4 weeks

---

## Summary Timeline

**Total**: 10-14 weeks (2.5-3.5 months)

```
Phase 0: Baseline          ✅ Complete
Phase 1: Saturation        🔄 2 weeks  [GATE]
Phase 2: Breadcrumbs       ⏸️  2 weeks  [GATE]
Phase 3: Verification      ⏸️  2 weeks  [GATE]
Phase 4: Entity Research   ⏸️  2 weeks  [GATE]
Phase 5: Learning          ⏸️  3-4 weeks [GATE]
```

**Key Decision Points**:
- After Phase 1: Continue to Phase 2 or stop?
- After Phase 2: Continue to Phase 3 or stop?
- After Phase 3: Continue to Phase 4 or stop?
- After Phase 4: Continue to Phase 5 or stop?

**Each phase delivers independent value** - can stop anywhere and have improved system.

---

## Risk Management

### **High Risks**

1. **Phase 1 doesn't improve results**
   - Mitigation: Validate with multiple test queries
   - Fallback: Reduce scope or rollback

2. **LLM saturation decisions are poor**
   - Mitigation: Extensive prompt engineering, examples
   - Fallback: Add simple heuristic as safety net

3. **Performance degradation**
   - Mitigation: Parallel execution, reasonable limits
   - Fallback: Reduce query ceilings

### **Medium Risks**

4. **Cost explosion**
   - Mitigation: Track costs per phase, set budgets
   - Fallback: Reduce query ceilings

5. **Complexity increases debugging difficulty**
   - Mitigation: Rich logging, clear error messages
   - Fallback: Simplify implementation

### **Low Risks**

6. **Integration conflicts**
   - Mitigation: Feature branch, incremental integration
   - Fallback: Revert specific changes

---

## Success Metrics

**Phase 1**:
- ✅ 30%+ more results than baseline
- ✅ <2x execution time
- ✅ No infinite loops

**Phase 2**:
- ✅ 10-20% more context vs Phase 1
- ✅ Breadcrumbs followed productively

**Phase 3**:
- ✅ Claims verified across sources
- ✅ Contradictions detected

**Phase 4**:
- ✅ Key entities researched
- ✅ Entity profiles linked to context

**Phase 5**:
- ✅ System improving over time
- ✅ Source quality tracked

---

## Current Status

**Phase 0**: ✅ Complete (baseline documented)
**Phase 1**: 📝 Planning complete, ready to implement
**Next Action**: User approval of Phase 1 plan

**Decision Point**: Proceed with Phase 1 implementation?
- [ ] Yes, proceed with Comprehensive Phase 1 (~500 lines, 2 weeks)
- [ ] Modify Phase 1 scope
- [ ] Defer entirely
