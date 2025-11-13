# LLM-Driven Intelligence Implementation Plan

**Created**: 2025-11-12
**Status**: Planning Phase
**Design Philosophy**: No hardcoded heuristics. Full LLM intelligence. Quality-first.

---

## Design Philosophy

This implementation follows the core principles documented in CLAUDE.md:

**Core Principle**: Trust the LLM to make intelligent decisions based on full context, not programmatic rules.

**Anti-Patterns** (FORBIDDEN):
- ❌ Hardcoded thresholds ("drop source after 2 failures")
- ❌ Fixed sampling limits (top 5, first 10, etc.)
- ❌ Rule-based decision trees ("if X then Y")
- ❌ Premature optimization for cost/speed over quality

**Correct Approach** (REQUIRED):
- ✅ Give LLM full context and ask for intelligent decisions
- ✅ Make ALL limits user-configurable (not hardcoded)
- ✅ Require LLM to justify all decisions with reasoning
- ✅ Optimize for quality - user configures budget upfront and walks away
- ✅ Use LLM's 1M token context fully (no artificial sampling)

**User Workflow**: Configure parameters once → Run research → Walk away → Get comprehensive results

---

## Phase 1: Mentor-Style Reasoning Notes

**Estimated Time**: 2 hours
**Goal**: LLM explains its decision-making process like an expert researcher
**Impact**: Users understand why research took the path it did, can adjust future queries

### Overview

Add reasoning capture to ALL major LLM decisions:
- Source selection (why these sources?)
- Continuation decisions (why keep searching or stop?)
- Query reformulation (why this new angle?)
- Result filtering (why keep/reject these results?)

The LLM acts as a mentor, explaining interesting decisions without arbitrary limits on which decisions to highlight.

### Prompt Changes

#### 1. Source Selection - `prompts/deep_research/source_selection.j2`

**Add to end of prompt (before schema)**:
```jinja2
REASONING REQUIREMENT:
For each source you select, explain:
1. What specific information it might provide for this query
2. Why it's relevant to this particular research question
3. What would be missing if we excluded it

For sources you DON'T select, you don't need to explain (focus on positive choices).
```

**Schema Change (lines 30-45)**:
```jinja2
{
  "type": "object",
  "properties": {
    "selected_sources": {
      "type": "array",
      "items": {"type": "string"},
      "description": "Sources to query for this task"
    },
    "reasoning": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "source": {"type": "string"},
          "why_selected": {"type": "string"},
          "expected_information": {"type": "string"},
          "value_proposition": {"type": "string"}
        },
        "required": ["source", "why_selected", "expected_information"]
      },
      "description": "Explanation for each selected source"
    }
  },
  "required": ["selected_sources", "reasoning"]
}
```

#### 2. Relevance Evaluation - `prompts/deep_research/relevance_evaluation.j2`

**Add to prompt (after numbered results, before schema)**:
```jinja2
REASONING REQUIREMENT:
In your response, explain:
1. Why you're accepting or rejecting this batch
2. For REJECT: What's fundamentally wrong? (off-topic, wrong domain, etc.)
3. For ACCEPT: What makes these results valuable?
4. For continue_searching: Why more results needed OR why current results sufficient?

Be specific - reference result numbers if helpful (e.g., "Results #2, #5, #8 are highly relevant because...")
```

**Schema Change (add reasoning field)**:
```jinja2
{
  "decision": "ACCEPT" | "REJECT",
  "reason": "Brief decision summary (1 sentence)",
  "detailed_reasoning": "Detailed explanation of decision (2-4 sentences)",
  "relevant_indices": [0, 2, 5],
  "continue_searching": true | false,
  "continuation_reason": "Why continue/stop",
  "continuation_reasoning": "Detailed explanation (2-3 sentences)"
}
```

#### 3. Query Reformulation - `prompts/deep_research/query_reformulation_relevance.j2`

**Add to prompt (before examples)**:
```jinja2
REASONING REQUIREMENT:
Explain your reformulation strategy:
1. What was wrong with the previous query?
2. What angle are you trying next?
3. What do you expect to find with this new query?
4. How does this query preserve the original task intent while improving results?

Be specific about your reasoning - this helps the user understand your search strategy.
```

**Schema Change**:
```jinja2
{
  "query": "reformulated search query",
  "reformulation_strategy": "Brief description of strategy",
  "detailed_reasoning": "Explanation of why this query will work better (2-4 sentences)",
  "expected_improvement": "What this query should find that previous didn't"
}
```

### Code Integration

#### File: `research/deep_research.py`

**Change 1 - Capture Source Selection Reasoning (lines 565-610)**

```python
# BEFORE (line 593):
selected_sources = parsed.get("selected_sources", [])

# AFTER:
selected_sources = parsed.get("selected_sources", [])
source_reasoning = parsed.get("reasoning", [])

# Log reasoning
if source_reasoning and self.logger:
    for reasoning in source_reasoning:
        self.logger.log_llm_reasoning(
            decision_type="source_selection",
            task_id=task.id,
            source=reasoning.get("source"),
            reasoning=reasoning.get("detailed_reasoning", reasoning.get("why_selected")),
            context={
                "expected_information": reasoning.get("expected_information"),
                "value_proposition": reasoning.get("value_proposition")
            }
        )
```

**Change 2 - Capture Relevance Reasoning (lines 1382-1412)**

```python
# BEFORE (line 1390):
should_accept = parsed.get("decision") == "ACCEPT"
reason = parsed.get("reason", "")

# AFTER:
should_accept = parsed.get("decision") == "ACCEPT"
reason = parsed.get("reason", "")
detailed_reasoning = parsed.get("detailed_reasoning", reason)
continuation_reasoning = parsed.get("continuation_reasoning", parsed.get("continuation_reason", ""))

# Log reasoning
if self.logger:
    self.logger.log_llm_reasoning(
        decision_type="relevance_evaluation",
        task_id=task.id,
        decision=parsed.get("decision"),
        reasoning=detailed_reasoning,
        context={
            "continuation_decision": should_continue,
            "continuation_reasoning": continuation_reasoning,
            "relevant_count": len(relevant_indices),
            "total_count": len(all_results)
        }
    )
```

**Change 3 - Capture Reformulation Reasoning (lines 1174-1230)**

