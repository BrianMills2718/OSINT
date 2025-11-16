# Phase 3B: Hypothesis Execution - Implementation Investigation

**Date**: 2025-11-15
**Purpose**: Identify all uncertainties, concerns, and design decisions before implementing Phase 3B
**Status**: Investigation - NOT YET IMPLEMENTED

---

## Executive Summary

Phase 3B would execute each hypothesis with its specific search strategy (instead of just displaying hypotheses in reports). This investigation identifies 23 critical concerns across 7 categories that must be resolved before implementation.

**Recommendation**: Proceed with CAUTIOUS implementation - uncertainties are manageable but require careful design decisions.

---

## 1. ARCHITECTURE CONCERNS (7 issues)

### 1.1 Task Multiplication vs Hypothesis Expansion ⚠️ CRITICAL DECISION

**Current (Phase 3A)**:
- User query → 3-5 tasks (e.g., "NSA programs" → "official docs", "whistleblowers", "technical leaks")
- Each task → 1-5 hypotheses (planning only)
- Total searches: 3-5 tasks × 1-3 sources = 9-15 searches

**Option A: Multiply Tasks** (Create new tasks per hypothesis):
- 3 tasks × 3 hypotheses/task = 9 tasks
- Each hypothesis-task runs like a normal task (source selection, query gen, search, filter)
- Total searches: 9 tasks × 1-3 sources = 9-27 searches

**Option B: Expand Within Task** (Execute hypotheses within existing task):
- Keep 3 tasks
- Each task executes 3 hypothesis searches (in addition to normal search)
- Total searches: (3 tasks × 1-3 sources) + (3 tasks × 3 hyp × 1 source) = 9-15 + 9 = 18-24 searches

**Concern**: Which architecture aligns with design philosophy?
- Option A: Simpler (hypothesis = task), but more LLM calls (source selection × 9)
- Option B: More efficient, but complex control flow (hypothesis loop inside task loop)

**Questions**:
- Do hypotheses need separate source selection? Or use hypothesis.search_strategy.sources directly?
- Do hypotheses need query reformulation/retry? Or single-shot execution?
- How do hypothesis results merge with task results?

**Design Philosophy Guidance**:
- "No hardcoded heuristics" → Let LLM decide if hypothesis needs retry
- "Full context" → Hypothesis results should be visible to LLM for synthesis
- "Quality over cost" → Don't skip LLM calls to save money

**Recommendation**: Option B (expand within task) with LLM control
- Use hypothesis.search_strategy.sources directly (skip source selection LLM call)
- Allow hypothesis to request retry via continuation_decision
- Merge hypothesis results into task.accumulated_results with hypothesis_id tag

---

### 1.2 Hypothesis Query Generation ⚠️ DESIGN DECISION

**Question**: How to generate queries for each hypothesis?

**Option A: LLM generates hypothesis-specific query**
- Call query_generation LLM for each hypothesis
- Passes: task.query, hypothesis.statement, hypothesis.search_strategy.signals
- Pro: Tailored query per hypothesis
- Con: +3-5 LLM calls per task (expensive)

**Option B: Reformulate task query with hypothesis context**
- Single LLM call: "Reformulate task query incorporating hypothesis signals"
- Passes: task.query, hypothesis.signals
- Pro: Cheaper (1 LLM call instead of 3-5)
- Con: Less tailored to specific hypothesis

**Option C: Use hypothesis.signals directly as query**
- No LLM call, just join signals: "GS-2210 cybersecurity specialist TS/SCI clearance"
- Pro: Free, fast
- Con: Crude query (not natural language)

**Concern**: Balance between query quality and cost

**Recommendation**: Option A (LLM per hypothesis) - aligns with quality-first philosophy
- LLM can craft better queries using hypothesis.statement + signals + expected_entities
- Cost increase acceptable (user sets max_hypotheses_per_task ceiling upfront)

---

### 1.3 Result Deduplication Strategy ⚠️ DATA INTEGRITY

**Problem**: Hypothesis searches may return duplicate results

**Scenarios**:
- Hypothesis 1 (USAJobs) finds: "NSA Cybersecurity Analyst - Fort Meade"
- Hypothesis 2 (USAJobs) finds: Same job posting
- Task normal search (USAJobs) finds: Same job posting

