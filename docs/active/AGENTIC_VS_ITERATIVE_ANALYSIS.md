# Agentic (BabyAGI) vs Iterative (Mozart) Approach

**Date**: 2025-10-20
**Question**: Should sam_gov use agentic task management (BabyAGI-style) or iterative refinement (Mozart-style)?

---

## What is BabyAGI?

**BabyAGI** = Autonomous agent that manages its own task list

**Core loop**:
1. Execute current task
2. Analyze result
3. Generate new tasks based on what was learned
4. Prioritize task list
5. Pick next task
6. Repeat

**Example BabyAGI execution**:
```
Objective: "Research FISA Section 702 surveillance programs"

Task 1: Search for FISA Section 702 overview
→ Result: Found overview mentioning NSA, Prism
→ Generate tasks: [Search NSA involvement, Research Prism program details]
→ Prioritize: [Prism (high priority), NSA (medium)]

Task 2: Research Prism program details
→ Result: Found Prism operated 2007-2013, involved tech companies
→ Generate tasks: [Find tech companies involved, Search for 2007 authorization docs]
→ Prioritize: [Tech companies (high), Authorization (low)]

Task 3: Find tech companies involved in Prism
→ Result: Google, Microsoft, Apple mentioned
→ Generate tasks: [Search Google FISA compliance, Microsoft cooperation timeline]
→ Continue until objective satisfied or task list empty...
```

**Key characteristics**:
- **Dynamic task generation** - creates new tasks based on what it learns
- **Priority management** - ranks tasks by importance to objective
- **Autonomous decision-making** - decides what to research next
- **Open-ended** - can pursue unexpected directions
- **Memory-based** - uses vector DB to remember all previous findings

---

## What is Mozart's Approach?

**Mozart** = Structured multi-phase pipeline with fixed refinement pattern

**Core loop**:
1. Broad initial search (fixed count: 15 sources)
2. Extract entities from top results (fixed count: top 5)
3. Targeted searches for entities (fixed count: 4 follow-ups)
4. Quality check (pass/fail, retry if fail)
5. Stop when quality threshold met or max iterations reached

**Example Mozart execution**:
```
Topic: "FISA Section 702"

Phase 1: Broad search
→ Search "FISA Section 702" → Get 15 sources
→ Analyze top 5 → Extract ["NSA", "Prism", "FISA court", "Snowden"]

Phase 2: Targeted searches (iteration 1)
→ Search "FISA Section 702 AND NSA" → 10 sources
→ Search "FISA Section 702 AND Prism" → 10 sources
→ Search "FISA Section 702 AND FISA court" → 10 sources
→ Analyze new top 5 → Extract ["Stellar Wind", "William Barr"]

Phase 3: Targeted searches (iteration 2)
→ Search "FISA Section 702 AND Stellar Wind" → 10 sources
→ Quality check: 0.75 >= 0.6 threshold ✓ STOP
```

**Key characteristics**:
- **Fixed structure** - always follows same pattern
- **Predictable** - you know exactly what it will do
- **Bounded** - max iterations, max results
- **Quality-driven** - stops when good enough
- **No task management** - just iterates on same search

---

## Comparison Table

| Aspect | BabyAGI (Agentic) | Mozart (Iterative) |
|--------|-------------------|-------------------|
| **Task Creation** | Dynamic - creates tasks as it learns | Fixed - predefined phases |
| **Decision Making** | Autonomous - decides next steps | Structured - follows pattern |
| **Exploration** | Open-ended - can pursue tangents | Focused - stays on topic |
| **Predictability** | Unpredictable - might go anywhere | Predictable - same pattern |
| **Stopping Condition** | Objective achieved or task list empty | Quality threshold or max iterations |
| **Cost** | Unbounded - could generate 100+ tasks | Bounded - max iterations known |
| **Speed** | Slower - task overhead, planning | Faster - no task management |
| **Memory** | Full memory of all findings (vector DB) | No long-term memory between searches |
| **Use Case** | Complex investigations, unknowns | Targeted research, known patterns |

---

## Example: Same Query, Both Approaches

**Query**: "Find all government surveillance programs related to FISA"

### BabyAGI Approach