```python
# BEFORE (line 1213):
reformulation = await self._reformulate_query(task, all_results, continuation_reason)
new_query = reformulation.get("query", task.query)

# AFTER:
reformulation = await self._reformulate_query(task, all_results, continuation_reason)
new_query = reformulation.get("query", task.query)
reformulation_reasoning = reformulation.get("detailed_reasoning", "")
reformulation_strategy = reformulation.get("reformulation_strategy", "")

# Log reasoning
if self.logger:
    self.logger.log_llm_reasoning(
        decision_type="query_reformulation",
        task_id=task.id,
        reasoning=reformulation_reasoning,
        context={
            "original_query": task.query,
            "new_query": new_query,
            "strategy": reformulation_strategy,
            "expected_improvement": reformulation.get("expected_improvement", "")
        }
    )
```

#### File: `research/execution_logger.py`

**Add New Method (after log_reformulation)**:

```python
def log_llm_reasoning(self, decision_type: str, task_id: int,
                     reasoning: str, context: Dict[str, Any],
                     decision: Optional[str] = None,
                     source: Optional[str] = None):
    """
    Log LLM reasoning for major decisions.

    Args:
        decision_type: Type of decision (source_selection, relevance_evaluation, etc.)
        task_id: Task ID
        reasoning: LLM's detailed reasoning
        context: Additional context (varies by decision type)
        decision: Optional decision outcome (ACCEPT/REJECT, etc.)
        source: Optional source name (for source selection)
    """
    entry = {
        "timestamp": datetime.now().isoformat(),
        "event": "llm_reasoning",
        "decision_type": decision_type,
        "task_id": task_id,
        "reasoning": reasoning,
        "decision": decision,
        "source": source,
        "context": context
    }

    with open(self.log_path, 'a', encoding='utf-8') as f:
        f.write(json.dumps(entry, ensure_ascii=False) + '\n')
```

### Configuration Options

**Add to `config_default.yaml` (new section after rate_limiting)**:

```yaml
# LLM Reasoning Configuration
llm_reasoning:
  # Enable detailed reasoning capture for all LLM decisions
  enabled: true

  # Which decision types to capture reasoning for
  capture_decisions:
    - source_selection
    - relevance_evaluation
    - query_reformulation
    - entity_extraction

  # Verbosity levels (affects prompt instructions)
  verbosity: "detailed"  # Options: "brief" | "detailed" | "exhaustive"

  # Include reasoning in final report
  include_in_report: true

  # Maximum reasoning length (characters, 0 = no limit)
  # Ceiling, not target - LLM decides actual length
  max_reasoning_length: 0
```

### Testing Strategy

**Test File**: `tests/test_phase1_reasoning.py`

```python
#!/usr/bin/env python3
"""Test Phase 1: Mentor-Style Reasoning Notes"""
import asyncio
from research.deep_research import SimpleDeepResearch
from dotenv import load_dotenv
import json
from pathlib import Path

load_dotenv()

async def test_reasoning_capture():
    """Test that LLM reasoning is captured for all decision types."""

    engine = SimpleDeepResearch(
        max_tasks=2,
        max_retries_per_task=1,
        max_time_minutes=3,
        save_output=True
    )

    result = await engine.research("What are federal cybersecurity jobs?")

    # Find execution log
    output_dir = Path(result['output_directory'])
    log_path = output_dir / "execution_log.jsonl"

    assert log_path.exists(), "Execution log not found"

    # Parse log entries
    reasoning_entries = []
    with open(log_path, 'r') as f:
        for line in f:
            entry = json.loads(line)
            if entry.get('event') == 'llm_reasoning':
                reasoning_entries.append(entry)

    # Verify reasoning captured for each decision type
    decision_types = set(e['decision_type'] for e in reasoning_entries)

    assert 'source_selection' in decision_types, "No source selection reasoning"
    assert 'relevance_evaluation' in decision_types, "No relevance reasoning"

    # Verify reasoning quality (not empty)
    for entry in reasoning_entries:
        assert len(entry['reasoning']) > 20, f"Reasoning too brief: {entry['reasoning']}"
        assert entry['context'], "No context provided"

    print(f"✅ Captured {len(reasoning_entries)} reasoning entries")
    print(f"✅ Decision types: {decision_types}")

    # Show sample reasoning
    for entry in reasoning_entries[:3]:
        print(f"\n{entry['decision_type']}:")
        print(f"  {entry['reasoning'][:100]}...")

if __name__ == "__main__":
    asyncio.run(test_reasoning_capture())
```

### Success Criteria

- [ ] All 4 decision types capture reasoning (source_selection, relevance_evaluation, query_reformulation, entity_extraction)
- [ ] Reasoning is substantive (>20 chars, references specifics)
- [ ] Reasoning appears in execution_log.jsonl with full context
- [ ] Configuration options control verbosity
- [ ] No hardcoded limits on reasoning length (config ceiling only)
- [ ] Test passes with real research query

---

## Phase 2: Source Re-Selection on Retry

**Estimated Time**: 4 hours
**Goal**: LLM reconsiders sources on every retry with full diagnostic context
**Impact**: Better source selection, fewer wasted API calls, more relevant results

### Overview

Currently, source selection happens once per task. On retry, we use the SAME sources with a reformulated query. This misses opportunities:
- Drop sources that returned errors or no results
- Add sources that might work better for reformulated query
- Adjust sources based on what worked/didn't work

Phase 2: On each retry, give LLM full diagnostic context and let it reconsider sources.

### Prompt Changes

#### 1. Create New Template - `prompts/deep_research/source_reselection.j2`

