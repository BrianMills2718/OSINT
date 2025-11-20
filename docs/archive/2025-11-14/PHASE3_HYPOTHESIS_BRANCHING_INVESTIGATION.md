# Phase 3: Hypothesis Branching - Comprehensive Investigation

**Date**: 2025-11-14
**Phase**: Pre-Implementation Investigation
**Estimated Implementation**: 12+ hours (complex feature)
**Status**: Investigation - awaiting approval before implementation

---

## Executive Summary

**What Is Hypothesis Branching?**

Instead of task decomposition generating a single linear query per subtask, **hypothesis branching** generates multiple investigative hypotheses with distinct search strategies. The LLM acts like a senior investigative journalist proposing different angles of investigation.

**Example** (traditional vs hypothesis branching):

**Traditional Task Decomposition** (current system):
```
Research Question: "What classified intelligence programs does the NSA operate?"

Task 0: "NSA classified programs official documentation"
  → Sources: Brave Search, Discord
  → Query: "NSA classified programs official leaks"

Task 1: "NSA surveillance programs whistleblower disclosures"
  → Sources: Twitter, Reddit
  → Query: "Edward Snowden NSA surveillance programs"
```

**Hypothesis Branching** (proposed):
```
Research Question: "What classified intelligence programs does the NSA operate?"

Hypothesis 1 (High Confidence): "Official leaks/disclosures pathway"
  → Statement: "Official government documents or court filings have disclosed program names"
  → Confidence: 70%
  → Search Strategy:
    - Sources: Brave Search (FOIA documents), Discord (research communities)
    - Signals: .gov domains, court filing dates, program codenames
    - Expected Entities: PRISM, XKEYSCORE, ECHELON
  → Exploration Order: First (highest confidence)

Hypothesis 2 (Medium Confidence): "Whistleblower testimony pathway"
  → Statement: "Former NSA employees disclosed program details publicly"
  → Confidence: 50%
  → Search Strategy:
    - Sources: Twitter (real-time), Reddit (discussions), Brave Search (news archives)
    - Signals: Verified whistleblower accounts, Congressional testimony, journalist citations
    - Expected Entities: Edward Snowden, William Binney, Thomas Drake
  → Exploration Order: Second (medium confidence)

Hypothesis 3 (Low Confidence): "Technical research pathway"
  → Statement: "Security researchers reverse-engineered NSA tools/infrastructure"
  → Confidence: 30%
  → Search Strategy:
    - Sources: Discord (infosec communities), Twitter (security researchers)
    - Signals: Technical analysis, malware reports, infrastructure fingerprints
    - Expected Entities: Equation Group, DOUBLEPULSAR, ETERNALBLUE
  → Exploration Order: Third (lower confidence, but high value if confirmed)

After exploring Hypothesis 1:
  - LLM assesses: "Found PRISM, XKEYSCORE via FOIA docs - 70% confidence validated"
  - LLM decides: "Continue to Hypothesis 2 for whistleblower context"
  - LLM adjusts: "Hypothesis 3 now less needed (already found programs), but may provide technical details"
```

**Key Difference**: Traditional system explores one angle at a time sequentially. Hypothesis branching maps out the ENTIRE investigative space upfront, assigns priorities, and allows the LLM to dynamically adjust exploration based on what's found.

---

## Design Philosophy Alignment

**Core Principle**: "No hardcoded heuristics. Full LLM intelligence. Quality-first."

**How Hypothesis Branching Aligns**:

1. ✅ **No Hardcoded Thresholds**: LLM decides hypothesis confidence scores (not rules like "if X then Y")
2. ✅ **Full LLM Intelligence**: LLM generates hypotheses, assigns priorities, decides exploration order
3. ✅ **Quality-First**: User configures `max_hypotheses_per_task` upfront (ceiling), walks away
4. ✅ **Full Context**: LLM sees all hypotheses before deciding which to explore
5. ✅ **LLM Justification**: Every hypothesis requires confidence score + search strategy reasoning
6. ✅ **User Workflow**: Configure once → Run research → Walk away → Get comprehensive results

**Anti-Patterns Avoided**:
- ❌ NOT using fixed sampling ("explore top 3 hypotheses")
- ❌ NOT using hardcoded thresholds ("confidence <50% = skip")
- ❌ NOT using rule-based trees ("if official docs found, skip whistleblowers")

