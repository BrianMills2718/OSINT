"""
Recursive Agent v2 - Single abstraction goal-pursuing agent.

This implements the recursive agent pattern where any goal can be:
1. Executed directly (atomic)
2. Decomposed into sub-goals (recursive)

The LLM decides the structure, not hardcoded hierarchy.
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
from enum import Enum

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


def _get_temporal_context() -> str:
    """
    Get temporal context header for prompts.

    This ensures LLM understands the current date for time-relative queries
    like "2024 contracts" or "recent awards".
    """
    now = datetime.now()
    return f"""TEMPORAL CONTEXT:
- Today's date: {now.strftime("%Y-%m-%d")}
- Current year: {now.year}
- When interpreting relative dates like "recent", "2024", or "last year", use this as reference.
"""

# Concurrency limit for parallel sub-goal execution
DEFAULT_MAX_CONCURRENT_TASKS = 5


# =============================================================================
# Data Structures
# =============================================================================

class GoalStatus(Enum):
    """Status of a goal."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CONSTRAINED = "constrained"  # Hit a limit
    CYCLE_DETECTED = "cycle_detected"


class ActionType(Enum):
    """Types of atomic actions."""
    API_CALL = "api_call"       # Call an integration
    ANALYZE = "analyze"         # Analyze existing evidence
    SYNTHESIZE = "synthesize"   # Synthesize into conclusion
    WEB_SEARCH = "web_search"   # General web search


@dataclass
class Constraints:
    """
    Configurable limits for recursive research.

    All values are user-configurable via config.yaml or CLI args.
    NO hardcoded magic numbers - everything goes here.
    """
    # === Core Limits ===
    max_depth: int = 15
    max_time_seconds: int = 1800  # 30 minutes
    max_cost_dollars: float = 5.0
    max_goals: int = 50
    max_results_per_source: int = 20
    max_concurrent_tasks: int = DEFAULT_MAX_CONCURRENT_TASKS

    # === Prompt Context Limits ===
    # How much context to include in LLM prompts
    max_sources_in_prompt: int = 20  # Sources shown to LLM in assessment
    max_evidence_in_prompt: int = 10  # Recent evidence pieces shown
    max_evidence_for_analysis: int = 20  # Evidence included in analysis
    max_sources_in_decompose: int = 15  # Sources shown in decomposition
    max_goals_in_prompt: int = 10  # Existing goals shown (for redundancy check)
    max_evidence_for_synthesis: int = 30  # Evidence pieces for synthesis
    max_content_chars_in_synthesis: int = 500  # Content truncation in synthesis

    # === LLM Cost Estimates (per call, in dollars) ===
    # These are rough estimates - override if using different models
    cost_per_assessment: float = 0.0002
    cost_per_analysis: float = 0.0003
    cost_per_decomposition: float = 0.0003
    cost_per_achievement_check: float = 0.0001
    cost_per_synthesis: float = 0.0005
    cost_per_filter: float = 0.0002
    cost_per_reformulation: float = 0.0002

    # === Early Exit Thresholds ===
    # When to check if goal achieved early
    min_evidence_for_achievement_check: int = 5  # Minimum evidence before checking
    min_successes_for_achievement_check: int = 2  # Minimum successful sub-goals
    min_results_to_filter: int = 3  # Don't filter if fewer results than this

    # === Output Limits ===
    max_evidence_in_saved_result: int = 50  # Evidence saved to JSON
    max_evidence_per_source_in_report: int = 5  # Per-source in markdown report
    max_content_chars_in_report: int = 200  # Content truncation in report


@dataclass
class Evidence:
    """A piece of evidence gathered during research."""
    source: str
    title: str
    content: str
    url: Optional[str] = None
    relevance_score: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Action:
    """An atomic action to execute."""
    type: ActionType
    source: Optional[str] = None  # For API_CALL
    params: Dict[str, Any] = field(default_factory=dict)
    prompt: Optional[str] = None  # For ANALYZE/SYNTHESIZE


@dataclass
class Assessment:
    """Result of assessing whether a goal is directly executable."""
    directly_executable: bool
    reasoning: str
    action: Optional[Action] = None  # If executable
    decomposition_rationale: Optional[str] = None  # If not executable


@dataclass
class SubGoal:
    """A sub-goal created from decomposition."""
    description: str
    rationale: str
    dependencies: List[int] = field(default_factory=list)  # Indices of dependencies
    estimated_complexity: str = "moderate"  # atomic, simple, moderate, complex


@dataclass
class GoalResult:
    """Result of pursuing a goal."""
    goal: str
    status: GoalStatus
    evidence: List[Evidence] = field(default_factory=list)
    sub_results: List['GoalResult'] = field(default_factory=list)
    synthesis: Optional[str] = None
    confidence: float = 0.0
    reasoning: Optional[str] = None
    error: Optional[str] = None
    depth: int = 0
    duration_seconds: float = 0.0
    cost_dollars: float = 0.0