```jinja2
You are re-selecting data sources for a research task after a previous attempt.

RESEARCH QUESTION: {{ research_question }}
TASK QUERY: {{ task_query }}
ATTEMPT NUMBER: {{ attempt_number }}

PREVIOUS ATTEMPT DIAGNOSTICS:
{% if sources_with_errors %}
Sources that returned ERRORS (API failures, timeouts):
{% for source in sources_with_errors %}
- {{ source }}: {{ source_errors[source] }}
{% endfor %}

⚠️ For error sources: Consider dropping if repeated failures, or keep if critical to research.
{% endif %}

{% if sources_with_zero_results %}
Sources that returned ZERO results:
{% for source in sources_with_zero_results %}
- {{ source }}: Query executed successfully but found nothing
{% endfor %}

💡 For zero-result sources: Consider dropping if query reformulation won't help, or keep if reformulated query might work.
{% endif %}

{% if sources_with_low_quality %}
Sources that returned LOW QUALITY results (filtered out by relevance):
{% for source in sources_with_low_quality %}
- {{ source }}: {{ low_quality_counts[source] }} results returned, 0 kept
{% endfor %}

💡 For low-quality sources: Consider dropping if fundamentally wrong source, or keep if reformulated query might improve quality.
{% endif %}

{% if sources_with_good_results %}
Sources that returned GOOD results (kept by relevance):
{% for source in sources_with_good_results %}
- {{ source }}: {{ good_result_counts[source] }} results kept
{% endfor %}

✅ These sources are working well - strongly consider keeping them.
{% endif %}

AVAILABLE SOURCES:
{% for source in available_sources %}
- {{ source }}
{% endfor %}

NEW QUERY (after reformulation): {{ new_query }}

TASK:
1. Decide which sources to KEEP, DROP, or ADD
2. For each decision, explain your reasoning
3. Consider:
   - API errors suggest infrastructure issues (may not resolve with retry)
   - Zero results may improve with reformulated query (depends on query change)
   - Low quality suggests wrong source type (unlikely to improve)
   - Good results suggest right source (keep unless saturated)

Return your source selection with detailed reasoning for each change.

RESPONSE FORMAT:
```json
{
  "selected_sources": ["source1", "source2"],
  "changes": [
    {
      "source": "source_name",
      "action": "KEEP" | "DROP" | "ADD",
      "reasoning": "Why this decision makes sense given diagnostics"
    }
  ],
  "overall_strategy": "High-level explanation of source selection strategy for this retry"
}
```

IMPORTANT: You are free to keep, drop, or add sources based on your expert judgment. There are no hardcoded rules about when to drop sources - you decide.
```

#### 2. Update Relevance Evaluation Template (for context collection)

**File**: `prompts/deep_research/relevance_evaluation.j2`

**No changes needed** - already captures continuation decision and reasoning

### Code Integration

#### File: `research/deep_research.py`

**Change 1 - Add source diagnostic tracking (new method after _reformulate_query)**

```python
def _collect_source_diagnostics(self, task: ResearchTask, all_results: List[Dict],
                                relevant_indices: List[int],
                                mcp_results: List[Dict]) -> Dict[str, List[str]]:
    """
    Collect diagnostics about how each source performed.

    Returns dict with keys:
    - sources_with_errors: List of sources that had API errors
    - sources_with_zero_results: List of sources that returned no results
    - sources_with_low_quality: List of sources where all results filtered out
    - sources_with_good_results: List of sources with kept results
    - source_errors: Dict mapping source -> error message
    - good_result_counts: Dict mapping source -> count of kept results
    - low_quality_counts: Dict mapping source -> count of filtered results
    """
    diagnostics = {
        "sources_with_errors": [],
        "sources_with_zero_results": [],
        "sources_with_low_quality": [],
        "sources_with_good_results": [],
        "source_errors": {},
        "good_result_counts": {},
        "low_quality_counts": {}
    }

    # Track which sources had errors
    for mcp_result in mcp_results:
        if not mcp_result["success"]:
            source = self.tool_name_to_display.get(mcp_result["tool"], mcp_result["tool"])
            diagnostics["sources_with_errors"].append(source)
            diagnostics["source_errors"][source] = mcp_result.get("error", "Unknown error")

    # Track results by source
    for source_display in task.selected_sources:
        source_results_indices = [
            i for i, r in enumerate(all_results)
            if r.get('source') == source_display
        ]

        if not source_results_indices:
            # No results from this source
            if source_display not in diagnostics["sources_with_errors"]:
                diagnostics["sources_with_zero_results"].append(source_display)
        else:
            # Check if any results were kept
            kept_count = sum(1 for i in source_results_indices if i in relevant_indices)
            total_count = len(source_results_indices)

            if kept_count > 0:
                diagnostics["sources_with_good_results"].append(source_display)
                diagnostics["good_result_counts"][source_display] = kept_count
            else:
                diagnostics["sources_with_low_quality"].append(source_display)
                diagnostics["low_quality_counts"][source_display] = total_count

    return diagnostics
```

**Change 2 - Add source re-selection method (new method after _collect_source_diagnostics)**

```python
async def _reselect_sources(self, task: ResearchTask, diagnostics: Dict[str, Any],
                           new_query: str) -> Tuple[List[str], Dict[str, Any]]:
    """
    Re-select sources based on previous attempt diagnostics.

    Returns:
        (selected_sources, reasoning_data)
    """
    # Get available sources
    available_sources = list(self.integrations.keys())

    # Render prompt
    prompt = render_prompt(
        "deep_research/source_reselection.j2",
        research_question=self.research_question,
        task_query=task.query,
        attempt_number=task.retry_count,
        new_query=new_query,
        available_sources=available_sources,
        sources_with_errors=diagnostics["sources_with_errors"],
        sources_with_zero_results=diagnostics["sources_with_zero_results"],
        sources_with_low_quality=diagnostics["sources_with_low_quality"],
        sources_with_good_results=diagnostics["sources_with_good_results"],
        source_errors=diagnostics["source_errors"],
        good_result_counts=diagnostics["good_result_counts"],
        low_quality_counts=diagnostics["low_quality_counts"]
    )

    # Call LLM
    schema = {
        "type": "object",
        "properties": {
            "selected_sources": {
                "type": "array",
                "items": {"type": "string"}
            },
            "changes": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "source": {"type": "string"},
                        "action": {"type": "string", "enum": ["KEEP", "DROP", "ADD"]},
                        "reasoning": {"type": "string"}
                    },
                    "required": ["source", "action", "reasoning"]
                }
            },
            "overall_strategy": {"type": "string"}
        },
        "required": ["selected_sources", "changes"]
    }

    response = await acompletion(
        model=self.model,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_schema", "json_schema": {"name": "source_reselection", "schema": schema, "strict": True}}
    )

    parsed = json.loads(response.choices[0].message.content)

    # Log reasoning
    if self.logger:
        for change in parsed.get("changes", []):
            self.logger.log_llm_reasoning(
                decision_type="source_reselection",
                task_id=task.id,
                source=change["source"],
                decision=change["action"],
                reasoning=change["reasoning"],
                context={
                    "attempt": task.retry_count,
                    "overall_strategy": parsed.get("overall_strategy", "")
                }
            )

    return parsed["selected_sources"], parsed
```

**Change 3 - Integrate into retry flow (lines 1174-1230, CONTINUE branch)**