**Correct Approach**:
- ✅ LLM generates 2-5 hypotheses (dynamic count based on question complexity)
- ✅ LLM assigns confidence based on full context (not rules)
- ✅ LLM decides exploration order (not hardcoded "high confidence first")
- ✅ LLM assesses coverage after each hypothesis ("do we need more?")

---

## Motivation: Why Build This?

### Problem 1: Missed Investigative Angles (Current System)

**Example**: "What classified intelligence programs does the NSA operate?"

**Current Behavior** (linear task decomposition):
- Task 0: "NSA classified programs" → finds PRISM, ECHELON
- Task 1: "NSA surveillance programs" → finds XKEYSCORE (partial overlap with Task 0)
- Task 2: "NSA cybersecurity operations" → finds TAO unit (new angle, but accidental)

**Issue**: System didn't plan to explore "technical reverse-engineering" angle (e.g., Equation Group leaks). It was never in the task decomposition because the LLM didn't think of it upfront.

**Hypothesis Branching Solution**:
- LLM maps ENTIRE space upfront: official leaks, whistleblowers, technical research, contractor disclosures
- Explores systematically based on confidence
- If one pathway yields rich results, LLM can deprioritize others

### Problem 2: No Systematic Coverage Assessment

**Example**: User asks "What classified programs does the CIA run?"

**Current Behavior**:
- System runs 5 tasks, finds 20 results, synthesizes report
- No way to know: "Did we explore all angles? Or did we miss entire categories?"

**Hypothesis Branching Solution**:
- LLM generates hypotheses BEFORE searching (coverage map)
- After each hypothesis explored, LLM assesses: "Do we have sufficient coverage?"
- User sees transparency: "Explored 3/4 hypotheses. Skipped Hypothesis 4 (contractor leaks) due to time budget."

### Problem 3: Inefficient Exploration (No Prioritization)

**Example**: "What are federal cybersecurity job opportunities?"

**Current Behavior** (equal priority):
- Task 0: Official job postings (USAJobs, ClearanceJobs) - HIGH VALUE
- Task 1: Career advice blogs (Brave Search) - LOW VALUE
- Task 2: Social media discussions (Twitter, Reddit) - MEDIUM VALUE

All tasks get equal resources (same retry budget, same time allocation).

**Hypothesis Branching Solution**:
- Hypothesis 1 (90% confidence): "Official job boards" → Explore first, allocate more retries
- Hypothesis 2 (60% confidence): "Social discussions" → Explore second
- Hypothesis 3 (30% confidence): "Career blogs" → Explore last, may skip if budget exhausted
- LLM decides dynamically: "Hypothesis 1 found 50 jobs, sufficient coverage, skip Hypothesis 3"

---

## Implementation Concept (High-Level)

### 1. Hypothesis Generation (New Step Before Task Execution)

**Current Flow**:
```
User Question → Task Decomposition → Execute Tasks → Synthesize Report
```

**New Flow**:
```
User Question → Task Decomposition → Hypothesis Generation (per task) → Execute Hypotheses → Synthesize Report
```

**Hypothesis Generation Prompt** (new template: `prompts/deep_research/hypothesis_generation.j2`):

