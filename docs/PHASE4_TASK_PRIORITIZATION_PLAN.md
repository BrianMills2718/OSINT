# Phase 4: Task Prioritization & Saturation Detection - Implementation Plan

**Branch**: `feature/phase4-task-prioritization`
**Estimated Time**: 10-13 hours
**Status**: PLANNING
**Created**: 2025-11-20

---

## EXECUTIVE SUMMARY

**Goal**: Transform deep research from budget-constrained mode to expert investigator mode with:
1. **Task Prioritization** - Manager LLM decides which angles to pursue first
2. **Saturation Detection** - Run until truly saturated (no more valuable angles)
3. **Periodic Checkpointing** - Save state, generate status reports, optional human input
4. **Dynamic Reprioritization** - Adjust priorities based on findings

**Current Architecture**: BabyAGI-inspired (task queue + execution loop) ✅ Already have foundation!

**What's Missing**: Task prioritization agent (the "manager" component)

**Effort Breakdown**:
- Phase 4A: Task Prioritization (6-8 hours)
- Phase 4B: Saturation Detection (3-4 hours)
- Phase 4C: Periodic Checkpointing (2-3 hours)
- **Total**: 11-15 hours

---

## WHAT CURRENTLY EXISTS (BabyAGI Components)

### ✅ Component 1: Task Creation Agent
**Location**: `deep_research.py` lines 722-792
- `_decompose_question()` - Creates initial 3-5 tasks
- `_create_follow_up_tasks()` - Creates follow-ups based on gaps
- **Status**: WORKING, production-ready

### ✅ Component 2: Task Execution Agent
**Location**: `deep_research.py` lines 822-1391
- `_execute_task_with_retry()` - Executes tasks with retry logic
- **Status**: WORKING, production-ready

### ❌ Component 3: Task Prioritization Agent
**Location**: DOES NOT EXIST
- Should rank tasks by value/urgency
- Should reprioritize based on findings
- **Status**: MISSING - this is Phase 4A

### ⚠️ Component 4: Stopping Logic
**Location**: Lines 392-399 (`research()` main loop)
- Current: Stop when `max_tasks` OR `max_time_minutes` reached
- Missing: Stop when "saturated" (no more valuable angles)
- **Status**: PARTIAL - this is Phase 4B

---

## PHASE 4A: TASK PRIORITIZATION (6-8 hours)

### **OBJECTIVE**: Add manager LLM that ranks task queue by priority

### **Step 1: Data Model Changes** (30 minutes)

**File**: `research/deep_research.py`
**Location**: Lines 79-106 (`ResearchTask` dataclass)

**Add fields**:
```python
@dataclass
class ResearchTask:
    # Existing fields...

    # Phase 4A: Task prioritization
    priority: int = 5  # 1=highest urgency, 10=lowest (default: medium priority)
    priority_reasoning: str = ""  # Why this priority level
    estimated_value: int = 50  # Expected information value 0-100
    estimated_redundancy: int = 50  # Expected overlap with existing findings 0-100
```

**Validation**:
```bash
python3 -c "from research.deep_research import ResearchTask; t = ResearchTask(id=0, query='test', rationale='test'); print(f'Priority: {t.priority}')"
```

**Expected output**: `Priority: 5`

---

### **Step 2: Create Prioritization Prompt** (1.5 hours)

**File**: `prompts/deep_research/task_prioritization.j2` (NEW)

**Content**:
```jinja2
You are a research manager prioritizing investigative tasks.

**RESEARCH CONTEXT**:
- Original Question: {{ research_question }}
- Research Duration: {{ elapsed_minutes }} minutes
- Tasks Completed: {{ completed_count }}
- Coverage Achieved: {{ global_coverage_summary }}

**COMPLETED TASKS** ({{ completed_count }} tasks):
{% for task in completed_tasks %}
Task {{ task.id }}: {{ task.query }}
  - Results: {{ task.results_count }}
  - Entities: {{ task.entities_count }}
  - Coverage: {{ task.coverage_score }}%
  - Key Gaps: {{ task.gaps_identified | join(", ") }}
{% endfor %}

**PENDING TASKS** ({{ pending_count }} tasks to prioritize):
{% for task in pending_tasks %}
Task {{ task.id }}: {{ task.query }}
  - Rationale: {{ task.rationale }}
  - Parent: {% if task.parent_task_id %}Task {{ task.parent_task_id }}{% else %}Initial{% endif %}
  - Current Priority: {{ task.priority }} (default)
{% endfor %}

**YOUR TASK**:
Assign priority scores (1-10) to each pending task based on:

**PRIORITY CRITERIA**:

1. **Gap Criticality** (Highest weight)
   - Does this task address a major gap from completed tasks?
   - Is missing information preventing comprehensive understanding?
   - Priority 1-2: Critical gaps (core to research question)
   - Priority 3-4: Important gaps (add significant value)
   - Priority 5-6: Moderate value (nice-to-have context)
   - Priority 7-10: Low value (peripheral, redundant)

2. **Likelihood of New Information**
   - Will this task likely find NEW documents (vs duplicates)?
   - Completed tasks show {{ deduplication_rate }}% deduplication
   - Tasks similar to completed ones: Lower priority (high redundancy risk)
   - Tasks exploring new angles: Higher priority (high novelty likelihood)

3. **Resource Efficiency**
   - Will this task yield high-quality results quickly?
   - Complex queries (multi-source, speculative): Lower priority initially
   - Focused queries (single authoritative source): Higher priority

4. **Strategic Value**
   - Does this unlock follow-up opportunities?
   - Does this validate/contradict existing findings?
   - Foundational tasks: Higher priority (enable dependent tasks)
   - Tangential tasks: Lower priority (can defer)

**DECISION GUIDANCE**:
- At MOST 2-3 tasks should be Priority 1-2 (critical)
- Majority should be Priority 3-6 (moderate value)
- Don't hesitate to assign Priority 8-10 (low value, consider skipping)

**OUTPUT FORMAT**:
Return JSON array with priority assignment for each pending task:

```json
{
  "priorities": [
    {
      "task_id": 4,
      "priority": 2,
      "estimated_value": 85,
      "estimated_redundancy": 20,
      "reasoning": "Addresses critical humanitarian impact gap from Task 1 (coverage 40%). High confidence in finding new authoritative sources (UN, NGOs). Foundational for understanding full policy picture."
    },
    ...
  ],
  "global_coverage_assessment": "After completing 4 tasks (avg 57% coverage), we have good policy/legislative coverage but missing humanitarian, grassroots, and business lobbying perspectives. Next priority should be humanitarian impact."
}
```

Now prioritize the pending tasks.
```

