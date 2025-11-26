# Recursive Agent Architecture

A general pattern for building LLM-powered autonomous agents that can handle tasks of arbitrary complexity through recursive self-decomposition.

---

## Core Insight

Most agent architectures impose a **fixed hierarchy** of abstractions:
```
Task → Subtask → Action → Result
```

This creates problems:
- Simple tasks are over-engineered (forced through unnecessary layers)
- Complex tasks are under-powered (capped at predefined depth)
- Each layer requires different code, different prompts, different mental models
- Information degrades as it passes through layers

The recursive agent pattern solves this with **one abstraction**: the **Goal**.

---

## The Single Abstraction: Goal

A Goal is simply a string describing what needs to be accomplished. The same abstraction works at every level:

```
"Plan a trip to Japan"                              # High-level
"Find flights from NYC to Tokyo in March"           # Mid-level
"Search Kayak for NYC-TYO flights, March 15-22"     # Low-level
"Execute Kayak API: origin=JFK, dest=NRT, ..."      # Atomic
```

The LLM decides the granularity. No hardcoded hierarchy.

---

## The Core Loop

```python
async def pursue_goal(goal: str, context: GoalContext) -> GoalResult:
    """
    The ONLY entry point. Handles any goal at any depth.
    """

    # Step 1: Assess - Can I execute this directly?
    assessment = await assess(goal, context)

    if assessment.directly_executable:
        # Atomic goal - execute it
        return await execute(goal, assessment.action)

    # Step 2: Decompose into sub-goals
    sub_goals = await decompose(goal, context)

    # Step 3: Pursue sub-goals recursively
    results = []
    for sub_goal in prioritize(sub_goals):
        result = await pursue_goal(
            sub_goal,
            context.with_parent(goal).with_evidence(results)
        )
        results.append(result)

        # Step 4: Check if goal is achieved
        if await goal_achieved(goal, results, context):
            break

    # Step 5: Synthesize results
    return await synthesize(goal, results, context)
```

Five components, one pattern, infinite depth.

---

## The Five Components

### 1. Assessment

The critical decision: **execute or decompose?**

```python
async def assess(goal: str, context: GoalContext) -> Assessment:
    """
    LLM decides if goal is directly executable or needs decomposition.
    """
    prompt = f"""
    GOAL: {goal}

    CONTEXT:
    - Original objective: {context.original_objective}
    - Current depth: {context.depth}
    - Evidence so far: {context.evidence_summary}
    - Available capabilities: {context.capabilities}

    Can this goal be executed directly (maps to a specific action)?
    Or does it need to be broken into smaller goals?

    Return:
    {{
        "directly_executable": true/false,
        "reasoning": "...",
        "action": {{...}} if executable,
        "decomposition_needed_because": "..." if not
    }}
    """
```

**Key insight**: The LLM has full context to make this decision intelligently. A goal that seems complex in isolation might be simple given existing evidence.

### 2. Execution

When a goal is atomic, execute it:

```python
async def execute(goal: str, action: Action) -> GoalResult:
    """
    Execute an atomic goal.
    """
    match action.type:
        case "api_call":
            result = await call_api(action.endpoint, action.params)
            return GoalResult(goal=goal, data=result)

        case "analyze":
            analysis = await analyze(action.prompt, context.evidence)
            return GoalResult(goal=goal, analysis=analysis)

        case "synthesize":
            synthesis = await synthesize(action.prompt, context.evidence)
            return GoalResult(goal=goal, synthesis=synthesis)

        case "delegate":
            # Hand off to specialized system
            result = await delegate(action.system, action.request)
            return GoalResult(goal=goal, data=result)
```

Action types are extensible. Add new capabilities by adding new action types.

### 3. Decomposition

When a goal needs breakdown:

```python
async def decompose(goal: str, context: GoalContext) -> List[SubGoal]:
    """
    LLM breaks goal into sub-goals.
    """
    prompt = f"""
    GOAL TO DECOMPOSE: {goal}

    CONTEXT:
    - Original objective: {context.original_objective}
    - Why decomposition needed: {context.decomposition_rationale}
    - Evidence so far: {context.evidence_summary}
    - Available capabilities: {context.capabilities}
    - Existing goals (avoid redundancy): {context.all_goals}

    Create sub-goals that:
    1. Together fully address the parent goal
    2. Are as independent as possible (enables parallelism)
    3. Are appropriately sized (not too broad, not too narrow)
    4. Don't duplicate existing or completed goals

    Return:
    {{
        "sub_goals": [
            {{
                "description": "...",
                "rationale": "why this helps achieve parent goal",
                "dependencies": [indices of goals this depends on],
                "estimated_complexity": "atomic|simple|moderate|complex"
            }}
        ],
        "coverage": "how these sub-goals cover the parent goal"
    }}
    """
```

**Key insight**: The LLM sees all existing goals and evidence, preventing redundant work.

### 4. Goal Achievement Check

When to stop pursuing sub-goals:

```python
async def goal_achieved(
    goal: str,
    results: List[GoalResult],
    context: GoalContext
) -> bool:
    """
    LLM decides if goal has been sufficiently achieved.
    """
    prompt = f"""
    GOAL: {goal}

    EVIDENCE GATHERED:
    {format_results(results)}

    ORIGINAL OBJECTIVE: {context.original_objective}

    Has this goal been sufficiently achieved?

    Consider:
    - Do we have enough evidence?
    - Are there obvious gaps?
    - Is further work likely to add significant value?
    - Are we hitting diminishing returns?

    Return:
    {{
        "achieved": true/false,
        "confidence": 0.0-1.0,
        "reasoning": "...",
        "remaining_gaps": ["..."] if not achieved
    }}
    """
```

**Key insight**: Stopping is a judgment call. The LLM makes it with full context, not arbitrary metrics.

### 5. Synthesis

Combine sub-goal results into parent goal result:

```python
async def synthesize(
    goal: str,
    results: List[GoalResult],
    context: GoalContext
) -> GoalResult:
    """
    Combine sub-goal results into coherent parent result.
    """
    prompt = f"""
    GOAL: {goal}

    SUB-GOAL RESULTS:
    {format_results(results)}

    ORIGINAL OBJECTIVE: {context.original_objective}

    Synthesize these results into a coherent response to the goal.
    Highlight key findings, note any contradictions, identify confidence levels.

    Return:
    {{
        "summary": "...",
        "key_findings": ["..."],
        "confidence": 0.0-1.0,
        "limitations": ["..."],
        "raw_evidence": [...]
    }}
    """
```

---

## Context: The Key to Intelligence

The context object carries everything needed for intelligent decisions:

```python
@dataclass
class GoalContext:
    # Never lost - available at every depth
    original_objective: str

    # Full ancestry - understand where we are
    goal_stack: List[str]

    # All evidence - no information loss
    accumulated_evidence: List[Evidence]

    # Available actions - what can we do
    capabilities: List[Capability]

    # Constraints - when to stop
    constraints: Constraints

    # Metadata
    depth: int
    start_time: datetime
    cost_incurred: float

    def with_parent(self, parent_goal: str) -> 'GoalContext':
        """Create child context with parent added to stack."""
        return GoalContext(
            original_objective=self.original_objective,
            goal_stack=[*self.goal_stack, parent_goal],
            accumulated_evidence=self.accumulated_evidence,
            capabilities=self.capabilities,
            constraints=self.constraints,
            depth=self.depth + 1,
            start_time=self.start_time,
            cost_incurred=self.cost_incurred
        )

    def with_evidence(self, new_evidence: List[Evidence]) -> 'GoalContext':
        """Create context with additional evidence."""
        return GoalContext(
            ...
            accumulated_evidence=[*self.accumulated_evidence, *new_evidence],
            ...
        )
```

**Key insight**: Every decision sees everything. No information loss between levels.

---

## Parallelism

Independent sub-goals can run concurrently:

```python
async def pursue_sub_goals(
    sub_goals: List[SubGoal],
    context: GoalContext
) -> List[GoalResult]:
    """
    Pursue sub-goals with intelligent parallelism.
    """
    # Group by dependency
    groups = group_by_dependency(sub_goals)

    results = []
    for group in groups:
        # Run independent goals in parallel
        group_results = await asyncio.gather(*[
            pursue_goal(g.description, context.with_evidence(results))
            for g in group
        ])
        results.extend(group_results)

        # Update context before next group (dependent goals see new evidence)
        context = context.with_evidence(group_results)

    return results


def group_by_dependency(sub_goals: List[SubGoal]) -> List[List[SubGoal]]:
    """
    Topological sort into dependency groups.
    Goals in same group can run in parallel.
    """
    # Build dependency graph
    # Return groups in execution order
    ...
```

---

## Constraint Enforcement

Prevent runaway recursion:

```python
@dataclass
class Constraints:
    max_depth: int = 15          # Recursion limit
    max_time_seconds: int = 3600  # Wall clock limit
    max_cost_dollars: float = 10.0  # LLM cost limit
    max_goals: int = 100          # Total goals limit

def check_constraints(context: GoalContext) -> Optional[str]:
    """
    Return violation message or None if OK.
    """
    if context.depth >= context.constraints.max_depth:
        return f"Max depth ({context.constraints.max_depth}) reached"

    elapsed = (datetime.now() - context.start_time).total_seconds()
    if elapsed >= context.constraints.max_time_seconds:
        return f"Time limit ({context.constraints.max_time_seconds}s) reached"

    if context.cost_incurred >= context.constraints.max_cost_dollars:
        return f"Cost limit (${context.constraints.max_cost_dollars}) reached"

    if context.total_goals >= context.constraints.max_goals:
        return f"Goal limit ({context.constraints.max_goals}) reached"

    return None
```

Integrate into main loop:

```python
async def pursue_goal(goal: str, context: GoalContext) -> GoalResult:
    # Check constraints first
    violation = check_constraints(context)
    if violation:
        return GoalResult(
            goal=goal,
            status="constrained",
            reason=violation
        )

    # ... rest of loop
```

---

## Cycle Detection

Prevent infinite loops:

```python
def detect_cycle(goal: str, context: GoalContext) -> bool:
    """
    Check if we're revisiting a goal.
    """
    # Exact match
    if goal in context.goal_stack:
        return True

    # Semantic similarity (optional, more expensive)
    for previous_goal in context.goal_stack:
        if semantic_similarity(goal, previous_goal) > 0.95:
            return True

    return False
```

---

## Logging and Observability

Structured logging for debugging:

```python
@dataclass
class GoalEvent:
    timestamp: datetime
    event_type: str  # "started", "assessed", "decomposed", "executed", "achieved", "synthesized"
    goal: str
    depth: int
    parent_goal: Optional[str]
    data: Dict[str, Any]

class ExecutionLogger:
    def __init__(self, output_path: Path):
        self.events: List[GoalEvent] = []
        self.output_path = output_path

    def log(self, event: GoalEvent):
        self.events.append(event)
        # Write incrementally for crash recovery
        with open(self.output_path, 'a') as f:
            f.write(json.dumps(asdict(event)) + '\n')

    def get_trace(self, goal: str) -> List[GoalEvent]:
        """Get all events for a goal and its descendants."""
        ...
```

---

## Complete Example