```jinja2
You are an investigative researcher planning a comprehensive investigation.

RESEARCH QUESTION: {{ research_question }}
SUBTASK: {{ task_query }}

Your job: Generate 2-5 investigative hypotheses for this subtask. Each hypothesis represents
a different angle of investigation.

For each hypothesis, provide:
1. **Statement**: What are you looking for? (1-2 sentences)
2. **Confidence**: How confident are you this pathway will yield results? (0-100%)
3. **Search Strategy**:
   - Which sources to prioritize (USAJobs, Twitter, Brave Search, etc.)
   - What signals to look for (keywords, domain patterns, author credentials)
   - Expected entities (organizations, people, programs, technologies)
4. **Exploration Priority**: Should this be explored first, second, third? Why?

GUIDELINES:
- Generate hypotheses that cover DIFFERENT investigative angles (not overlapping)
- Assign confidence based on question type:
  - Factual queries (job listings, official docs): high confidence for official sources
  - Speculative queries (classified programs): lower confidence, multiple pathways needed
- Explain search strategy reasoning (why these sources, why these signals)
- Prioritize hypotheses by confidence × value (high confidence + high value = explore first)

OUTPUT (JSON):
{
  "hypotheses": [
    {
      "id": 1,
      "statement": "Official government job postings contain structured listings for cybersecurity roles",
      "confidence": 90,
      "search_strategy": {
        "sources": ["USAJobs", "ClearanceJobs"],
        "signals": ["GS-2210 series", "cybersecurity specialist", "TS/SCI clearance"],
        "expected_entities": ["NSA", "FBI", "CISA", "GS-2210"]
      },
      "exploration_priority": 1,
      "priority_reasoning": "Highest confidence pathway - official sources directly answer query"
    },
    {
      "id": 2,
      "statement": "Federal employees discuss hiring trends and application tips on social media",
      "confidence": 60,
      "search_strategy": {
        "sources": ["Twitter", "Reddit"],
        "signals": ["#FedJobs", "r/fednews", "verified government accounts"],
        "expected_entities": ["USAJOBS", "security clearance process", "hiring freezes"]
      },
      "exploration_priority": 2,
      "priority_reasoning": "Medium confidence - social media provides context and insider tips"
    }
  ],
  "coverage_assessment": "Two hypotheses cover official and informal pathways - sufficient for job query"
}
```

**Key Fields**:
- `confidence` (0-100): LLM's assessment of success probability
- `search_strategy.sources`: Which integrations to use (prioritized order)
- `search_strategy.signals`: What patterns indicate relevance
- `expected_entities`: What entities we expect to find (helps validation)
- `exploration_priority`: Order to explore (1 = first)

### 2. Hypothesis Execution (Modified Task Execution)

**Current Execution**:
```python
# research/deep_research.py - _execute_task_with_retry()
# Fixed approach: select sources, generate query, execute, retry if needed
```

**Hypothesis-Based Execution**:
```python
# research/deep_research.py - _execute_hypothesis()
async def _execute_hypothesis(self, task: ResearchTask, hypothesis: Dict) -> HypothesisResult:
    """Execute a single hypothesis with its defined search strategy."""

    # Use hypothesis-defined sources (skip source selection LLM call)
    selected_sources = hypothesis["search_strategy"]["sources"]

    # Use hypothesis-defined signals in query generation
    query_params = await self._generate_query_for_hypothesis(
        task_query=task.query,
        hypothesis_statement=hypothesis["statement"],
        expected_signals=hypothesis["search_strategy"]["signals"]
    )

    # Execute search with hypothesis-specific signals
    results = await self._execute_searches(selected_sources, query_params)

    # Validate results against expected entities
    validated = await self._validate_hypothesis_results(
        results=results,
        expected_entities=hypothesis["search_strategy"]["expected_entities"],
        hypothesis_statement=hypothesis["statement"]
    )

    return HypothesisResult(
        hypothesis_id=hypothesis["id"],
        confidence_actual=validated["actual_confidence"],  # Did it match expected?
        results_found=validated["results"],
        entities_found=validated["entities"],
        coverage_contribution=validated["coverage"]  # How much new information?
    )
```

**Key Changes**:
1. **Skip source selection**: Use hypothesis-defined sources directly
2. **Signal-aware query generation**: Incorporate expected signals into query
3. **Expected entity validation**: Check if we found what hypothesis predicted
4. **Coverage tracking**: Measure how much new information each hypothesis contributes

### 3. Hypothesis Prioritization & Dynamic Exploration

**Priority Queue Approach**:
```python
# research/deep_research.py - _execute_task_with_hypotheses()
async def _execute_task_with_hypotheses(self, task: ResearchTask) -> TaskResult:
    """Execute task using hypothesis branching."""

    # Step 1: Generate hypotheses
    hypotheses = await self._generate_hypotheses(task.query, self.research_question)

    # Step 2: Sort by exploration_priority (LLM-defined order)
    hypotheses_sorted = sorted(hypotheses["hypotheses"], key=lambda h: h["exploration_priority"])

    # Step 3: Execute in priority order
    results_accumulated = []
    for hypothesis in hypotheses_sorted:
        # Check budget (time, retries, max_hypotheses)
        if self._should_skip_hypothesis(hypothesis, results_accumulated):
            print(f"⏭️ Skipping Hypothesis {hypothesis['id']} - sufficient coverage or budget exhausted")
            continue

        # Execute hypothesis
        print(f"🔬 Exploring Hypothesis {hypothesis['id']}: {hypothesis['statement']}")
        result = await self._execute_hypothesis(task, hypothesis)
        results_accumulated.append(result)

        # Assess coverage after each hypothesis
        coverage_decision = await self._assess_coverage(
            hypotheses_explored=results_accumulated,
            hypotheses_remaining=[h for h in hypotheses_sorted if h not in results_accumulated],
            research_question=self.research_question
        )

        if coverage_decision["sufficient"]:
            print(f"✅ Coverage sufficient: {coverage_decision['reasoning']}")
            break

    return TaskResult(
        task_id=task.id,
        hypotheses_explored=results_accumulated,
        coverage_assessment=coverage_decision
    )
```