**Validation**:
```bash
python3 -c "from core.prompt_loader import render_prompt; print(render_prompt('deep_research/task_prioritization.j2', research_question='test', completed_tasks=[], pending_tasks=[], completed_count=0, pending_count=0, elapsed_minutes=0, global_coverage_summary='', deduplication_rate=0)[:100])"
```

---

### **Step 3: Implement Prioritization Method** (2-3 hours)

**File**: `research/deep_research.py`
**Location**: Insert around line 900 (after `_generate_hypotheses()`)

**Code**:
```python
async def _prioritize_tasks(
    self,
    tasks: List[ResearchTask],
    global_coverage_summary: str = ""
) -> List[ResearchTask]:
    """
    LLM-driven task prioritization (Phase 4A - Manager Agent).

    Ranks pending tasks based on:
    - Gap criticality (from completed task coverage decisions)
    - Likelihood of new information (vs redundancy)
    - Resource efficiency
    - Strategic value (unlocks follow-ups, validates findings)

    Args:
        tasks: List of pending tasks to prioritize
        global_coverage_summary: Optional global coverage context

    Returns:
        Same tasks with updated priority/reasoning fields
    """
    if not tasks:
        return tasks

    if len(tasks) == 1:
        # Single task - no prioritization needed
        tasks[0].priority = 1
        tasks[0].priority_reasoning = "Only pending task"
        return tasks

    # Prepare completed task summaries
    completed_summaries = []
    for task in self.completed_tasks:
        coverage_decisions = task.metadata.get("coverage_decisions", [])
        latest_coverage = coverage_decisions[-1] if coverage_decisions else {}

        completed_summaries.append({
            "id": task.id,
            "query": task.query,
            "results_count": len(task.accumulated_results),
            "entities_count": len(task.entities_found) if task.entities_found else 0,
            "coverage_score": latest_coverage.get("coverage_score", "N/A"),
            "gaps_identified": latest_coverage.get("gaps_identified", [])
        })

    # Prepare pending task data
    pending_summaries = []
    for task in tasks:
        pending_summaries.append({
            "id": task.id,
            "query": task.query,
            "rationale": task.rationale,
            "parent_task_id": task.parent_task_id,
            "priority": task.priority
        })

    # Calculate global deduplication rate
    total_fetched = sum(len(t.accumulated_results) for t in self.completed_tasks)
    # Get unique count from results_by_task
    total_unique = sum(r.get("total_results", 0) for r in self.results_by_task.values())
    dedup_rate = int((1 - total_unique / total_fetched) * 100) if total_fetched > 0 else 0

    # Render prioritization prompt
    prompt = render_prompt(
        "deep_research/task_prioritization.j2",
        research_question=self.research_question,
        elapsed_minutes=(datetime.now() - self.start_time).total_seconds() / 60,
        completed_tasks=completed_summaries,
        completed_count=len(completed_summaries),
        pending_tasks=pending_summaries,
        pending_count=len(pending_summaries),
        global_coverage_summary=global_coverage_summary,
        deduplication_rate=dedup_rate
    )

    # Define schema
    schema = {
        "type": "object",
        "properties": {
            "priorities": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "task_id": {"type": "integer"},
                        "priority": {"type": "integer", "minimum": 1, "maximum": 10},
                        "estimated_value": {"type": "integer", "minimum": 0, "maximum": 100},
                        "estimated_redundancy": {"type": "integer", "minimum": 0, "maximum": 100},
                        "reasoning": {"type": "string"}
                    },
                    "required": ["task_id", "priority", "estimated_value", "estimated_redundancy", "reasoning"],
                    "additionalProperties": False
                }
            },
            "global_coverage_assessment": {"type": "string"}
        },
        "required": ["priorities", "global_coverage_assessment"],
        "additionalProperties": False
    }

    try:
        response = await acompletion(
            model=config.get_model("analysis"),
            messages=[{"role": "user", "content": prompt}],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "task_prioritization",
                    "strict": True,
                    "schema": schema
                }
            }
        )

        result = json.loads(response.choices[0].message.content)

        # Update tasks with priority assignments
        priority_map = {p["task_id"]: p for p in result["priorities"]}

        for task in tasks:
            if task.id in priority_map:
                p = priority_map[task.id]
                task.priority = p["priority"]
                task.priority_reasoning = p["reasoning"]
                task.estimated_value = p["estimated_value"]
                task.estimated_redundancy = p["estimated_redundancy"]

        # Log prioritization
        print(f"\n📊 Task Prioritization (Manager LLM):")
        print(f"   Global Assessment: {result['global_coverage_assessment'][:150]}...")
        for task in sorted(tasks, key=lambda t: t.priority):
            print(f"   P{task.priority}: Task {task.id} - {task.query[:60]}...")
            print(f"       Value: {task.estimated_value}%, Redundancy: {task.estimated_redundancy}%")
            print(f"       Reason: {task.priority_reasoning[:100]}...")

        # Sort tasks by priority (ascending - P1 executes first)
        tasks.sort(key=lambda t: (t.priority, t.id))

        return tasks

    except Exception as e:
        logging.error(f"Task prioritization failed: {type(e).__name__}: {e}")
        print(f"⚠️  Prioritization failed, using default priority order")
        # On error, return tasks as-is (FIFO order)
        return tasks
```