**Question**: When and how to deduplicate?

**Option A: Deduplicate per hypothesis** (before storage)
- Each hypothesis removes duplicates from previous hypotheses
- Pro: Clean hypothesis-specific results
- Con: Later hypotheses disadvantaged (fewer results to filter)

**Option B: Deduplicate at task end** (after all hypotheses)
- Store all hypothesis results with hypothesis_id tag
- Deduplicate across all accumulated results at task completion
- Pro: Fair to all hypotheses
- Con: More duplicates in intermediate storage

**Option C: No deduplication** (keep all with tags)
- Tag each result with hypothesis_id
- Deduplication happens at final synthesis (across all tasks)
- Pro: Preserves which hypothesis found each result
- Con: More storage, more processing at synthesis

**Concern**: Maintaining hypothesis attribution while avoiding duplicate bloat

**Recommendation**: Option C (tag, deduplicate at synthesis)
- Preserves hypothesis attribution for analysis
- Allows LLM to see "which hypotheses found overlapping results" (useful insight)
- Consistent with existing deduplication at synthesis phase

---

### 1.4 Hypothesis Execution Order ⚠️ PERFORMANCE

**Current Design**: Each hypothesis has `exploration_priority` (1-5)

**Question**: Do we execute hypotheses sequentially or in parallel?

**Option A: Sequential** (by priority)
- Execute Priority 1, then Priority 2, etc.
- Pro: Can stop early if sufficient results found
- Con: Slower (no parallelism), complex stopping logic

**Option B: Parallel** (all at once)
- Execute all hypotheses concurrently
- Pro: Faster (parallelism), simpler code
- Con: Can't stop early, may execute low-priority hypotheses unnecessarily

**Option C: Batched** (priorities 1-2 parallel, then 3-5 if needed)
- Execute high-priority hypotheses first
- Check coverage, decide if low-priority needed
- Pro: Balance of speed and efficiency
- Con: More complex, requires coverage assessment LLM call

**Concern**: Trading off speed vs unnecessary work

**Recommendation**: Option B (parallel) for simplicity
- Design philosophy: "User configures budget upfront and walks away"
- No mid-run stopping decisions (fully autonomous)
- Parallelism aligns with existing batch execution model

---

### 1.5 Hypothesis Failure Handling ⚠️ RESILIENCE

**Question**: What happens if a hypothesis search fails?

**Failure Scenarios**:
- API timeout (ClearanceJobs Playwright)
- Rate limit (Twitter 429)
- Zero results found
- LLM query generation error

**Option A: Fail entire task**
- If any hypothesis fails, task fails
- Pro: Conservative (ensures complete coverage)
- Con: Brittle (one bad hypothesis kills entire task)

**Option B: Mark hypothesis failed, continue**
- Log failure, continue with remaining hypotheses
- Pro: Resilient (partial results better than none)
- Con: Incomplete hypothesis coverage

**Option C: Retry failed hypothesis**
- Apply same retry logic as normal tasks
- Pro: Maximizes success rate
- Con: More complex (retry per hypothesis vs per task)

**Concern**: Balancing resilience with completeness