**Dynamic Decision Points**:
1. **Before each hypothesis**: Check budget (time, retries remaining, max_hypotheses config)
2. **After each hypothesis**: Ask LLM: "Do we have sufficient coverage to stop?"
3. **Coverage assessment**: LLM decides whether to continue based on results found

### 4. Coverage Assessment (New LLM Call After Each Hypothesis)

**Coverage Assessment Prompt** (new template: `prompts/deep_research/coverage_assessment.j2`):

```jinja2
You are assessing research coverage for an investigative query.

RESEARCH QUESTION: {{ research_question }}
SUBTASK: {{ task_query }}

HYPOTHESES EXPLORED SO FAR:
{% for result in hypotheses_explored %}
Hypothesis {{ result.hypothesis_id }}: {{ result.hypothesis_statement }}
  - Expected Confidence: {{ result.confidence_expected }}%
  - Actual Confidence: {{ result.confidence_actual }}%
  - Results Found: {{ result.results_count }}
  - Entities Found: {{ result.entities|join(', ') }}
  - Coverage Contribution: {{ result.coverage_contribution }}
{% endfor %}

HYPOTHESES REMAINING:
{% for hypothesis in hypotheses_remaining %}
Hypothesis {{ hypothesis.id }}: {{ hypothesis.statement }}
  - Expected Confidence: {{ hypothesis.confidence }}%
  - Exploration Priority: {{ hypothesis.exploration_priority }}
{% endfor %}

BUDGET STATUS:
- Time Remaining: {{ time_remaining_minutes }} minutes
- Max Hypotheses: {{ max_hypotheses }} ({{ hypotheses_explored|length }} explored)
- Retry Budget: {{ retries_remaining }} retries available

QUESTION: Do we have sufficient coverage to stop exploring hypotheses?

Consider:
1. Have we found diverse results across multiple pathways?
2. Are remaining hypotheses low-value (low confidence × low expected entities)?
3. Would exploring more hypotheses yield diminishing returns?
4. Do we have budget constraints (time, retries)?

OUTPUT (JSON):
{
  "sufficient": true | false,
  "reasoning": "Why coverage is sufficient (or why we should continue)",
  "recommended_next": 3 | null  // If continue, which hypothesis ID to explore next?
}
```

**Coverage Decision Factors** (LLM evaluates):
- **Diversity**: Have we explored multiple pathways? (official, unofficial, technical, etc.)
- **Diminishing Returns**: Would next hypothesis add significant new information?
- **Budget**: Do we have time/retries to explore more?
- **Confidence Validation**: Did high-confidence hypotheses pan out? (If yes, stop. If no, continue.)

---

## Configuration (User-Adjustable)

**New Config Section** (`config_default.yaml`):

```yaml
research:
  # Existing config
  max_tasks: 5
  max_retries_per_task: 2
  max_time_minutes: 10

  # NEW: Hypothesis Branching Config
  hypothesis_branching:
    enabled: true  # Toggle feature on/off

    max_hypotheses_per_task: 5  # CEILING (not target) - LLM decides actual count

    hypothesis_mode: "adaptive"  # Options: "adaptive", "exhaustive", "best_first"
    # - adaptive: LLM decides when to stop (coverage assessment)
    # - exhaustive: Explore ALL hypotheses within budget
    # - best_first: Explore only highest priority (exploration_priority=1)

    exploration_mode: "sequential"  # Options: "sequential", "parallel"
    # - sequential: Explore hypotheses one at a time (allows coverage assessment between)
    # - parallel: Explore all hypotheses concurrently (faster, but no early stopping)

    min_confidence_threshold: 0  # OPTIONAL filter (0 = no filter, LLM decides all)
    # If >0: Skip hypotheses with confidence < threshold
    # Recommendation: Leave at 0 (let LLM decide) unless user wants hard filter
```