**Validation**:
```python
# Test prioritization logic
engine = SimpleDeepResearch(max_tasks=5)
tasks = [
    ResearchTask(id=0, query="Test 1", rationale="Test"),
    ResearchTask(id=1, query="Test 2", rationale="Test"),
    ResearchTask(id=2, query="Test 3", rationale="Test")
]
# Simulate completed task with coverage
engine.completed_tasks = [ResearchTask(id=99, query="Done", rationale="Done")]
engine.completed_tasks[0].metadata["coverage_decisions"] = [{"coverage_score": 40, "gaps_identified": ["gap1"]}]

prioritized = await engine._prioritize_tasks(tasks)
assert prioritized[0].priority <= prioritized[1].priority  # Sorted by priority
print("[PASS] Prioritization working")
```

---

### **Step 4: Integration Point - Reprioritize After Each Task** (1 hour)

**File**: `research/deep_research.py`
**Location**: Lines 565-586 (after task completes, before creating follow-ups)

**Modify**:
```python
# EXISTING CODE (line 563):
if self._should_create_follow_ups(task, total_pending_workload):
    follow_ups = await self._create_follow_up_tasks(task, task_counter)
    # ... hypothesis generation ...
    task_counter += len(follow_ups)
    self.task_queue.extend(follow_ups)

    # NEW CODE (Phase 4A):
    # Reprioritize entire queue based on new findings
    print(f"\n🎯 Reprioritizing {len(self.task_queue)} pending tasks based on findings...")
    self.task_queue = await self._prioritize_tasks(
        self.task_queue,
        global_coverage_summary=self._generate_global_coverage_summary()
    )
    print(f"   Next task: P{self.task_queue[0].priority} - Task {self.task_queue[0].id}")
```

**Helper method** (insert around line 2600):
```python
def _generate_global_coverage_summary(self) -> str:
    """
    Generate concise summary of overall research coverage.

    Returns:
        Text summary for prioritization context
    """
    if not self.completed_tasks:
        return "No tasks completed yet."

    # Aggregate coverage scores
    coverage_scores = []
    for task in self.completed_tasks:
        coverage_decisions = task.metadata.get("coverage_decisions", [])
        if coverage_decisions:
            latest = coverage_decisions[-1]
            coverage_scores.append(latest.get("coverage_score", 0))

    avg_coverage = int(sum(coverage_scores) / len(coverage_scores)) if coverage_scores else 0

    # Sample gaps
    all_gaps = []
    for task in self.completed_tasks:
        coverage_decisions = task.metadata.get("coverage_decisions", [])
        for decision in coverage_decisions:
            all_gaps.extend(decision.get("gaps_identified", []))

    unique_gaps = list(dict.fromkeys(all_gaps))[:5]  # Top 5 unique gaps

    return (
        f"Completed {len(self.completed_tasks)} tasks, avg {avg_coverage}% coverage. "
        f"Total results: {sum(len(t.accumulated_results) for t in self.completed_tasks)}. "
        f"Main gaps: {'; '.join(unique_gaps[:3])}..."
    )
```

---

### **Step 5: Initial Queue Prioritization** (30 minutes)

**File**: `research/deep_research.py`
**Location**: Lines 777-791 (after initial task decomposition)

**Add after hypothesis generation**:
```python
# Phase 3A: Generate hypotheses (existing code)
if self.hypothesis_branching_enabled:
    # ... hypothesis generation ...

# Phase 4A: Prioritize initial tasks (NEW)
print(f"\n🎯 Prioritizing {len(tasks)} initial tasks...")
tasks = await self._prioritize_tasks(tasks, global_coverage_summary="Initial decomposition")
print(f"   Execution order: {', '.join([f'P{t.priority}(T{t.id})' for t in tasks])}")

return tasks
```

---

### **Step 6: Metadata Persistence** (30 minutes)

**File**: `research/deep_research.py`
**Location**: Lines 2283-2297 (`_save_research_output()` metadata section)

**Add**:
```python
# Existing engine_config...
"engine_config": {
    "max_tasks": self.max_tasks,
    # ... existing fields ...

    # Phase 4A: Prioritization enabled
    "task_prioritization_enabled": True  # NEW
},

# NEW: Task execution order (for analysis)
"task_execution_order": [
    {
        "task_id": task.id,
        "priority": task.priority,
        "priority_reasoning": task.priority_reasoning,
        "estimated_value": getattr(task, "estimated_value", None),
        "estimated_redundancy": getattr(task, "estimated_redundancy", None),
        "actual_results": len(task.accumulated_results),
        "actual_coverage": task.metadata.get("coverage_decisions", [{}])[-1].get("coverage_score") if task.metadata.get("coverage_decisions") else None
    }
    for task in (self.completed_tasks + self.failed_tasks)
],
```

**Benefit**: Can analyze "did high-priority tasks actually yield high value?" post-run

---

### **Step 7: Testing** (2 hours)

**File**: `tests/test_phase4a_prioritization.py` (NEW)

**Test cases**:
1. Prioritization on empty queue (should handle gracefully)
2. Prioritization with 1 task (should assign P1)
3. Prioritization with 5 tasks (should spread 1-10)
4. Reprioritization after task completion (should adjust based on gaps)
5. Priority-based execution order (P1 runs before P5)

**Run**:
```bash
source .venv/bin/activate
python3 tests/test_phase4a_prioritization.py
```

---

## PHASE 4B: SATURATION DETECTION (3-4 hours)

### **OBJECTIVE**: Detect when research has reached saturation (no more valuable angles to explore)

### **Step 1: Saturation Detection Prompt** (1.5 hours)

**File**: `prompts/deep_research/saturation_detection.j2` (NEW)

