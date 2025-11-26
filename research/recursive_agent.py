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
from research.services.entity_analyzer import EntityAnalyzer

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

    # === Progressive Summarization ===
    enable_summarization: bool = True  # Whether to summarize evidence
    max_content_before_summarize: int = 300  # Summarize if content > this many chars
    summary_target_chars: int = 150  # Target summary length
    cost_per_summarization: float = 0.0003  # Cost per batch summarization

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
# Execution Logger (Enhanced)
# =============================================================================

SCHEMA_VERSION = "2.0"


@dataclass
class GoalEvent:
    """A logged event in goal execution."""
    timestamp: str
    schema_version: str
    event_type: str
    goal: str
    depth: int
    parent_goal: Optional[str]
    data: Dict[str, Any]


class ExecutionLogger:
    """
    Enhanced structured logging for v2 recursive agent execution.

    Provides comprehensive logging of goal execution traces using JSONL format
    (one JSON object per line) to enable streaming writes, line-by-line filtering,
    and post-hoc forensic analysis.

    Key Features:
    - JSONL format (append-only, survives crashes, easy to filter)
    - Schema versioning for backward compatibility
    - Rich event types for detailed tracing
    - Raw response archiving to separate files
    - Performance metrics (timing, cost tracking)
    """

    def __init__(self, output_dir: Union[str, Path]):
        self.output_dir = Path(output_dir) if isinstance(output_dir, str) else output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.raw_dir = self.output_dir / "raw"
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.log_path = self.output_dir / "execution_log.jsonl"
        self.events: List[GoalEvent] = []

    def _write_entry(self, event_type: str, goal: str, depth: int,
                     parent_goal: Optional[str], data: Dict[str, Any]):
        """Write a single log entry to JSONL file."""
        event = GoalEvent(
            timestamp=datetime.now().isoformat(),
            schema_version=SCHEMA_VERSION,
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

        # Console logging
        prefix = "  " * depth
        logger.info(f"{prefix}[{event_type}] {goal[:60]}...")

    def log(self, event_type: str, goal: str, depth: int,
            parent_goal: Optional[str], data: Dict[str, Any]):
        """Generic log method for backward compatibility."""
        self._write_entry(event_type, goal, depth, parent_goal, data)

    # === Run-Level Events ===

    def log_run_start(self, objective: str, constraints: Dict[str, Any],
                      sources_available: int):
        """Log research run start."""
        self._write_entry("run_start", objective, 0, None, {
            "constraints": constraints,
            "sources_available": sources_available,
            "start_time": datetime.now().isoformat()
        })

    def log_run_complete(self, objective: str, status: str,
                         total_evidence: int, total_goals: int,
                         elapsed_seconds: float, total_cost: float):
        """Log research run completion."""
        self._write_entry("run_complete", objective, 0, None, {
            "status": status,
            "total_evidence": total_evidence,
            "total_goals": total_goals,
            "elapsed_seconds": elapsed_seconds,
            "total_cost_dollars": total_cost
        })

    # === Goal-Level Events ===

    def log_goal_started(self, goal: str, depth: int, parent_goal: Optional[str]):
        """Log goal execution start."""
        self._write_entry("goal_started", goal, depth, parent_goal, {})

    def log_goal_assessed(self, goal: str, depth: int, parent_goal: Optional[str],
                          directly_executable: bool, reasoning: str,
                          action_type: Optional[str] = None, source: Optional[str] = None):
        """Log goal assessment decision."""
        self._write_entry("goal_assessed", goal, depth, parent_goal, {
            "directly_executable": directly_executable,
            "reasoning": reasoning[:200],
            "action_type": action_type,
            "source": source
        })

    def log_goal_decomposed(self, goal: str, depth: int, parent_goal: Optional[str],
                            sub_goals: List[str], rationale: str):
        """Log goal decomposition into sub-goals."""
        self._write_entry("goal_decomposed", goal, depth, parent_goal, {
            "sub_goal_count": len(sub_goals),
            "sub_goals": [sg[:80] for sg in sub_goals],
            "decomposition_rationale": rationale[:200]
        })

    def log_goal_completed(self, goal: str, depth: int, parent_goal: Optional[str],
                           status: str, evidence_count: int, confidence: float,
                           duration_seconds: float, cost_dollars: float):
        """Log goal completion."""
        self._write_entry("goal_completed", goal, depth, parent_goal, {
            "status": status,
            "evidence_count": evidence_count,
            "confidence": confidence,
            "duration_seconds": duration_seconds,
            "cost_dollars": cost_dollars
        })

    # === Source Execution Events ===

    def log_api_call(self, goal: str, depth: int, parent_goal: Optional[str],
                     source: str, query_params: Dict[str, Any]):
        """Log API call being made."""
        self._write_entry("api_call", goal, depth, parent_goal, {
            "source": source,
            "query_params": query_params
        })

    def log_api_response(self, goal: str, depth: int, parent_goal: Optional[str],
                         source: str, success: bool, result_count: int,
                         response_time_ms: float, error: Optional[str] = None):
        """Log API response received."""
        self._write_entry("api_response", goal, depth, parent_goal, {
            "source": source,
            "success": success,
            "result_count": result_count,
            "response_time_ms": response_time_ms,
            "error": error
        })

    def log_query_reformulation(self, goal: str, depth: int, parent_goal: Optional[str],
                                source: str, original_params: Dict[str, Any],
                                error_message: str, fixed_params: Optional[Dict[str, Any]],
                                can_fix: bool, explanation: str):
        """Log query reformulation attempt."""
        self._write_entry("query_reformulation", goal, depth, parent_goal, {
            "source": source,
            "original_params": original_params,
            "error_message": error_message[:200],
            "can_fix": can_fix,
            "fixed_params": fixed_params,
            "explanation": explanation[:200]
        })

    # === Filtering Events ===

    def log_filter_decision(self, goal: str, depth: int, parent_goal: Optional[str],
                            source: str, original_count: int, filtered_count: int,
                            rationale: str):
        """Log relevance filtering decision."""
        self._write_entry("filter_decision", goal, depth, parent_goal, {
            "source": source,
            "original_count": original_count,
            "filtered_count": filtered_count,
            "kept_ratio": filtered_count / original_count if original_count > 0 else 0,
            "rationale": rationale[:200]
        })

    # === Achievement Events ===

    def log_achievement_check(self, goal: str, depth: int, parent_goal: Optional[str],
                              sub_goals_completed: int, total_sub_goals: int,
                              total_evidence: int, achieved: bool, reasoning: str):
        """Log goal achievement check."""
        self._write_entry("achievement_check", goal, depth, parent_goal, {
            "sub_goals_completed": sub_goals_completed,
            "total_sub_goals": total_sub_goals,
            "total_evidence": total_evidence,
            "achieved": achieved,
            "reasoning": reasoning[:200]
        })

    # === Synthesis Events ===

    def log_synthesis(self, goal: str, depth: int, parent_goal: Optional[str],
                      evidence_count: int, confidence: float,
                      key_findings_count: int, limitations_count: int):
        """Log synthesis completion."""
        self._write_entry("synthesis", goal, depth, parent_goal, {
            "evidence_count": evidence_count,
            "confidence": confidence,
            "key_findings_count": key_findings_count,
            "limitations_count": limitations_count
        })

    # === Constraint Events ===

    def log_constraint_violation(self, goal: str, depth: int, parent_goal: Optional[str],
                                 constraint_type: str, current_value: Any,
                                 limit_value: Any):
        """Log constraint violation."""
        self._write_entry("constraint_violation", goal, depth, parent_goal, {
            "constraint_type": constraint_type,
            "current_value": current_value,
            "limit_value": limit_value
        })

    def log_cycle_detected(self, goal: str, depth: int, parent_goal: Optional[str],
                           goal_stack: List[str]):
        """Log cycle detection."""
        self._write_entry("cycle_detected", goal, depth, parent_goal, {
            "goal_stack": goal_stack
        })

    # === Utility Methods ===

    def save_raw_response(self, source: str, goal_hash: str, results: List[Dict]) -> str:
        """
        Save raw API results to separate file.

        Returns relative path to the saved file.
        """
        safe_source = source.lower().replace(' ', '_').replace('.', '_')
        filename = f"{safe_source}_{goal_hash[:8]}.json"
        filepath = self.raw_dir / filename

        with open(filepath, 'w') as f:
            json.dump(results, f, indent=2, default=str)

        return f"raw/{filename}"


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

        # Entity analyzer for relationship tracking
        self.entity_analyzer = EntityAnalyzer(
            progress_callback=lambda event, msg: logger.info(f"[Entity] {event}: {msg}")
        )

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

        # Log run start with enhanced logging
        self.logger.log_run_start(
            objective=question,
            constraints=asdict(self.constraints),
            sources_available=len(self.available_sources)
        )

        result = await self.pursue_goal(question, context)

        # Log run complete
        self.logger.log_run_complete(
            objective=question,
            status=result.status.value,
            total_evidence=len(result.evidence),
            total_goals=context.goals_created,
            elapsed_seconds=result.duration_seconds,
            total_cost=result.cost_dollars
        )

        # Save final result (async for LLM-based report synthesis)
        await self._save_result(result)

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

        self.logger.log_goal_started(goal, context.depth, parent_goal)

        # === CONSTRAINT CHECK ===
        violation = self._check_constraints(context)
        if violation:
            self.logger.log_constraint_violation(
                goal, context.depth, parent_goal,
                constraint_type=violation.split(" ")[0].lower(),  # e.g., "max_depth"
                current_value=None,
                limit_value=violation
            )
            return GoalResult(
                goal=goal,
                status=GoalStatus.CONSTRAINED,
                reasoning=violation,
                depth=context.depth
            )

        # === CYCLE CHECK ===
        if self._detect_cycle(goal, context):
            self.logger.log_cycle_detected(goal, context.depth, parent_goal, context.goal_stack)
            return GoalResult(
                goal=goal,
                status=GoalStatus.CYCLE_DETECTED,
                reasoning="Goal appears in ancestry (would create infinite loop)",
                depth=context.depth
            )

        # === ASSESSMENT: Execute or Decompose? ===
        assessment = await self._assess(goal, context)
        self.logger.log_goal_assessed(
            goal, context.depth, parent_goal,
            directly_executable=assessment.directly_executable,
            reasoning=assessment.reasoning,
            action_type=assessment.action.type.value if assessment.action else None,
            source=assessment.action.source if assessment.action else None
        )

        if assessment.directly_executable:
            # === EXECUTE DIRECTLY ===
            result = await self._execute(goal, assessment.action, context)
            result.duration_seconds = (datetime.now() - start_time).total_seconds()
            result.cost_dollars = context.cost_incurred  # Include cost from assessment LLM call

            self.logger.log_goal_completed(
                goal, context.depth, parent_goal,
                status=result.status.value,
                evidence_count=len(result.evidence),
                confidence=result.confidence,
                duration_seconds=result.duration_seconds,
                cost_dollars=result.cost_dollars
            )
            return result

        # === DECOMPOSE INTO SUB-GOALS ===
        context_with_rationale = context.with_decomposition_rationale(
            assessment.decomposition_rationale
        )
        sub_goals = await self._decompose(goal, context_with_rationale)

        self.logger.log_goal_decomposed(
            goal, context.depth, parent_goal,
            sub_goals=[sg.description for sg in sub_goals],
            rationale=assessment.decomposition_rationale or "Goal too complex for direct execution"
        )

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
        seen_urls: set = set()  # Track URLs for deduplication
        duplicate_count: int = 0  # Track duplicates for logging

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
                # Deduplicate evidence by URL before accumulating
                for evidence in result.evidence:
                    url = evidence.url
                    if url:
                        if url not in seen_urls:
                            seen_urls.add(url)
                            all_evidence.append(evidence)
                        else:
                            duplicate_count += 1
                    else:
                        # No URL - can't deduplicate, keep it
                        all_evidence.append(evidence)

            # === CHECK IF GOAL ACHIEVED ===
            achieved = await self._goal_achieved(goal, sub_results, context)
            if achieved:
                self.logger.log_achievement_check(
                    goal, context.depth, parent_goal,
                    sub_goals_completed=len(sub_results),
                    total_sub_goals=len(sub_goals),
                    total_evidence=len(all_evidence),
                    achieved=True,
                    reasoning="Goal achieved early based on LLM assessment"
                )
                break

        # Log deduplication stats if any duplicates were found
        if duplicate_count > 0:
            total_before_dedup = len(all_evidence) + duplicate_count
            logger.info(f"Deduplication: {total_before_dedup} → {len(all_evidence)} "
                       f"({duplicate_count} duplicates removed)")

        # === SYNTHESIZE RESULTS ===
        synthesis = await self._synthesize(goal, sub_results, context)

        self.logger.log_synthesis(
            goal, context.depth, parent_goal,
            evidence_count=len(all_evidence),
            confidence=synthesis.confidence,
            key_findings_count=len(sub_results),
            limitations_count=sum(1 for r in sub_results if r.status == GoalStatus.FAILED)
        )

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
            parent_goal = context.goal_stack[-1] if context.goal_stack else None
            max_retries = 2
            current_params = query_params
            result = None

            for attempt in range(max_retries):
                # Log API call
                self.logger.log_api_call(
                    goal, context.depth, parent_goal,
                    source=source_id,
                    query_params=current_params
                )

                start_time = datetime.now()
                result = await integration.execute_search(
                    current_params,
                    limit=context.constraints.max_results_per_source
                )
                response_time_ms = (datetime.now() - start_time).total_seconds() * 1000

                # Log API response
                self.logger.log_api_response(
                    goal, context.depth, parent_goal,
                    source=source_id,
                    success=result.success,
                    result_count=len(result.results) if result.results else 0,
                    response_time_ms=response_time_ms,
                    error=result.error
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

                    # Log reformulation attempt
                    self.logger.log_query_reformulation(
                        goal, context.depth, parent_goal,
                        source=source_id,
                        original_params=current_params,
                        error_message=str(result.error),
                        fixed_params=fixed_params,
                        can_fix=fixed_params is not None,
                        explanation="LLM reformulation attempt" if fixed_params else "Could not fix query"
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

                # Log filter decision
                if original_count != len(evidence):
                    self.logger.log_filter_decision(
                        goal, context.depth, parent_goal,
                        source=source_id,
                        original_count=original_count,
                        filtered_count=len(evidence),
                        rationale=f"LLM relevance filtering kept {len(evidence)} of {original_count} results"
                    )

            filtered_msg = f" (filtered {original_count}→{len(evidence)})" if len(evidence) != original_count else ""
            print(f"    ✓ {source_id}: {len(evidence)} results{filtered_msg}")

            # Extract entities from results (builds relationship graph)
            if evidence:
                results_for_extraction = [
                    {"title": e.title, "snippet": e.content[:300], "url": e.url}
                    for e in evidence
                ]
                entities = await self.entity_analyzer.extract_and_update(
                    results=results_for_extraction,
                    research_question=context.original_objective,
                    task_query=goal
                )
                if entities:
                    print(f"    📊 Extracted {len(entities)} entities: {', '.join(entities[:5])}")

                # Summarize long content to preserve key info in fewer tokens
                evidence = await self._summarize_evidence(evidence, goal, context)

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

    async def _summarize_evidence(
        self,
        evidence: List[Evidence],
        goal: str,
        context: GoalContext
    ) -> List[Evidence]:
        """
        Summarize evidence content to preserve key information in fewer tokens.

        Replaces truncation with intelligent summarization. Only summarizes
        evidence items with content longer than max_content_before_summarize.

        Args:
            evidence: List of Evidence items to potentially summarize
            goal: Current goal for context
            context: GoalContext for constraints and cost tracking

        Returns:
            Evidence list with long content summarized
        """
        if not context.constraints.enable_summarization:
            return evidence

        # Find evidence needing summarization (store with sequential index for prompt)
        needs_summary = [
            (seq_idx, orig_idx, e)
            for seq_idx, (orig_idx, e) in enumerate(
                (i, e) for i, e in enumerate(evidence)
                if len(e.content) > context.constraints.max_content_before_summarize
            )
        ]

        if not needs_summary:
            return evidence

        from llm_utils import acompletion

        # Batch summarization for efficiency - use sequential indices (0, 1, 2...)
        items_text = "\n\n".join([
            f"Item #{seq_idx}:\nTitle: {e.title}\nContent: {e.content}"
            for seq_idx, orig_idx, e in needs_summary
        ])

        prompt = f"""Summarize each item to ~{context.constraints.summary_target_chars} characters.
Preserve: key facts, numbers, names, dates, relationships.
Remove: boilerplate, redundancy, filler.

CONTEXT: {goal}

ITEMS TO SUMMARIZE:
{items_text}

Return JSON with item_index matching the Item # shown above:
{{
    "summaries": [
        {{"item_index": 0, "summary": "Concise summary preserving key facts..."}},
        {{"item_index": 1, "summary": "..."}}
    ]
}}"""

        try:
            response = await acompletion(
                model="gemini/gemini-2.5-flash",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )

            context.add_cost(context.constraints.cost_per_summarization)

            result = json.loads(response.choices[0].message.content)
            summaries = {s["item_index"]: s["summary"] for s in result.get("summaries", [])}

            # Apply summaries using sequential index mapping
            summarized_count = 0
            for seq_idx, orig_idx, e in needs_summary:
                if seq_idx in summaries:
                    # Store original in metadata, replace content with summary
                    e.metadata["original_content"] = e.content
                    e.content = summaries[seq_idx]
                    summarized_count += 1

            if summarized_count > 0:
                logger.info(f"Summarized {summarized_count} evidence items")

            return evidence

        except Exception as e:
            logger.warning(f"Summarization failed: {e}, keeping original content")
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

    async def _save_result(self, result: GoalResult):
        """Save the final result to disk."""
        # Save JSON result (includes entity graph)
        result_dict = self._result_to_dict(result)
        result_dict["entity_graph"] = self.entity_analyzer.get_entity_graph()
        result_dict["entities_discovered"] = len(self.entity_analyzer.get_all_entities())

        result_path = self.output_dir / "result.json"
        with open(result_path, 'w') as f:
            json.dump(result_dict, f, indent=2, default=str)

        # Save entity graph separately for easy access
        entity_path = self.output_dir / "entities.json"
        with open(entity_path, 'w') as f:
            json.dump({
                "entities": self.entity_analyzer.get_all_entities(),
                "graph": self.entity_analyzer.get_entity_graph()
            }, f, indent=2, default=str)

        # Generate and save markdown report (LLM-based synthesis)
        print("Generating report synthesis...")
        report = await self._generate_report(result)
        report_path = self.output_dir / "report.md"
        with open(report_path, 'w') as f:
            f.write(report)

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

    async def _generate_report(self, result: GoalResult) -> str:
        """
        Generate a comprehensive markdown report using LLM synthesis.

        Uses structured JSON synthesis with Jinja2 templates for professional
        investigative-quality reports with inline citations.
        """
        from llm_utils import acompletion
        from core.prompt_loader import render_prompt
        from config_loader import config

        # Group evidence by source
        by_source: Dict[str, List[Dict]] = {}
        for e in result.evidence:
            by_source.setdefault(e.source, []).append({
                "title": e.title,
                "content": e.content[:500],
                "url": e.url,
                "metadata": e.metadata
            })

        # Prepare sub-results summary
        sub_results_summary = []
        for sr in result.sub_results:
            sub_results_summary.append({
                "goal": sr.goal,
                "status": sr.status.value,
                "evidence_count": len(sr.evidence),
                "confidence": sr.confidence,
                "synthesis": sr.synthesis[:300] if sr.synthesis else None
            })

        # Collect unique sources queried
        sources_queried = list(by_source.keys())

        # Get entity graph for report
        entity_graph = self.entity_analyzer.get_entity_graph()
        entities_list = self.entity_analyzer.get_all_entities()

        # Format entity relationships for prompt
        entity_relationships = []
        for entity_name, data in entity_graph.items():
            related = data.get("related_entities", [])
            evidence = data.get("evidence", [])
            entity_relationships.append({
                "name": entity_name,
                "related_to": related[:5],  # Limit for prompt size
                "evidence": evidence[:2] if evidence else []
            })

        try:
            # Render prompt with template
            prompt = render_prompt(
                "deep_research/v2_report_synthesis.j2",
                objective=result.goal,
                evidence_count=len(result.evidence),
                source_count=len(sources_queried),
                evidence_by_source=by_source,
                sub_results=sub_results_summary,
                goals_pursued=len(result.sub_results) + 1,
                sources_queried=sources_queried,
                entities_discovered=len(entities_list),
                entity_relationships=entity_relationships[:20]  # Top 20 entities
            )

            # Call LLM for structured synthesis
            response = await acompletion(
                model=config.get_model("synthesis"),
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )

            synthesis_json = json.loads(response.choices[0].message.content)

            # Convert JSON to markdown
            report = self._format_synthesis_to_markdown(synthesis_json, result)

            return report

        except Exception as e:
            logger.error(f"Report synthesis failed: {e}", exc_info=True)
            # Fallback to basic report
            return self._generate_basic_report(result, by_source)

    def _format_synthesis_to_markdown(self, json_data: Dict, result: GoalResult) -> str:
        """Convert structured synthesis JSON to markdown report."""
        try:
            report_data = json_data.get("report", {})
        except (AttributeError, TypeError):
            return "# Error: Invalid synthesis JSON structure\n\nThe synthesis LLM returned malformed JSON."

        md = []

        # Title
        title = report_data.get("title", "Research Report")
        md.append(f"# {title}\n\n")

        # Metadata
        md.append(f"**Objective:** {result.goal}\n")
        md.append(f"**Status:** {result.status.value} | **Confidence:** {result.confidence:.0%}\n")
        md.append(f"**Duration:** {result.duration_seconds:.1f}s | **Evidence:** {len(result.evidence)} pieces\n\n")

        # Executive Summary
        exec_summary = report_data.get("executive_summary", {})
        md.append("## Executive Summary\n\n")
        md.append(f"{exec_summary.get('text', 'No summary provided.')}\n\n")

        if exec_summary.get("key_points"):
            md.append("**Key Points:**\n\n")
            for kp in exec_summary["key_points"]:
                point = kp.get("point", "")
                citations = kp.get("inline_citations", [])
                citation_links = []
                for c in citations:
                    title_str = c.get("title", "Source")
                    url_str = c.get("url", "")
                    link = f"[{title_str}]({url_str})" if url_str else title_str
                    citation_links.append(link)

                citations_str = ", ".join(citation_links) if citation_links else ""
                if citations_str:
                    md.append(f"- {point} — {citations_str}\n")
                else:
                    md.append(f"- {point}\n")
            md.append("\n")

        # Source Groups (Key Findings)
        source_groups = report_data.get("source_groups", [])
        if source_groups:
            md.append("## Key Findings\n\n")
            for group in source_groups:
                group_name = group.get("group_name", "Unknown Group")
                reliability = group.get("reliability_context", "")

                md.append(f"### {group_name}\n\n")
                if reliability:
                    md.append(f"*{reliability}*\n\n")

                findings = group.get("findings", [])
                for finding in findings:
                    claim = finding.get("claim", "")
                    citations = finding.get("inline_citations", [])
                    supporting = finding.get("supporting_detail")

                    citation_links = []
                    for c in citations:
                        title_str = c.get("title", "Source")
                        url_str = c.get("url", "")
                        link = f"[{title_str}]({url_str})" if url_str else title_str
                        citation_links.append(link)

                    citations_str = "; ".join(citation_links) if citation_links else ""
                    if citations_str:
                        md.append(f"- {claim} ({citations_str})\n")
                    else:
                        md.append(f"- {claim}\n")

                    if supporting:
                        md.append(f"  > {supporting}\n")

                md.append("\n")

        # Entity Network
        entity_network = report_data.get("entity_network", {})
        if entity_network and entity_network.get("key_entities"):
            md.append("## Entity Network\n\n")
            md.append(f"{entity_network.get('description', '')}\n\n")

            for entity in entity_network.get("key_entities", []):
                name = entity.get("name", "Unknown")
                context = entity.get("context", "")
                relationships = entity.get("relationships", [])

                md.append(f"**{name}**: {context}\n")
                for rel in relationships:
                    md.append(f"  - {rel}\n")
                md.append("\n")

        # Timeline
        timeline = report_data.get("timeline", [])
        if timeline:
            md.append("## Timeline\n\n")
            for item in timeline:
                date = item.get("date", "Unknown")
                event = item.get("event", "")
                sources = item.get("sources", [])

                source_links = []
                for s in sources:
                    s_title = s.get("title", "Source")
                    s_url = s.get("url", "")
                    source_links.append(f"[{s_title}]({s_url})" if s_url else s_title)

                sources_str = ", ".join(source_links) if source_links else ""
                md.append(f"- **{date}**: {event}")
                if sources_str:
                    md.append(f" ({sources_str})")
                md.append("\n")
            md.append("\n")

        # Methodology
        methodology = report_data.get("methodology", {})
        if methodology:
            md.append("## Methodology\n\n")
            approach = methodology.get("approach", "")
            if approach:
                md.append(f"{approach}\n\n")

            md.append(f"- **Goals pursued**: {methodology.get('goals_pursued', 0)}\n")
            md.append(f"- **Sources queried**: {methodology.get('sources_queried', [])}\n")
            md.append(f"- **Total evidence**: {methodology.get('total_evidence', 0)}\n")
            md.append(f"- **Confidence level**: {methodology.get('confidence_level', 'Unknown')}\n\n")

        # Limitations
        limitations = report_data.get("limitations", {})
        if limitations:
            md.append("## Limitations\n\n")
            gaps = limitations.get("gaps_identified", [])
            if gaps:
                md.append("**Gaps Identified:**\n")
                for gap in gaps:
                    md.append(f"- {gap}\n")
                md.append("\n")

            areas = limitations.get("areas_for_further_research", [])
            if areas:
                md.append("**Areas for Further Research:**\n")
                for area in areas:
                    md.append(f"- {area}\n")
                md.append("\n")

            notes = limitations.get("data_quality_notes")
            if notes:
                md.append(f"**Data Quality Notes:** {notes}\n\n")

        return "".join(md)

    def _generate_basic_report(self, result: GoalResult, by_source: Dict[str, List[Dict]]) -> str:
        """Fallback basic report when LLM synthesis fails."""
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

        for source, evidence_list in by_source.items():
            lines.append(f"### {source} ({len(evidence_list)} results)")
            lines.append("")
            for e in evidence_list[:self.constraints.max_evidence_per_source_in_report]:
                lines.append(f"- **{e['title']}**")
                if e.get('url'):
                    lines.append(f"  - URL: {e['url']}")
                lines.append(f"  - {e['content'][:self.constraints.max_content_chars_in_report]}...")
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