```python
# BEFORE (line 1213):
reformulation = await self._reformulate_query(task, all_results, continuation_reason)
new_query = reformulation.get("query", task.query)

# Update task with new query
task.query = new_query
task.retry_count += 1

# AFTER:
# Step 1: Collect diagnostics from this attempt
diagnostics = self._collect_source_diagnostics(task, all_results, relevant_indices, mcp_results)

# Step 2: Reformulate query
reformulation = await self._reformulate_query(task, all_results, continuation_reason)
new_query = reformulation.get("query", task.query)

# Step 3: Re-select sources based on diagnostics + new query
reselected_sources, source_reasoning = await self._reselect_sources(task, diagnostics, new_query)

# Step 4: Update task
task.query = new_query
task.selected_sources = reselected_sources  # Use new source selection
task.retry_count += 1

# Log source changes
print(f"  🔄 Source re-selection: {len(task.selected_sources)} sources selected")
if source_reasoning.get("overall_strategy"):
    print(f"     Strategy: {source_reasoning['overall_strategy']}")
```

### Configuration Options

**Add to `config_default.yaml` (under llm_reasoning section)**:

```yaml
# Source Re-Selection Configuration (Phase 2)
source_reselection:
  # Enable source re-selection on retry attempts
  enabled: true

  # Maximum sources to select per retry (ceiling, not target)
  # 0 = no limit, LLM decides
  max_sources_per_retry: 0

  # Minimum sources to keep (floor)
  # Prevents LLM from dropping all sources
  min_sources_per_retry: 1

  # Allow adding new sources not in original selection
  allow_new_sources: true

  # Sticky sources: never drop these sources even on errors
  # (for critical sources like USAJobs for job queries)
  sticky_sources: []
```

### Testing Strategy

**Test File**: `tests/test_phase2_source_reselection.py`

```python
#!/usr/bin/env python3
"""Test Phase 2: Source Re-Selection on Retry"""
import asyncio
from research.deep_research import SimpleDeepResearch
from dotenv import load_dotenv
import json
from pathlib import Path

load_dotenv()

async def test_source_reselection():
    """Test that sources are reconsidered on retry."""

    engine = SimpleDeepResearch(
        max_tasks=2,
        max_retries_per_task=2,  # Force retries
        max_time_minutes=5,
        save_output=True
    )

    # Use query likely to trigger retries
    result = await engine.research("What are federal cybersecurity jobs?")

    # Find execution log
    output_dir = Path(result['output_directory'])
    log_path = output_dir / "execution_log.jsonl"

    # Parse log entries for source reselection
    reselection_entries = []
    with open(log_path, 'r') as f:
        for line in f:
            entry = json.loads(line)
            if entry.get('decision_type') == 'source_reselection':
                reselection_entries.append(entry)

    if not reselection_entries:
        print("⚠️  No retries occurred, cannot test source reselection")
        return

    # Verify source changes logged
    assert len(reselection_entries) > 0, "No source reselection entries found"

    # Verify actions are valid
    actions = set(e['decision'] for e in reselection_entries)
    valid_actions = {'KEEP', 'DROP', 'ADD'}
    assert actions.issubset(valid_actions), f"Invalid actions: {actions - valid_actions}"

    # Verify reasoning exists
    for entry in reselection_entries:
        assert len(entry['reasoning']) > 10, "Reasoning too brief"
        assert entry['source'], "No source specified"

    print(f"✅ Found {len(reselection_entries)} source reselection decisions")
    print(f"✅ Actions taken: {actions}")

    # Show sample decisions
    for entry in reselection_entries[:5]:
        print(f"\n{entry['decision']} {entry['source']}:")
        print(f"  {entry['reasoning'][:100]}...")

if __name__ == "__main__":
    asyncio.run(test_source_reselection())
```

### Success Criteria

- [ ] Source diagnostics collected correctly (errors, zero results, low quality, good results)
- [ ] LLM receives full diagnostic context in re-selection prompt
- [ ] LLM makes KEEP/DROP/ADD decisions with reasoning
- [ ] Source changes logged with full context
- [ ] Configuration options control behavior (max sources, sticky sources)
- [ ] No hardcoded rules about when to drop sources
- [ ] Test shows source changes on retry

---

## Phase 3: Hypothesis Branching

**Estimated Time**: 12-16 hours
**Goal**: LLM generates multiple investigative hypotheses with distinct search strategies
**Impact**: More comprehensive research, explores multiple angles, better coverage

### Overview

Currently, research is linear: decompose → tasks → execute → synthesize.