**Configuration Philosophy**:
- `max_hypotheses_per_task`: CEILING (LLM can generate fewer)
- `hypothesis_mode`: "adaptive" = LLM-driven stopping (recommended)
- `exploration_mode`: "sequential" allows coverage assessment (recommended)
- `min_confidence_threshold`: 0 = no hardcoded filter (LLM intelligence)

**User Workflow**:
```python
# User configures ONCE
research = SimpleDeepResearch(
    max_tasks=3,
    max_hypotheses_per_task=4,  # Up to 4 hypotheses per task
    hypothesis_mode="adaptive",  # LLM decides when sufficient
    max_time_minutes=15
)

# User walks away - system handles rest
result = await research.research("What classified intelligence programs does the NSA operate?")

# System generates 2-4 hypotheses per task (LLM decides count)
# Explores sequentially, LLM assesses coverage after each
# Stops early if sufficient coverage (no wasted budget)
```

---

## Implementation Complexity Analysis

### Estimated Time: 12-16 hours

**Breakdown**:

1. **Hypothesis Generation** (3-4 hours)
   - Create `prompts/deep_research/hypothesis_generation.j2` template
   - Add `_generate_hypotheses()` method to `research/deep_research.py`
   - JSON schema design (hypothesis structure)
   - Testing with 3-5 different query types

2. **Hypothesis Execution** (4-5 hours)
   - Create `_execute_hypothesis()` method
   - Modify `_execute_task_with_retry()` to call `_execute_task_with_hypotheses()`
   - Signal-aware query generation (incorporate expected signals)
   - Expected entity validation logic
   - Coverage contribution calculation

3. **Coverage Assessment** (2-3 hours)
   - Create `prompts/deep_research/coverage_assessment.j2` template
   - Add `_assess_coverage()` method
   - Dynamic stopping logic (check coverage after each hypothesis)
   - Budget tracking (time, retries, max_hypotheses)

4. **Configuration & Control Flow** (2-3 hours)
   - Add `hypothesis_branching` config section
   - Implement hypothesis_mode logic (adaptive/exhaustive/best_first)
   - Implement exploration_mode logic (sequential/parallel)
   - Backward compatibility (feature toggle - enabled: false uses old system)

5. **Testing & Validation** (3-4 hours)
   - Create test suite with diverse queries:
     - Factual query: "federal cybersecurity job opportunities" (expect 1-2 hypotheses, high confidence)
     - Speculative query: "NSA classified programs" (expect 3-5 hypotheses, varied confidence)
     - Narrow query: "GS-2210 job series" (expect 1 hypothesis, very high confidence)
   - Validate hypothesis generation quality
   - Validate coverage assessment decisions
   - Validate backward compatibility (enabled: false works)

6. **Report Integration** (1-2 hours)
   - Update `prompts/deep_research/report_synthesis.j2`
   - Add "Hypothesis Exploration" section to final report
   - Show which hypotheses were explored, which were skipped, coverage reasoning

**Total**: 15-21 hours (median ~18 hours)

**Complexity Factors**:
- **High**: Multiple new LLM calls (hypothesis generation, coverage assessment)
- **High**: New data structures (HypothesisResult, coverage tracking)
- **Medium**: Control flow changes (priority queue, dynamic stopping)
- **Low**: Configuration (straightforward YAML additions)

---

## Concerns & Uncertainties

### Concern 1: LLM Hypothesis Quality

**Question**: Will the LLM generate diverse, non-overlapping hypotheses?

**Risk**: LLM generates 3 nearly-identical hypotheses with slight wording changes
- Example: "Official job postings", "Government job listings", "Federal employment opportunities" (all the same)

**Mitigation**:
- Prompt explicitly requires: "Generate hypotheses that cover DIFFERENT investigative angles"
- Add examples to prompt showing diverse vs overlapping hypotheses
- Validation step: Check hypothesis similarity (if >80% overlap in sources/signals, merge)

