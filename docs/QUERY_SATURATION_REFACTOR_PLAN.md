# Query-Level Saturation Refactor - Comprehensive Plan (REVISED)

**Branch**: `feature/query-level-saturation`
**Created**: 2025-11-21
**Revised**: 2025-11-21 (removed overengineered phases)
**Status**: Planning Phase

---

## Executive Summary

**Problem**: Current system executes ONE query per source per hypothesis, which is too shallow for thorough investigative research.

**Solution**: Implement query-level saturation with LLM-driven iterative querying until each source is saturated, plus intelligent capabilities that expert investigators use.

**Impact**:
- ✅ More thorough research (especially for rich sources like SAM.gov)
- ✅ Adaptive depth (stops quickly for shallow sources like Twitter)
- ✅ Intelligence capabilities: breadcrumb following, verification, entity research
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
5. Doesn't follow leads mentioned in results
6. No verification or cross-referencing
7. Doesn't research entities discovered

---

## Target Architecture (Simplified & Focused)

```
Research Question
│
└─ Task Decomposition (existing - works well)
   └─ Tasks with hypotheses
      │
      └─ For each hypothesis:
         │
         ├─ PARALLEL: Source Saturation Threads (NEW - PHASE 1)
         │  │
         │  ├─ SAM.gov Thread:
         │  │  └─ Query Loop:
         │  │     ├─ Query 1 → results
         │  │     ├─ LLM assesses: saturated? terminology working? strategy effective?
         │  │     ├─ Query 2 (adapted based on Q1 results) → results
         │  │     ├─ LLM assesses: continue or stop?
         │  │     └─ ... until saturated
         │  │
         │  ├─ Brave Thread: (same pattern)
         │  └─ Twitter Thread: (same pattern)
         │
         ├─ Breadcrumb Following (NEW - PHASE 2)
         │  └─ Extract entities/IDs/names from results → Investigate them
         │  └─ Example: Result mentions "Contract #12345" → Look up in SAM.gov
         │  └─ Example: Result mentions "CDAO" → Research what it is
         │
         ├─ Verification & Triangulation (NEW - PHASE 3)
         │  └─ Cross-reference claims across sources
         │  └─ Detect contradictions
         │  └─ Flag unverified single-source claims
         │  └─ Prefer official sources over social media
         │
         └─ Coverage Assessment (existing - works well)
            └─ Continue to next hypothesis?
```

**Key Design Principle**: The query saturation loop with sophisticated LLM reasoning handles what "reconnaissance" and "question understanding" phases tried to do, without adding separate phases.

---

## Core Innovation: The Smart Saturation Loop

The intelligence is in the **prompt and reasoning**, not in architectural phases:

### What Makes It Smart

```python
# LLM receives FULL CONTEXT for each query decision:

Query History:
1. "DoD AI 2024" → 0 results
   Reasoning: "Tried abbreviations, got nothing"

2. "Department of Defense artificial intelligence 2024" → 10 results
   Reasoning: "Formal terminology works! SAM.gov requires full agency names"

3. "Department of Defense machine learning contracts 2024" → 8 results
   Reasoning: "Synonym exploration successful, found different contracts"

Current Gaps:
- Found contracts but 60% lack dollar amounts
- Missing Q4 2024 contracts (only Q1-Q3 found)
- No Defense Innovation Unit contracts found

LLM Decision:
{
  "action": "continue",
  "query": "Department of Defense artificial intelligence contract value awarded 2024",
  "reasoning": "Previous queries found contracts but not amounts. Adding 'contract
               value' to query targets financial data gap. Critical info worth
               another query.",
  "expected_value": "high",
  "confidence_will_find": 75
}
```

**This ONE loop handles:**
- ✅ Terminology discovery (sees what keywords work)
- ✅ Source assessment (stops if source is empty)
- ✅ Strategy adaptation (pivots when not working)
- ✅ Gap-driven querying (targets missing information)
- ✅ Meta-cognitive reasoning (learns from query history)

**No separate phases needed!**

---

## Implementation Phases (Revised)

### Phase 1: Core Query Saturation (Weeks 1-2)
**Goal**: Iterative querying per source until saturated

**Components**:

1. **`_saturate_source_for_hypothesis()` method**
   - Iterative query loop for single source
   - Maintains query history
   - Respects source-specific ceilings (SAM.gov: 10, Twitter: 3)
   - Returns accumulated unique results