**Content**:
```jinja2
You are a research completion analyst determining if investigation has reached saturation.

**RESEARCH QUESTION**: {{ research_question }}

**COMPLETED TASKS**: {{ completed_count }} tasks
**Total Results**: {{ total_results }}
**Total Entities**: {{ total_entities }}
**Avg Coverage**: {{ avg_coverage }}%
**Duration**: {{ elapsed_minutes }} minutes

**RECENT TASKS** (last 5):
{% for task in recent_tasks %}
Task {{ task.id }}: {{ task.query }}
  - Results: {{ task.results_count }} ({{ task.new_results }} new, {{ task.duplicate_results }} duplicates)
  - Coverage: {{ task.coverage_score }}%
  - Incremental value: {{ task.incremental_value }}%
{% endfor %}

**PENDING TASKS**: {{ pending_count }} remaining
{% for task in pending_tasks[:5] %}
  - P{{ task.priority }}: {{ task.query }} (Est. value: {{ task.estimated_value }}%)
{% endfor %}

**SATURATION INDICATORS**:

Check for these patterns:

1. **Diminishing Returns** (Strong signal):
   - Last 3+ tasks yielded <15% new results?
   - Coverage scores plateaued (no increase in last 3 tasks)?
   - Entity discovery slowed (<2 new entities per task)?

2. **Coverage Completeness** (Moderate signal):
   - Average coverage across tasks >70%?
   - No critical gaps identified in recent tasks?
   - All major topic dimensions explored?

3. **Pending Queue Quality** (Moderate signal):
   - Remaining tasks all Priority 6-10 (low value)?
   - Estimated redundancy >60% for pending tasks?
   - No high-confidence angles remaining?

4. **Topic Exhaustion** (Strong signal):
   - Follow-up generator creating <2 follow-ups per task?
   - Same sources being re-queried with similar queries?
   - Gaps identified are peripheral (not core to question)?

**DECISION**:
- **SATURATED**: Continuing would yield mostly duplicates, peripheral information, or low-value angles
- **NOT SATURATED**: Clear valuable angles remain, recent tasks still finding new information

**OUTPUT FORMAT**:
```json
{
  "saturated": true | false,
  "confidence": 0-100,
  "rationale": "2-3 sentences explaining saturation decision",
  "evidence": {
    "diminishing_returns": true | false,
    "coverage_completeness": true | false,
    "pending_queue_quality": "high" | "medium" | "low",
    "topic_exhaustion": true | false
  },
  "recommendation": "stop" | "continue_limited" | "continue_full",
  "recommended_additional_tasks": 0-5
}
```

Now assess saturation.
```

---

### **Step 2: Implement Saturation Detection** (1.5 hours)

**File**: `research/deep_research.py`
**Location**: Insert around line 1000 (after `_prioritize_tasks()`)

**Code**:
```python
async def _is_saturated(self) -> Dict[str, Any]:
    """
    Detect research saturation (Phase 4B).

    Manager LLM analyzes all completed tasks holistically to determine
    if continuing research would yield valuable new information or just
    redundancy and peripheral findings.

    Returns:
        Dict with:
        - saturated: bool
        - confidence: int (0-100)
        - rationale: str
        - recommendation: "stop" | "continue_limited" | "continue_full"
        - recommended_additional_tasks: int
    """
    if len(self.completed_tasks) < 3:
        # Too early to assess saturation
        return {
            "saturated": False,
            "confidence": 100,
            "rationale": "Too few tasks completed to assess saturation (need 3+)",
            "recommendation": "continue_full",
            "recommended_additional_tasks": 5
        }

    # Prepare recent task summaries (last 5 tasks)
    recent_tasks = []
    for task in self.completed_tasks[-5:]:
        coverage_decisions = task.metadata.get("coverage_decisions", [])
        latest_coverage = coverage_decisions[-1] if coverage_decisions else {}

        # Calculate new vs duplicate results from hypothesis runs
        total_results = sum(run.get("results_count", 0) for run in task.hypothesis_runs)
        new_results = sum(
            run.get("delta_metrics", {}).get("results_new", 0)
            for run in task.hypothesis_runs
        )
        duplicate_results = total_results - new_results
        incremental_value = int(new_results / total_results * 100) if total_results > 0 else 0

        recent_tasks.append({
            "id": task.id,
            "query": task.query,
            "results_count": len(task.accumulated_results),
            "new_results": new_results,
            "duplicate_results": duplicate_results,
            "coverage_score": latest_coverage.get("coverage_score", 0),
            "incremental_value": incremental_value
        })

    # Prepare pending task summaries
    pending_summaries = [
        {
            "priority": t.priority,
            "query": t.query,
            "estimated_value": getattr(t, "estimated_value", 50),
            "estimated_redundancy": getattr(t, "estimated_redundancy", 50)
        }
        for t in self.task_queue[:5]
    ]

    # Calculate stats
    total_results = sum(len(t.accumulated_results) for t in self.completed_tasks)
    total_entities = len(set().union(*[set(t.entities_found or []) for t in self.completed_tasks]))

    coverage_scores = []
    for task in self.completed_tasks:
        coverage_decisions = task.metadata.get("coverage_decisions", [])
        if coverage_decisions:
            coverage_scores.append(coverage_decisions[-1].get("coverage_score", 0))
    avg_coverage = int(sum(coverage_scores) / len(coverage_scores)) if coverage_scores else 0

    elapsed_minutes = (datetime.now() - self.start_time).total_seconds() / 60

    # Render prompt
    prompt = render_prompt(
        "deep_research/saturation_detection.j2",
        research_question=self.research_question,
        completed_count=len(self.completed_tasks),
        total_results=total_results,
        total_entities=total_entities,
        avg_coverage=avg_coverage,
        elapsed_minutes=elapsed_minutes,
        recent_tasks=recent_tasks,
        pending_count=len(self.task_queue),
        pending_tasks=pending_summaries
    )

    schema = {
        "type": "object",
        "properties": {
            "saturated": {"type": "boolean"},
            "confidence": {"type": "integer", "minimum": 0, "maximum": 100},
            "rationale": {"type": "string"},
            "evidence": {
                "type": "object",
                "properties": {
                    "diminishing_returns": {"type": "boolean"},
                    "coverage_completeness": {"type": "boolean"},
                    "pending_queue_quality": {"type": "string", "enum": ["high", "medium", "low"]},
                    "topic_exhaustion": {"type": "boolean"}
                },
                "required": ["diminishing_returns", "coverage_completeness", "pending_queue_quality", "topic_exhaustion"],
                "additionalProperties": False
            },
            "recommendation": {"type": "string", "enum": ["stop", "continue_limited", "continue_full"]},
            "recommended_additional_tasks": {"type": "integer", "minimum": 0, "maximum": 10}
        },
        "required": ["saturated", "confidence", "rationale", "evidence", "recommendation", "recommended_additional_tasks"],
        "additionalProperties": False
    }

    try:
        response = await acompletion(
            model=config.get_model("analysis"),
            messages=[{"role": "user", "content": prompt}],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "saturation_detection",
                    "strict": True,
                    "schema": schema
                }
            }
        )

        result = json.loads(response.choices[0].message.content)

        # Log saturation assessment
        print(f"\n🧠 Saturation Assessment:")
        print(f"   Saturated: {result['saturated']} (confidence: {result['confidence']}%)")
        print(f"   Rationale: {result['rationale']}")
        print(f"   Recommendation: {result['recommendation'].upper()}")
        if not result['saturated']:
            print(f"   Continue with: {result['recommended_additional_tasks']} more tasks")

        return result

    except Exception as e:
        logging.error(f"Saturation detection failed: {type(e).__name__}: {e}")
        # On error, assume not saturated (continue research)
        return {
            "saturated": False,
            "confidence": 0,
            "rationale": f"Saturation check failed ({type(e).__name__}), defaulting to continue",
            "recommendation": "continue_full",
            "recommended_additional_tasks": 3
        }
```