Phase 3: LLM generates 2-5 investigative hypotheses, each with:
- Core hypothesis (what we're investigating)
- Search strategy (how to investigate it)
- Confidence level (how likely it's fruitful)
- Expected information (what we'd find if correct)

LLM then decides:
- Which hypotheses to explore first (prioritization)
- When to switch between hypotheses (exploration strategy)
- When hypothesis is validated/invalidated (stopping condition)
- Overall research coverage (are we done?)

### Prompt Changes

#### 1. Create New Template - `prompts/deep_research/hypothesis_generation.j2`

```jinja2
You are an expert researcher planning a comprehensive investigation.

RESEARCH QUESTION: {{ research_question }}

TASK: Generate 2-5 investigative hypotheses that would comprehensively answer this question.

Each hypothesis should represent a distinct angle or approach to the research question.

For each hypothesis, provide:
1. **Core Hypothesis**: What you're investigating (1 sentence)
2. **Search Strategy**: How you'd investigate it (specific sources, query types)
3. **Confidence Level**: How likely this angle is fruitful (1-10 scale)
4. **Expected Information**: What you'd find if this hypothesis is correct
5. **Validation Criteria**: What results would confirm/refute this hypothesis

GUIDELINES:
- Generate 2-5 hypotheses (you decide based on question complexity)
- Hypotheses should be DISTINCT (different angles, not overlapping)
- Each hypothesis should be actionable (clear search strategy)
- Prioritize breadth over depth (cover multiple angles)
- Consider: direct evidence, indirect evidence, expert opinions, official sources, community knowledge

EXAMPLE (for "What are federal cybersecurity jobs?"):

Hypothesis 1:
- Core: Federal cybersecurity jobs are primarily posted on official government job boards
- Strategy: Query USAJobs with cybersecurity keywords, analyze official postings
- Confidence: 9/10 (very likely to find direct evidence)
- Expected: Job titles, requirements, agencies, clearance levels
- Validation: Finding 20+ current job postings on USAJobs

Hypothesis 2:
- Core: Cybersecurity professionals discuss federal opportunities on social platforms
- Strategy: Query Twitter/Reddit for discussions about federal cyber jobs, clearances
- Confidence: 6/10 (may find informal knowledge)
- Expected: Application tips, salary discussions, agency culture
- Validation: Finding 10+ substantive discussions about federal cyber careers

Hypothesis 3:
- Core: Contractor job boards list federal cybersecurity contract positions
- Strategy: Query ClearanceJobs with cybersecurity + federal keywords
- Confidence: 8/10 (likely to find contractor roles)
- Expected: Contract positions requiring clearances, government clients
- Validation: Finding 15+ cleared contractor cyber jobs

YOUR TURN: Generate hypotheses for the research question above.

RESPONSE FORMAT:
```json
{
  "hypotheses": [
    {
      "id": 1,
      "core_hypothesis": "What you're investigating",
      "search_strategy": "How you'll investigate it",
      "confidence": 8,
      "expected_information": "What you expect to find",
      "validation_criteria": "What confirms/refutes this",
      "priority": "high" | "medium" | "low"
    }
  ],
  "exploration_strategy": "Overall plan for how you'll explore these hypotheses (parallel, sequential, etc.)",
  "coverage_assessment": "How these hypotheses provide comprehensive coverage of the research question"
}
```

IMPORTANT:
- You decide how many hypotheses (2-5 range is a guideline, not a rule)
- You decide priority and exploration strategy
- No hardcoded stopping conditions - you'll assess coverage as you go
```

#### 2. Create New Template - `prompts/deep_research/hypothesis_evaluation.j2`

```jinja2
You are evaluating progress on an investigative hypothesis.

RESEARCH QUESTION: {{ research_question }}

HYPOTHESIS:
- Core: {{ hypothesis.core_hypothesis }}
- Strategy: {{ hypothesis.search_strategy }}
- Confidence: {{ hypothesis.confidence }}/10
- Expected: {{ hypothesis.expected_information }}
- Validation: {{ hypothesis.validation_criteria }}

RESULTS SO FAR:
{{ results_summary }}

TASK: Evaluate this hypothesis based on results collected.

Questions to answer:
1. **Status**: Is this hypothesis VALIDATED, REFUTED, or INCONCLUSIVE?
2. **Evidence**: What results support/refute this hypothesis?
3. **Next Steps**: Should we:
   - CONTINUE exploring this hypothesis (need more results)
   - COMPLETE this hypothesis (sufficient evidence)
   - PIVOT this hypothesis (adjust search strategy)
   - ABANDON this hypothesis (clearly wrong)
4. **Coverage**: What % of this hypothesis is covered by current results? (0-100%)

RESPONSE FORMAT:
```json
{
  "status": "VALIDATED" | "REFUTED" | "INCONCLUSIVE",
  "evidence_summary": "Key findings that support/refute this hypothesis",
  "confidence_update": 8,
  "coverage_percent": 75,
  "next_action": "CONTINUE" | "COMPLETE" | "PIVOT" | "ABANDON",
  "reasoning": "Why this action makes sense given results",
  "pivot_strategy": "If PIVOT: what new strategy to try"
}
```

IMPORTANT: You decide when hypothesis is sufficiently explored. No hardcoded thresholds.
```

#### 3. Create New Template - `prompts/deep_research/research_coverage.j2`

```jinja2
You are assessing overall research coverage for a question.

RESEARCH QUESTION: {{ research_question }}

HYPOTHESES EXPLORED:
{% for h in hypotheses %}
Hypothesis {{ h.id }}: {{ h.core_hypothesis }}
- Status: {{ h.status }}
- Coverage: {{ h.coverage_percent }}%
- Results: {{ h.results_count }} results
{% endfor %}

TOTAL RESULTS COLLECTED: {{ total_results }}

TASK: Assess overall research coverage and decide next steps.

Questions to answer:
1. **Coverage Assessment**: How comprehensively have we answered the research question? (0-100%)
2. **Gaps**: What important angles are missing or underexplored?
3. **Next Steps**: Should we:
   - CONTINUE with existing hypotheses (specific hypotheses need more)
   - ADD new hypotheses (identified gaps)
   - COMPLETE research (sufficient coverage)
4. **Quality Assessment**: Are results high quality and diverse?

RESPONSE FORMAT:
```json
{
  "coverage_percent": 85,
  "coverage_assessment": "What we've covered well and what's missing",
  "identified_gaps": ["gap 1", "gap 2"],
  "next_action": "CONTINUE" | "ADD_HYPOTHESES" | "COMPLETE",
  "reasoning": "Why this action makes sense",
  "new_hypotheses": [
    {
      "core_hypothesis": "...",
      "search_strategy": "...",
      ...
    }
  ]
}
```

IMPORTANT:
- You decide when research is complete (no hardcoded thresholds)
- You decide if gaps warrant new hypotheses
- You assess quality, not just quantity
```

### Code Integration

This is a major refactor requiring new orchestration logic.

#### File: `research/deep_research.py`

**Change 1 - Add Hypothesis dataclass (after ResearchTask)**

```python
@dataclass
class Hypothesis:
    """Represents an investigative hypothesis."""
    id: int
    core_hypothesis: str
    search_strategy: str
    confidence: int  # 1-10
    expected_information: str
    validation_criteria: str
    priority: str  # "high" | "medium" | "low"

    # Runtime state
    status: str = "ACTIVE"  # ACTIVE | VALIDATED | REFUTED | INCONCLUSIVE | ABANDONED
    coverage_percent: int = 0
    tasks: List[ResearchTask] = field(default_factory=list)
    results_count: int = 0
```

**Change 2 - Add hypothesis generation method**

```python
async def _generate_hypotheses(self, research_question: str) -> List[Hypothesis]:
    """Generate investigative hypotheses for research question."""

    prompt = render_prompt(
        "deep_research/hypothesis_generation.j2",
        research_question=research_question
    )

    schema = {
        "type": "object",
        "properties": {
            "hypotheses": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer"},
                        "core_hypothesis": {"type": "string"},
                        "search_strategy": {"type": "string"},
                        "confidence": {"type": "integer", "minimum": 1, "maximum": 10},
                        "expected_information": {"type": "string"},
                        "validation_criteria": {"type": "string"},
                        "priority": {"type": "string", "enum": ["high", "medium", "low"]}
                    },
                    "required": ["id", "core_hypothesis", "search_strategy", "confidence"]
                }
            },
            "exploration_strategy": {"type": "string"},
            "coverage_assessment": {"type": "string"}
        },
        "required": ["hypotheses"]
    }

    response = await acompletion(
        model=self.model,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_schema", "json_schema": {"name": "hypothesis_generation", "schema": schema, "strict": True}}
    )

    parsed = json.loads(response.choices[0].message.content)

    # Convert to Hypothesis objects
    hypotheses = [
        Hypothesis(
            id=h["id"],
            core_hypothesis=h["core_hypothesis"],
            search_strategy=h["search_strategy"],
            confidence=h.get("confidence", 5),
            expected_information=h.get("expected_information", ""),
            validation_criteria=h.get("validation_criteria", ""),
            priority=h.get("priority", "medium")
        )
        for h in parsed["hypotheses"]
    ]

    # Log hypotheses
    print(f"\n🔬 Generated {len(hypotheses)} investigative hypotheses:")
    for h in hypotheses:
        print(f"   {h.id}. {h.core_hypothesis} (confidence: {h.confidence}/10, priority: {h.priority})")

    if self.logger:
        self.logger.log_llm_reasoning(
            decision_type="hypothesis_generation",
            task_id=0,
            reasoning=parsed.get("exploration_strategy", ""),
            context={
                "hypotheses_count": len(hypotheses),
                "coverage_assessment": parsed.get("coverage_assessment", ""),
                "hypotheses": [h.__dict__ for h in hypotheses]
            }
        )

    return hypotheses
```

**Change 3 - Add hypothesis evaluation method**

```python
async def _evaluate_hypothesis(self, hypothesis: Hypothesis) -> Dict[str, Any]:
    """Evaluate progress on a hypothesis."""

    # Summarize results for this hypothesis
    all_results = []
    for task in hypothesis.tasks:
        all_results.extend(task.accumulated_results)

    results_summary = f"{len(all_results)} results collected across {len(hypothesis.tasks)} tasks"
    if all_results:
        results_summary += f"\nSample results:\n"
        for r in all_results[:5]:
            results_summary += f"- {r.get('title', 'Untitled')}\n"

    prompt = render_prompt(
        "deep_research/hypothesis_evaluation.j2",
        research_question=self.research_question,
        hypothesis=hypothesis,
        results_summary=results_summary
    )

    schema = {
        "type": "object",
        "properties": {
            "status": {"type": "string", "enum": ["VALIDATED", "REFUTED", "INCONCLUSIVE"]},
            "evidence_summary": {"type": "string"},
            "confidence_update": {"type": "integer", "minimum": 1, "maximum": 10},
            "coverage_percent": {"type": "integer", "minimum": 0, "maximum": 100},
            "next_action": {"type": "string", "enum": ["CONTINUE", "COMPLETE", "PIVOT", "ABANDON"]},
            "reasoning": {"type": "string"},
            "pivot_strategy": {"type": "string"}
        },
        "required": ["status", "next_action", "reasoning"]
    }

    response = await acompletion(
        model=self.model,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_schema", "json_schema": {"name": "hypothesis_evaluation", "schema": schema, "strict": True}}
    )

    parsed = json.loads(response.choices[0].message.content)

    # Update hypothesis state
    hypothesis.status = parsed.get("status", "INCONCLUSIVE")
    hypothesis.coverage_percent = parsed.get("coverage_percent", 0)
    hypothesis.confidence = parsed.get("confidence_update", hypothesis.confidence)
    hypothesis.results_count = len(all_results)

    # Log evaluation
    if self.logger:
        self.logger.log_llm_reasoning(
            decision_type="hypothesis_evaluation",
            task_id=hypothesis.id,
            reasoning=parsed["reasoning"],
            decision=parsed["next_action"],
            context={
                "hypothesis": hypothesis.core_hypothesis,
                "status": hypothesis.status,
                "coverage": hypothesis.coverage_percent,
                "results_count": hypothesis.results_count,
                "evidence_summary": parsed.get("evidence_summary", "")
            }
        )

    return parsed
```

**Change 4 - Add research coverage assessment method**

```python
async def _assess_research_coverage(self, hypotheses: List[Hypothesis]) -> Dict[str, Any]:
    """Assess overall research coverage."""

    total_results = sum(h.results_count for h in hypotheses)

    prompt = render_prompt(
        "deep_research/research_coverage.j2",
        research_question=self.research_question,
        hypotheses=[
            {
                "id": h.id,
                "core_hypothesis": h.core_hypothesis,
                "status": h.status,
                "coverage_percent": h.coverage_percent,
                "results_count": h.results_count
            }
            for h in hypotheses
        ],
        total_results=total_results
    )

    schema = {
        "type": "object",
        "properties": {
            "coverage_percent": {"type": "integer", "minimum": 0, "maximum": 100},
            "coverage_assessment": {"type": "string"},
            "identified_gaps": {"type": "array", "items": {"type": "string"}},
            "next_action": {"type": "string", "enum": ["CONTINUE", "ADD_HYPOTHESES", "COMPLETE"]},
            "reasoning": {"type": "string"},
            "new_hypotheses": {"type": "array"}
        },
        "required": ["coverage_percent", "next_action", "reasoning"]
    }

    response = await acompletion(
        model=self.model,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_schema", "json_schema": {"name": "research_coverage", "schema": schema, "strict": True}}
    )

    parsed = json.loads(response.choices[0].message.content)

    # Log assessment
    if self.logger:
        self.logger.log_llm_reasoning(
            decision_type="research_coverage",
            task_id=0,
            reasoning=parsed["reasoning"],
            decision=parsed["next_action"],
            context={
                "coverage_percent": parsed["coverage_percent"],
                "gaps": parsed.get("identified_gaps", []),
                "total_hypotheses": len(hypotheses),
                "total_results": total_results
            }
        )

    return parsed
```

**Change 5 - New hypothesis-driven research method**

```python
async def research_with_hypotheses(self, research_question: str) -> Dict[str, Any]:
    """
    Execute research using hypothesis branching.

    Flow:
    1. Generate hypotheses
    2. For each hypothesis (by priority):
       a. Decompose into tasks
       b. Execute tasks
       c. Evaluate hypothesis
       d. Decide next steps (continue, complete, pivot, abandon)
    3. Assess overall coverage
    4. Repeat until coverage satisfactory or time limit
    """
    self.research_question = research_question
    start_time = time.time()

    print(f"\n{'='*80}")
    print(f"HYPOTHESIS-DRIVEN DEEP RESEARCH")
    print(f"Question: {research_question}")
    print(f"{'='*80}\n")

    # Step 1: Generate hypotheses
    hypotheses = await self._generate_hypotheses(research_question)

    # Sort by priority (high -> medium -> low)
    priority_order = {"high": 0, "medium": 1, "low": 2}
    hypotheses.sort(key=lambda h: (priority_order.get(h.priority, 1), -h.confidence))

    # Step 2: Explore hypotheses
    iterations = 0
    max_iterations = self.config.get("hypothesis_branching", {}).get("max_iterations", 10)

    while iterations < max_iterations:
        iterations += 1

        # Check time limit
        elapsed = (time.time() - start_time) / 60
        if elapsed > self.max_time_minutes:
            print(f"\n⏱️  Time limit reached ({self.max_time_minutes} min)")
            break

        # Step 2a: Assess coverage
        coverage = await self._assess_research_coverage(hypotheses)
        print(f"\n📊 Research Coverage: {coverage['coverage_percent']}%")
        print(f"   {coverage['coverage_assessment']}")

        if coverage["next_action"] == "COMPLETE":
            print(f"   ✅ Research complete")
            break
        elif coverage["next_action"] == "ADD_HYPOTHESES":
            # Add new hypotheses for gaps
            new_hypotheses_data = coverage.get("new_hypotheses", [])
            for h_data in new_hypotheses_data:
                new_h = Hypothesis(
                    id=len(hypotheses) + 1,
                    core_hypothesis=h_data["core_hypothesis"],
                    search_strategy=h_data["search_strategy"],
                    confidence=h_data.get("confidence", 5),
                    expected_information=h_data.get("expected_information", ""),
                    validation_criteria=h_data.get("validation_criteria", ""),
                    priority=h_data.get("priority", "medium")
                )
                hypotheses.append(new_h)
                print(f"   🆕 Added hypothesis {new_h.id}: {new_h.core_hypothesis}")

        # Step 2b: Work on active hypotheses
        for hypothesis in hypotheses:
            if hypothesis.status in ["VALIDATED", "ABANDONED"]:
                continue  # Skip completed hypotheses

            print(f"\n🔬 Working on Hypothesis {hypothesis.id}:")
            print(f"   {hypothesis.core_hypothesis}")

            # Decompose hypothesis into tasks (reuse existing logic)
            tasks = await self._decompose_question(
                f"{research_question} - {hypothesis.core_hypothesis}",
                hypothesis.search_strategy
            )

            # Execute tasks (reuse existing logic, but limit per hypothesis)
            max_tasks_per_hypothesis = self.config.get("hypothesis_branching", {}).get("max_tasks_per_hypothesis", 3)
            for task in tasks[:max_tasks_per_hypothesis]:
                task_result = await self._execute_task_with_retry(task)
                hypothesis.tasks.append(task)

            # Evaluate hypothesis
            evaluation = await self._evaluate_hypothesis(hypothesis)
            print(f"   Status: {hypothesis.status} ({hypothesis.coverage_percent}% coverage)")
            print(f"   Next: {evaluation['next_action']} - {evaluation['reasoning']}")

            if evaluation["next_action"] == "COMPLETE":
                hypothesis.status = "VALIDATED"
            elif evaluation["next_action"] == "ABANDON":
                hypothesis.status = "ABANDONED"
            elif evaluation["next_action"] == "PIVOT":
                # Update search strategy
                hypothesis.search_strategy = evaluation.get("pivot_strategy", hypothesis.search_strategy)
                print(f"   🔄 Pivoting strategy: {hypothesis.search_strategy}")

    # Step 3: Synthesize final report (across all hypotheses)
    all_results = []
    for h in hypotheses:
        for task in h.tasks:
            all_results.extend(task.accumulated_results)

    # Build result object
    result = {
        "research_question": research_question,
        "hypotheses": [
            {
                "id": h.id,
                "core_hypothesis": h.core_hypothesis,
                "status": h.status,
                "coverage": h.coverage_percent,
                "results_count": h.results_count,
                "tasks_count": len(h.tasks)
            }
            for h in hypotheses
        ],
        "total_results": len(all_results),
        "total_hypotheses": len(hypotheses),
        "iterations": iterations,
        "elapsed_minutes": elapsed
    }

    # Generate final report
    report = await self._synthesize_report(result)
    result["report"] = report

    return result
```

**Change 6 - Add entry point in main research() method**

```python
async def research(self, research_question: str) -> Dict[str, Any]:
    """Execute deep research (choose mode based on config)."""

    # Check if hypothesis branching enabled
    use_hypotheses = self.config.get("hypothesis_branching", {}).get("enabled", False)

    if use_hypotheses:
        return await self.research_with_hypotheses(research_question)
    else:
        # Original linear research flow
        return await self._research_linear(research_question)
```

**Change 7 - Rename existing research() logic to _research_linear()**

```python
async def _research_linear(self, research_question: str) -> Dict[str, Any]:
    """Execute linear research (original flow)."""
    # [All existing research() code goes here]
```

### Configuration Options

**Add to `config_default.yaml` (new section)**:

```yaml
# Hypothesis Branching Configuration (Phase 3)
hypothesis_branching:
  # Enable hypothesis-driven research
  enabled: false

  # Hypothesis generation
  min_hypotheses: 2
  max_hypotheses: 5  # Ceiling - LLM decides actual count

  # Exploration limits (ceilings, not targets)
  max_iterations: 10  # Max research cycles
  max_tasks_per_hypothesis: 3  # Max tasks per hypothesis per iteration
  max_total_tasks: 20  # Max tasks across all hypotheses

  # Coverage thresholds (guidance for LLM, not hard stops)
  target_coverage_percent: 80  # Suggested coverage target
  minimum_coverage_percent: 60  # Minimum acceptable coverage

  # Priority handling
  always_explore_high_priority: true  # Always explore high-priority hypotheses

  # Time allocation
  max_time_per_hypothesis_minutes: 10  # Ceiling per hypothesis
```

### Testing Strategy

**Test File**: `tests/test_phase3_hypothesis_branching.py`

```python
#!/usr/bin/env python3
"""Test Phase 3: Hypothesis Branching"""
import asyncio
from research.deep_research import SimpleDeepResearch
from dotenv import load_dotenv
import json
from pathlib import Path

load_dotenv()

async def test_hypothesis_branching():
    """Test hypothesis-driven research."""

    # Override config to enable hypothesis branching
    from config_loader import ConfigLoader
    config = ConfigLoader()
    config._config["hypothesis_branching"] = {
        "enabled": True,
        "max_hypotheses": 3,
        "max_iterations": 3,
        "max_tasks_per_hypothesis": 2
    }

    engine = SimpleDeepResearch(
        max_tasks=10,  # High limit (hypothesis mode manages tasks differently)
        max_time_minutes=8,
        save_output=True,
        config=config
    )

    result = await engine.research("What are federal cybersecurity jobs?")

    # Verify hypothesis structure
    assert "hypotheses" in result, "No hypotheses in result"
    assert len(result["hypotheses"]) >= 2, "Too few hypotheses generated"
    assert len(result["hypotheses"]) <= 5, "Too many hypotheses generated"

    # Verify hypothesis coverage
    for h in result["hypotheses"]:
        assert "core_hypothesis" in h
        assert "status" in h
        assert "coverage" in h
        assert h["coverage"] >= 0 and h["coverage"] <= 100

    # Verify results collected
    assert result["total_results"] > 0, "No results collected"

    # Check execution log for hypothesis reasoning
    output_dir = Path(result['output_directory'])
    log_path = output_dir / "execution_log.jsonl"

    hypothesis_entries = []
    with open(log_path, 'r') as f:
        for line in f:
            entry = json.loads(line)
            if entry.get('decision_type') in ['hypothesis_generation', 'hypothesis_evaluation', 'research_coverage']:
                hypothesis_entries.append(entry)

    assert len(hypothesis_entries) > 0, "No hypothesis reasoning logged"

    print(f"✅ Generated {len(result['hypotheses'])} hypotheses")
    print(f"✅ Collected {result['total_results']} total results")
    print(f"✅ Iterations: {result['iterations']}")

    for h in result["hypotheses"]:
        print(f"\nHypothesis {h['id']}: {h['core_hypothesis']}")
        print(f"  Status: {h['status']}, Coverage: {h['coverage']}%")
        print(f"  Results: {h['results_count']}, Tasks: {h['tasks_count']}")

if __name__ == "__main__":
    asyncio.run(test_hypothesis_branching())
```

### Success Criteria

- [ ] LLM generates 2-5 hypotheses with distinct search strategies
- [ ] Each hypothesis has core idea, strategy, confidence, validation criteria
- [ ] Hypotheses explored in priority order (high -> medium -> low)
- [ ] Hypothesis evaluation assesses status (validated/refuted/inconclusive)
- [ ] Coverage assessment identifies gaps and suggests new hypotheses
- [ ] LLM decides when research is complete (no hardcoded thresholds)
- [ ] Configuration controls exploration depth (ceilings, not targets)
- [ ] Test shows multi-hypothesis exploration with coverage assessment

---

## Implementation Order

1. **Phase 1 First** (2 hours) - Foundation for reasoning infrastructure
   - Adds reasoning capture to all LLM decisions
   - Establishes logging patterns for Phases 2 & 3
   - Low risk, high value

2. **Phase 2 Second** (4 hours) - Builds on Phase 1 reasoning
   - Uses reasoning infrastructure from Phase 1
   - Moderate complexity, clear integration points
   - High impact on research quality

3. **Phase 3 Last** (12-16 hours) - Major architectural change
   - Requires Phase 1 reasoning and Phase 2 source selection
   - Most complex, needs careful testing
   - Highest impact on research comprehensiveness

**Total Estimated Time**: 18-22 hours for all three phases

---

## Risk Mitigation

### Risk 1: LLM Cost Explosion
**Risk**: Hypothesis branching could generate many LLM calls
**Mitigation**:
- Configuration ceilings on iterations, tasks per hypothesis, total tasks
- User sets budget upfront, system operates within it
- Logging tracks LLM call costs for visibility

### Risk 2: Reasoning Verbosity
**Risk**: LLM reasoning could be too verbose or too brief
**Mitigation**:
- Configuration controls verbosity level
- Prompt instructs on reasoning depth
- User can adjust config based on preferences

### Risk 3: Source Re-Selection Instability
**Risk**: LLM might thrash (add/drop sources repeatedly)
**Mitigation**:
- Provide full diagnostic context (why sources failed)
- Sticky sources configuration prevents critical sources from being dropped
- Reasoning logged for debugging

### Risk 4: Hypothesis Overlap
**Risk**: LLM generates overlapping hypotheses
**Mitigation**:
- Prompt explicitly asks for DISTINCT hypotheses
- Coverage assessment identifies redundancy
- LLM can consolidate hypotheses during coverage review

### Risk 5: Incomplete Coverage
**Risk**: Research stops before comprehensive coverage
**Mitigation**:
- LLM assesses coverage percentage and gaps
- Configuration sets target coverage (guidance, not hard stop)
- User reviews coverage assessment in execution log

---

## Future Enhancements

These are NOT part of the current plan but could be added later:

1. **Adaptive Time Allocation**: LLM dynamically allocates time budgets to hypotheses based on productivity
2. **Cross-Hypothesis Learning**: LLM adjusts strategy for Hypothesis B based on learnings from Hypothesis A
3. **Collaborative Filtering**: LLM identifies result overlap between hypotheses to avoid redundancy
4. **Meta-Reasoning**: LLM reflects on overall research process and suggests methodology improvements
5. **Incremental Synthesis**: Generate partial reports after each hypothesis (instead of final synthesis only)

All following the same principle: **No hardcoded heuristics. Full LLM intelligence. Quality-first.**

---

## Appendix: Key Design Decisions

### Decision 1: Why Reasoning First (Phase 1)?
Reasoning capture provides visibility into LLM decisions. Without it, Phases 2 & 3 are black boxes. Building reasoning infrastructure first lets us debug and validate later phases.

### Decision 2: Why Source Re-Selection (Phase 2) Before Hypothesis Branching (Phase 3)?
Source re-selection is simpler and builds on existing retry logic. It's a good complexity step between Phase 1 (simple) and Phase 3 (complex).

### Decision 3: Why No Hardcoded Thresholds?
Hardcoded thresholds (e.g., "drop source after 2 failures") assume we know better than the LLM. We don't. Different queries need different strategies. LLM has full context and can make better decisions.

### Decision 4: Why Configurable Ceilings Instead of Targets?
Ceilings (max_tasks=20) give LLM freedom to operate within budget. Targets (generate exactly 3 hypotheses) force artificial precision. LLM should decide optimal count based on question complexity.

### Decision 5: Why No Mid-Run User Feedback?
User wants to configure once and walk away. Mid-run feedback breaks autonomous operation. LLM should have all information upfront to make decisions without human intervention.

### Decision 6: Why Hypothesis Branching Last?
It's the most complex feature with highest risk. Building on top of Phase 1 reasoning and Phase 2 source selection provides better foundation and debugging capability.

---

**END OF IMPLEMENTATION PLAN**