@dataclass
class GoalContext:
    """
    Full context available at every decision point.

    Key principle: No information loss between levels.
    Every decision sees everything.
    """
    # Never lost
    original_objective: str

    # Full ancestry
    goal_stack: List[str] = field(default_factory=list)

    # All evidence gathered so far
    accumulated_evidence: List[Evidence] = field(default_factory=list)

    # Available capabilities (sources)
    available_sources: List[Dict[str, Any]] = field(default_factory=list)

    # Constraints
    constraints: Constraints = field(default_factory=Constraints)

    # All goals seen (for cycle detection and redundancy)
    all_goals: List[str] = field(default_factory=list)

    # Tracking
    depth: int = 0
    start_time: datetime = field(default_factory=datetime.now)
    cost_incurred: float = 0.0
    goals_created: int = 0

    # Decomposition context (why we're decomposing)
    decomposition_rationale: Optional[str] = None

    def with_parent(self, parent_goal: str) -> 'GoalContext':
        """Create child context with parent added to stack."""
        return GoalContext(
            original_objective=self.original_objective,
            goal_stack=[*self.goal_stack, parent_goal],
            accumulated_evidence=self.accumulated_evidence.copy(),
            available_sources=self.available_sources,
            constraints=self.constraints,
            all_goals=self.all_goals,
            depth=self.depth + 1,
            start_time=self.start_time,
            cost_incurred=self.cost_incurred,
            goals_created=self.goals_created,
            decomposition_rationale=self.decomposition_rationale
        )

    def with_evidence(self, new_evidence: List[Evidence]) -> 'GoalContext':
        """Create context with additional evidence."""
        return GoalContext(
            original_objective=self.original_objective,
            goal_stack=self.goal_stack,
            accumulated_evidence=[*self.accumulated_evidence, *new_evidence],
            available_sources=self.available_sources,
            constraints=self.constraints,
            all_goals=self.all_goals,
            depth=self.depth,
            start_time=self.start_time,
            cost_incurred=self.cost_incurred,
            goals_created=self.goals_created,
            decomposition_rationale=self.decomposition_rationale
        )

    def with_decomposition_rationale(self, rationale: str) -> 'GoalContext':
        """Create context with decomposition rationale."""
        ctx = GoalContext(
            original_objective=self.original_objective,
            goal_stack=self.goal_stack,
            accumulated_evidence=self.accumulated_evidence,
            available_sources=self.available_sources,
            constraints=self.constraints,
            all_goals=self.all_goals,
            depth=self.depth,
            start_time=self.start_time,
            cost_incurred=self.cost_incurred,
            goals_created=self.goals_created,
            decomposition_rationale=rationale
        )
        return ctx

    def add_goal(self, goal: str) -> None:
        """Track a goal (mutates in place for efficiency)."""
        self.all_goals.append(goal)
        self.goals_created += 1

    def add_cost(self, cost: float) -> None:
        """Track cost (mutates in place)."""
        self.cost_incurred += cost

    @property
    def elapsed_seconds(self) -> float:
        """Time elapsed since start."""
        return (datetime.now() - self.start_time).total_seconds()

    @property
    def evidence_summary(self) -> str:
        """Brief summary of accumulated evidence."""
        if not self.accumulated_evidence:
            return "No evidence gathered yet."
        return f"{len(self.accumulated_evidence)} pieces of evidence from {len(set(e.source for e in self.accumulated_evidence))} sources."


# =============================================================================
# Execution Logger
# =============================================================================

@dataclass
class GoalEvent:
    """A logged event in goal execution."""
    timestamp: str
    event_type: str
    goal: str
    depth: int
    parent_goal: Optional[str]
    data: Dict[str, Any]


class ExecutionLogger:
    """Structured logging for goal execution."""

    def __init__(self, output_dir: Union[str, Path]):
        self.output_dir = Path(output_dir) if isinstance(output_dir, str) else output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.log_path = self.output_dir / "execution_log.jsonl"
        self.events: List[GoalEvent] = []

    def log(self, event_type: str, goal: str, depth: int,
            parent_goal: Optional[str], data: Dict[str, Any]):
        """Log an event."""
        event = GoalEvent(
            timestamp=datetime.now().isoformat(),
            event_type=event_type,
            goal=goal,
            depth=depth,
            parent_goal=parent_goal,
            data=data
        )
        self.events.append(event)

        # Write incrementally
        with open(self.log_path, 'a') as f:
            f.write(json.dumps(asdict(event)) + '\n')

        # Also log to console
        prefix = "  " * depth
        logger.info(f"{prefix}[{event_type}] {goal[:60]}...")


# =============================================================================
# Recursive Agent
# =============================================================================

