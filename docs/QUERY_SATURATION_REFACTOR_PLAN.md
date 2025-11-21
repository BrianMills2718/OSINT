# Query-Level Saturation Refactor - Comprehensive Plan

**Branch**: `feature/query-level-saturation`
**Created**: 2025-11-21
**Status**: Planning Phase

---

## Executive Summary

**Problem**: Current system executes ONE query per source per hypothesis, which is too shallow for thorough investigative research.

**Solution**: Implement query-level saturation with LLM-driven iterative querying until each source is saturated.

**Impact**:
- ✅ More thorough research (especially for rich sources like SAM.gov)
- ✅ Adaptive depth (stops quickly for shallow sources like Twitter)
- ✅ Better aligned with investigative journalism workflow
- ⚠️ More LLM calls (acceptable tradeoff for quality)
- ⚠️ Slightly slower (mitigated by source-level parallelism)

---

## Current Architecture (Baseline)

```
Research Question
└─ Tasks (decomposition)
   └─ Task 0
      └─ Hypotheses (investigative angles)
         └─ Hypothesis 1
            ├─ Generate ONE query for SAM.gov
            ├─ Execute SAM.gov query (single-shot) → 10 results
            ├─ Generate ONE query for Brave
            ├─ Execute Brave query (single-shot) → 15 results
            ├─ Generate ONE query for Twitter
            └─ Execute Twitter query (single-shot) → 5 results

            → Filter + deduplicate (30 results)
            → Coverage Assessment: Execute Hypothesis 2?
```

**Limitations**:
1. One query per source = shallow coverage
2. No iterative exploration of query space
3. Can't adapt based on results
4. Misses information requiring alternative formulations

---

## Target Architecture (Refactor Goal)

```
Research Question
└─ Tasks (decomposition)
   └─ Task 0
      └─ Hypotheses (investigative angles)
         └─ Hypothesis 1
            │
            ├─ SAM.gov Thread (parallel):
            │  ├─ Query 1: "DoD AI contracts 2024" → 10 results (10 new)
            │  ├─ Saturation check → CONTINUE (high value)
            │  ├─ Query 2: "Department of Defense artificial intelligence" → 15 results (8 new)
            │  ├─ Saturation check → CONTINUE (finding new info)
            │  ├─ Query 3: "Pentagon ML contracts" → 12 results (3 new)
            │  ├─ Saturation check → CONTINUE (gaps remain)
            │  ├─ Query 4: "CDAO AI awards" → 8 results (1 new)
            │  └─ Saturation check → STOP (diminishing returns)
            │
            ├─ Brave Thread (parallel):
            │  ├─ Query 1: "DoD AI contracts news 2024" → 20 results (18 new)
            │  ├─ Saturation check → CONTINUE
            │  ├─ Query 2: "Defense AI awards announcements" → 15 results (2 new)
            │  └─ Saturation check → STOP (saturated)
            │
            └─ Twitter Thread (parallel):
               ├─ Query 1: "#DoD #AI contracts" → 8 results (8 new)
               └─ Saturation check → STOP (shallow source)

            Wait for all threads → Combine (67 unique results)
            → Coverage Assessment: Execute Hypothesis 2?
```

**Improvements**:
1. ✅ Multiple queries per source (adaptive depth)
2. ✅ Iterative query generation based on results
3. ✅ Sophisticated saturation reasoning (existence confidence, gap analysis)
4. ✅ Source-level parallelism (speed + thoroughness)

---

## Key Components to Build

### 1. Source Saturation Loop

**New Method**: `_saturate_source_for_hypothesis()`

```python
async def _saturate_source_for_hypothesis(
    self,
    hypothesis: Dict,
    source_name: str,
    task: ResearchTask,
    research_question: str
) -> List[Dict]:
    """
    Iteratively query ONE source until saturated.

    Returns:
        All unique results from this source for this hypothesis
    """
    # Iterative loop:
    # 1. Generate next query (with full history context)
    # 2. Execute query
    # 3. Deduplicate
    # 4. Assess saturation (LLM decision)
    # 5. If not saturated: loop to step 1
    # 6. If saturated: return results
```

**Responsibilities**:
- Maintains query history for this source
- Calls saturation assessment LLM after each query
- Respects source-specific query ceiling (SAM.gov: 10, Twitter: 3)
- Returns all accumulated unique results

### 2. Saturation Decision LLM

**New Method**: `_decide_next_query()`

**New Prompt**: `prompts/deep_research/source_saturation.j2`

**Inputs**:
- Hypothesis statement
- Source name + characteristics
- Query history (queries, results counts, incremental %)
- Coverage gaps identified
- Accumulated results count

**LLM Reasoning**:
1. **Existence Confidence**: Does this info likely exist in this source?
2. **Query Effectiveness**: Are queries finding new info or hitting duplicates?
3. **Gap Value**: Are remaining gaps high-value or peripheral?
4. **Query Space**: Have we exhausted terminology/angles?
5. **Source Depth**: Have we queried proportionally to expected richness?