**Recommendation**: Option B (continue on failure) with logging
- Aligns with existing error handling (entity extraction failures don't fail tasks)
- Log hypothesis failures to execution_log.jsonl for visibility
- Report shows "Hypothesis 3: Failed (timeout)" with reasoning

---

### 1.6 Hypothesis Results Storage ⚠️ DATA MODEL

**Question**: How to store hypothesis-specific results?

**Current Structure** (ResearchTask):
```python
@dataclass
class ResearchTask:
    accumulated_results: List[Dict]  # All results
    hypotheses: Optional[Dict]  # Hypothesis definitions
```

**Option A: Flat with tags**
```python
accumulated_results = [
    {"title": "X", "source": "USAJobs", "hypothesis_id": 1},
    {"title": "Y", "source": "USAJobs", "hypothesis_id": 2},
    {"title": "Z", "source": "USAJobs", "hypothesis_id": None}  # From normal search
]
```

**Option B: Nested by hypothesis**
```python
hypothesis_results = {
    1: [{"title": "X", "source": "USAJobs"}],
    2: [{"title": "Y", "source": "USAJobs"}],
    "normal": [{"title": "Z", "source": "USAJobs"}]
}
```

**Option C: Separate field**
```python
accumulated_results: List[Dict]  # Normal search results
hypothesis_results: Dict[int, List[Dict]]  # Per-hypothesis results
```

**Concern**: Querying, deduplication, and synthesis complexity

**Recommendation**: Option A (flat with tags)
- Consistent with existing accumulated_results pattern
- Deduplication works across all results
- Simple filtering: `[r for r in results if r.get('hypothesis_id') == 1]`

---

### 1.7 Configuration Granularity ⚠️ USER CONTROL

**Question**: What should be configurable?

**Current Config**:
```yaml
hypothesis_branching:
  enabled: true
  max_hypotheses_per_task: 5
```

**Proposed Phase 3B Config**:
```yaml
hypothesis_branching:
  enabled: true  # true = Phase 3A (planning), or needs new value?
  execution_mode: "planning_only" | "full_execution"  # NEW
  max_hypotheses_per_task: 5
  execute_mode: "parallel" | "sequential" | "priority_batched"  # NEW?
  allow_hypothesis_retry: true  # NEW?
  max_retries_per_hypothesis: 2  # NEW?
```

**Concerns**:
- Too many knobs → user confusion
- Too few knobs → user can't control behavior
- Config naming: "enabled: true" now ambiguous (planning or execution?)

**Recommendation**: Minimal config with clear semantics
```yaml
hypothesis_branching:
  mode: "off" | "planning" | "execution"  # Clear progression
  max_hypotheses_per_task: 5
  # execution_mode implicit: always parallel (simple, fast)
  # retry implicit: no retry (single-shot per hypothesis)
```

---

## 2. PERFORMANCE CONCERNS (4 issues)

### 2.1 Cost Explosion ⚠️ BUDGET

**Current Cost** (Phase 3A):
- Task decomposition: 1 LLM call
- Per task: 1 source sel + 1 query gen + 1 relevance + 1 entity = 4 LLM calls
- Per hypothesis: 1 generation = 1 LLM call
- Total: 1 + (4 × 3 tasks) + (3 hypotheses × 3 tasks) = 1 + 12 + 9 = 22 LLM calls

**Phase 3B Cost** (Option A: LLM query gen per hypothesis):
- Per hypothesis execution: 1 query gen + 1 relevance + 1 entity? = 3 LLM calls
- Total: 22 (Phase 3A) + (3 LLM × 3 hyp × 3 tasks) = 22 + 27 = 49 LLM calls
- **Cost increase**: 2.2x (49 / 22)

**Phase 3B Cost** (Option B: No query gen, direct signals):
- Per hypothesis execution: 1 relevance + 1 entity? = 2 LLM calls
- Total: 22 + (2 LLM × 9 hyp) = 22 + 18 = 40 LLM calls
- **Cost increase**: 1.8x (40 / 22)

**Question**: Is 2x cost increase acceptable?

**Mitigation Strategies**:
- Use cheaper model for hypothesis queries (gpt-4o-mini instead of gemini-flash)
- Skip entity extraction per hypothesis (only extract at task end from all results)
- Skip relevance filtering per hypothesis (trust hypothesis sources directly)

**Recommendation**: Skip entity extraction per hypothesis
- Extract entities ONCE per task from all accumulated results (normal + hypothesis)
- Reduces: 49 → 31 LLM calls (1.4x increase instead of 2.2x)
- Still expensive but manageable for quality gain

---

### 2.2 Latency Increase ⚠️ USER EXPERIENCE

**Current Runtime** (3 tasks, 2 retries max):
- Task decomposition: ~10s
- Per task (parallel): ~30-60s (source sel + query gen + searches + filter + entity)
- Total: 10s + 60s = 70s (best case)

**Phase 3B Runtime** (3 hyp × 3 tasks = 9 hypothesis executions):
- Hypothesis query gen (parallel): ~15s (3 hyp × 5s)
- Hypothesis searches (parallel): ~30s (depends on sources)
- Hypothesis filtering (parallel): ~20s (3 hyp × 7s)
- Per task: 60s (normal) + 65s (hypotheses) = 125s
- Total: 10s + 125s = 135s (best case)

**Concern**: 2x runtime increase (70s → 135s)

**Mitigation**:
- Parallel execution within task (all hypotheses at once)
- Skip hypothesis retry (single-shot, no reformulation loop)
- User sets timeout ceiling (walks away, accepts longer wait for quality)

**Recommendation**: Accept 2x runtime, optimize parallelism
- Design philosophy: "Quality over speed"
- User configures once, walks away
- Timeout should be 5-10 minutes (not 2-3)

---

### 2.3 API Rate Limiting ⚠️ QUOTA EXHAUSTION

**Problem**: More searches = higher chance of hitting rate limits

**Example**:
- USAJobs: 3 normal tasks + 6 hypothesis searches = 9 USAJobs calls
- Twitter: 3 normal tasks + 3 hypothesis searches = 6 Twitter calls
- Risk: Burn through daily quota faster

**Concern**: Circuit breaker effectiveness

**Current Circuit Breaker**: Skip source for remaining TASKS
- If USAJobs hits 429 on Task 1, skip USAJobs for Tasks 2-3

**Question**: Should circuit breaker skip hypotheses too?
- If USAJobs hits 429 on Hypothesis 1 of Task 1, skip USAJobs for:
  - Remaining hypotheses in Task 1?
  - All Tasks 2-3 (normal + hypothesis)?

**Recommendation**: Extend circuit breaker to hypotheses
- 429 on any search (normal or hypothesis) → skip source for ALL remaining work
- Applies to: remaining hypotheses in current task + all future tasks
- Consistent with existing circuit breaker logic

---

### 2.4 Memory Footprint ⚠️ RESOURCE USAGE

**Current Memory** (3 tasks, 20 results/task):
- In-memory: 60 results × ~2KB = 120KB
- Negligible

**Phase 3B Memory** (3 tasks, 3 hyp, 20 results/hyp):
- Normal: 60 results
- Hypothesis: 9 hyp × 20 results = 180 results
- Total: 240 results × ~2KB = 480KB
- Still negligible

**Concern**: Minimal - not a real issue unless user sets max_hypotheses_per_task > 10

**Recommendation**: No action needed, document memory scaling in config comments

---

## 3. QUALITY CONCERNS (5 issues)

### 3.1 Hypothesis Overlap vs Duplication ⚠️ VALUE PROPOSITION

**Problem**: Hypotheses may find the same results

**Example**:
- Hypothesis 1: "Official job boards" (USAJobs, ClearanceJobs)
- Hypothesis 2: "Contractor career pages" (Brave Search for "Lockheed careers")
- Hypothesis 3: "Social discussions" (Reddit, Twitter)

If all 3 hypotheses include USAJobs:
- 3 duplicate searches to USAJobs
- 3× the results to filter
- Marginal value gain

**Question**: Is overlap a bug or a feature?

**Arguments FOR Overlap**:
- Each hypothesis has DIFFERENT search strategy (different signals, different expected entities)
- Same source, different query → potentially different results
- Example: USAJobs with "GS-2210" vs "cybersecurity Fort Meade" → different listings

**Arguments AGAINST Overlap**:
- Wastes API quota (3 calls instead of 1)
- Duplicates processing (3× filtering, 3× entity extraction)
- Minimal value gain if queries too similar

**Recommendation**: Allow overlap, but LLM should minimize
- Update hypothesis_generation.j2 prompt:
  - "Avoid selecting the same source for multiple hypotheses UNLESS you have distinctly different signals"
  - "If hypotheses share sources, explain why the search strategies differ"
- Let LLM decide (not hardcoded deduplication)

---

### 3.2 Hypothesis Quality Validation ⚠️ GARBAGE IN, GARBAGE OUT

**Problem**: Bad hypotheses → wasted searches

**Bad Hypothesis Examples**:
- **Too vague**: "Government sources might have information" (sources: [all], signals: [none])
- **Duplicate strategy**: Hypothesis 1 and 2 both say "search USAJobs for GS-2210"
- **Unrealistic**: "Dark web forums leak classified programs" (confidence: 85%) - false confidence

**Question**: Should we validate hypothesis quality before execution?

**Option A: Trust LLM** (no validation)
- LLM generates hypotheses, system executes blindly
- Pro: Simple, aligns with "full LLM intelligence" philosophy
- Con: Risk of wasted searches on bad hypotheses

**Option B: LLM self-critique** (before execution)
- After generation, ask LLM: "Review these hypotheses for overlap, vagueness, realism"
- LLM revises hypotheses
- Pro: Better quality
- Con: +1 LLM call per task

**Option C: Heuristic validation** (Python checks)
- Check: sources list not empty, signals list not empty, no exact duplicates
- Pro: Fast, catches obvious errors
- Con: Hardcoded rules (violates design philosophy)

**Recommendation**: Option B (LLM self-critique) ONLY if user enables
- New config: `hypothesis_branching.self_critique: true` (default false)
- Adds 1 LLM call but improves quality
- User choice: speed vs quality

---

### 3.3 Coverage Assessment Truthfulness ⚠️ LLM HONESTY

**Current**: LLM provides coverage_assessment explaining why hypotheses are sufficient

**Example**:
> "Four hypotheses cover official disclosures, whistleblowers, technical research, and journalism - comprehensive coverage of all known pathways"

**Problem**: LLM might claim comprehensive coverage when it's actually incomplete

**Scenario**:
- Query: "What cybersecurity certifications do federal jobs require?"
- LLM generates 2 hypotheses:
  - H1: USAJobs postings
  - H2: Reddit discussions
- Coverage: "Sufficient - official postings + community insights"
- **Missing**: OPM qualification standards, training provider sites, certification vendor pages

**Question**: How to ensure LLM doesn't over-claim coverage?

**Mitigation Options**:
- Add to prompt: "Be honest about coverage gaps - incomplete coverage is OK if you've identified the BEST pathways"
- Ask LLM: "What pathways might exist that these hypotheses DON'T cover?"
- Post-execution: LLM reviews results and assesses if coverage gaps exist

**Recommendation**: Honesty prompt + post-execution review
- Hypothesis generation: "Acknowledge coverage gaps if they exist"
- After execution: LLM sees all results, assesses "Did we miss any obvious pathways?"
- Report includes: "Coverage Gaps Identified" section (transparency)

---

### 3.4 Hypothesis Validation Against Results ⚠️ LEARNING

**Question**: Should we track which hypotheses succeeded/failed?

**Value Proposition**:
- Hypothesis 1 predicted 15 results → found 2 (failed)
- Hypothesis 2 predicted 5 results → found 20 (exceeded)
- Learning: Which hypotheses are accurate predictors?

**Option A: Track and report**
- Store: hypothesis_id, predicted_confidence, actual_results_count, success_rate
- Report shows: "Hypothesis Validation" section with accuracy
- Pro: User learns which hypotheses are reliable
- Con: More complexity, not clear value yet

**Option B: Ignore predictions**
- Hypotheses are exploration, not predictions
- Don't track accuracy
- Pro: Simple
- Con: Miss learning opportunity

**Recommendation**: Option B (ignore) for Phase 3B
- Defer to Phase 3C (if we build adaptive hypothesis tuning)
- For now, focus on execution not optimization

---

### 3.5 Synthesis Complexity ⚠️ REPORT QUALITY

**Problem**: More results = harder synthesis

**Current Synthesis** (Phase 3A):
- Input: 60 results across 3 tasks
- LLM synthesizes: Executive summary, key findings, research process notes
- Works well

**Phase 3B Synthesis**:
- Input: 240 results across 3 tasks × 3-5 hypotheses
- 4x more results to process
- Risk: LLM overwhelmed, report becomes unfocused

**Question**: How to synthesize hypothesis results effectively?

**Option A: Flat synthesis** (ignore hypothesis attribution)
- Treat all 240 results equally
- Synthesize normally
- Pro: Simple
- Con: Loses "which hypothesis found what" insight

**Option B: Hypothesis-aware synthesis** (group by hypothesis)
- Show findings per hypothesis: "Hypothesis 1 found X, Hypothesis 2 found Y"
- Pro: Shows value of each hypothesis
- Con: Report structure more complex

**Option C: Tiered synthesis** (hypothesis summary + overall summary)
- First: Summarize each hypothesis's findings (3-5 mini-summaries)
- Second: Synthesize across all hypotheses (overall findings)
- Pro: Structured, preserves hypothesis value
- Con: Longer reports

**Recommendation**: Option C (tiered synthesis)
- Aligns with "full transparency" philosophy
- User sees value of each hypothesis
- Template adds: "Hypothesis Findings" section before "Key Findings"

---

## 4. USER EXPERIENCE CONCERNS (3 issues)

### 4.1 Report Length Explosion ⚠️ READABILITY

**Current Report Length** (Phase 3A):
- Executive Summary: 3-5 sentences
- Suggested Investigative Angles: 15-30 lines (hypotheses planning)
- Key Findings: 5-10 bullet points
- Research Process Notes: 30-50 lines
- Total: ~100 lines

**Phase 3B Report Length** (with hypothesis findings):
- Executive Summary: 3-5 sentences
- Hypothesis Findings: 50-100 lines (3 hyp × 15-30 lines each)
- Key Findings: 10-15 bullet points (more results → more findings)
- Research Process Notes: 50-75 lines (more tasks/hypotheses)
- Total: ~150-200 lines

**Concern**: 2x report length might overwhelm users

**Mitigation**:
- Collapsible sections in Streamlit UI
- Summary-first structure (key findings up top)
- "Detailed Hypothesis Analysis" as appendix
- Config option: `hypothesis_branching.include_hypothesis_details: false` to hide

**Recommendation**: Structured report with optional details
- Always show: Executive Summary + Key Findings
- Optional: Hypothesis Findings (default: shown, can hide via config)
- Appendix: Full research process notes

---

### 4.2 Progress Visibility ⚠️ USER ANXIETY

**Current Progress** (Phase 3A):
```
🔬 Hypothesis branching enabled - generating investigative hypotheses for 3 tasks...
   ✓ Task 0: Generated 1 hypothesis
   ✓ Task 1: Generated 3 hypotheses
   ✓ Task 2: Generated 3 hypotheses
```

**Phase 3B Progress** (executing hypotheses):
```
🔬 Executing Hypothesis 1/3 for Task 0...
  📋 Query generated: "GS-2210 official OPM standards"
  🔍 Searching: Brave Search, USAJobs
  ✓ Found 15 results
  🔍 Filtering for relevance...
  ✓ Kept 12 results

🔬 Executing Hypothesis 2/3 for Task 0...
  ...
```

**Concern**: Too verbose? Or helpful transparency?

**Recommendation**: Tiered verbosity
- Default: One line per hypothesis: `✓ Hypothesis 1: Found 12 results (15 total, 12 kept)`
- Verbose mode (config): Show full progress like above
- Aligns with existing verbosity patterns

---

### 4.3 Configuration Complexity ⚠️ EASE OF USE

**Problem**: More features = more configuration options

**Current Config** (simple):
```yaml
hypothesis_branching:
  enabled: true
  max_hypotheses_per_task: 5
```

**Phase 3B Config** (with all options):
```yaml
hypothesis_branching:
  mode: "execution"  # off | planning | execution
  max_hypotheses_per_task: 5
  self_critique: false  # LLM reviews hypotheses before execution
  include_hypothesis_details: true  # Show hypothesis findings in report
  execution_timeout_minutes: 10  # Per-hypothesis timeout
```

**Concern**: Too many knobs → user confusion

**Recommendation**: Minimal config with smart defaults
```yaml
hypothesis_branching:
  mode: "execution"  # Simple toggle: off | planning | execution
  max_hypotheses_per_task: 5  # Quality ceiling
  # All other options use smart defaults (no configuration needed)
```

---

## 5. DATA INTEGRITY CONCERNS (2 issues)

### 5.1 Hypothesis Attribution Preservation ⚠️ TRACEABILITY

**Problem**: Need to track which hypothesis found each result

**Storage Strategy** (see Architecture 1.6):
- Tag each result with `hypothesis_id`
- Allows filtering: "Show me results from Hypothesis 2"
- Allows analysis: "Hypothesis 1 found 15 results, Hypothesis 2 found 3"

**Question**: What happens during deduplication?

**Scenario**:
- Hypothesis 1 finds: Result A
- Hypothesis 2 finds: Result A (duplicate)
- Deduplication keeps: 1 copy of Result A
- **Which hypothesis_id to keep?** First? Both (comma-separated)? Priority-based?

**Option A: Keep first**
- Deduplication keeps result with earliest hypothesis_id
- Pro: Simple, deterministic
- Con: Later hypotheses get no credit

**Option B: Keep all (multi-tag)**
```python
{
  "title": "Result A",
  "hypothesis_ids": [1, 2, 3]  # Found by multiple hypotheses
}
```
- Pro: Complete attribution
- Con: More complex querying

**Recommendation**: Option B (multi-tag)
- Preserves complete attribution
- Report can show: "Result A validated by Hypotheses 1, 2, 3" (high confidence)
- Useful for analysis

---

### 5.2 Metadata Explosion ⚠️ FILE SIZE

**Current metadata.json** (Phase 3A):
```json
{
  "hypotheses_by_task": {
    "0": {"hypotheses": [...]},  // ~2KB per task
    "1": {"hypotheses": [...]},
    "2": {"hypotheses": [...]}
  }
}
```
Size: ~6KB

**Phase 3B metadata.json** (with execution results):
```json
{
  "hypotheses_by_task": {
    "0": {
      "hypotheses": [...],  // Definitions (~2KB)
      "execution_results": {
        "1": {"results_found": 15, "results_kept": 12, "errors": null},
        "2": {"results_found": 3, "results_kept": 3, "errors": null}
      }
    }
  }
}
```
Size: ~8KB (still negligible)

**Concern**: Not a real issue unless storing full results in metadata

**Recommendation**: Store summary stats only (not full results)
- execution_results: counts, errors, timing
- Full results stay in results.json (separate file)
- Keeps metadata.json lightweight

---

## 6. TESTING CONCERNS (2 issues)

### 6.1 Test Coverage Complexity ⚠️ VALIDATION

**Phase 3A Testing** (current):
- Test 1: Disabled mode (no hypotheses)
- Test 2: Enabled mode (hypotheses generated)
- Simple: 2 tests, clear success criteria

**Phase 3B Testing** (needed):
- Test 1: Disabled mode (no execution)
- Test 2: Planning mode (Phase 3A behavior)
- Test 3: Execution mode - single hypothesis
- Test 4: Execution mode - multiple hypotheses (parallel)
- Test 5: Execution mode - hypothesis failure handling
- Test 6: Execution mode - deduplication across hypotheses
- Test 7: Execution mode - circuit breaker interaction

**Concern**: 7 tests instead of 2 → more maintenance

**Recommendation**: Tiered testing
- Unit tests: Hypothesis query gen, result tagging, deduplication
- Integration test: 1 comprehensive test (execution mode, 2 tasks, 2 hyp each)
- Validation: Disabled + Planning + Execution (3 E2E tests)

---

### 6.2 Test Query Selection ⚠️ REALISTIC VALIDATION

**Question**: What query to use for Phase 3B testing?

**Requirements**:
- Complex enough to warrant 3-5 hypotheses
- Not too speculative (need actual results, not timeouts)
- Diverse sources (test hypothesis.sources variety)

**Candidates**:
1. "What cybersecurity job opportunities exist for cleared professionals?"
   - Pro: 3-4 hypotheses (official postings, social discussions, contractor sites)
   - Pro: Diverse sources (USAJobs, ClearanceJobs, Twitter, Reddit)
   - Con: Similar to existing tests (not novel validation)

2. "What classified intelligence programs has the NSA operated?"
   - Pro: 4-5 hypotheses (FOIA docs, whistleblowers, technical leaks, journalism)
   - Pro: Tests speculative queries
   - Con: May timeout (sparse results, broad search)

3. "What are the salary ranges for GS-2210 positions in Washington DC?"
   - Pro: 2-3 hypotheses (USAJobs listings, salary databases, social discussions)
   - Pro: Factual, likely to succeed
   - Con: Less hypothesis diversity (mostly official sources)

**Recommendation**: Candidate #1 (cybersecurity jobs)
- Proven to work in existing tests
- Good hypothesis diversity
- Fast execution (under 3 minutes)
- Add assertion: Verify hypothesis_id tags present in results

---

## 7. BACKWARD COMPATIBILITY CONCERNS (1 issue)

### 7.1 Phased Rollout Strategy ⚠️ MIGRATION PATH

**Problem**: Existing users have `hypothesis_branching.enabled: true` for Phase 3A

**Question**: How to introduce Phase 3B without breaking Phase 3A users?

**Option A: New config key**
```yaml
hypothesis_branching:
  enabled: true  # Phase 3A (planning)
  execute: false  # Phase 3B (execution) - NEW KEY
```
- Pro: Backward compatible (enabled: true still works)
- Con: Confusing naming (what does "enabled" mean now?)

**Option B: Rename enabled → mode**
```yaml
hypothesis_branching:
  mode: "planning"  # off | planning | execution
```
- Pro: Clear semantics
- Con: Breaking change (existing configs need update)

**Option C: Auto-upgrade**
```python
# In deep_research.py __init__():
if config.get("hypothesis_branching", {}).get("enabled") is True:
    # Legacy config detected - treat as "planning" mode
    self.hypothesis_mode = "planning"
else:
    self.hypothesis_mode = config.get("hypothesis_branching", {}).get("mode", "off")
```
- Pro: Backward compatible + clear naming
- Con: Config file doesn't reflect actual behavior

**Recommendation**: Option C (auto-upgrade) with deprecation warning
- Support both `enabled: true` (legacy) and `mode: "planning"` (new)
- Print warning: "⚠️  hypothesis_branching.enabled is deprecated, use mode: 'planning' instead"
- Update config_default.yaml to use `mode`

---

## SUMMARY: 23 Critical Concerns

### Architecture (7)
1. Task multiplication vs hypothesis expansion - **CRITICAL**
2. Hypothesis query generation strategy
3. Result deduplication timing and attribution
4. Hypothesis execution order (sequential vs parallel)
5. Hypothesis failure handling
6. Hypothesis results storage model
7. Configuration granularity

### Performance (4)
8. Cost explosion (2x LLM calls)
9. Latency increase (2x runtime)
10. API rate limiting (quota exhaustion)
11. Memory footprint (negligible)

### Quality (5)
12. Hypothesis overlap vs duplication
13. Hypothesis quality validation
14. Coverage assessment truthfulness
15. Hypothesis validation against results
16. Synthesis complexity with 4x results

### User Experience (3)
17. Report length explosion (2x lines)
18. Progress visibility (verbosity)
19. Configuration complexity (too many knobs)

### Data Integrity (2)
20. Hypothesis attribution preservation (multi-tag)
21. Metadata explosion (file size)

### Testing (2)
22. Test coverage complexity (7 tests vs 2)
23. Test query selection

### Backward Compatibility (1)
24. Phased rollout strategy (auto-upgrade recommended)

---

## FINAL RECOMMENDATION

**Proceed with Phase 3B implementation** with the following approach:

### High Priority (Must Resolve Before Coding)
1. **Architecture Decision**: Expand within task (Option B from 1.1)
2. **Query Generation**: LLM per hypothesis (Option A from 1.2)
3. **Deduplication**: Tag with hypothesis_id, dedupe at synthesis (Option C from 1.3)
4. **Execution Order**: Parallel (Option B from 1.4)
5. **Failure Handling**: Continue on failure with logging (Option B from 1.5)
6. **Storage Model**: Flat with tags (Option A from 1.6)
7. **Config Strategy**: Auto-upgrade with deprecation warning (Option C from 7.1)

### Medium Priority (Design During Implementation)
8. **Synthesis**: Tiered (hypothesis findings + overall) (Option C from 3.5)
9. **Report Structure**: Collapsible sections, summary-first (from 4.1)
10. **Progress Verbosity**: One line per hypothesis (from 4.2)
11. **Configuration**: Minimal with smart defaults (from 4.3)

### Low Priority (Defer to Phase 3C)
12. **Hypothesis validation**: No quality checks initially (from 3.2)
13. **Coverage gaps**: Add honesty prompt, no post-execution review yet (from 3.3)
14. **Hypothesis tracking**: Don't track accuracy yet (from 3.4)

### Estimated Implementation Time
- Architecture: 4-6 hours (hypothesis execution loop, query gen, result tagging)
- Testing: 2-3 hours (comprehensive integration test + validation)
- Documentation: 1 hour (config updates, CLAUDE.md)
- **Total**: 7-10 hours

### Risk Assessment
- **High Risk**: Cost explosion (2x), report length (2x)
- **Medium Risk**: Latency (2x), hypothesis overlap, synthesis complexity
- **Low Risk**: Memory, API limits (circuit breaker handles), backward compatibility (auto-upgrade)

**Overall**: Proceed with CAUTION - benefits (hypothesis execution value) likely outweigh costs, but user must accept 2x cost/time tradeoff.