```
Objective: Find all government surveillance programs related to FISA

Initial task list: [Search for FISA surveillance programs]

Execution:

Task 1: Search for FISA surveillance programs
→ Execute: Search SAM.gov, DVIDS, Federal Register
→ Result: Found 12 documents mentioning Section 702, Prism, Stellar Wind
→ New tasks generated:
   - Research Section 702 in detail (priority: HIGH)
   - Research Prism program history (priority: HIGH)
   - Research Stellar Wind program (priority: MEDIUM)
   - Find legal authorizations for these programs (priority: LOW)
→ Task list: [Section 702, Prism, Stellar Wind, Legal authorizations]

Task 2: Research Section 702 in detail (picked because HIGH priority)
→ Execute: Search "Section 702" across all sources
→ Result: Found 8 documents, mentions NSA, FBI, FISA court approvals
→ New tasks generated:
   - Investigate NSA's role in Section 702 (priority: HIGH)
   - Find FISA court approval documents (priority: MEDIUM)
   - Research FBI's use of Section 702 data (priority: MEDIUM)
→ Task list updated, reprioritized

Task 3: Investigate NSA's role in Section 702
→ Execute: Search "NSA Section 702"
→ Result: Found 15 documents, mentions XKEYSCORE, MUSCULAR programs
→ New tasks generated:
   - Research XKEYSCORE capabilities (priority: HIGH)
   - Research MUSCULAR program (priority: HIGH)
   - Find NSA contractors involved (priority: LOW)
→ Task list now has 8 tasks

... continues until objective satisfied or budget exhausted ...

Final result:
- 47 tasks executed
- Discovered 12 surveillance programs (Section 702, Prism, Stellar Wind,
  XKEYSCORE, MUSCULAR, and 7 others)
- Found connections: NSA → multiple programs → tech companies
- Total: 156 documents found
- Cost: ~$2.50 in LLM calls
- Time: 25 minutes
```

**Strengths**:
- Discovered programs you didn't know existed (XKEYSCORE, MUSCULAR)
- Followed connections autonomously (NSA → programs → contractors)
- Comprehensive investigation

**Weaknesses**:
- Unpredictable - could have gone deeper and cost more
- Slower - task management overhead
- Hard to tune - how do you control what it explores?

---

### Mozart Approach

```
Topic: "FISA surveillance programs"

Phase 1: Broad search (15 sources)
→ Search "FISA surveillance programs"
→ Results: 15 documents from SAM.gov, DVIDS, Federal Register
→ Extract entities from top 5: ["Section 702", "Prism", "NSA", "FISA court"]

Phase 2: Targeted searches (iteration 1)
→ Search "FISA AND Section 702" → 10 documents
→ Search "FISA AND Prism" → 10 documents
→ Search "FISA AND NSA" → 10 documents
→ Search "FISA AND FISA court" → 10 documents
→ Total: 40 new documents
→ Extract entities: ["Stellar Wind", "XKEYSCORE"]
→ Quality check: 0.68 (good enough) ✓ STOP

Final result:
- 2 iterations
- Discovered 6 related entities (Section 702, Prism, NSA, FISA court, Stellar Wind, XKEYSCORE)
- Total: 55 documents found
- Cost: ~$0.40 in LLM calls
- Time: 8 minutes
```

**Strengths**:
- Fast - completed in 2 iterations
- Predictable - you know max cost/time
- Efficient - found major programs quickly
- Easy to tune - adjust iteration count, quality threshold