**Output Schema**:
```json
{
  "action": "continue" | "stop",
  "reasoning": "Why continue/stop based on factors above",
  "next_query": "If continuing, specific query targeting gaps",
  "query_rationale": "Why this query will find what previous missed",
  "expected_new_results": "high (>50%)" | "medium (20-50%)" | "low (<20%)",
  "confidence_gaps_fillable": 0-100
}
```

### 3. Modified Hypothesis Execution

**Modified Method**: `_execute_hypothesis()`

**Changes**:
- Remove: Loop over sources with single query per source
- Add: Launch parallel source saturation tasks
- Add: Wait for all sources to complete (`asyncio.gather`)
- Keep: Cross-source deduplication
- Keep: Result attribution with hypothesis IDs

### 4. Gap Analysis

**New Method**: `_identify_coverage_gaps()`

**Purpose**: Identify what information we're seeking but haven't found

**Examples**:
- "Contract dollar amounts missing for 12/15 contracts"
- "No contracts from Oct-Dec 2024 timeframe"
- "Defense Innovation Unit contracts mentioned in news but not found"
- "Specific awardee companies not identified"

**Used By**: Saturation LLM to assess if continuing is worthwhile

### 5. Source-Specific Configuration

**New Config Section**: `config.yaml` (or defaults in code)

```yaml
research:
  source_saturation:
    # Query ceilings (hard stops)
    sam_gov_max_queries: 10
    brave_search_max_queries: 6
    twitter_max_queries: 3
    reddit_max_queries: 4
    discord_max_queries: 4
    dvids_max_queries: 5
    usajobs_max_queries: 4
    clearancejobs_max_queries: 4

    # Source depth expectations (for LLM guidance)
    source_characteristics:
      sam_gov: "Rich, structured government database with deep historical data"
      brave_search: "Broad web index, good for news/announcements"
      twitter: "Shallow, limited search depth, real-time focus"
      reddit: "Medium depth, community discussions"
      # etc.
```

### 6. Logging Enhancements

**New Log Event**: `source_query` (in `execution_logger.py`)

```python
def log_source_query(
    self,
    task_id: int,
    hypothesis_id: str,
    source_name: str,
    query_number: int,
    query: str,
    results_total: int,
    results_new: int,
    reasoning: str
):
    """Log each individual source query in saturation loop."""
```

**Purpose**: Complete audit trail of ALL queries executed, not just final results

---

## Implementation Phases

### Phase 1: Core Infrastructure (Week 1)
**Goal**: Build saturation loop without breaking existing functionality

- [ ] Create `_saturate_source_for_hypothesis()` method
- [ ] Create `prompts/deep_research/source_saturation.j2` prompt
- [ ] Create `_decide_next_query()` LLM call method
- [ ] Add `log_source_query()` to ExecutionLogger
- [ ] Add source configuration defaults
- [ ] **Validation**: Run system in "compatibility mode" (old behavior)

### Phase 2: Gap Analysis (Week 1-2)
**Goal**: Enable LLM to reason about missing information

- [ ] Create `_identify_coverage_gaps()` method
- [ ] Integrate gap analysis into saturation prompt
- [ ] Test gap identification accuracy
- [ ] **Validation**: Gaps logged correctly in execution_log.jsonl

### Phase 3: Parallel Source Execution (Week 2)
**Goal**: Enable sources to query in parallel

- [ ] Modify `_execute_hypothesis()` to launch parallel tasks
- [ ] Add proper error handling for parallel execution
- [ ] Ensure cross-source deduplication works
- [ ] **Validation**: All sources complete, results combined correctly

### Phase 4: Integration Testing (Week 2-3)
**Goal**: End-to-end validation

- [ ] Test with simple query (2-3 tasks, 1-2 hypotheses each)
- [ ] Test with complex query (5+ tasks, 3-4 hypotheses each)
- [ ] Compare results vs old system (should find MORE information)
- [ ] Measure cost increase (LLM calls)
- [ ] Measure time increase (should be minimal due to parallelism)
- [ ] **Validation**: System finds 30-50% more results than baseline

### Phase 5: Production Readiness (Week 3-4)
**Goal**: Polish and optimize

- [ ] Add circuit breakers (max time per source)
- [ ] Add cost tracking for saturation queries
- [ ] Optimize prompt length (saturation prompt gets large with history)
- [ ] Add configuration options (enable/disable per source)
- [ ] Update documentation
- [ ] **Validation**: Clean execution logs, no errors, configurable

---

## Compatibility & Migration Strategy

### Backward Compatibility Options

**Option A: Flag-Based (Recommended)**
```python
# Config toggle
hypothesis_saturation_enabled: true  # New behavior
hypothesis_saturation_enabled: false # Old behavior (one query per source)
```

**Why**: Allows A/B testing, easy rollback if issues

**Option B: Automatic Migration**
- Remove old code paths entirely
- All users get new behavior immediately

**Recommendation**: Option A during development, migrate to Option B after 30 days of validation

### Migration Plan