2. **`prompts/deep_research/source_saturation.j2` prompt**
   - Inputs: query history, results counts, gaps, source characteristics
   - LLM reasoning: existence confidence, query effectiveness, gap value, strategy
   - Output: continue/stop decision + next query + reasoning

3. **`_decide_next_query()` LLM call**
   - Wraps saturation prompt
   - Returns structured decision

4. **Modified `_execute_hypothesis()` for parallelism**
   - Launch parallel source saturation tasks
   - Wait for all with `asyncio.gather()`
   - Cross-source deduplication

5. **Logging enhancements**
   - New event: `source_query` (log each individual query)
   - Fields: task_id, hypothesis_id, source, query_num, query, results_total, results_new, reasoning

6. **Source configuration**
   - Query ceilings per source
   - Source characteristics for LLM guidance

**Success Criteria**:
- [ ] System executes 2+ queries per source when warranted
- [ ] LLM makes intelligent stop/continue decisions
- [ ] Finds 30%+ more results than baseline
- [ ] No infinite loops
- [ ] <2x baseline execution time

---

### Phase 2: Breadcrumb Following (Weeks 3-4)
**Goal**: Investigate entities/IDs mentioned in results

**Components**:

1. **`_extract_breadcrumbs()` method**
   - Parse results for entities, contract IDs, organization names
   - Identify leads worth investigating
   - Return structured list of breadcrumbs

2. **`_follow_breadcrumb()` method**
   - Takes breadcrumb (type + value)
   - Determines best source to investigate
   - Executes targeted query
   - Returns results

3. **Integration with hypothesis execution**
   - After source saturation, extract breadcrumbs
   - Follow high-value breadcrumbs (configurable limit)
   - Add breadcrumb results to hypothesis results

**Examples**:
```python
# Result: "Contract #GS-35F-0119Y awarded..."
Breadcrumb: (type="contract_id", value="GS-35F-0119Y")
→ Query SAM.gov with exact contract ID

# Result: "CDAO announced partnership..."
Breadcrumb: (type="entity", value="CDAO")
→ Research: What is CDAO? Budget? Leadership? Role?

# Result: "Dr. Jane Smith testified..."
Breadcrumb: (type="person", value="Dr. Jane Smith")
→ Research: Who is Jane Smith? Position? Expertise?
```

**Success Criteria**:
- [ ] System extracts 5-10 breadcrumbs per hypothesis
- [ ] Follows high-value breadcrumbs (contract IDs, entities)
- [ ] Breadcrumb following adds 10-20% more context
- [ ] No excessive following (configurable limits work)

---

### Phase 3: Verification & Triangulation (Weeks 5-6)
**Goal**: Cross-reference claims, detect contradictions

**Components**:

1. **`_verify_claim()` method**
   - Takes claim + sources
   - Checks if sources are independent (not citing each other)
   - Searches for confirmation in official sources
   - Returns verification status + confidence

2. **`_detect_contradictions()` method**
   - Compares claims across results
   - Identifies conflicts (dates, amounts, names)
   - Attempts resolution via official sources
   - Flags unresolvable contradictions

3. **Verification metadata**
   - Tag each result with verification status:
     - `verified_official`: Confirmed by official source
     - `verified_multi`: Confirmed by multiple independent sources
     - `unverified_single`: Only one source
     - `contradicted`: Conflicts with other sources

4. **Report enhancements**
   - Clearly mark unverified claims
   - Explain contradictions found
   - Prioritize verified information

**Examples**:
```python
# Claim: "OpenAI received $200M DoD contract in 2024"
Sources: [Twitter, DefenseTech.com, Reddit]
Check: All 3 cite same Twitter post → Not independent

Action: Search SAM.gov for OpenAI contracts
Result: Found contract #123, $200M, awarded Oct 2023 (not 2024)

Verification:
- Amount: VERIFIED ($200M)
- Recipient: VERIFIED (OpenAI)
- Year: CONTRADICTED (2023, not 2024)
```

**Success Criteria**:
- [ ] System verifies high-value claims (>$100M contracts, key facts)
- [ ] Detects date mismatches, amount discrepancies
- [ ] Report clearly marks unverified information
- [ ] No false contradictions (handles date format variations)

---

### Phase 4: Entity Research (Weeks 7-8)
**Goal**: Research key entities discovered during investigation

**Components**:

1. **`_research_entity()` method**
   - Takes entity name/type
   - Generates targeted queries about entity
   - Collects: description, role, leadership, budget, history
   - Returns entity profile