**Weaknesses**:
- Might miss connections (didn't explore XKEYSCORE deeply)
- Stays focused - won't pursue tangents
- Fixed depth - stops after max iterations even if more to find

---

## When to Use Which?

### Use BabyAGI (Agentic) When:

**1. Complex, open-ended investigations**:
- "Map the entire surveillance apparatus" - unknown scope
- "Find all connections between NSA and tech companies" - network discovery
- "Investigate everything related to UFO programs" - exploratory research

**2. You don't know what you're looking for**:
- Following leads wherever they go
- Discovering unknown unknowns
- Building comprehensive knowledge graphs

**3. Time > Cost**:
- Willing to wait 30+ minutes for thorough investigation
- Budget allows $2-5 per investigation
- Depth more important than speed

**4. Need memory across searches**:
- Building long-term knowledge base
- Remembering previous findings
- Connecting dots across multiple investigations

---

### Use Mozart (Iterative) When:

**1. Focused, bounded research**:
- "Research FISA Section 702" - specific topic
- "Find contracts related to keyword X" - targeted search
- "Monitor new documents about Y" - ongoing monitoring

**2. You know roughly what you're looking for**:
- Expanding known topics
- Finding recent updates
- Monitoring specific areas

**3. Cost > Time**:
- Need results in <10 minutes
- Budget constrained (~$0.50 per search)
- Speed matters (daily monitoring)

**4. Predictability matters**:
- Production systems (need reliable cost/time)
- User-facing features (can't take 30 min)
- Automated monitoring (runs daily)

---

## For Your Use Case (SigInt Platform)

**Your current system**:
- Boolean monitoring (daily automated searches)
- 5 production monitors
- Budget-conscious ($15/month → $6/month target)
- Need predictable email alerts

**Recommendation**: **Start with Mozart (Iterative), add BabyAGI selectively**

### Why Mozart First:

1. **Your monitors need predictability**:
   - Run daily at 6am
   - Must complete in reasonable time
   - Can't have unbounded cost
   - Need consistent email format

2. **Your budget is limited**:
   - Mozart: ~$0.40/monitor/day = $60/month for 5 monitors
   - BabyAGI: ~$2-5/investigation = unpredictable

3. **Your queries are focused**:
   - "Domestic extremism classifications"
   - "FISA surveillance programs"
   - These are targeted topics, not open-ended

4. **Production stability**:
   - Mozart is proven (your friend runs it daily)
   - BabyAGI is experimental (task explosion risk)

### Where to Add BabyAGI:

**Use BabyAGI for on-demand deep dives**:

```python
# Daily monitoring: Mozart (predictable, fast)
monitors = [
    "FISA monitoring",        # Runs daily with Mozart
    "Extremism classifications",  # Runs daily with Mozart
    # ... 3 more daily monitors
]

# Manual investigations: BabyAGI (when user wants deep research)
investigations = [
    "User requests: 'Investigate all NSA surveillance programs'"
    → Launch BabyAGI agent
    → User waits 20-30 minutes
    → Gets comprehensive report

    "User requests: 'Map connections between FBI and tech companies'"
    → Launch BabyAGI agent
    → Explores network autonomously
    → Returns knowledge graph
]
```

**Architecture**:
```
┌─────────────────────────────────┐
│ Daily Monitoring (Automated)    │
│                                 │
│ - Mozart iterative search       │
│ - Runs at 6am daily             │
│ - Predictable cost/time         │
│ - Email alerts                  │
└─────────────────────────────────┘

┌─────────────────────────────────┐
│ Deep Investigations (On-Demand) │
│                                 │
│ - BabyAGI agentic search        │
│ - User triggers manually        │
│ - Takes 20-30 minutes           │
│ - Returns comprehensive report  │
└─────────────────────────────────┘
```

---

## Hybrid Approach (Best of Both)

**Combine them**:

### Level 1: Daily Monitoring (Mozart)
```yaml
# surveillance_fisa_monitor.yaml
mode: "iterative"  # Mozart-style
keywords:
  - "FISA Section 702"
  - "NSA surveillance"
adaptive_config:
  max_iterations: 3
  min_quality: 0.6
  phase1_count: 15
schedule: "daily at 6am"
```

**Result**: Fast, predictable, daily email alerts

---

### Level 2: Weekly Deep Dive (BabyAGI)
```yaml
# weekly_intelligence_investigation.yaml
mode: "agentic"  # BabyAGI-style
objective: "Discover new surveillance programs and connections"
starting_tasks:
  - "Search for new FISA-related contracts"
  - "Find recent oversight reports"
max_tasks: 50
max_cost: $5.00
max_time: 30 minutes
schedule: "weekly on Sunday"
```

**Result**: Comprehensive weekly intelligence report

---

### Level 3: On-Demand Investigation (BabyAGI)
```python
# User clicks "Deep Investigation" button in UI
result = await babyagi_agent.investigate(
    objective="Map all connections between NSA and surveillance programs",
    max_cost=10.00,
    max_time=60  # minutes
)

# Returns comprehensive knowledge graph
```

**Result**: User-triggered deep research when needed

---

## Implementation Recommendation

### Phase 1: Mozart Iterative (Week 1-4)
**Build**: Adaptive search engine with iterative refinement

**Files**:
- `core/adaptive_search_engine.py` - Mozart-style iteration
- `monitoring/adaptive_boolean_monitor.py` - Integration

**Use for**: Daily monitoring (all 5 monitors)

**Cost**: ~$0.40/monitor/day = $60/month

---

### Phase 2: BabyAGI On-Demand (Week 5-8)
**Build**: Autonomous agent for deep investigations

**Files**:
- `core/agentic_investigator.py` - BabyAGI-style task management
- `apps/deep_investigation.py` - User-triggered investigations

**Use for**: Manual deep dives when user wants comprehensive research

**Cost**: ~$2-5/investigation, user-triggered

---

## BabyAGI Implementation Pattern

If you do add BabyAGI, here's how it would work:

```python
"""Agentic investigator using BabyAGI pattern."""

from typing import List, Dict
from dataclasses import dataclass
import asyncio
from llm_utils import acompletion
import json

@dataclass
class Task:
    """Single research task."""
    id: int
    description: str
    priority: int  # 1-10, higher = more important
    status: str  # "pending", "executing", "completed"
    result: Dict = None
    generated_tasks: List['Task'] = None

class AgenticInvestigator:
    """
    BabyAGI-style autonomous investigator.

    Manages its own task list, generates new tasks based on findings.
    """

    def __init__(
        self,
        parallel_executor,
        max_tasks: int = 50,
        max_cost: float = 5.00,
        max_time_minutes: int = 30
    ):
        self.executor = parallel_executor
        self.max_tasks = max_tasks
        self.max_cost = max_cost
        self.max_time = max_time_minutes
        self.task_id_counter = 0
        self.total_cost = 0.0

    async def investigate(self, objective: str) -> Dict:
        """
        Autonomous investigation pursuing objective.

        Returns comprehensive findings.
        """
        # Initialize task list with objective
        task_list = [
            Task(
                id=0,
                description=f"Search for information about: {objective}",
                priority=10,
                status="pending"
            )
        ]

        completed_tasks = []
        findings = []

        # Main execution loop
        while task_list and len(completed_tasks) < self.max_tasks:
            # Get highest priority task
            task_list.sort(key=lambda t: t.priority, reverse=True)
            current_task = task_list.pop(0)

            # Execute task
            print(f"[Task {current_task.id}] {current_task.description} (priority: {current_task.priority})")

            result = await self._execute_task(current_task, objective)
            current_task.result = result
            current_task.status = "completed"
            completed_tasks.append(current_task)

            findings.append(result)

            # Generate new tasks based on result
            new_tasks = await self._generate_tasks(
                current_task,
                result,
                objective
            )

            # Prioritize new tasks
            prioritized_tasks = await self._prioritize_tasks(
                new_tasks,
                objective,
                completed_tasks
            )

            task_list.extend(prioritized_tasks)

            print(f"  → Found {result.get('results_count', 0)} results")
            print(f"  → Generated {len(new_tasks)} new tasks")
            print(f"  → Task list now has {len(task_list)} pending tasks")

            # Check stopping conditions
            if self.total_cost >= self.max_cost:
                print(f"Max cost reached (${self.total_cost:.2f})")
                break

        # Synthesize findings
        final_report = await self._synthesize_findings(
            objective,
            completed_tasks,
            findings
        )

        return final_report

    async def _execute_task(self, task: Task, objective: str) -> Dict:
        """Execute single research task."""
        # Extract search query from task description
        query = task.description

        # Search using parallel executor
        results = await self.executor.execute_parallel_search(
            research_question=query,
            limit=10
        )

        self.total_cost += 0.05  # Estimate, track actual

        return {
            "task_id": task.id,
            "query": query,
            "results": results,
            "results_count": len(results)
        }

    async def _generate_tasks(
        self,
        completed_task: Task,
        result: Dict,
        objective: str
    ) -> List[Task]:
        """
        Generate new tasks based on task result.

        LLM analyzes findings and creates follow-up tasks.
        """
        if not result.get('results'):
            return []

        # Summarize results for LLM
        results_summary = "\n".join([
            f"- {r.get('title', 'Untitled')}: {r.get('description', '')[:100]}"
            for r in result['results'][:5]
        ])

        prompt = f"""You are a research assistant generating follow-up investigation tasks.

Objective: {objective}

Completed task: {completed_task.description}

Findings:
{results_summary}

Based on these findings, generate 2-4 follow-up tasks that would help achieve the objective.

Focus on:
- Specific entities mentioned (programs, organizations, people)
- Gaps in information
- Related topics worth investigating
- Connections between findings

Return as JSON:
{{
    "tasks": [
        {{"description": "Search for X", "reasoning": "Because Y"}},
        ...
    ]
}}
"""

        response = await acompletion(
            model="gpt-5-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "strict": True,
                    "name": "task_generation",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "tasks": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "description": {"type": "string"},
                                        "reasoning": {"type": "string"}
                                    },
                                    "required": ["description", "reasoning"],
                                    "additionalProperties": False
                                }
                            }
                        },
                        "required": ["tasks"],
                        "additionalProperties": False
                    }
                }
            }
        )

        data = json.loads(response.choices[0].message.content)
        self.total_cost += 0.02

        # Convert to Task objects
        new_tasks = []
        for task_data in data['tasks']:
            self.task_id_counter += 1
            new_tasks.append(Task(
                id=self.task_id_counter,
                description=task_data['description'],
                priority=5,  # Will be reprioritized
                status="pending"
            ))

        return new_tasks

    async def _prioritize_tasks(
        self,
        tasks: List[Task],
        objective: str,
        completed_tasks: List[Task]
    ) -> List[Task]:
        """
        Prioritize tasks based on objective relevance.

        LLM scores each task 1-10 for importance.
        """
        if not tasks:
            return []

        task_descriptions = "\n".join([
            f"{i+1}. {t.description}"
            for i, t in enumerate(tasks)
        ])

        prompt = f"""You are prioritizing research tasks for an investigation.

Objective: {objective}

Tasks completed so far: {len(completed_tasks)}

Pending tasks to prioritize:
{task_descriptions}

Rate each task's importance to the objective (1-10, higher = more important).

Consider:
- Direct relevance to objective
- Potential to discover new information
- Avoiding redundancy with completed tasks

Return as JSON:
{{
    "priorities": [8, 5, 9, ...]  // One score per task, in order
}}
"""

        response = await acompletion(
            model="gpt-5-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "strict": True,
                    "name": "prioritization",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "priorities": {
                                "type": "array",
                                "items": {"type": "integer"}
                            }
                        },
                        "required": ["priorities"],
                        "additionalProperties": False
                    }
                }
            }
        )

        data = json.loads(response.choices[0].message.content)
        priorities = data['priorities']

        # Assign priorities
        for task, priority in zip(tasks, priorities):
            task.priority = priority

        self.total_cost += 0.02

        return tasks

    async def _synthesize_findings(
        self,
        objective: str,
        completed_tasks: List[Task],
        findings: List[Dict]
    ) -> Dict:
        """Synthesize all findings into comprehensive report."""
        # Use LLM to synthesize comprehensive summary
        # Return structured report with key findings, connections, etc.
        pass  # Implementation left as exercise
```

---

## Decision Matrix

| Your Need | Mozart | BabyAGI | Recommendation |
|-----------|--------|---------|----------------|
| Daily monitoring | ✓ Perfect | ✗ Too slow | **Mozart** |
| Email alerts | ✓ Predictable | ✗ Variable | **Mozart** |
| Budget-conscious | ✓ $0.40/run | ✗ $2-5/run | **Mozart** |
| Speed matters | ✓ <10 min | ✗ 20-30 min | **Mozart** |
| Unknown scope | ✗ Focused | ✓ Exploratory | **BabyAGI** |
| Deep investigation | ✗ Bounded | ✓ Thorough | **BabyAGI** |
| Network discovery | ✗ Limited | ✓ Excellent | **BabyAGI** |
| User-triggered | ✗ Auto | ✓ On-demand | **BabyAGI** |

---

## Final Recommendation

**For your SigInt platform**:

1. **Now (Weeks 1-4)**: Build Mozart-style adaptive search
   - Use for all 5 daily monitors
   - Predictable, fast, cost-effective
   - Production-ready

2. **Later (Weeks 5-8)**: Add BabyAGI for deep dives
   - User-triggered investigations
   - "Investigate" button in UI
   - Comprehensive research when needed

3. **Eventually**: Hybrid system
   - Mozart: Daily monitoring (automated)
   - BabyAGI: Deep investigations (on-demand)
   - Best of both worlds

**Start with Mozart** - it's proven, predictable, and fits your monitoring use case perfectly.

**Add BabyAGI later** when users want to do deep, open-ended investigations that justify the time/cost.

---

**Last Updated**: 2025-10-20
**Recommendation**: Mozart first (iterative), BabyAGI later (agentic on-demand)