---

### **Step 3: Integrate Saturation Check into Main Loop** (30 minutes)

**File**: `research/deep_research.py`
**Location**: Lines 392-399 (main research loop)

**Modify**:
```python
# EXISTING CODE:
while self.task_queue and len(self.completed_tasks) < self.max_tasks:
    # Check time limit
    if self._check_time_limit():
        self._emit_progress(
            "time_limit_reached",
            f"Time limit reached ({self.max_time_minutes} minutes)"
        )
        break

    # NEW CODE (Phase 4B): Check saturation every 3 tasks
    if len(self.completed_tasks) % 3 == 0 and len(self.completed_tasks) >= 3:
        saturation_check = await self._is_saturated()

        if saturation_check["saturated"] and saturation_check["confidence"] >= 70:
            self._emit_progress(
                "research_saturated",
                f"Research saturated: {saturation_check['rationale']}",
                data=saturation_check
            )
            print(f"\n✅ Research saturated - stopping investigation")
            break
        elif saturation_check["recommendation"] == "continue_limited":
            # Adjust max_tasks dynamically
            recommended_tasks = len(self.completed_tasks) + saturation_check["recommended_additional_tasks"]
            if recommended_tasks < self.max_tasks:
                print(f"\n📊 Reducing scope: {self.max_tasks} → {recommended_tasks} tasks (saturation approaching)")
                self.max_tasks = recommended_tasks

    # ... rest of loop (batch execution)
```

---

### **Step 4: Configuration** (15 minutes)

**File**: `config_default.yaml`
**Location**: After `deep_research` section (around line 200)

**Add**:
```yaml
# ============================================================================
# Phase 4: Manager-Agent Architecture
# ============================================================================
# Task prioritization and saturation detection for expert investigator mode
manager_agent:
  enabled: true                     # Enable task prioritization (Phase 4A)

  saturation_detection: true        # Check for research saturation (Phase 4B)
  saturation_check_interval: 3      # Check every N tasks (avoid over-calling)
  saturation_confidence_threshold: 70  # Stop if saturation confidence >= % (70-90 recommended)

  reprioritize_after_task: true     # Reprioritize queue after each completion

  # Stopping behavior
  allow_saturation_stop: true       # Stop when saturated (even if under max_tasks)
  # If false: Always run until max_tasks (saturation just informational)
```

---

### **Step 5: Testing** (1 hour)

**File**: `tests/test_phase4b_saturation.py` (NEW)

**Test scenarios**:
1. Early saturation (3 tasks, all 80%+ coverage, no gaps)
2. No saturation (3 tasks, all 40% coverage, many gaps)
3. Saturation check every 3 tasks (verify interval logic)
4. Dynamic max_tasks adjustment (continue_limited recommendation)

---

## PHASE 4C: PERIODIC CHECKPOINTING (2-3 hours)

### **OBJECTIVE**: Save state periodically, optional human input, resume capability

### **Step 1: Checkpoint Schema** (30 minutes)

**File**: `research/checkpoint.py` (NEW)

```python
from dataclasses import dataclass, asdict
from typing import List, Dict
import json
from pathlib import Path

@dataclass
class ResearchCheckpoint:
    """State snapshot for resuming research."""
    timestamp: str
    research_question: str
    elapsed_minutes: float

    # Task state
    completed_task_ids: List[int]
    failed_task_ids: List[int]
    pending_tasks: List[Dict]  # Serialized ResearchTask objects

    # Progress
    total_results: int
    total_entities: int
    avg_coverage: int

    # Manager state
    global_coverage_summary: str
    saturation_check: Dict

    def save(self, output_dir: str):
        """Save checkpoint to JSON file."""
        path = Path(output_dir) / f"checkpoint_{self.timestamp}.json"
        with open(path, 'w') as f:
            json.dump(asdict(self), f, indent=2)

    @staticmethod
    def load(checkpoint_file: str) -> 'ResearchCheckpoint':
        """Load checkpoint from JSON file."""
        with open(checkpoint_file, 'r') as f:
            data = json.load(f)
        return ResearchCheckpoint(**data)
```