2. **Entity identification**
   - During research, track entities encountered
   - Rank by frequency + relevance
   - Select top N for deep research (configurable)

3. **Entity profiles in report**
   - Dedicated section: "Key Actors"
   - For each entity: profile, role in findings, significance

**Examples**:
```python
# Frequent mention of "CDAO" in results

Research CDAO:
- Full name: Chief Digital and Artificial Intelligence Office
- Created: 2022
- Leadership: Craig Martell (Chief Digital and AI Officer)
- Budget: $500M annually
- Role: Centralize DoD AI/data initiatives
- Significance: Awarded 60% of FY2024 DoD AI contracts

# This context transforms interpretation:
"CDAO centralization explains spike in contract volume and
standardization of procurement process observed in findings"
```

**Success Criteria**:
- [ ] System identifies 5-10 key entities per research
- [ ] Researches top entities automatically
- [ ] Entity profiles add context to report
- [ ] Profiles help explain patterns/significance

---

## Key Components Detail

### 1. Source Saturation Loop (Phase 1 - Core)

**Method**: `_saturate_source_for_hypothesis()`

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
    query_history = []
    all_results = []
    url_dedup = set()

    max_queries = self._get_source_query_ceiling(source_name)

    for query_num in range(max_queries):
        # LLM decides: continue or stop?
        decision = await self._decide_next_query(
            hypothesis=hypothesis,
            source_name=source_name,
            research_question=research_question,
            task_query=task.query,
            query_history=query_history,
            accumulated_results=len(all_results),
            coverage_gaps=self._identify_gaps(task, hypothesis)
        )

        if decision["action"] == "stop":
            break

        # Execute query
        query = decision["next_query"]
        results = await self._execute_source_query(source_name, query)

        # Deduplicate
        new_results = [r for r in results if r.get('url') not in url_dedup]

        # Update state
        for r in new_results:
            if r.get('url'):
                url_dedup.add(r['url'])
            all_results.append(r)

        # Record history
        query_history.append({
            "query": query,
            "reasoning": decision.get("query_rationale", ""),
            "results_total": len(results),
            "results_new": len(new_results),
            "results_duplicate": len(results) - len(new_results),
            "incremental_pct": len(new_results) / len(results) * 100 if results else 0
        })

        # Log
        if self.logger:
            self.logger.log_source_query(
                task_id=task.id,
                hypothesis_id=hypothesis["id"],
                source_name=source_name,
                query_number=query_num + 1,
                query=query,
                results_total=len(results),
                results_new=len(new_results),
                reasoning=decision.get("query_rationale", "")
            )

    return all_results
```

### 2. Saturation Decision Prompt (Phase 1 - Core)

**File**: `prompts/deep_research/source_saturation.j2`

```jinja2
You are deciding whether to continue querying {{ source_name }} for this hypothesis.

## Context

**Research Question**: {{ research_question }}
**Task**: {{ task_query }}
**Hypothesis**: {{ hypothesis_statement }}
**Source**: {{ source_name }}

Source Characteristics: {{ source_characteristics }}

## Query History (This Source Only)

{% for query in query_history %}
{{ loop.index }}. Query: "{{ query.query }}"
   → Results: {{ query.results_total }} ({{ query.results_new }} new, {{ query.results_duplicate }} duplicate)
   → Incremental: {{ query.incremental_pct|round(1) }}%
   → Reasoning: {{ query.reasoning }}
{% endfor %}

## Current State

- Total unique results from this source: {{ accumulated_results }}
- Queries executed: {{ query_count }}
- Query ceiling for this source: {{ max_queries }}

## Information Gaps

What we're seeking but haven't found yet:
{% for gap in coverage_gaps %}
- {{ gap }}
{% endfor %}

## Your Task: Assess Whether to Continue

Consider these factors:

1. **Existence Confidence**: How confident are you this information exists in {{ source_name }}?
   - High confidence + not finding it → Likely query problem → Continue with better formulation
   - Low confidence + not finding it → Information probably doesn't exist → Stop

2. **Query Effectiveness**: Is our strategy working?
   - Recent queries finding new info (>40% new) → Good signal → Continue
   - Recent queries mostly duplicates (<20% new) → Diminishing returns → Consider stopping
   - BUT: Critical gaps remain despite duplicates → Continue with targeted queries

3. **Gap Value**: How important are remaining gaps?
   - High-value gaps (contract amounts, dates, awardees) → Justify more queries
   - Low-value gaps (peripheral mentions) → Not worth many queries