**Test Plan**:
- Run hypothesis generation on 10 diverse queries
- Manually review: Are hypotheses truly distinct? Or overlapping?
- If overlapping >30%: Iterate on prompt

**Likelihood**: Medium (LLMs sometimes struggle with "diverse" without examples)

### Concern 2: Coverage Assessment Accuracy

**Question**: Can the LLM accurately assess when coverage is sufficient?

**Risk**: LLM stops too early ("1 hypothesis found 10 results, sufficient!") or too late (explores all 5 hypotheses when 2 would suffice)

**Mitigation**:
- Provide clear criteria in coverage assessment prompt:
  - Diversity: "Have we explored at least 2 different pathways?"
  - Diminishing Returns: "Would next hypothesis yield >20% new information?"
  - Budget: "Do we have <30% budget remaining? If so, stop."
- Test with queries that have clear stopping points

**Test Plan**:
- Query 1 (obvious coverage): "federal job postings" - expect stop after Hypothesis 1 (official sources)
- Query 2 (needs multiple): "NSA programs" - expect explore 2-3 hypotheses (diverse pathways needed)
- Query 3 (budget exhausted): Set low time budget, verify early stopping

**Likelihood**: Medium (coverage is subjective, LLM may be conservative or aggressive)

### Concern 3: Increased LLM Cost

**Question**: How many additional LLM calls does this add?

**Current System** (per task):
- 1 source selection call
- 1-3 relevance evaluation calls (per retry)
- Total: ~2-4 LLM calls per task

**Hypothesis System** (per task):
- 1 hypothesis generation call (new)
- 0 source selection calls (hypothesis defines sources)
- 1-5 hypothesis execution calls (each hypothesis = mini-task)
  - Each includes: 1 query generation, 1 relevance evaluation
- 1-4 coverage assessment calls (after each hypothesis)
- Total: ~6-15 LLM calls per task

**Cost Impact**:
- **Best Case**: 6 calls (1 hypothesis + 1 coverage) vs 2 calls (current) = 3x cost
- **Worst Case**: 15 calls (5 hypotheses + 5 coverage) vs 4 calls (current) = 3.75x cost

**Mitigation**:
- User configures `max_hypotheses_per_task` as budget control
- LLM uses adaptive mode to stop early (coverage assessment prevents wasted calls)
- Cost increase justified by quality improvement (diverse angles, systematic coverage)

**User Control**:
```yaml
# Low-budget user
hypothesis_branching:
  enabled: true
  max_hypotheses_per_task: 2  # Only explore 2 hypotheses max

# High-budget user
hypothesis_branching:
  enabled: true
  max_hypotheses_per_task: 5  # Comprehensive exploration
```

**Likelihood**: High (cost increase is real, but controllable)

### Concern 4: Hypothesis Overhead for Simple Queries

**Question**: Does hypothesis branching add unnecessary complexity for straightforward queries?

**Example**: "GS-2210 job series official documentation"
- This query has 1 obvious pathway: Official government sources
- Generating 3-5 hypotheses wastes time/cost

**Mitigation**:
- LLM can generate 1 hypothesis for simple queries (no minimum enforced)
- Hypothesis generation prompt: "Generate 2-5 hypotheses. For simple queries, 1-2 is sufficient."
- Coverage assessment: If Hypothesis 1 has 95% confidence AND finds expected entities, stop immediately

**Test Plan**:
- Query 1 (simple): "GS-2210 job series" - expect 1 hypothesis, stop after exploration
- Query 2 (complex): "NSA programs" - expect 3-5 hypotheses, explore multiple

**Likelihood**: Low (LLM can adapt hypothesis count, but prompt must guide this)

### Concern 5: Parallelization Challenges (exploration_mode: "parallel")

**Question**: Can we run hypotheses in parallel without losing coverage assessment benefits?

**Trade-offs**:

**Sequential Exploration**:
- ✅ Coverage assessment after each hypothesis (dynamic stopping)
- ✅ Budget-aware (can stop mid-exploration)
- ❌ Slower (one hypothesis at a time)

**Parallel Exploration**:
- ✅ Faster (all hypotheses execute concurrently)
- ❌ No early stopping (must explore ALL hypotheses)
- ❌ No coverage assessment between hypotheses

**Mitigation**:
- Default to `exploration_mode: "sequential"` (recommended)
- Offer `parallel` for time-constrained users who want speed over efficiency
- Document trade-offs clearly in config