---

### **Step 2: Periodic Checkpoint Logic** (1.5 hours)

**File**: `research/deep_research.py`
**Location**: In main loop (around line 415)

**Add**:
```python
# Before batch execution:
# Phase 4C: Periodic checkpointing
if hasattr(self, 'last_checkpoint_time'):
    checkpoint_interval = config.get_raw_config().get("research", {}).get("manager_agent", {}).get("checkpoint_interval_minutes", 10)
    time_since_checkpoint = (datetime.now() - self.last_checkpoint_time).total_seconds() / 60

    if time_since_checkpoint >= checkpoint_interval:
        await self._save_checkpoint()
        self.last_checkpoint_time = datetime.now()

        # Human-in-loop check
        if config.get_raw_config().get("research", {}).get("manager_agent", {}).get("human_in_loop", False):
            print(f"\n" + "="*80)
            print(f"🛑 CHECKPOINT - Human Input Requested")
            print(f"="*80)
            print(f"Progress: {len(self.completed_tasks)} tasks, {total_results} results, {elapsed_minutes:.1f} min")
            print(f"Options: [C]ontinue  [S]top  [R]edirect")
            # In real implementation, would await user input
            # For now, auto-continue
            print(f"Auto-continuing (human_in_loop requires interactive mode)")
else:
    self.last_checkpoint_time = datetime.now()
```

**Helper method**:
```python
async def _save_checkpoint(self):
    """Save research state to checkpoint file."""
    from research.checkpoint import ResearchCheckpoint

    checkpoint = ResearchCheckpoint(
        timestamp=datetime.now().strftime("%Y-%m-%d_%H-%M-%S"),
        research_question=self.research_question,
        elapsed_minutes=(datetime.now() - self.start_time).total_seconds() / 60,
        completed_task_ids=[t.id for t in self.completed_tasks],
        failed_task_ids=[t.id for t in self.failed_tasks],
        pending_tasks=[asdict(t) for t in self.task_queue],
        total_results=sum(len(t.accumulated_results) for t in self.completed_tasks),
        total_entities=len(self.entity_graph),
        avg_coverage=self._calculate_avg_coverage(),
        global_coverage_summary=self._generate_global_coverage_summary(),
        saturation_check=getattr(self, 'last_saturation_check', {})
    )

    if self.logger:
        checkpoint.save(self.logger.output_dir)
        print(f"💾 Checkpoint saved: {checkpoint.timestamp}")
```

---

### **Step 3: Update Config** (15 minutes)

**File**: `config_default.yaml`

**Add to manager_agent section**:
```yaml
# Checkpointing
checkpoint_interval_minutes: 10   # Save state every N minutes
checkpoint_enabled: true          # Enable periodic checkpointing
human_in_loop: false              # Pause for human input at checkpoints (requires interactive mode)
```

---

## ALL UNCERTAINTIES & RISKS

### **UNCERTAINTY #1: Prioritization Prompt Effectiveness**

**Question**: Will LLM make good priority decisions with limited context?

**Risk**: LLM assigns random/poor priorities, wastes high-value tasks

**Mitigation**:
- Test with Cuba data (14 completed tasks, can verify retrospectively)
- Compare: LLM priority vs actual value (results_count, coverage_score)
- Iterate on prompt until correlation >70%

**Validation Test**:
```python
# Use Cuba test metadata
# Ask LLM to prioritize tasks AFTER seeing results
# Compare LLM priority to actual value
# Measure: "Did high-priority tasks yield high results?"
```

---

### **UNCERTAINTY #2: Saturation Detection Accuracy**

**Question**: Can LLM reliably detect when research is "done"?

**Risk**:
- False positive: Stop too early, miss valuable angles
- False negative: Continue too long, waste resources

**Mitigation**:
- Require high confidence (70%+) for saturation stop
- User can override with config: `allow_saturation_stop: false`
- Log saturation checks for post-analysis

**Unknown**: What "saturation" looks like for different query types
- Factual queries: Saturates quickly (3-5 tasks?)
- Investigative queries: Saturates slowly (10-15 tasks?)

---

### **UNCERTAINTY #3: Reprioritization Overhead**

**Question**: Is reprioritizing after EVERY task too expensive?

**Cost**:
- 1 LLM call per task completion
- If 14 tasks → 14 prioritization calls
- @ $0.005 each = $0.07

**Alternatives**:
- Reprioritize every 3 tasks (reduce calls)
- Only reprioritize if new high-value gap found
- Hybrid: Reprioritize follow-ups only (not initial queue)

**Recommendation**: Start with "every task", measure overhead, optimize later

---

### **UNCERTAINTY #4: Global Coverage Summary Calculation**

**Question**: How to calculate "global coverage" across all tasks?

**Options**:
1. **Average task coverage** (simple): `sum(task_coverage) / num_tasks`
   - Pro: Easy to compute
   - Con: Doesn't account for overlap between tasks

2. **Dimension-based** (complex): Track which dimensions covered
   - Pro: Accurate (5/10 dimensions = 50%)
   - Con: Requires LLM to identify dimensions upfront

3. **LLM holistic estimate** (intelligent): Ask LLM "what % of question answered?"
   - Pro: Contextual, handles nuance
   - Con: Adds LLM call, subjective

**Current plan uses Option 1 (simple)**

**Risk**: May be inaccurate for overlapping tasks

**Future enhancement**: Add Option 3 for higher accuracy

---

### **UNCERTAINTY #5: Priority Spread**

**Question**: Should we force priority distribution (2 P1, 3 P2-3, etc.)?

**Current plan**: No forced distribution (LLM decides naturally)

**Risk**: LLM might assign everything P5 (no differentiation)

**Mitigation**:
- Prompt explicitly says "at MOST 2-3 tasks Priority 1-2"
- Validation test checks for reasonable spread
- If too narrow, iterate on prompt

