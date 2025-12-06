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
from core.database_integration_base import Evidence, SearchResult
from core.error_classifier import ErrorClassifier, ErrorCategory, APIError

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
class IndexEntry:
    """
    Compact evidence metadata for global index.

    Used by LLM to select relevant evidence from global index without
    loading full content (which would exceed token limits).
    """
    evidence_id: str  # UUID
    goal: str  # Which goal produced this evidence
    source: str  # Which integration (e.g., "usaspending", "sam")
    title: str  # Evidence title
    snippet: str  # First 200 chars of content (for LLM preview)
    goal_ancestry: List[str]  # goal_stack at time of creation


@dataclass
class ResearchRun:
    """
    Global evidence index for cross-branch sharing.

    Enables sub-goals to see evidence from sibling/cousin branches,
    solving P0 #2 (cross-branch context loss).

    Architecture: Stored in GoalContext (run-level shared state),
    referenced (not copied) in all with_*() methods.
    """
    index: List[IndexEntry] = field(default_factory=list)
    evidence_store: Dict[str, Evidence] = field(default_factory=dict)
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    max_index_items_for_selection: int = 50  # Limit shown to LLM


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

    # === Iterative Research Loop ===
    max_iterations: int = 10  # Maximum follow-up iterations (safety limit only)
    cost_per_coverage_check: float = 0.0003  # Cost per coverage assessment
    cost_per_follow_up_generation: float = 0.0004  # Cost per follow-up generation

    # NOTE: No hardcoded thresholds for "enough evidence" or "enough sources"
    # The LLM reasons through what SHOULD exist and whether it has exhausted options