**Recommendation**: Start with sequential only (defer parallel to future optimization)

**Likelihood**: Low (sequential is simpler, defer parallel until proven need)

### Concern 6: Backward Compatibility

**Question**: Can we disable hypothesis branching without breaking existing code?

**Mitigation**:
- Add feature toggle: `hypothesis_branching.enabled: false` (uses old task execution)
- Keep existing `_execute_task_with_retry()` method intact
- New code path: `_execute_task_with_hypotheses()` only called if enabled
- All existing tests pass with `enabled: false`

**Implementation**:
```python
# research/deep_research.py
async def _execute_task(self, task: ResearchTask):
    """Execute task - chooses hypothesis branching or traditional based on config."""

    if self.config.get("hypothesis_branching", {}).get("enabled", False):
        return await self._execute_task_with_hypotheses(task)  # NEW
    else:
        return await self._execute_task_with_retry(task)  # EXISTING
```

**Test Plan**:
- Run full test suite with `enabled: false` - expect all tests pass
- Run full test suite with `enabled: true` - expect new behavior

**Likelihood**: Low (straightforward feature toggle pattern)

---

## Open Questions (Need User Input Before Implementation)

### Question 1: Hypothesis Count - Ceiling or Target?

**Current Design**: `max_hypotheses_per_task: 5` is a CEILING (LLM can generate 1-5)

**Alternative**: Make it a TARGET ("generate exactly 5 hypotheses for every task")

**Recommendation**: CEILING (aligns with design philosophy - LLM decides, no hardcoded targets)

**User Decision Needed**: Confirm ceiling approach is correct?

### Question 2: Confidence Threshold - Hard Filter or Soft Guidance?

**Current Design**: `min_confidence_threshold: 0` (no filter, LLM decides all hypotheses)

**Alternative**: `min_confidence_threshold: 30` (skip hypotheses with confidence <30%)

**Recommendation**: 0 (no hardcoded filter - LLM intelligence decides)

**User Decision Needed**: Should we offer hard filter, or trust LLM entirely?

### Question 3: Parallel Exploration - Now or Later?

**Current Design**: Implement `sequential` only (defer `parallel` to future)

**Alternative**: Implement both modes from start (adds 2-3 hours to timeline)

**Recommendation**: Sequential only (simpler, defer parallel until proven need)

**User Decision Needed**: Start with sequential, or build both modes now?

### Question 4: Expected Entity Validation - Strict or Lenient?

**Hypothesis includes**: `expected_entities: ["PRISM", "XKEYSCORE", "ECHELON"]`

**Strict Validation**: If hypothesis finds 0 expected entities → mark hypothesis as "failed confidence"
**Lenient Validation**: If hypothesis finds valuable results (even if not expected entities) → mark as success

**Current Design**: Lenient (entities are guidance, not hard requirements)

**User Decision Needed**: Should expected entities be strict validation or soft guidance?

### Question 5: Hypothesis Storage - In Report or Metadata?

**Where to document explored hypotheses?**

**Option A**: Final report has "Hypothesis Exploration" section showing all hypotheses + coverage reasoning
**Option B**: Metadata only (execution_log.jsonl contains hypothesis data, report stays concise)
**Option C**: Both (report has summary, metadata has full details)

**Recommendation**: Option C (report summary + metadata details)

**User Decision Needed**: How much hypothesis detail should appear in final report?

---

## Success Criteria (Before Claiming "Phase 3 Complete")

### Functional Criteria

- [ ] Hypothesis generation produces 1-5 hypotheses per task (LLM-decided count)
- [ ] Hypotheses are diverse (not overlapping >30% in sources/signals)
- [ ] Hypotheses include all required fields (statement, confidence, search_strategy, priority)
- [ ] Hypothesis execution uses hypothesis-defined sources (skips source selection)
- [ ] Coverage assessment makes intelligent stopping decisions (not always exhaustive)
- [ ] Adaptive mode stops early when coverage sufficient (saves budget)
- [ ] Config toggle `enabled: false` uses old system (backward compatible)

### Quality Criteria