---

## ALL RISKS

### **RISK #1: Performance Regression** (High Impact, Low Probability)

**Scenario**: Prioritization adds latency, slows research

**Impact**: Research takes 2x longer (40 min → 80 min)

**Probability**: LOW (1 LLM call per task ~5s each = 70s total for 14 tasks)

**Mitigation**:
- Benchmark before/after (Cuba query on master vs branch)
- If >20% slowdown, make reprioritization optional

---

### **RISK #2: Prioritization Errors** (Medium Impact, Medium Probability)

**Scenario**: LLM prioritizes wrong tasks, wastes time on low-value angles

**Impact**: Poor task order, low-value tasks execute first

**Probability**: MEDIUM (LLM judgment is subjective)

**Mitigation**:
- Validate on Cuba data (retrospective priority prediction)
- Iterate on prompt until accuracy >70%
- Add "override priority" config option for manual control

---

### **RISK #3: Saturation False Positives** (High Impact, Low Probability)

**Scenario**: LLM says "saturated" at 50% coverage, stops prematurely

**Impact**: Incomplete research, missed angles

**Probability**: LOW (requires 70%+ confidence, only checks every 3 tasks)

**Mitigation**:
- High confidence threshold (70%)
- User can disable: `allow_saturation_stop: false`
- Log saturation checks for audit

---

### **RISK #4: Increased Complexity** (Low Impact, High Probability)

**Scenario**: Code becomes harder to debug/maintain

**Impact**: Future changes take longer, more bugs

**Probability**: HIGH (adding 3 new components)

**Mitigation**:
- Comprehensive testing (3 test files)
- Feature flags (can disable prioritization if broken)
- Clear code comments
- Rollback plan (delete branch, return to master)

---

### **RISK #5: Config Incompatibility** (Low Impact, Low Probability)

**Scenario**: Existing configs break with new manager_agent section

**Impact**: Users must update config.yaml

**Probability**: LOW (new section, existing configs ignore it)

**Mitigation**:
- Backward compatible (manager disabled if config missing)
- Auto-migration from old config
- Update config_default.yaml with defaults

---

## CRITICAL DESIGN DECISIONS

### **DECISION #1: When to Prioritize**

**Options**:
A. **Before batch** - Prioritize, then execute top N in parallel
B. **Every task** - Reprioritize after each completion
C. **Hybrid** - Initial priority, reprioritize every 3 tasks

**Current Plan**: Option A (before batch)
**Reason**: Simpler, fewer LLM calls, still dynamic (batch = 4 tasks)

**Trade-off**: Less adaptive than Option B, more than Option C

---

### **DECISION #2: Saturation Stopping Behavior**

**Options**:
A. **Hard stop** - Immediately stop when saturated
B. **Soft stop** - Complete current batch, then stop
C. **Advisory** - Log saturation but continue to max_tasks

**Current Plan**: Option B (soft stop)
**Reason**: Don't waste in-progress batch, but respect saturation

**Configurable**: `allow_saturation_stop: true|false`

---

### **DECISION #3: Prioritization Scope**

**Options**:
A. **All tasks** - Prioritize initial + follow-ups together
B. **Separate queues** - Initial queue + follow-up queue (prioritized separately)
C. **Follow-ups only** - Initial FIFO, follow-ups prioritized

**Current Plan**: Option A (all tasks together)
**Reason**: Follow-ups can have higher priority than remaining initial tasks

**Example**: Follow-up addressing critical gap > remaining initial task exploring peripheral angle

---

## IMPLEMENTATION TIMELINE

### **Day 1: Phase 4A - Prioritization** (6-8 hours)

**Morning** (3-4 hours):
- [ ] Step 1: Add priority fields to ResearchTask (30 min)
- [ ] Step 2: Create task_prioritization.j2 prompt (1.5 hours)
- [ ] Step 3: Implement `_prioritize_tasks()` method (2 hours)
- [ ] Validate: Template renders, method compiles

**Afternoon** (3-4 hours):
- [ ] Step 4: Integrate reprioritization after task completion (1 hour)
- [ ] Step 5: Add initial queue prioritization (30 min)
- [ ] Step 6: Metadata persistence (30 min)
- [ ] Step 7: Create and run tests (2 hours)

**End of Day 1**: Prioritization working, tested, committed

---

### **Day 2: Phase 4B - Saturation** (3-4 hours)

**Morning** (2-3 hours):
- [ ] Step 1: Create saturation_detection.j2 prompt (1.5 hours)
- [ ] Step 2: Implement `_is_saturated()` method (1.5 hours)

**Afternoon** (1-2 hours):
- [ ] Step 3: Integrate saturation check in main loop (30 min)
- [ ] Step 4: Update config with manager_agent section (15 min)
- [ ] Step 5: Testing (1 hour)

**End of Day 2**: Saturation detection working, tested

---

### **Optional: Phase 4C - Checkpointing** (2-3 hours)

**If time permits**:
- [ ] Create checkpoint.py module
- [ ] Implement periodic saving
- [ ] Add resume capability
- [ ] Test checkpoint/resume cycle

---

## VALIDATION STRATEGY

### **Validation Test 1: Priority Prediction Accuracy**

**Method**: Retrospective analysis on Cuba test
```python
# Use Cuba metadata (14 tasks completed)
# Hide actual results from LLM
# Ask LLM to prioritize based on task queries only
# Compare: LLM priority vs actual value (results, coverage)
# Measure: Spearman correlation
```

**Success Criteria**: Correlation ≥ 0.6 (moderate-strong)

---

### **Validation Test 2: Saturation Detection**

**Method**: Test on known saturated/unsaturated scenarios
```python
# Scenario A: 3 tasks, all 80%+ coverage, no gaps
#   → Should detect saturated
#
# Scenario B: 3 tasks, all 40% coverage, many gaps
#   → Should detect NOT saturated
```

**Success Criteria**: Correctly classifies both scenarios