1. **Week 1-2**: New code in feature branch, old behavior default
2. **Week 3**: Enable for internal testing, compare outputs
3. **Week 4**: Enable by default, monitor for issues
4. **Week 5-6**: Remove old code paths, simplify architecture

---

## Testing Strategy

### Unit Tests

```python
# tests/test_source_saturation.py
async def test_saturation_stops_after_3_queries():
    """Verify LLM can decide to stop after N queries"""

async def test_saturation_continues_for_high_value_gaps():
    """Verify system persists when critical info missing"""

async def test_parallel_source_execution():
    """Verify sources execute in parallel, not sequential"""

async def test_query_history_passed_to_llm():
    """Verify LLM receives full query history for decisions"""
```

### Integration Tests

```python
# tests/test_query_saturation_e2e.py
async def test_e2e_dod_contracts():
    """
    End-to-end test: "Recent DoD AI contracts 2024"

    Expected:
    - SAM.gov: 5-8 queries (rich source)
    - Brave: 3-5 queries (medium source)
    - Twitter: 1-2 queries (shallow source)
    - Total results: 40-60 (vs 20-30 with old system)
    """
```

### Validation Criteria

**Success Metrics**:
- ✅ Finds 30%+ more results than baseline
- ✅ LLM stops within query ceilings (no infinite loops)
- ✅ Execution time <2x baseline (parallelism mitigates sequential queries)
- ✅ No crashes or timeouts
- ✅ Clean execution logs with full audit trail

**Cost Metrics**:
- LLM call increase: Expect 3-5x more LLM calls (acceptable for quality)
- Total cost: Track per-research cost, ensure <$5 for typical query

---

## Risk Analysis

### High Risk

1. **Infinite Loop Risk**
   - **Mitigation**: Hard query ceilings per source (10 max for SAM.gov, 3 for Twitter)
   - **Fallback**: Timeout after N seconds per source

2. **Cost Explosion**
   - **Mitigation**: Track cumulative LLM calls, add budget circuit breaker
   - **Fallback**: Disable saturation for expensive sources

### Medium Risk

3. **Slower Execution**
   - **Mitigation**: Parallel source execution
   - **Fallback**: Reduce query ceilings (SAM.gov: 10 → 6)

4. **LLM Decision Quality**
   - **Mitigation**: Extensive prompt engineering, A/B testing
   - **Fallback**: Simpler heuristic (>80% duplicates → stop)

### Low Risk

5. **Complexity Increase**
   - **Mitigation**: Good documentation, clear code structure
   - **Impact**: Higher maintenance burden

---

## Success Criteria

**Minimum Viable Product (MVP)**:
- [ ] System executes 2+ queries per source when warranted
- [ ] LLM makes stop/continue decisions based on results
- [ ] No infinite loops or crashes
- [ ] Finds more information than baseline

**Production Ready**:
- [ ] All tests passing
- [ ] <2x baseline execution time
- [ ] Complete execution logs
- [ ] Configuration options documented
- [ ] Validated on 5+ different research questions

**Exceptional**:
- [ ] Finds 50%+ more results than baseline
- [ ] Adaptive query strategy clearly visible in logs
- [ ] Users report significantly better research quality
- [ ] Cost increase <50% vs baseline

---

## Open Questions

1. **Should saturation assessment be per-query or per-batch?**
   - Per-query: Assess after EACH query (more adaptive, slower)
   - Per-batch: Execute 2-3 queries, then assess (faster, less precise)
   - **Recommendation**: Per-query for MVP, experiment with batching later

2. **How to handle query reformulation vs new queries?**
   - Current system has "reformulation" for retries
   - New system has "saturation-driven new queries"
   - Are these the same or different?
   - **Recommendation**: Treat as same - saturation loop subsumes reformulation

3. **Should we parallelize within a source?**
   - E.g., SAM.gov Query 1 + Query 2 simultaneously?
   - **Recommendation**: No - Query N+1 should use results of Query N

4. **What about source-specific query strategies?**
   - SAM.gov: Try different date formats, contract types
   - Twitter: Try hashtags vs full text
   - **Recommendation**: Encode in source_characteristics, let LLM adapt

---

## Next Steps

**Immediate Actions**:
1. Review this plan with user - get approval/feedback
2. Create detailed task breakdown for Phase 1
3. Set up test harness for comparing old vs new system
4. Begin implementation of `_saturate_source_for_hypothesis()`

**Before Starting Implementation**:
- [ ] User approves architecture
- [ ] User approves phasing plan
- [ ] User approves success criteria
- [ ] Decision on open questions documented

---

## References

- **Original Discussion**: Session 2025-11-21 (saturation architecture deep-dive)
- **Current System**: `research/deep_research.py:1371` (`_execute_hypothesis`)
- **Coverage Assessment**: `research/deep_research.py:1498` (`_assess_coverage`)
- **Hypothesis Execution**: `research/deep_research.py:1777` (`_execute_hypotheses_sequential`)

---

**Document Status**: Planning - Awaiting User Approval