4. **Terminology Discovery**: Have we found what works?
   - Query 1 failed, Query 2 succeeded → We learned correct terminology → Continue variations
   - All queries failing → Wrong approach OR info doesn't exist → Consider stopping

5. **Source Depth**: Is this source rich or shallow?
   - {{ source_name }} typical depth: {{ source_depth_expectation }}
   - Have we explored proportionally to expected richness?

## Output (JSON)

{
  "action": "continue" | "stop",
  "reasoning": "Explain decision considering existence confidence, query effectiveness, gap value, terminology, source depth",
  "next_query": "If continuing: specific query targeting remaining gaps OR exploring new terminology",
  "query_rationale": "Why this query will find what previous queries missed",
  "expected_new_results": "high (>50% new)" | "medium (20-50% new)" | "low (<20% new)",
  "confidence_gaps_fillable": 0-100
}
```

### 3. Modified Hypothesis Execution (Phase 1 - Core)

**Method**: `_execute_hypothesis()`

```python
async def _execute_hypothesis(
    self,
    hypothesis: Dict,
    task: ResearchTask,
    research_question: str
) -> List[Dict]:
    """
    Execute hypothesis by saturating multiple sources IN PARALLEL.
    """
    sources = hypothesis["search_strategy"]["sources"]

    print(f"\n🔬 Executing Hypothesis {hypothesis['id']}")
    print(f"   Sources: {', '.join(sources)} (parallel)")

    # Launch parallel source saturation
    source_tasks = []
    for source in sources:
        coro = self._saturate_source_for_hypothesis(
            hypothesis=hypothesis,
            source_name=source,
            task=task,
            research_question=research_question
        )
        source_tasks.append(coro)

    # Wait for all sources
    results_by_source = await asyncio.gather(*source_tasks, return_exceptions=True)

    # Combine
    all_results = []
    for i, results in enumerate(results_by_source):
        if isinstance(results, Exception):
            logging.error(f"Source {sources[i]} failed: {results}")
            continue
        all_results.extend(results)

    # Cross-source deduplication
    deduplicated = self._deduplicate_with_attribution(all_results, hypothesis["id"])

    print(f"   📊 Hypothesis {hypothesis['id']}: {len(deduplicated)} unique results")

    return deduplicated
```

---

## Source-Specific Configuration

```python
# In config or code defaults:

SOURCE_QUERY_CEILINGS = {
    "sam_gov": 10,           # Rich government database
    "brave_search": 6,       # Broad web index
    "twitter": 3,            # Shallow, noisy
    "reddit": 4,             # Medium depth
    "discord": 4,            # Medium depth
    "dvids": 5,              # Specialized military media
    "usajobs": 4,            # Job postings
    "clearancejobs": 4       # Job postings
}

SOURCE_CHARACTERISTICS = {
    "sam_gov": "Official federal procurement database with deep historical data. Requires exact formal terminology (full agency names, no abbreviations).",
    "brave_search": "Broad web index, good for news articles, press releases, and general announcements.",
    "twitter": "Real-time social media with limited search depth. Good for breaking news and official announcements but noisy.",
    "reddit": "Community discussions with moderate depth. Good for informal insights and leads.",
    # etc.
}
```

---

## Testing Strategy

### Phase 1 Tests (Query Saturation)

```python
# tests/test_source_saturation.py

async def test_saturation_stops_at_ceiling():
    """Verify system respects query ceilings"""
    # SAM.gov ceiling = 10
    # Even if LLM says continue, stop at 10

async def test_saturation_stops_early_when_empty():
    """Verify system stops quickly for empty sources"""
    # Query 1: 0 results
    # Query 2: 0 results
    # LLM should decide: "Source is empty, stop"

async def test_terminology_discovery():
    """Verify system learns from query results"""
    # Query 1: "DoD AI" → 0 results
    # LLM should try: "Department of Defense artificial intelligence"

async def test_parallel_source_execution():
    """Verify sources execute in parallel"""
    # Time 3 sources
    # Should be ~1x slowest source, not 3x sum

async def test_gap_driven_querying():
    """Verify system targets specific gaps"""
    # Gap: "Contract amounts missing"
    # Next query should include "value" or "amount"
```

### Integration Tests

```python
# tests/test_query_saturation_e2e.py

async def test_e2e_dod_contracts_baseline_comparison():
    """
    Compare new system vs baseline.

    Expected improvements:
    - 30-50% more results
    - Better quality (more specific info)
    - <2x execution time
    """