---

### **Validation Test 3: E2E with Real Query**

**Method**: Run full research with prioritization enabled
```python
# Query: "GS-2210 qualifications" (known topic)
# Enable: task_prioritization, saturation_detection
# Observe: Task execution order, saturation detection
# Compare: Results vs Cuba test (similar query)
```

**Success Criteria**:
- High-priority tasks execute first
- Saturation detected at reasonable point (8-12 tasks)
- No crashes, errors handled gracefully

---

## ROLLBACK PLAN

### **If Prioritization Breaks Things**

**Quick rollback**:
```bash
git checkout master
# Or: Disable in config
manager_agent:
  enabled: false
```

**Partial rollback** (keep code, disable feature):
```yaml
manager_agent:
  enabled: false  # Revert to FIFO task order
```

---

### **If Saturation Detection Too Aggressive**

**Disable saturation stop**:
```yaml
manager_agent:
  allow_saturation_stop: false  # Log saturation but don't stop
```

**Or adjust threshold**:
```yaml
manager_agent:
  saturation_confidence_threshold: 90  # Require very high confidence
```

---

## RECOMMENDATIONS

### **Recommendation #1: Start with Phase 4A Only**

**Rationale**:
- Prioritization has clear value (execute high-priority first)
- Saturation detection is experimental (don't know optimal behavior yet)
- Can add 4B/4C later if 4A proves valuable

**Alternative**: Build all 3 phases, but make each independently disableable

---

### **Recommendation #2: Measure Before/After**

**Metrics to track**:
- Execution time (does prioritization slow things?)
- Result quality (do high-priority tasks yield more results?)
- Coverage distribution (does prioritization improve coverage?)

**Benchmark**:
- Run Cuba query on master (current)
- Run Cuba query on branch (with prioritization)
- Compare metrics

---

### **Recommendation #3: Make Everything Configurable**

**Philosophy alignment**: "Make ALL limits user-configurable"

**All new features should have config flags**:
```yaml
manager_agent:
  enabled: true|false
  saturation_detection: true|false
  reprioritize_after_task: true|false
  allow_saturation_stop: true|false
```

**Benefit**: User controls behavior, can disable if issues

---

### **Recommendation #4: Validation-First Development**

**Approach**:
1. Write test FIRST (test_phase4a_prioritization.py)
2. Implement feature to pass test
3. Run test continuously during development
4. Don't commit until test passes

**Benefit**: Catch issues early, ensure correctness

---

## IS CURRENT APPROACH OPTIMAL?

### **What's Good** ✅:

1. **BabyAGI foundation** - Already have task queue + execution loop (don't need full refactor)
2. **Clean separation** - Prioritization is self-contained (can disable easily)
3. **Incremental** - Phase 4A → 4B → 4C (can stop anytime)
4. **Configurable** - All features behind flags

### **What Could Be Better** ⚠️:

1. **Reprioritization might be expensive** (14 LLM calls for 14 tasks)
   - **Alternative**: Reprioritize every 3 tasks (4-5 calls instead)
   - **Impact**: Less adaptive, cheaper

2. **Saturation detection interval is arbitrary** (every 3 tasks)
   - **Alternative**: Check when avg coverage plateaus
   - **Impact**: More intelligent, but requires tracking

3. **No LangGraph/framework** (building from scratch)
   - **Alternative**: Refactor to LangGraph (10-15 hours)
   - **Impact**: Professional checkpointing, but major refactor risk

### **My Assessment**: **Current approach is optimal given**:
- You have working BabyAGI-style code (don't break what works)
- Need is narrow (just add prioritization)
- Want to move fast (branch can fail safely)
- Value observability (LangGraph adds abstraction)

**PROCEED WITH CURRENT PLAN** ✅

---

## IMPLEMENTATION CHECKLIST

### **Phase 4A: Prioritization**
- [ ] Add priority fields to ResearchTask
- [ ] Create task_prioritization.j2 prompt
- [ ] Implement `_prioritize_tasks()` method
- [ ] Add `_generate_global_coverage_summary()` helper
- [ ] Integrate initial queue prioritization
- [ ] Integrate reprioritization after task completion
- [ ] Update metadata persistence
- [ ] Create test_phase4a_prioritization.py
- [ ] Run tests, fix bugs
- [ ] Validate on Cuba data
- [ ] Commit Phase 4A

### **Phase 4B: Saturation**
- [ ] Create saturation_detection.j2 prompt
- [ ] Implement `_is_saturated()` method
- [ ] Integrate saturation check in main loop
- [ ] Add config section (manager_agent)
- [ ] Create test_phase4b_saturation.py
- [ ] Run tests, fix bugs
- [ ] Validate on real query
- [ ] Commit Phase 4B

### **Phase 4C: Checkpointing** (Optional)
- [ ] Create checkpoint.py module
- [ ] Implement `_save_checkpoint()` method
- [ ] Add periodic checkpoint logic
- [ ] Update config
- [ ] Test checkpoint save/load
- [ ] Commit Phase 4C

---

## BRANCH STRATEGY

**Branch**: `feature/phase4-task-prioritization`

**Development Flow**:
```
1. Implement Phase 4A → Test → Commit
2. Implement Phase 4B → Test → Commit
3. (Optional) Phase 4C → Test → Commit
4. Full E2E validation
5. If successful → Merge to master
6. If issues → Keep iterating on branch OR abandon
```

**Safety**: Master remains stable, can abandon branch anytime

---

## NEXT IMMEDIATE STEPS

1. ✅ Commit current work (DONE)
2. ✅ Create feature branch (DONE)
3. ⏭️ **START PHASE 4A**: Add priority fields to ResearchTask
4. ⏭️ Create task_prioritization.j2 prompt
5. ⏭️ Implement `_prioritize_tasks()` method
6. ⏭️ ... (follow checklist)

**Ready to begin implementation aggressively** ✅

---

**END OF IMPLEMENTATION PLAN**