```python
class RecursiveAgent:
    def __init__(self, capabilities: List[Capability], constraints: Constraints):
        self.capabilities = capabilities
        self.constraints = constraints
        self.logger = ExecutionLogger(Path("execution.jsonl"))

    async def run(self, objective: str) -> GoalResult:
        """Main entry point."""
        context = GoalContext(
            original_objective=objective,
            goal_stack=[],
            accumulated_evidence=[],
            capabilities=self.capabilities,
            constraints=self.constraints,
            depth=0,
            start_time=datetime.now(),
            cost_incurred=0.0
        )

        return await self.pursue_goal(objective, context)

    async def pursue_goal(self, goal: str, context: GoalContext) -> GoalResult:
        self.logger.log(GoalEvent(
            timestamp=datetime.now(),
            event_type="started",
            goal=goal,
            depth=context.depth,
            parent_goal=context.goal_stack[-1] if context.goal_stack else None,
            data={}
        ))

        # Constraint check
        violation = check_constraints(context)
        if violation:
            return GoalResult(goal=goal, status="constrained", reason=violation)

        # Cycle check
        if detect_cycle(goal, context):
            return GoalResult(goal=goal, status="cycle_detected")

        # Assessment
        assessment = await self.assess(goal, context)
        self.logger.log(GoalEvent(
            timestamp=datetime.now(),
            event_type="assessed",
            goal=goal,
            depth=context.depth,
            parent_goal=context.goal_stack[-1] if context.goal_stack else None,
            data={"directly_executable": assessment.directly_executable}
        ))

        if assessment.directly_executable:
            result = await self.execute(goal, assessment.action)
            self.logger.log(GoalEvent(
                timestamp=datetime.now(),
                event_type="executed",
                goal=goal,
                depth=context.depth,
                parent_goal=context.goal_stack[-1] if context.goal_stack else None,
                data={"success": result.success}
            ))
            return result

        # Decomposition
        sub_goals = await self.decompose(goal, context)
        self.logger.log(GoalEvent(
            timestamp=datetime.now(),
            event_type="decomposed",
            goal=goal,
            depth=context.depth,
            parent_goal=context.goal_stack[-1] if context.goal_stack else None,
            data={"sub_goal_count": len(sub_goals)}
        ))

        # Recursive pursuit
        child_context = context.with_parent(goal)
        results = []

        for sub_goal in self.prioritize(sub_goals):
            result = await self.pursue_goal(
                sub_goal.description,
                child_context.with_evidence(results)
            )
            results.append(result)

            # Check achievement
            if await self.goal_achieved(goal, results, context):
                self.logger.log(GoalEvent(
                    timestamp=datetime.now(),
                    event_type="achieved",
                    goal=goal,
                    depth=context.depth,
                    parent_goal=context.goal_stack[-1] if context.goal_stack else None,
                    data={"sub_goals_completed": len(results)}
                ))
                break

        # Synthesis
        synthesis = await self.synthesize(goal, results, context)
        self.logger.log(GoalEvent(
            timestamp=datetime.now(),
            event_type="synthesized",
            goal=goal,
            depth=context.depth,
            parent_goal=context.goal_stack[-1] if context.goal_stack else None,
            data={"confidence": synthesis.confidence}
        ))

        return synthesis
```

---

## Advantages

| Aspect | Fixed Hierarchy | Recursive Agent |
|--------|-----------------|-----------------|
| Abstractions | Multiple (task, subtask, action...) | One (goal) |
| Depth | Fixed | Variable (LLM decides) |
| Context | Degrades per level | Full everywhere |
| Code complexity | O(levels) | O(1) |
| Simple tasks | Over-engineered | Adapts |
| Complex tasks | Under-powered | Goes deeper |
| New capabilities | New pipeline stages | New action types |
| Debugging | Trace multiple flows | Single recursive trace |

---

## When to Use This Pattern

**Good fit:**
- Open-ended objectives
- Variable complexity tasks
- Need for adaptive depth
- Full context is valuable at all levels

**Poor fit:**
- Fixed, well-defined pipelines (use simple sequential)
- Real-time latency requirements (recursion adds overhead)
- Very simple tasks (overkill)

---

## Implementation Checklist

1. [ ] Define `GoalContext` with all needed state
2. [ ] Implement `assess()` - execute or decompose decision
3. [ ] Implement `execute()` - atomic goal execution
4. [ ] Implement `decompose()` - goal breakdown
5. [ ] Implement `goal_achieved()` - stopping criterion
6. [ ] Implement `synthesize()` - result combination
7. [ ] Add constraint enforcement
8. [ ] Add cycle detection
9. [ ] Add structured logging
10. [ ] Add parallelism for independent sub-goals
11. [ ] Test with varying complexity objectives
12. [ ] Tune prompts based on failure modes

---

## References

- **BabyAGI** - Original task-driven autonomous agent
- **AutoGPT** - Goal-pursuing agent with tool use
- **Tree of Thoughts** - Deliberate problem decomposition
- **ReAct** - Reasoning + Acting pattern
- **LATS** - Language Agent Tree Search

This pattern synthesizes insights from all of these into a clean, recursive abstraction.