async def test_e2e_source_adaptation():
    """
    Verify system adapts to source characteristics.

    Expected:
    - SAM.gov: 5-8 queries (rich source)
    - Twitter: 1-2 queries (shallow source)
    """
```

---

## Success Metrics

### Phase 1: Query Saturation

**Must Have**:
- [ ] Finds 30%+ more results than baseline
- [ ] LLM stops within query ceilings (no infinite loops)
- [ ] Execution time <2x baseline
- [ ] No crashes or timeouts
- [ ] Clean execution logs with query audit trail

**Nice to Have**:
- [ ] Finds 50%+ more results
- [ ] Execution time <1.5x baseline (parallelism working well)
- [ ] Clear evidence of intelligent query adaptation in logs

**Cost Metrics**:
- Expect 3-5x more LLM calls (acceptable for quality)
- Track per-research cost, target <$5 for typical query

---

## Risk Analysis & Mitigations

### High Risk

1. **Infinite Loop Risk**
   - **Mitigation**: Hard query ceilings per source
   - **Fallback**: Timeout after 1800s per source

2. **Cost Explosion**
   - **Mitigation**: Track LLM calls, add budget circuit breaker
   - **Fallback**: Reduce query ceilings if needed

### Medium Risk

3. **LLM Decision Quality**
   - **Mitigation**: Extensive prompt engineering, validation testing
   - **Fallback**: Simple heuristic (>80% duplicates → stop)

4. **Slower Execution**
   - **Mitigation**: Source-level parallelism
   - **Fallback**: Reduce query ceilings

---

## Open Questions & Decisions

### Question 1: Query Reformulation vs New Queries

**Context**: Current system has "reformulation" for retries. New system has "saturation-driven new queries". Are these the same?

**Decision**: MERGE THEM. Saturation loop subsumes reformulation. Query N+1 is always based on results of Query N, whether it's a "reformulation" or "new angle".

### Question 2: Source-Specific Query Strategies

**Context**: Should we encode SAM.gov-specific strategies (date formats, contract types) or let LLM discover?

**Decision**: PROVIDE IN SOURCE CHARACTERISTICS. Give LLM guidance ("SAM.gov requires formal terminology") but let it adapt the details.

### Question 3: Breadcrumb Following Limits

**Context**: Could potentially follow unlimited breadcrumbs, exploding scope.

**Decision**: CONFIGURABLE LIMIT. Follow top 5-10 high-value breadcrumbs per hypothesis. Prioritize: contract IDs > entity names > person names > other.

---

## Implementation Schedule

**Week 1-2**: Phase 1 Core Infrastructure
- [ ] `_saturate_source_for_hypothesis()` method
- [ ] Saturation prompt
- [ ] `_decide_next_query()` method
- [ ] Modified `_execute_hypothesis()`
- [ ] Logging enhancements
- [ ] Unit tests

**Week 3-4**: Phase 1 Validation & Phase 2 Start
- [ ] Integration testing (compare vs baseline)
- [ ] Cost/performance analysis
- [ ] Start breadcrumb following implementation

**Week 5-6**: Phase 2 Completion & Phase 3 Start
- [ ] Complete breadcrumb following
- [ ] Start verification/triangulation

**Week 7-8**: Phase 3 & 4
- [ ] Complete verification
- [ ] Start entity research

---

## References

- **Original Discussion**: Session 2025-11-21 (saturation architecture deep-dive)
- **Current System**: `research/deep_research.py:1371` (`_execute_hypothesis`)
- **Coverage Assessment**: `research/deep_research.py:1498` (`_assess_coverage`)
- **Ultrathink Analysis**: Session 2025-11-21 (expert investigator process)

---

## Changelog

**2025-11-21 (Initial)**: Created comprehensive refactor plan
**2025-11-21 (Revision 1)**: Removed overengineered Phase 0/1, simplified to focused implementation

**Key Changes in Revision**:
- ❌ Removed: Separate "Question Understanding" phase (overengineered)
- ❌ Removed: Separate "Reconnaissance" phase (overengineered)
- ✅ Kept: Query saturation with smart prompting (handles what Phase 0/1 tried to do)
- ✅ Added: Breadcrumb following (Phase 2)
- ✅ Added: Verification/triangulation (Phase 3)
- ✅ Added: Entity research (Phase 4)

---

**Document Status**: Planning - Ready for Implementation