class RecursiveResearchAgent:
    """
    v2 Research Agent using recursive goal decomposition.

    Single entry point: pursue_goal()
    Single abstraction: Goal
    Variable depth: LLM decides
    Full context: At every level
    """

    def __init__(
        self,
        constraints: Optional[Constraints] = None,
        output_dir: Optional[Union[str, Path]] = None
    ):
        self.constraints = constraints or Constraints()
        if output_dir is None:
            self.output_dir = Path(f"data/research_v2/{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}")
        else:
            self.output_dir = Path(output_dir) if isinstance(output_dir, str) else output_dir
        self.logger = ExecutionLogger(self.output_dir)

        # Will be initialized
        self.registry = None
        self.available_sources: List[Dict[str, Any]] = []

    async def initialize(self):
        """Initialize the agent with available sources."""
        from integrations.registry import registry

        self.registry = registry

        # Get all source metadata
        for source_id in registry.get_all():
            try:
                integration = registry.get_instance(source_id)
                if integration and hasattr(integration, 'metadata'):
                    meta = integration.metadata
                    self.available_sources.append({
                        "id": source_id,
                        "name": meta.name,
                        "description": meta.description,
                        "category": str(meta.category.value) if hasattr(meta.category, 'value') else str(meta.category)
                    })
            except Exception as e:
                logger.warning(f"Could not load source {source_id}: {e}")

        logger.info(f"Initialized with {len(self.available_sources)} sources")

    async def research(self, question: str) -> GoalResult:
        """
        Main entry point for research.

        Args:
            question: The research question/objective

        Returns:
            GoalResult with all findings
        """
        if not self.registry:
            await self.initialize()

        context = GoalContext(
            original_objective=question,
            available_sources=self.available_sources,
            constraints=self.constraints,
            start_time=datetime.now()
        )

        print(f"\n{'='*60}")
        print(f"RECURSIVE AGENT v2")
        print(f"{'='*60}")
        print(f"Objective: {question}")
        print(f"Constraints: depth={self.constraints.max_depth}, "
              f"time={self.constraints.max_time_seconds}s, "
              f"cost=${self.constraints.max_cost_dollars}")
        print(f"Sources: {len(self.available_sources)} available")
        print(f"{'='*60}\n")

        result = await self.pursue_goal(question, context)

        # Save final result
        self._save_result(result)

        return result

    async def pursue_goal(self, goal: str, context: GoalContext) -> GoalResult:
        """
        The core recursive loop.

        This is the ONLY entry point for pursuing any goal at any depth.
        """
        start_time = datetime.now()
        parent_goal = context.goal_stack[-1] if context.goal_stack else None

        # Track this goal
        context.add_goal(goal)

        self.logger.log("started", goal, context.depth, parent_goal, {})

        # === CONSTRAINT CHECK ===
        violation = self._check_constraints(context)
        if violation:
            self.logger.log("constrained", goal, context.depth, parent_goal,
                          {"reason": violation})
            return GoalResult(
                goal=goal,
                status=GoalStatus.CONSTRAINED,
                reasoning=violation,
                depth=context.depth
            )

        # === CYCLE CHECK ===
        if self._detect_cycle(goal, context):
            self.logger.log("cycle_detected", goal, context.depth, parent_goal, {})
            return GoalResult(
                goal=goal,
                status=GoalStatus.CYCLE_DETECTED,
                reasoning="Goal appears in ancestry (would create infinite loop)",
                depth=context.depth
            )

        # === ASSESSMENT: Execute or Decompose? ===
        assessment = await self._assess(goal, context)
        self.logger.log("assessed", goal, context.depth, parent_goal, {
            "directly_executable": assessment.directly_executable,
            "reasoning": assessment.reasoning[:100]
        })

        if assessment.directly_executable:
            # === EXECUTE DIRECTLY ===
            result = await self._execute(goal, assessment.action, context)
            result.duration_seconds = (datetime.now() - start_time).total_seconds()
            result.cost_dollars = context.cost_incurred  # Include cost from assessment LLM call

            self.logger.log("executed", goal, context.depth, parent_goal, {
                "status": result.status.value,
                "evidence_count": len(result.evidence)
            })
            return result

        # === DECOMPOSE INTO SUB-GOALS ===
        context_with_rationale = context.with_decomposition_rationale(
            assessment.decomposition_rationale
        )
        sub_goals = await self._decompose(goal, context_with_rationale)

        self.logger.log("decomposed", goal, context.depth, parent_goal, {
            "sub_goal_count": len(sub_goals),
            "sub_goals": [sg.description[:50] for sg in sub_goals]
        })

        if not sub_goals:
            # Decomposition failed - try to execute anyway
            return GoalResult(
                goal=goal,
                status=GoalStatus.FAILED,
                reasoning="Could not decompose goal and not directly executable",
                depth=context.depth,
                duration_seconds=(datetime.now() - start_time).total_seconds()
            )

        # === PURSUE SUB-GOALS RECURSIVELY ===
        child_context = context.with_parent(goal)
        sub_results: List[GoalResult] = []
        all_evidence: List[Evidence] = []

        # Group by dependency for parallelism
        goal_groups = self._group_by_dependency(sub_goals)

        # Bug fix: Add semaphore to limit concurrent tasks
        semaphore = asyncio.Semaphore(context.constraints.max_concurrent_tasks)

        async def limited_pursue(sg_description: str, ctx: GoalContext) -> GoalResult:
            """Pursue a goal with concurrency limiting."""
            async with semaphore:
                return await self.pursue_goal(sg_description, ctx)

        for group in goal_groups:
            # Run independent goals in parallel (with concurrency limit)
            group_tasks = [
                limited_pursue(
                    sg.description,
                    child_context.with_evidence(all_evidence)
                )
                for sg in group
            ]
            group_results = await asyncio.gather(*group_tasks)

            for result in group_results:
                sub_results.append(result)
                all_evidence.extend(result.evidence)

            # === CHECK IF GOAL ACHIEVED ===
            achieved = await self._goal_achieved(goal, sub_results, context)
            if achieved:
                self.logger.log("achieved_early", goal, context.depth, parent_goal, {
                    "sub_goals_completed": len(sub_results),
                    "total_sub_goals": len(sub_goals)
                })
                break

        # === SYNTHESIZE RESULTS ===
        synthesis = await self._synthesize(goal, sub_results, context)

        self.logger.log("synthesized", goal, context.depth, parent_goal, {
            "confidence": synthesis.confidence,
            "evidence_count": len(all_evidence)
        })

        # Bug fix: Determine parent status based on child results
        failed_count = sum(1 for r in sub_results if r.status == GoalStatus.FAILED)
        completed_count = sum(1 for r in sub_results if r.status == GoalStatus.COMPLETED)

        if failed_count == len(sub_results):
            # All children failed -> parent fails
            parent_status = GoalStatus.FAILED
        elif completed_count == 0 and failed_count > 0:
            # No successes but some failures -> parent fails
            parent_status = GoalStatus.FAILED
        else:
            # At least some children succeeded -> parent completes
            parent_status = GoalStatus.COMPLETED

        return GoalResult(
            goal=goal,
            status=parent_status,
            evidence=all_evidence,
            sub_results=sub_results,
            synthesis=synthesis.synthesis,
            confidence=synthesis.confidence,
            depth=context.depth,
            duration_seconds=(datetime.now() - start_time).total_seconds(),
            cost_dollars=context.cost_incurred
        )

    # =========================================================================
    # Component Methods
    # =========================================================================

    async def _assess(self, goal: str, context: GoalContext) -> Assessment:
        """
        Assess whether a goal is directly executable or needs decomposition.

        This is the critical decision point.
        """
        from llm_utils import acompletion

        # Format sources for prompt
        sources_text = "\n".join([
            f"- {s['name']}: {s['description']}"
            for s in context.available_sources[:context.constraints.max_sources_in_prompt]
        ])

        # Format evidence summary
        evidence_text = "None yet." if not context.accumulated_evidence else "\n".join([
            f"- [{e.source}] {e.title}: {e.content[:100]}..."
            for e in context.accumulated_evidence[-context.constraints.max_evidence_in_prompt:]
        ])

        prompt = f"""You are a research agent assessing a goal.

{_get_temporal_context()}

ORIGINAL OBJECTIVE: {context.original_objective}

CURRENT GOAL TO ASSESS: {goal}

GOAL ANCESTRY (how we got here):
{chr(10).join(f"  {i+1}. {g}" for i, g in enumerate(context.goal_stack)) or "  (This is the root goal)"}

EVIDENCE ACCUMULATED SO FAR:
{evidence_text}

AVAILABLE DATA SOURCES:
{sources_text}

CURRENT STATE:
- Depth: {context.depth}/{context.constraints.max_depth}
- Time elapsed: {context.elapsed_seconds:.0f}s / {context.constraints.max_time_seconds}s
- Goals created: {context.goals_created}/{context.constraints.max_goals}

DECISION REQUIRED:
Is this goal DIRECTLY EXECUTABLE (maps to a specific action like an API call or analysis)?
Or does it need to be DECOMPOSED into smaller sub-goals?

A goal is directly executable if:
- It maps to a specific API call to one of the available sources
- It's an analysis task on existing evidence
- It's a synthesis task combining existing findings
- It's simple enough to execute in one step

A goal needs decomposition if:
- It requires multiple different sources
- It has multiple distinct aspects to investigate
- It's too broad to answer with a single query

Return JSON:
{{
    "directly_executable": true or false,
    "reasoning": "Brief explanation of your decision",
    "action": {{
        "type": "api_call" or "analyze" or "synthesize" or "web_search",
        "source": "source_id if api_call",
        "params": {{"query": "...", ...}},
        "prompt": "analysis prompt if analyze/synthesize"
    }} if directly_executable else null,
    "decomposition_rationale": "Why this needs to be broken down" if not directly_executable else null
}}"""

        try:
            response = await acompletion(
                model="gemini/gemini-2.5-flash",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )

            # Track cost
            context.add_cost(context.constraints.cost_per_assessment)

            result = json.loads(response.choices[0].message.content)

            action = None
            if result.get("directly_executable") and result.get("action"):
                action_data = result["action"]
                action = Action(
                    type=ActionType(action_data.get("type", "api_call")),
                    source=action_data.get("source"),
                    params=action_data.get("params", {}),
                    prompt=action_data.get("prompt")
                )

            return Assessment(
                directly_executable=result.get("directly_executable", False),
                reasoning=result.get("reasoning", ""),
                action=action,
                decomposition_rationale=result.get("decomposition_rationale")
            )

        except Exception as e:
            logger.error(f"Assessment failed: {e}")
            # Default to decomposition on error
            return Assessment(
                directly_executable=False,
                reasoning=f"Assessment failed: {e}",
                decomposition_rationale="Defaulting to decomposition due to assessment error"
            )

    async def _execute(self, goal: str, action: Action, context: GoalContext) -> GoalResult:
        """
        Execute an atomic goal.
        """
        try:
            if action.type == ActionType.API_CALL:
                return await self._execute_api_call(goal, action, context)
            elif action.type == ActionType.WEB_SEARCH:
                return await self._execute_web_search(goal, action, context)
            elif action.type == ActionType.ANALYZE:
                return await self._execute_analysis(goal, action, context)
            elif action.type == ActionType.SYNTHESIZE:
                return await self._execute_synthesis(goal, action, context)
            else:
                return GoalResult(
                    goal=goal,
                    status=GoalStatus.FAILED,
                    error=f"Unknown action type: {action.type}",
                    depth=context.depth
                )
        except Exception as e:
            logger.error(f"Execution failed for {goal}: {e}")
            return GoalResult(
                goal=goal,
                status=GoalStatus.FAILED,
                error=str(e),
                depth=context.depth
            )

    async def _execute_api_call(self, goal: str, action: Action, context: GoalContext) -> GoalResult:
        """Execute an API call to a data source."""
        source_id = action.source
        if not source_id:
            return GoalResult(
                goal=goal,
                status=GoalStatus.FAILED,
                error="No source specified for API call",
                depth=context.depth
            )

        try:
            integration = self.registry.get_instance(source_id)
            if not integration:
                return GoalResult(
                    goal=goal,
                    status=GoalStatus.FAILED,
                    error=f"Source not found: {source_id}",
                    depth=context.depth
                )

            # Use integration's generate_query to get proper API parameters
            # This leverages the existing LLM-driven query generation per source
            query_text = action.params.get("query", goal)
            query_params = await integration.generate_query(query_text)

            if not query_params:
                logger.warning(f"No query params generated for {source_id}")
                return GoalResult(
                    goal=goal,
                    status=GoalStatus.COMPLETED,
                    evidence=[],
                    confidence=0.3,
                    reasoning=f"Could not generate query parameters for {source_id}",
                    depth=context.depth
                )

            # Execute search with generated params (with retry on error)
            max_retries = 2
            current_params = query_params
            result = None

            for attempt in range(max_retries):
                result = await integration.execute_search(
                    current_params,
                    limit=context.constraints.max_results_per_source
                )

                # If successful or not a validation error, break
                if result.success or not result.error:
                    break

                # Try to reformulate on error
                if attempt < max_retries - 1:
                    logger.warning(f"{source_id} error: {result.error}, attempting reformulation")
                    fixed_params = await self._reformulate_on_error(
                        source_id, goal, current_params, str(result.error), context
                    )
                    if fixed_params:
                        current_params = fixed_params
                        print(f"    ↻ {source_id}: Reformulating query...")
                    else:
                        break

            # Convert to evidence
            evidence = []
            if result and result.success and result.results:
                for item in result.results:
                    evidence.append(Evidence(
                        source=source_id,
                        title=item.get("title", "Untitled"),
                        content=item.get("description", item.get("content", "")),
                        url=item.get("url"),
                        metadata=item
                    ))

            # Filter for relevance
            original_count = len(evidence)
            if evidence:
                evidence = await self._filter_results(goal, evidence, context)

            filtered_msg = f" (filtered {original_count}→{len(evidence)})" if len(evidence) != original_count else ""
            print(f"    ✓ {source_id}: {len(evidence)} results{filtered_msg}")

            return GoalResult(
                goal=goal,
                status=GoalStatus.COMPLETED if evidence else GoalStatus.FAILED,
                evidence=evidence,
                confidence=0.8 if evidence else 0.3,
                reasoning=f"Searched {source_id}, found {len(evidence)} relevant results",
                depth=context.depth
            )

        except Exception as e:
            logger.error(f"API call to {source_id} failed: {e}")
            return GoalResult(
                goal=goal,
                status=GoalStatus.FAILED,
                error=str(e),
                depth=context.depth
            )

    async def _execute_web_search(self, goal: str, action: Action, context: GoalContext) -> GoalResult:
        """Execute a web search."""
        # Use Brave Search or Exa
        action.source = "brave_search"
        return await self._execute_api_call(goal, action, context)

    async def _execute_analysis(self, goal: str, action: Action, context: GoalContext) -> GoalResult:
        """Analyze existing evidence."""
        from llm_utils import acompletion

        evidence_text = "\n\n".join([
            f"[{e.source}] {e.title}\n{e.content}"
            for e in context.accumulated_evidence[-context.constraints.max_evidence_for_analysis:]
        ])

        prompt = action.prompt or f"Analyze the following evidence to address: {goal}"
        full_prompt = f"{prompt}\n\nEVIDENCE:\n{evidence_text}"

        try:
            response = await acompletion(
                model="gemini/gemini-2.5-flash",
                messages=[{"role": "user", "content": full_prompt}]
            )

            # Track cost
            context.add_cost(context.constraints.cost_per_analysis)

            analysis = response.choices[0].message.content

            return GoalResult(
                goal=goal,
                status=GoalStatus.COMPLETED,
                synthesis=analysis,
                confidence=0.7,
                reasoning="Analysis of accumulated evidence",
                depth=context.depth
            )
        except Exception as e:
            return GoalResult(
                goal=goal,
                status=GoalStatus.FAILED,
                error=str(e),
                depth=context.depth
            )

    async def _execute_synthesis(self, goal: str, action: Action, context: GoalContext) -> GoalResult:
        """Synthesize evidence into conclusions."""
        # Similar to analysis but focused on synthesis
        return await self._execute_analysis(goal, action, context)

    async def _decompose(self, goal: str, context: GoalContext) -> List[SubGoal]:
        """
        Decompose a goal into sub-goals.
        """
        from llm_utils import acompletion

        sources_text = "\n".join([
            f"- {s['name']}: {s['description']}"
            for s in context.available_sources[:context.constraints.max_sources_in_decompose]
        ])

        existing_goals = "\n".join([
            f"  - {g}" for g in context.all_goals[-context.constraints.max_goals_in_prompt:]
        ]) or "  (none yet)"

        prompt = f"""You are a research agent decomposing a goal into sub-goals.

{_get_temporal_context()}

ORIGINAL OBJECTIVE: {context.original_objective}

GOAL TO DECOMPOSE: {goal}

WHY DECOMPOSITION IS NEEDED:
{context.decomposition_rationale or "Goal is too broad for direct execution"}

GOAL ANCESTRY:
{chr(10).join(f"  {i+1}. {g}" for i, g in enumerate(context.goal_stack)) or "  (root goal)"}

EVIDENCE SO FAR: {context.evidence_summary}

AVAILABLE DATA SOURCES:
{sources_text}

EXISTING GOALS (avoid redundancy):
{existing_goals}

CONSTRAINTS:
- Remaining depth: {context.constraints.max_depth - context.depth} levels
- Remaining goals: {context.constraints.max_goals - context.goals_created}

Create sub-goals that:
1. Together fully address the parent goal
2. Are as INDEPENDENT as possible (can run in parallel)
3. Are appropriately sized (not too broad, not too narrow)
4. DON'T duplicate existing goals
5. Each sub-goal should be achievable with 1-3 data source queries

Return JSON:
{{
    "sub_goals": [
        {{
            "description": "Clear, actionable goal description",
            "rationale": "How this helps achieve the parent goal",
            "dependencies": [0, 1],  // Indices of sub-goals this depends on (empty if independent)
            "estimated_complexity": "atomic|simple|moderate|complex"
        }}
    ],
    "coverage_assessment": "How these sub-goals cover the parent goal"
}}"""

        try:
            response = await acompletion(
                model="gemini/gemini-2.5-flash",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )

            # Track cost
            context.add_cost(context.constraints.cost_per_decomposition)

            result = json.loads(response.choices[0].message.content)

            sub_goals = []
            for sg_data in result.get("sub_goals", []):
                sub_goals.append(SubGoal(
                    description=sg_data.get("description", ""),
                    rationale=sg_data.get("rationale", ""),
                    dependencies=sg_data.get("dependencies", []),
                    estimated_complexity=sg_data.get("estimated_complexity", "moderate")
                ))

            return sub_goals

        except Exception as e:
            logger.error(f"Decomposition failed: {e}")
            return []

    async def _goal_achieved(
        self,
        goal: str,
        sub_results: List[GoalResult],
        context: GoalContext
    ) -> bool:
        """
        Check if a goal has been sufficiently achieved.
        """
        from llm_utils import acompletion

        # Quick heuristic checks first
        if not sub_results:
            return False

        # Count evidence
        total_evidence = sum(len(r.evidence) for r in sub_results)
        successful_results = sum(1 for r in sub_results if r.status == GoalStatus.COMPLETED)

        # If we have substantial evidence, ask LLM
        if (total_evidence < context.constraints.min_evidence_for_achievement_check and
                successful_results < context.constraints.min_successes_for_achievement_check):
            return False  # Keep going

        results_summary = "\n".join([
            f"- {r.goal[:50]}: {r.status.value}, {len(r.evidence)} evidence"
            for r in sub_results
        ])

        prompt = f"""GOAL: {goal}

ORIGINAL OBJECTIVE: {context.original_objective}

SUB-GOAL RESULTS:
{results_summary}

TOTAL EVIDENCE GATHERED: {total_evidence} pieces

Has this goal been SUFFICIENTLY achieved to stop pursuing more sub-goals?

Consider:
- Do we have enough evidence to answer the goal?
- Are there obvious critical gaps?
- Is continuing likely to add significant new value?

Return JSON:
{{
    "achieved": true or false,
    "confidence": 0.0 to 1.0,
    "reasoning": "Brief explanation"
}}"""

        try:
            response = await acompletion(
                model="gemini/gemini-2.5-flash",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )

            # Track cost
            context.add_cost(context.constraints.cost_per_achievement_check)

            result = json.loads(response.choices[0].message.content)
            return result.get("achieved", False)

        except Exception as e:
            logger.error(f"Achievement check failed: {e}")
            return False  # Keep going on error

    async def _synthesize(
        self,
        goal: str,
        sub_results: List[GoalResult],
        context: GoalContext
    ) -> GoalResult:
        """
        Synthesize sub-goal results into a coherent parent result.
        """
        from llm_utils import acompletion

        # Gather all evidence
        all_evidence = []
        for r in sub_results:
            all_evidence.extend(r.evidence)

        # Format for synthesis
        max_content = context.constraints.max_content_chars_in_synthesis
        evidence_text = "\n\n".join([
            f"[{e.source}] {e.title}\n{e.content[:max_content]}"
            for e in all_evidence[:context.constraints.max_evidence_for_synthesis]
        ])

        sub_syntheses = "\n".join([
            f"- {r.goal}: {r.synthesis or r.reasoning or 'No synthesis'}"
            for r in sub_results if r.synthesis or r.reasoning
        ])

        prompt = f"""Synthesize research findings for:

{_get_temporal_context()}

GOAL: {goal}

ORIGINAL OBJECTIVE: {context.original_objective}

SUB-GOAL FINDINGS:
{sub_syntheses}

KEY EVIDENCE ({len(all_evidence)} total pieces):
{evidence_text}

Create a coherent synthesis that:
1. Directly addresses the goal
2. Highlights key findings
3. Notes confidence levels and limitations
4. Identifies any contradictions

Return JSON:
{{
    "synthesis": "Comprehensive synthesis addressing the goal",
    "key_findings": ["Finding 1", "Finding 2", ...],
    "confidence": 0.0 to 1.0,
    "limitations": ["Limitation 1", ...]
}}"""

        try:
            response = await acompletion(
                model="gemini/gemini-2.5-flash",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )

            # Track cost
            context.add_cost(context.constraints.cost_per_synthesis)

            result = json.loads(response.choices[0].message.content)

            return GoalResult(
                goal=goal,
                status=GoalStatus.COMPLETED,
                evidence=all_evidence,
                sub_results=sub_results,
                synthesis=result.get("synthesis", ""),
                confidence=result.get("confidence", 0.5),
                depth=context.depth
            )

        except Exception as e:
            logger.error(f"Synthesis failed: {e}")
            return GoalResult(
                goal=goal,
                status=GoalStatus.COMPLETED,
                evidence=all_evidence,
                sub_results=sub_results,
                synthesis=f"Synthesis failed: {e}. Raw evidence available.",
                confidence=0.3,
                depth=context.depth
            )

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def _check_constraints(self, context: GoalContext) -> Optional[str]:
        """Check if any constraints are violated."""
        if context.depth >= context.constraints.max_depth:
            return f"Max depth ({context.constraints.max_depth}) reached"

        if context.elapsed_seconds >= context.constraints.max_time_seconds:
            return f"Time limit ({context.constraints.max_time_seconds}s) reached"

        if context.cost_incurred >= context.constraints.max_cost_dollars:
            return f"Cost limit (${context.constraints.max_cost_dollars}) reached"

        if context.goals_created >= context.constraints.max_goals:
            return f"Goal limit ({context.constraints.max_goals}) reached"

        return None

    def _detect_cycle(self, goal: str, context: GoalContext) -> bool:
        """Detect if pursuing this goal would create a cycle."""
        # Exact match in ancestry
        if goal in context.goal_stack:
            return True

        # Could add semantic similarity check here
        return False

    async def _filter_results(
        self,
        goal: str,
        evidence: List[Evidence],
        context: GoalContext
    ) -> List[Evidence]:
        """
        Filter results for relevance to the goal.

        Uses LLM to evaluate each result and keep only relevant ones.
        This improves signal-to-noise ratio in the final output.
        """
        if len(evidence) <= context.constraints.min_results_to_filter:
            # Too few results to filter
            return evidence

        from llm_utils import acompletion

        # Format evidence for evaluation
        evidence_text = "\n\n".join([
            f"Result #{i}:\nTitle: {e.title}\nContent: {e.content[:300]}..."
            for i, e in enumerate(evidence)
        ])

        prompt = f"""You are filtering research results for relevance.

{_get_temporal_context()}

ORIGINAL OBJECTIVE: {context.original_objective}

CURRENT GOAL: {goal}

RESULTS TO FILTER:
{evidence_text}

Evaluate each result's relevance to the goal. Return a JSON object with:
{{
    "relevant_indices": [0, 2, 5],  // List of result indices that ARE relevant
    "filtering_rationale": "Brief explanation of filtering decisions"
}}

Be generous - include results that have ANY connection to the goal.
Only filter out results that are clearly off-topic or irrelevant."""

        try:
            response = await acompletion(
                model="gemini/gemini-2.5-flash",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )

            # Track cost
            context.add_cost(context.constraints.cost_per_filter)

            result = json.loads(response.choices[0].message.content)
            relevant_indices = result.get("relevant_indices", list(range(len(evidence))))

            # Filter to relevant results
            filtered = [evidence[i] for i in relevant_indices if i < len(evidence)]

            # Assign relevance scores
            for i, e in enumerate(filtered):
                e.relevance_score = 1.0  # Marked as relevant by LLM

            logger.info(f"Filtered {len(evidence)} → {len(filtered)} results")
            return filtered

        except Exception as e:
            logger.warning(f"Filtering failed: {e}, keeping all results")
            return evidence

    async def _reformulate_on_error(
        self,
        source_id: str,
        goal: str,
        original_params: Dict[str, Any],
        error_message: str,
        context: GoalContext
    ) -> Optional[Dict[str, Any]]:
        """
        Reformulate query parameters when API returns an error.

        Uses LLM to understand the error and fix the query.
        """
        from llm_utils import acompletion

        prompt = f"""An API returned an error. Analyze and fix the query parameters.

{_get_temporal_context()}

SOURCE: {source_id}
RESEARCH GOAL: {goal}

ORIGINAL PARAMETERS:
{json.dumps(original_params, indent=2)}

ERROR MESSAGE:
{error_message}

COMMON API ERROR PATTERNS AND FIXES:
1. **Parameter validation errors** (HTTP 400/422):
   - Value too short: Expand abbreviations (e.g., "AI" → "artificial intelligence")
   - Invalid enum value: Use a valid value from the API's allowed set
   - Invalid date format: Use YYYY-MM-DD

2. **Search constraint errors**:
   - Query too broad: Add specific filters
   - Query too narrow: Remove restrictive filters

3. **Unfixable errors** (rate limit, auth) - Return can_fix: false

Return JSON:
{{
    "can_fix": true/false,
    "fixed_params": {{ ... corrected parameters ... }},
    "explanation": "Brief explanation of fix"
}}"""

        try:
            response = await acompletion(
                model="gemini/gemini-2.5-flash",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )

            context.add_cost(context.constraints.cost_per_reformulation)

            result = json.loads(response.choices[0].message.content)

            if result.get("can_fix") and result.get("fixed_params"):
                logger.info(f"Reformulated query for {source_id}: {result.get('explanation', 'Fixed')}")
                return result["fixed_params"]
            else:
                logger.warning(f"Cannot fix query for {source_id}: {result.get('explanation', 'Unknown')}")
                return None

        except Exception as e:
            logger.error(f"Reformulation failed for {source_id}: {e}")
            return None

    def _group_by_dependency(self, sub_goals: List[SubGoal]) -> List[List[SubGoal]]:
        """
        Group sub-goals by dependency for parallel execution.

        Returns groups in execution order - goals in same group can run in parallel.
        """
        if not sub_goals:
            return []

        # Simple topological sort
        remaining = list(range(len(sub_goals)))
        completed = set()
        groups = []

        while remaining:
            # Find goals with all dependencies satisfied
            ready = []
            for i in remaining:
                deps = sub_goals[i].dependencies
                if all(d in completed for d in deps):
                    ready.append(i)

            if not ready:
                # Circular dependency - just add remaining
                ready = remaining

            groups.append([sub_goals[i] for i in ready])
            completed.update(ready)
            remaining = [i for i in remaining if i not in completed]

        return groups

    def _save_result(self, result: GoalResult):
        """Save the final result to disk."""
        # Save JSON result
        result_path = self.output_dir / "result.json"
        with open(result_path, 'w') as f:
            json.dump(self._result_to_dict(result), f, indent=2, default=str)

        # Save markdown report
        report_path = self.output_dir / "report.md"
        with open(report_path, 'w') as f:
            f.write(self._generate_report(result))

        print(f"\nResults saved to: {self.output_dir}")

    def _result_to_dict(self, result: GoalResult) -> Dict:
        """Convert GoalResult to serializable dict."""
        return {
            "goal": result.goal,
            "status": result.status.value,
            "synthesis": result.synthesis,
            "confidence": result.confidence,
            "evidence_count": len(result.evidence),
            "sub_results_count": len(result.sub_results),
            "depth": result.depth,
            "duration_seconds": result.duration_seconds,
            "evidence": [
                {
                    "source": e.source,
                    "title": e.title,
                    "content": e.content[:self.constraints.max_content_chars_in_synthesis],
                    "url": e.url
                }
                for e in result.evidence[:self.constraints.max_evidence_in_saved_result]
            ],
            "sub_results": [
                self._result_to_dict(sr) for sr in result.sub_results
            ]
        }

    def _generate_report(self, result: GoalResult) -> str:
        """Generate a markdown report from the result."""
        lines = [
            f"# Research Report",
            f"",
            f"**Objective:** {result.goal}",
            f"",
            f"**Status:** {result.status.value}",
            f"**Confidence:** {result.confidence:.0%}",
            f"**Duration:** {result.duration_seconds:.1f}s",
            f"**Evidence:** {len(result.evidence)} pieces",
            f"",
            f"## Summary",
            f"",
            result.synthesis or "No synthesis available.",
            f"",
            f"## Evidence Sources",
            f""
        ]

        # Group evidence by source
        by_source: Dict[str, List[Evidence]] = {}
        for e in result.evidence:
            by_source.setdefault(e.source, []).append(e)

        for source, evidence in by_source.items():
            lines.append(f"### {source} ({len(evidence)} results)")
            lines.append("")
            for e in evidence[:self.constraints.max_evidence_per_source_in_report]:
                lines.append(f"- **{e.title}**")
                if e.url:
                    lines.append(f"  - URL: {e.url}")
                lines.append(f"  - {e.content[:self.constraints.max_content_chars_in_report]}...")
                lines.append("")

        return "\n".join(lines)


# =============================================================================
# CLI Entry Point
# =============================================================================

async def main():
    """CLI entry point for testing."""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python recursive_agent.py 'research question'")
        sys.exit(1)

    question = sys.argv[1]

    agent = RecursiveResearchAgent(
        constraints=Constraints(
            max_depth=10,
            max_time_seconds=300,  # 5 minutes for testing
            max_goals=30
        )
    )

    result = await agent.research(question)

    print(f"\n{'='*60}")
    print("FINAL RESULT")
    print(f"{'='*60}")
    print(f"Status: {result.status.value}")
    print(f"Confidence: {result.confidence:.0%}")
    print(f"Evidence: {len(result.evidence)} pieces")
    print(f"Duration: {result.duration_seconds:.1f}s")
    print(f"\nSynthesis:\n{result.synthesis}")


if __name__ == "__main__":
    asyncio.run(main())