- [ ] Hypothesis generation quality: 3/5 test queries produce excellent hypotheses (diverse, high-value)
- [ ] Coverage assessment accuracy: 4/5 test queries stop at appropriate point (not too early, not too late)
- [ ] Cost efficiency: Adaptive mode uses <150% cost vs exhaustive mode (early stopping works)
- [ ] Simple queries: Queries with 1 obvious pathway generate 1-2 hypotheses (not forcing 5)
- [ ] Complex queries: Queries with multiple angles generate 3-5 hypotheses (comprehensive coverage)

### Testing Criteria

- [ ] Test 1 (simple): "GS-2210 job series" → 1 hypothesis, 100% confidence, stops after first
- [ ] Test 2 (factual): "federal cybersecurity jobs" → 2-3 hypotheses, high confidence, stops after 1-2
- [ ] Test 3 (speculative): "NSA classified programs" → 3-5 hypotheses, varied confidence, explores 2-3
- [ ] Test 4 (budget exhausted): Low time budget → early stopping via coverage assessment
- [ ] Test 5 (backward compat): `enabled: false` → uses old system, all existing tests pass

### Documentation Criteria

- [ ] CONFIG_DEFAULT.yaml has hypothesis_branching section with comments
- [ ] CLAUDE.md updated with Phase 3 status
- [ ] STATUS.md updated with Phase 3 validation results
- [ ] Final report includes "Hypothesis Exploration" section (if enabled)
- [ ] Execution log contains hypothesis metadata (generation, exploration, coverage decisions)

---

## Implementation Phases (If Approved)

### Phase 3A: Foundation (4-5 hours)

**Goal**: Hypothesis generation working, no execution yet

1. Create `prompts/deep_research/hypothesis_generation.j2` template
2. Add `_generate_hypotheses()` method to `research/deep_research.py`
3. Add config section `hypothesis_branching` to `config_default.yaml`
4. Test hypothesis generation on 5 diverse queries (manual review quality)

**Deliverable**: Hypothesis generation produces diverse hypotheses for test queries

### Phase 3B: Execution (5-6 hours)

**Goal**: Hypotheses execute with their defined search strategies

1. Create `_execute_hypothesis()` method
2. Create `_execute_task_with_hypotheses()` method (priority queue logic)
3. Modify `_execute_task()` to route based on config toggle
4. Test hypothesis execution (no coverage assessment yet - runs all hypotheses)

**Deliverable**: Hypothesis-based execution works, produces results per hypothesis

### Phase 3C: Coverage Assessment (3-4 hours)

**Goal**: LLM decides when to stop exploring hypotheses

1. Create `prompts/deep_research/coverage_assessment.j2` template
2. Add `_assess_coverage()` method
3. Integrate coverage assessment into hypothesis execution loop
4. Test adaptive stopping on 5 diverse queries

**Deliverable**: Adaptive mode stops early when coverage sufficient

### Phase 3D: Polish & Validation (3-4 hours)

**Goal**: Production-ready, tested, documented

1. Update report template with "Hypothesis Exploration" section
2. Add hypothesis metadata to execution_log.jsonl
3. Run full test suite with `enabled: false` (backward compat)
4. Run full test suite with `enabled: true` (new behavior)
5. Update CLAUDE.md, STATUS.md with Phase 3 validation results

**Deliverable**: Phase 3 production-ready, all success criteria met

---

## Recommendation

**Proceed with Phase 3 implementation?**

**Pros**:
- ✅ Aligns perfectly with design philosophy (LLM intelligence, no hardcoded heuristics)
- ✅ Solves real problems (missed angles, no coverage assessment, inefficient exploration)
- ✅ User maintains control (config-driven, feature toggle, budget limits)
- ✅ Clear success criteria (testable, measurable)

**Cons**:
- ⚠️ High complexity (12-16 hours estimated, 3-4x LLM cost increase)
- ⚠️ Some uncertainties (hypothesis quality, coverage accuracy)
- ⚠️ Overhead for simple queries (mitigated by LLM-adaptive hypothesis count)

**Recommendation**: **PROCEED** if user confirms:
1. Ceiling approach for `max_hypotheses_per_task` (LLM decides count)
2. No hard confidence filter (trust LLM intelligence)
3. Sequential exploration only (defer parallel)
4. Lenient entity validation (guidance not strict requirements)
5. Report summary + metadata details (both)

**Next Step**: Get user approval on open questions, then start Phase 3A (foundation).

---

**END OF INVESTIGATION**