# Evidence is now imported from core.database_integration_base
# It extends SearchResult via inheritance, providing:
# - Zero drift: SearchResult fields automatically inherited
# - Type safety: Pydantic validation
# - Single source of truth: Field definitions in one place


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

    Fields are categorized into:
    - Run-level shared state (referenced, not copied in with_* methods)
    - Branch-local state (copied per branch)
    """
    # === RUN-LEVEL SHARED STATE (referenced across all contexts) ===

    # Global evidence index for cross-branch sharing
    research_run: Optional[ResearchRun] = None

    # Available capabilities (sources)
    available_sources: List[Dict[str, Any]] = field(default_factory=list)

    # Constraints
    constraints: Constraints = field(default_factory=Constraints)

    # All goals seen (for cycle detection and redundancy)
    all_goals: List[str] = field(default_factory=list)

    # === BRANCH-LOCAL STATE (copied per context) ===

    # Never lost
    original_objective: str = ""

    # Full ancestry
    goal_stack: List[str] = field(default_factory=list)

    # All evidence gathered so far (branch-local)
    accumulated_evidence: List[Evidence] = field(default_factory=list)

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
            # Run-level shared state (REFERENCED - same instance)
            research_run=self.research_run,
            available_sources=self.available_sources,
            constraints=self.constraints,
            all_goals=self.all_goals,

            # Branch-local state (copied)
            original_objective=self.original_objective,
            goal_stack=[*self.goal_stack, parent_goal],
            accumulated_evidence=self.accumulated_evidence.copy(),
            depth=self.depth + 1,

            # Tracking
            start_time=self.start_time,
            cost_incurred=self.cost_incurred,
            goals_created=self.goals_created,
            decomposition_rationale=self.decomposition_rationale
        )

    def with_evidence(self, new_evidence: List[Evidence]) -> 'GoalContext':
        """Create context with additional evidence."""
        return GoalContext(
            # Run-level shared state (REFERENCED - same instance)
            research_run=self.research_run,
            available_sources=self.available_sources,
            constraints=self.constraints,
            all_goals=self.all_goals,

            # Branch-local state (copied/updated)
            original_objective=self.original_objective,
            goal_stack=self.goal_stack,
            accumulated_evidence=[*self.accumulated_evidence, *new_evidence],
            depth=self.depth,

            # Tracking
            start_time=self.start_time,
            cost_incurred=self.cost_incurred,
            goals_created=self.goals_created,
            decomposition_rationale=self.decomposition_rationale
        )

    def with_decomposition_rationale(self, rationale: str) -> 'GoalContext':
        """Create context with decomposition rationale."""
        return GoalContext(
            # Run-level shared state (REFERENCED - same instance)
            research_run=self.research_run,
            available_sources=self.available_sources,
            constraints=self.constraints,
            all_goals=self.all_goals,

            # Branch-local state
            original_objective=self.original_objective,
            goal_stack=self.goal_stack,
            accumulated_evidence=self.accumulated_evidence,
            depth=self.depth,

            # Tracking + update rationale
            start_time=self.start_time,
            cost_incurred=self.cost_incurred,
            goals_created=self.goals_created,
            decomposition_rationale=rationale
        )

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
                            sub_goals: Union[List[str], List['SubGoal']], rationale: str):
        """
        Log goal decomposition into sub-goals.

        Args:
            sub_goals: Either List[str] (legacy) or List[SubGoal] (with dependencies)
        """
        # Handle both legacy List[str] and new List[SubGoal]
        if sub_goals and hasattr(sub_goals[0], 'description'):
            # New format: List[SubGoal] with dependencies
            sub_goals_data = [
                {
                    "description": sg.description[:80],
                    "dependencies": sg.dependencies,
                    "complexity": sg.estimated_complexity
                }
                for sg in sub_goals
            ]
        else:
            # Legacy format: List[str]
            sub_goals_data = [sg[:80] for sg in sub_goals]

        self._write_entry("goal_decomposed", goal, depth, parent_goal, {
            "sub_goal_count": len(sub_goals),
            "sub_goals": sub_goals_data,
            "decomposition_rationale": rationale[:200]
        })

    def log_dependency_groups(self, goal: str, depth: int, parent_goal: Optional[str],
                               groups: List[List['SubGoal']]):
        """
        Log DAG execution groups after topological sort.

        Each group contains sub-goals that can execute in parallel.
        Groups execute sequentially (group N+1 waits for group N to complete).
        """
        groups_data = []
        for group_idx, group in enumerate(groups):
            group_info = {
                "group_index": group_idx,
                "goal_count": len(group),
                "goals": [
                    {
                        "description": sg.description[:60],
                        "dependencies": sg.dependencies,
                        "complexity": sg.estimated_complexity
                    }
                    for sg in group
                ]
            }
            groups_data.append(group_info)

        self._write_entry("dependency_groups_execution", goal, depth, parent_goal, {
            "total_groups": len(groups),
            "groups": groups_data,
            "execution_note": "Groups execute sequentially, goals within groups execute in parallel"
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
                         response_time_ms: float, error: Optional[str] = None,
                         http_code: Optional[int] = None, error_category: Optional[str] = None):
        """Log API response received with structured error info."""
        data = {
            "source": source,
            "success": success,
            "result_count": result_count,
            "response_time_ms": response_time_ms,
            "error": error
        }

        # Add structured error fields if present
        if http_code is not None:
            data["http_code"] = http_code
        if error_category is not None:
            data["error_category"] = error_category

        self._write_entry("api_response", goal, depth, parent_goal, data)

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

        # Load default model from config (single source of truth)
        from config_loader import config
        self.model = config.default_model
        self.config = config  # Store config reference for error handling patterns

        # Entity analyzer for relationship tracking
        self.entity_analyzer = EntityAnalyzer(
            progress_callback=lambda event, msg: logger.info(f"[Entity] {event}: {msg}")
        )

        # Session-level rate limit tracking
        # Sources in this set will be skipped for the rest of the session
        self.rate_limited_sources: set = set()

        # Error classifier for structured error handling
        self.error_classifier = ErrorClassifier(self.config)

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

        Runs an ITERATIVE research loop:
        1. Pursue the main goal
        2. Assess coverage gaps
        3. Generate follow-up goals to fill gaps
        4. Continue until coverage sufficient OR budget exhausted

        Args:
            question: The research question/objective

        Returns:
            GoalResult with all findings
        """
        if not self.registry:
            await self.initialize()

        # Initialize global evidence index for cross-branch sharing
        research_run = ResearchRun()

        context = GoalContext(
            original_objective=question,
            research_run=research_run,
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
        print(f"Max iterations: {self.constraints.max_iterations}")
        print(f"{'='*60}\n")

        # Log run start with enhanced logging
        self.logger.log_run_start(
            objective=question,
            constraints=asdict(self.constraints),
            sources_available=len(self.available_sources)
        )

        # === ITERATIVE RESEARCH LOOP ===
        all_evidence: List[Evidence] = []
        all_sub_results: List[GoalResult] = []
        iteration = 0
        total_cost = 0.0
        start_time = datetime.now()
        coverage: Dict[str, Any] = {}  # Will hold coverage assessment between iterations

        while iteration < self.constraints.max_iterations:
            iteration += 1
            print(f"\n--- Iteration {iteration}/{self.constraints.max_iterations} ---")

            # Check budget constraints
            elapsed = (datetime.now() - start_time).total_seconds()
            if elapsed > self.constraints.max_time_seconds:
                print(f"  ⏱️ Time limit reached ({elapsed:.0f}s > {self.constraints.max_time_seconds}s)")
                break
            if total_cost > self.constraints.max_cost_dollars:
                print(f"  💰 Cost limit reached (${total_cost:.4f} > ${self.constraints.max_cost_dollars})")
                break

            if iteration == 1:
                # First iteration: pursue the main goal
                result = await self.pursue_goal(question, context)
                all_evidence.extend(result.evidence)
                all_sub_results.append(result)
                total_cost += result.cost_dollars
            else:
                # Subsequent iterations: generate and pursue follow-ups
                # Pass coverage reasoning so follow-ups address identified gaps
                follow_ups = await self._generate_follow_ups(
                    question, all_evidence, context,
                    coverage_reasoning=coverage  # From previous iteration
                )
                total_cost += self.constraints.cost_per_follow_up_generation

                if not follow_ups:
                    print("  ✓ No more follow-ups needed - research exhausted")
                    break

                print(f"  📋 Generated {len(follow_ups)} follow-up goals")
                for fu in follow_ups:
                    print(f"    - {fu[:60]}...")

                # Pursue follow-ups (with fresh context but accumulated evidence)
                for follow_up in follow_ups:
                    # Check constraints before each follow-up
                    elapsed = (datetime.now() - start_time).total_seconds()
                    if elapsed > self.constraints.max_time_seconds:
                        break
                    if total_cost > self.constraints.max_cost_dollars:
                        break

                    fu_context = context.with_evidence(all_evidence)
                    fu_result = await self.pursue_goal(follow_up, fu_context)
                    all_evidence.extend(fu_result.evidence)
                    all_sub_results.append(fu_result)
                    total_cost += fu_result.cost_dollars

            # Assess coverage after each iteration - LLM reasons through completeness
            coverage = await self._assess_coverage(question, all_evidence, context)
            total_cost += self.constraints.cost_per_coverage_check

            # Show reasoning-based assessment
            print(f"  📊 Assessment: {len(all_evidence)} evidence from "
                  f"{len(set(e.source for e in all_evidence))} sources")

            if coverage.get('sufficient', False):
                print(f"  ✓ Research exhausted: {coverage.get('reasoning', '')[:80]}...")
                break

            # Show what LLM identified as untried strategies
            gaps = coverage.get('gaps', [])
            if gaps:
                print(f"  🔍 Untried strategies: {', '.join(str(g)[:40] for g in gaps[:3])}")

        # === FINAL SYNTHESIS ===
        print(f"\n--- Final Synthesis ---")
        print(f"Total iterations: {iteration}")
        print(f"Total evidence: {len(all_evidence)}")
        print(f"Total cost: ${total_cost:.4f}")

        # Create final result combining all iterations
        final_result = GoalResult(
            goal=question,
            status=GoalStatus.COMPLETED,
            evidence=all_evidence,
            sub_results=all_sub_results,
            confidence=coverage.get('confidence', 0.5),
            reasoning=coverage.get('reasoning', 'Research completed'),
            depth=0,
            duration_seconds=(datetime.now() - start_time).total_seconds(),
            cost_dollars=total_cost
        )

        # Generate synthesis
        synthesis = await self._synthesize(question, all_sub_results, context)
        final_result.synthesis = synthesis.text if hasattr(synthesis, 'text') else str(synthesis)
        final_result.confidence = synthesis.confidence if hasattr(synthesis, 'confidence') else coverage.get('confidence', 0.5)

        # Log run complete
        self.logger.log_run_complete(
            objective=question,
            status=final_result.status.value,
            total_evidence=len(final_result.evidence),
            total_goals=context.goals_created,
            elapsed_seconds=final_result.duration_seconds,
            total_cost=final_result.cost_dollars
        )

        # Save final result (async for LLM-based report synthesis)
        await self._save_result(final_result)

        return final_result

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
            sub_goals=sub_goals,  # Pass full SubGoal objects (includes dependencies)
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

        # Log dependency groups execution plan
        if len(goal_groups) > 1 or (goal_groups and any(sg.dependencies for sg in goal_groups[0])):
            # Only log if there are multiple groups or dependencies declared
            self.logger.log_dependency_groups(goal, context.depth, parent_goal, goal_groups)

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
            # Skip early exit for comparative/synthesis goals to ensure all dependency groups complete
            goal_appears_comparative = any(
                word in goal.lower()
                for word in ["compare", "vs", "versus", "analysis", "competitive", "contrast",
                            "synthesis", "analyze", "assess", "evaluate"]
            )

            if not goal_appears_comparative:
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

        from core.prompt_loader import render_prompt

        prompt = render_prompt(
            "recursive_agent/goal_assessment.j2",
            temporal_context=_get_temporal_context(),
            original_objective=context.original_objective,
            goal=goal,
            goal_stack=context.goal_stack,
            evidence_text=evidence_text,
            sources_text=sources_text,
            depth=context.depth,
            max_depth=context.constraints.max_depth,
            elapsed_seconds=int(context.elapsed_seconds),
            max_time_seconds=context.constraints.max_time_seconds,
            goals_created=context.goals_created,
            max_goals=context.constraints.max_goals
        )

        try:
            response = await acompletion(
                model=self.model,
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

        # Normalize source name (LLM may return "Brave Search" or "brave_search")
        normalized_id = self.registry.normalize_source_name(source_id)
        if normalized_id:
            source_id = normalized_id

        # Session-level rate limit check: skip sources that hit rate limits earlier
        if source_id in self.rate_limited_sources:
            logger.info(f"{source_id}: Skipping - rate limited earlier in session")
            print(f"    ⏭ {source_id}: Skipped (rate limited)")
            return GoalResult(
                goal=goal,
                status=GoalStatus.FAILED,
                error=f"Source {source_id} rate-limited earlier in session",
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
                # Bug fix: Get API key from registry (was missing, causing 16+ source failures)
                api_key = self.registry.get_api_key(source_id)
                result = await integration.execute_search(
                    current_params,
                    api_key=api_key,
                    limit=context.constraints.max_results_per_source
                )
                response_time_ms = (datetime.now() - start_time).total_seconds() * 1000

                # Classify error if present (for structured logging and error handling)
                error_info = None
                if not result.success and result.error:
                    error_info = self.error_classifier.classify(
                        error_str=str(result.error),
                        http_code=result.http_code,  # Extract HTTP code from QueryResult
                        source_id=source_id
                    )

                    # Log structured error with category and HTTP code
                    logger.warning(
                        f"{source_id}: {error_info.category.value} error "
                        f"(HTTP {error_info.http_code if error_info.http_code else 'N/A'}): {result.error}"
                    )

                # Log API response with structured error info
                self.logger.log_api_response(
                    goal, context.depth, parent_goal,
                    source=source_id,
                    success=result.success,
                    result_count=len(result.results) if result.results else 0,
                    response_time_ms=response_time_ms,
                    error=result.error,
                    http_code=result.http_code if error_info else None,
                    error_category=error_info.category.value if error_info else None
                )

                # If successful or not a validation error, break
                if result.success or not result.error:
                    break

                # Check if error is reformulable (replaces pattern matching)
                if not error_info.is_reformulable:
                    # Log category-specific message
                    if error_info.category == ErrorCategory.RATE_LIMIT:
                        logger.warning(f"{source_id}: Rate limit detected, adding to session blocklist")
                        self.rate_limited_sources.add(source_id)  # Skip this source for rest of session
                        print(f"    ⚠ {source_id}: Rate limited - will skip for rest of session")
                    elif error_info.category == ErrorCategory.TIMEOUT:
                        logger.warning(f"{source_id}: Timeout detected (infrastructure issue), skipping reformulation")
                        print(f"    ⚠ {source_id}: Timeout error - cannot fix with query reformulation")
                    elif error_info.category == ErrorCategory.AUTHENTICATION:
                        logger.warning(f"{source_id}: Authentication error (invalid API key), skipping reformulation")
                        print(f"    ⚠ {source_id}: Auth error - check API key configuration")
                    else:
                        logger.warning(f"{source_id}: {error_info.category.value} error detected, skipping reformulation")
                        print(f"    ⚠ {source_id}: {error_info.category.value} error - cannot fix with query reformulation")

                    break  # Exit retry loop - unreformulable errors can't be fixed by query changes

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

            # Convert to evidence using factory method (Pydantic validation + type safety)
            evidence = []
            if result and result.success and result.results:
                for item in result.results:
                    evidence.append(Evidence.from_dict(item, source_id))

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

                # Add to global research index for cross-branch sharing
                await self._add_to_run_index(evidence, goal, context)

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
        """Analyze existing evidence (includes cross-branch evidence from global index)."""
        from llm_utils import acompletion

        # Try to get relevant evidence from global index (cross-branch sharing)
        global_evidence = []
        if context.research_run:
            try:
                global_evidence = await self._select_relevant_evidence_ids(goal, context)
            except Exception as e:
                logger.warning(f"Global evidence selection failed: {e}, using local evidence only")

        # Merge local + global evidence
        all_evidence = [*context.accumulated_evidence, *global_evidence]

        # Take most recent items up to limit
        evidence_to_analyze = all_evidence[-context.constraints.max_evidence_for_analysis:]

        evidence_text = "\n\n".join([
            f"[{e.source}] {e.title}\n{e.content}"
            for e in evidence_to_analyze
        ])

        prompt = action.prompt or f"Analyze the following evidence to address: {goal}"
        full_prompt = f"{prompt}\n\nEVIDENCE:\n{evidence_text}"

        try:
            response = await acompletion(
                model=self.model,
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
        from core.prompt_loader import render_prompt

        sources_text = "\n".join([
            f"- {s['name']}: {s['description']}"
            for s in context.available_sources[:context.constraints.max_sources_in_decompose]
        ])

        existing_goals = "\n".join([
            f"  - {g}" for g in context.all_goals[-context.constraints.max_goals_in_prompt:]
        ]) or "  (none yet)"

        prompt = render_prompt(
            "recursive_agent/goal_decomposition.j2",
            temporal_context=_get_temporal_context(),
            original_objective=context.original_objective,
            goal=goal,
            decomposition_rationale=context.decomposition_rationale or "Goal is too broad for direct execution",
            goal_stack=context.goal_stack,
            evidence_summary=context.evidence_summary,
            sources_text=sources_text,
            existing_goals=existing_goals,
            remaining_depth=context.constraints.max_depth - context.depth,
            remaining_goals=context.constraints.max_goals - context.goals_created
        )

        try:
            response = await acompletion(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )

            # Track cost
            context.add_cost(context.constraints.cost_per_decomposition)

            result = json.loads(response.choices[0].message.content)

            # Log raw LLM response (to verify dependencies are being returned)
            self.logger.log("llm_decomposition_response", goal, context.depth,
                            context.goal_stack[-2] if len(context.goal_stack) > 1 else None, {
                                "sub_goal_count": len(result.get("sub_goals", [])),
                                "raw_dependencies": [
                                    {
                                        "description": sg.get("description", "")[:60],
                                        "dependencies": sg.get("dependencies", []),
                                        "complexity": sg.get("estimated_complexity", "moderate")
                                    }
                                    for sg in result.get("sub_goals", [])
                                ]
                            })

            sub_goals = []
            for sg_data in result.get("sub_goals", []):
                # Sanitize dependencies - ensure they are integers
                raw_deps = sg_data.get("dependencies", [])
                deps = []
                if isinstance(raw_deps, list):
                    for d in raw_deps:
                        if isinstance(d, int):
                            deps.append(d)
                        elif isinstance(d, str) and d.isdigit():
                            deps.append(int(d))
                        # Skip non-integer dependencies (LLM sometimes returns dicts)

                sub_goals.append(SubGoal(
                    description=sg_data.get("description", ""),
                    rationale=sg_data.get("rationale", ""),
                    dependencies=deps,
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
        from core.prompt_loader import render_prompt

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

        prompt = render_prompt(
            "recursive_agent/achievement_check.j2",
            goal=goal,
            original_objective=context.original_objective,
            results_summary=results_summary,
            total_evidence=total_evidence
        )

        try:
            response = await acompletion(
                model=self.model,
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

    async def _assess_coverage(
        self,
        objective: str,
        evidence: List[Evidence],
        context: GoalContext
    ) -> Dict[str, Any]:
        """
        Reasoning-based assessment of whether research is complete.

        NO arbitrary thresholds. The LLM reasons through:
        1. What types of information SHOULD exist for this objective?
        2. What sources COULD have this information?
        3. What has been tried vs not tried?
        4. Have all reasonable search strategies been exhausted?
        5. What is still missing that could realistically be found?

        Returns dict with:
            - exhausted: bool - whether all reasonable options have been tried
            - confidence: float - confidence in completeness (for reporting only)
            - untried_strategies: list - strategies that haven't been attempted
            - reasoning: str - full reasoning chain
        """
        from llm_utils import acompletion
        from core.prompt_loader import render_prompt

        # Gather context for LLM reasoning
        sources_used = set(e.source for e in evidence)
        sources_not_used = [
            s for s in context.available_sources
            if s['name'] not in sources_used and s['id'] not in {su.lower().replace(' ', '_') for su in sources_used}
        ]

        # Full evidence by source - let LLM decide what's important
        # Philosophy: Give LLM full context, use the context window
        evidence_by_source = {}
        for e in evidence:
            if e.source not in evidence_by_source:
                evidence_by_source[e.source] = []
            evidence_by_source[e.source].append(e.title)

        evidence_summary = "\n".join([
            f"  {source} ({len(titles)} items): {', '.join(titles)}"
            for source, titles in evidence_by_source.items()
        ])

        # All unused sources with full descriptions
        unused_sources_text = "\n".join([
            f"  - {s['name']}: {s['description']}"
            for s in sources_not_used
        ]) or "  (All available sources have been queried)"

        # Rate-limited sources that were attempted but failed
        rate_limited_text = "\n".join([
            f"  - {s}"
            for s in self.rate_limited_sources
        ]) if self.rate_limited_sources else "  (None)"

        prompt = render_prompt(
            "recursive_agent/coverage_assessment.j2",
            objective=objective,
            evidence_count=len(evidence),
            sources_used_count=len(sources_used),
            evidence_summary=evidence_summary,
            unused_sources_text=unused_sources_text,
            rate_limited_text=rate_limited_text
        )

        try:
            response = await acompletion(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )

            result = json.loads(response.choices[0].message.content)

            # Extract for backward compatibility
            reasoning_chain = result.get("reasoning_chain", {})
            return {
                "sufficient": result.get("exhausted", False),
                "confidence": result.get("confidence", 0.5),
                "gaps": reasoning_chain.get("untried_strategies", []),
                "reasoning": result.get("recommendation", ""),
                "full_reasoning": reasoning_chain
            }

        except Exception as e:
            logger.error(f"Coverage assessment failed: {e}")
            return {
                "sufficient": False,
                "confidence": 0.5,
                "gaps": ["Assessment failed - continue research"],
                "reasoning": str(e)
            }

    async def _generate_follow_ups(
        self,
        objective: str,
        evidence: List[Evidence],
        context: GoalContext,
        coverage_reasoning: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """
        Generate strategic follow-up research goals based on reasoning.

        Uses the untried_strategies from coverage assessment to guide follow-ups.
        Focuses on what the LLM reasoned SHOULD be tried next.

        Returns list of follow-up goal descriptions.
        """
        from llm_utils import acompletion
        from core.prompt_loader import render_prompt

        # Summarize what we have
        sources_used = set(e.source for e in evidence)

        # Group evidence by source - full titles, let LLM decide importance
        # Philosophy: Give LLM full context, use the context window
        evidence_by_source = {}
        for e in evidence:
            if e.source not in evidence_by_source:
                evidence_by_source[e.source] = []
            evidence_by_source[e.source].append(e.title)

        evidence_summary = "\n".join([
            f"  {source}: {', '.join(titles)}"
            for source, titles in evidence_by_source.items()
        ])

        # Get ALL entity data from EntityAnalyzer - let LLM decide what's important
        # Philosophy: Give LLM full context, not pre-filtered samples
        entity_graph = self.entity_analyzer.get_entity_graph()

        # Format ALL entities with full context for LLM decision-making
        entity_details = []
        for entity_name, data in entity_graph.items():
            mention_count = data.get("source_count", 0) or len(data.get("evidence", []))
            related = data.get("related_entities", [])
            # Note: evidence is List[str] (quotes/paraphrases), not List[Dict]
            # We can't extract source names from evidence strings
            evidence_list = data.get("evidence", [])
            evidence_count = len(evidence_list) if isinstance(evidence_list, list) else 0

            # Title-case for readability
            display_name = entity_name.title()

            # Build comprehensive entity info for LLM - full context, no truncation
            # Philosophy: Let LLM see all sources and relationships, it can decide importance
            entity_info = f"- {display_name}"
            if mention_count > 0:
                entity_info += f" (mentioned {mention_count}x"
                if evidence_count > 0:
                    entity_info += f", {evidence_count} evidence pieces"
                entity_info += ")"
            if related:
                related_display = [r.title() for r in related]  # Full relationship list
                entity_info += f"\n    Related to: {', '.join(related_display)}"

            entity_details.append(entity_info)

        # Join all entities - let LLM see full picture and decide importance
        entity_section = "\n".join(entity_details) if entity_details else "(None extracted)"

        # Find unused sources
        used_source_ids = {s.lower().replace(" ", "_") for s in sources_used}
        unused_sources = [
            s for s in context.available_sources
            if s['id'].lower() not in used_source_ids
        ]

        unused_sources_text = "\n".join([
            f"  - {s['name']}: {s['description']}"
            for s in unused_sources
        ]) or "  (All sources queried)"

        # Include untried strategies from coverage assessment if available
        untried_strategies = []
        if coverage_reasoning and coverage_reasoning.get("full_reasoning"):
            untried_strategies = coverage_reasoning["full_reasoning"].get("untried_strategies", [])

        untried_text = "\n".join([f"  - {s}" for s in untried_strategies]) if untried_strategies else "  (None identified)"

        prompt = render_prompt(
            "recursive_agent/follow_up_generation.j2",
            objective=objective,
            evidence_count=len(evidence),
            sources_used_count=len(sources_used),
            evidence_summary=evidence_summary,
            entity_section=entity_section,
            untried_text=untried_text,
            unused_sources_text=unused_sources_text
        )

        try:
            response = await acompletion(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )

            result = json.loads(response.choices[0].message.content)

            follow_ups = result.get("follow_ups", [])
            if not follow_ups:
                stop_reason = result.get("stop_reason", "No follow-ups generated")
                logger.info(f"No follow-ups: {stop_reason}")
                return []

            # Log the strategic reasoning
            if result.get("strategic_reasoning"):
                logger.info(f"Follow-up strategy: {result['strategic_reasoning']}")

            return [fu["goal"] for fu in follow_ups if fu.get("goal")]

        except Exception as e:
            logger.error(f"Follow-up generation failed: {e}")
            return []

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
        from core.prompt_loader import render_prompt

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

        # Collect source health for confidence calibration
        sources_with_results = list(set(e.source for e in all_evidence))

        # Extract failed source names by searching goal/error text for known sources
        known_sources = [s['name'] for s in self.available_sources] if self.available_sources else []
        sources_with_errors = []
        for r in sub_results:
            if r.status == GoalStatus.FAILED and r.error:
                # Search for known source names in goal or error text
                search_text = f"{r.goal} {r.error}".lower()
                for source in known_sources:
                    if source.lower() in search_text:
                        sources_with_errors.append(source)
                        break  # Only add first match per failed goal
        sources_with_errors = list(set(sources_with_errors))  # Deduplicate

        prompt = render_prompt(
            "recursive_agent/evidence_synthesis.j2",
            temporal_context=_get_temporal_context(),
            goal=goal,
            original_objective=context.original_objective,
            sub_syntheses=sub_syntheses,
            evidence_count=len(all_evidence),
            evidence_text=evidence_text,
            sources_with_results=sources_with_results,
            sources_with_errors=sources_with_errors,
            rate_limited_sources=list(self.rate_limited_sources)
        )

        try:
            response = await acompletion(
                model=self.model,
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
        from core.prompt_loader import render_prompt

        # Format evidence for evaluation
        evidence_text = "\n\n".join([
            f"Result #{i}:\nTitle: {e.title}\nContent: {e.content[:300]}..."
            for i, e in enumerate(evidence)
        ])

        prompt = render_prompt(
            "recursive_agent/result_filtering.j2",
            temporal_context=_get_temporal_context(),
            original_objective=context.original_objective,
            goal=goal,
            evidence_text=evidence_text
        )

        try:
            response = await acompletion(
                model=self.model,
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
        from core.prompt_loader import render_prompt

        # Batch summarization for efficiency - use sequential indices (0, 1, 2...)
        items_text = "\n\n".join([
            f"Item #{seq_idx}:\nTitle: {e.title}\nContent: {e.content}"
            for seq_idx, orig_idx, e in needs_summary
        ])

        prompt = render_prompt(
            "recursive_agent/result_summarization.j2",
            summary_target_chars=context.constraints.summary_target_chars,
            goal=goal,
            items_text=items_text
        )

        try:
            response = await acompletion(
                model=self.model,
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
                    # Store original in metadata, replace snippet with summary
                    e.metadata["original_content"] = e.content
                    e.snippet = summaries[seq_idx]  # Use snippet (writable), not content (read-only property)
                    summarized_count += 1

            if summarized_count > 0:
                logger.info(f"Summarized {summarized_count} evidence items")

            return evidence

        except Exception as e:
            logger.warning(f"Summarization failed: {e}, keeping original content")
            return evidence

    async def _add_to_run_index(
        self,
        evidence: List[Evidence],
        goal: str,
        context: GoalContext
    ) -> None:
        """
        Add evidence to global research index for cross-branch sharing.

        Thread-safe: Prepares data outside lock, only acquires for atomic writes.

        Args:
            evidence: List of Evidence objects to index
            goal: The goal that produced this evidence
            context: Current goal context (contains goal_stack and research_run)
        """
        import uuid

        # Guard: Skip if no research_run (shouldn't happen, but defensive)
        if not context.research_run:
            return

        # Prepare index entries outside lock (minimize lock-held time)
        entries_to_add = []
        for e in evidence:
            evidence_id = str(uuid.uuid4())
            entry = IndexEntry(
                evidence_id=evidence_id,
                goal=goal,
                source=e.source,
                title=e.title,
                snippet=e.content[:200] if e.content else "",
                goal_ancestry=context.goal_stack.copy()
            )
            entries_to_add.append((evidence_id, entry, e))

        # Acquire lock only for atomic writes
        async with context.research_run.lock:
            for evidence_id, entry, e in entries_to_add:
                context.research_run.index.append(entry)
                context.research_run.evidence_store[evidence_id] = e

    async def _select_relevant_evidence_ids(
        self,
        goal: str,
        context: GoalContext
    ) -> List[Evidence]:
        """
        Select relevant evidence from global index using LLM.

        Shows LLM compact index (title, snippet) and asks it to select
        evidence IDs that are relevant to the current goal.

        Args:
            goal: Current goal being pursued
            context: Current goal context (contains research_run and goal_stack)

        Returns:
            List of Evidence objects from global index
        """
        from llm_utils import acompletion
        from core.prompt_loader import render_prompt
        import json

        # Guard: Return empty if no research_run or empty index
        if not context.research_run or not context.research_run.index:
            return []

        # Slice to last N entries (prevent token overflow)
        max_items = context.research_run.max_index_items_for_selection
        index_entries = context.research_run.index[-max_items:]

        # Convert to dict for template (Jinja needs dict, not dataclass)
        index_dicts = [
            {
                "evidence_id": e.evidence_id,
                "goal": e.goal,
                "source": e.source,
                "title": e.title,
                "snippet": e.snippet,
                "goal_ancestry": e.goal_ancestry
            }
            for e in index_entries
        ]

        # Render prompt
        prompt = render_prompt(
            "deep_research/global_evidence_selection.j2",
            goal=goal,
            goal_ancestry=context.goal_stack,
            local_evidence_count=len(context.accumulated_evidence),
            index_size=len(context.research_run.index),
            index_entries=index_dicts
        )

        # Define JSON schema
        schema = {
            "type": "object",
            "properties": {
                "evidence_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of evidence IDs to include"
                }
            },
            "required": ["evidence_ids"],
            "additionalProperties": False
        }

        # Call LLM
        response = await acompletion(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "strict": True,
                    "name": "global_evidence_selection",
                    "schema": schema
                }
            }
        )

        result = json.loads(response.choices[0].message.content)
        selected_ids = result.get("evidence_ids", [])

        # Track cost for global evidence selection LLM call
        context.add_cost(context.constraints.cost_per_filter)

        # Filter to valid IDs and retrieve evidence
        evidence_list = []
        for evidence_id in selected_ids:
            if evidence_id in context.research_run.evidence_store:
                evidence_list.append(context.research_run.evidence_store[evidence_id])

        # Log global evidence selection
        parent_goal = context.goal_stack[-1] if context.goal_stack else None
        self.logger.log(
            event_type="global_evidence_selection",
            goal=goal,
            depth=context.depth,
            parent_goal=parent_goal,
            data={
                "selected_count": len(evidence_list),
                "total_index_size": len(context.research_run.index),
                "selected_ids": selected_ids
            }
        )

        return evidence_list

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
        from core.prompt_loader import render_prompt

        prompt = render_prompt(
            "recursive_agent/query_reformulation.j2",
            temporal_context=_get_temporal_context(),
            source_id=source_id,
            goal=goal,
            original_params_json=json.dumps(original_params, indent=2),
            error_message=error_message
        )

        try:
            response = await acompletion(
                model=self.model,
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
        """
        Convert GoalResult to serializable dict.

        Three-tier model preservation:
        - raw_content: Full content, never truncated (for reprocessing)
        - content: Truncated content (for backward compatibility)
        - date: Structured date from API
        - metadata: Additional source-specific data
        """
        # Check for evidence truncation and warn
        total_evidence = len(result.evidence)
        max_saved = self.constraints.max_evidence_in_saved_result
        if total_evidence > max_saved:
            truncated_count = total_evidence - max_saved
            logger.warning(
                f"Evidence truncated: {total_evidence} pieces collected, "
                f"only {max_saved} saved to result.json ({truncated_count} dropped). "
                f"Increase max_evidence_in_saved_result to preserve all evidence."
            )
            print(f"  ⚠ Warning: {truncated_count} evidence pieces truncated ({total_evidence} → {max_saved})")

        return {
            "goal": result.goal,
            "status": result.status.value,
            "synthesis": result.synthesis,
            "confidence": result.confidence,
            "evidence_count": len(result.evidence),
            "evidence_saved": min(total_evidence, max_saved),  # NEW: How many actually saved
            "evidence_truncated": max(0, total_evidence - max_saved),  # NEW: How many dropped
            "sub_results_count": len(result.sub_results),
            "depth": result.depth,
            "duration_seconds": result.duration_seconds,
            "cost_dollars": result.cost_dollars,
            "rate_limited_sources": list(self.rate_limited_sources),
            "evidence": [
                {
                    "source": e.source,
                    "title": e.title,
                    # Backward compatible: truncated content for existing tools
                    "content": e.content[:self.constraints.max_content_chars_in_synthesis],
                    "url": e.url,
                    # NEW: Three-tier model fields
                    "raw_content": e.full_content,  # Full content, never truncated
                    "date": e.date,  # Structured date from API
                    "relevance_score": e.relevance_score,  # LLM-assigned score
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

        # Group evidence by source (using to_dict for consistent serialization)
        by_source: Dict[str, List[Dict]] = {}
        for e in result.evidence:
            by_source.setdefault(e.source, []).append(e.to_dict(max_content_length=500))

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

        # Format entity relationships for prompt - give LLM full context
        # Philosophy: Use the full context window, let LLM decide what's important
        entity_relationships = []
        for entity_name, data in entity_graph.items():
            related = data.get("related_entities", [])
            evidence = data.get("evidence", [])
            entity_relationships.append({
                "name": entity_name,
                "related_to": related,  # Full relationship list
                "evidence": evidence  # Full evidence list
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
                entity_relationships=entity_relationships  # Full entity list
            )

            # Call LLM for structured synthesis
            response = await acompletion(
                model=config.get_model("synthesis"),
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )

            synthesis_json = json.loads(response.choices[0].message.content)

            # Log synthesis decisions for debugging (timeline, citations, etc.)
            self._log_synthesis_decisions(synthesis_json, result.goal)

            # Convert JSON to markdown
            report = self._format_synthesis_to_markdown(synthesis_json, result)

            return report

        except Exception as e:
            logger.error(f"FALLBACK TRIGGERED: Report synthesis failed: {e}", exc_info=True)
            # Log to execution log for forensic traceability
            self.logger._write_entry("fallback_triggered", result.goal, 0, None, {
                "fallback_type": "llm_synthesis_to_basic_report",
                "error": str(e),
                "error_type": type(e).__name__,
                "reason": "LLM report synthesis failed, generating basic markdown report"
            })
            return self._generate_basic_report(result, by_source)

    def _log_synthesis_decisions(self, synthesis_json: Dict, objective: str):
        """
        Log synthesis decisions for debugging and forensic analysis.

        Captures timeline items, citation sources, and quality check results
        to help diagnose issues like irrelevant timeline items or missing citations.
        """
        try:
            report_data = synthesis_json.get("report", {})

            # Log timeline decisions
            timeline = report_data.get("timeline", [])
            if timeline:
                logger.info(f"[Synthesis] Timeline has {len(timeline)} events:")
                for item in timeline:
                    event = item.get("event", "")[:60]
                    date = item.get("date", "Unknown")
                    logger.info(f"  - {date}: {event}...")

                # Log to execution log for forensics
                self.logger._write_entry("synthesis_timeline", objective, 0, None, {
                    "timeline_count": len(timeline),
                    "events": [{"date": t.get("date"), "event": t.get("event", "")[:80]} for t in timeline]
                })

            # Log citation quality check
            quality = report_data.get("synthesis_quality_check", {})
            if quality:
                all_cited = quality.get("all_claims_have_citations", False)
                logger.info(f"[Synthesis] All claims cited: {all_cited}")
                if not all_cited:
                    logger.warning("[Synthesis] Some claims may be missing citations!")

                self.logger._write_entry("synthesis_quality", objective, 0, None, {
                    "all_claims_have_citations": all_cited,
                    "source_grouping_reasoning": quality.get("source_grouping_reasoning", ""),
                    "limitations_noted": quality.get("limitations_noted", "")
                })

            # Log source groups
            source_groups = report_data.get("source_groups", [])
            if source_groups:
                logger.info(f"[Synthesis] Report organized into {len(source_groups)} source groups")

        except Exception as e:
            logger.warning(f"Failed to log synthesis decisions: {e}")

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

        # Source Availability (operational metadata - not from LLM synthesis)
        # Surfaces rate-limited sources so users know which sources couldn't be queried
        if self.rate_limited_sources:
            md.append("## Source Availability\n\n")
            md.append("**Rate-Limited Sources:**\n")
            md.append("The following sources hit rate limits during this research session and couldn't be fully queried:\n\n")
            for source in sorted(self.rate_limited_sources):
                md.append(f"- {source}\n")
            md.append("\n*Consider re-running research later when rate limits reset, or check API quota.*\n\n")

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
                if e.get('date'):
                    lines.append(f"  - Date: {e['date']}")
                if e.get('url'):
                    lines.append(f"  - URL: {e['url']}")
                # Only show truncation indicator if content was actually truncated
                content = e['content']
                max_chars = self.constraints.max_content_chars_in_report
                was_truncated = len(content) > max_chars
                display_content = content[:max_chars] + ("..." if was_truncated else "")
                lines.append(f"  - {display_content}")
                lines.append("")

        # Add rate-limited sources section
        if self.rate_limited_sources:
            lines.append("## Source Availability")
            lines.append("")
            lines.append("**Rate-Limited Sources:**")
            for source in sorted(self.rate_limited_sources):
                lines.append(f"- {source}")
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
