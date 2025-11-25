#!/usr/bin/env python3
"""
Simple Deep Research Engine - No framework needed.

Capabilities:
- Task decomposition (LLM breaks complex questions into searches)
- Retry logic (if search fails, reformulate query and retry)
- Entity relationship tracking (connects findings across tasks)
- Live progress streaming (human can course-correct)
- Multi-hour investigations (configurable limits)

Based on BabyAGI concept but simpler - just task queue + your existing code.
"""

import asyncio
import json
import sys
import os
import logging
import time
from typing import List, Dict, Optional, Callable, Any, Tuple
from datetime import datetime
from dataclasses import dataclass, asdict, field
from enum import Enum

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from llm_utils import acompletion
from config_loader import config
from dotenv import load_dotenv
import aiohttp

# Registry import for dynamic tool loading
from integrations.registry import registry

# NOTE: MCP servers exist for external tool access (Claude Desktop integration)
# but deep_research.py calls integrations directly via registry.
# This eliminates the redundant MCP layer for internal use.

# Execution logging
from research.execution_logger import ExecutionLogger

# Jinja2 prompts
from core.prompt_loader import render_prompt

# Mixins for god class decomposition
from research.mixins import (
    EntityAnalysisMixin,
    HypothesisMixin,
    QueryGenerationMixin,
    QueryReformulationMixin,
    ReportSynthesizerMixin,
    ResultFilterMixin,
    SourceExecutorMixin
)

load_dotenv()

# Set up logger for this module
logger = logging.getLogger(__name__)


class ResourceManager:
    """
    Centralized manager for API rate limiting and resource gating.

    Ensures all code paths respect rate limits and prevents concurrent
    access issues with shared state.
    """

    def __init__(self):
        # Global Brave Search lock (1 req/sec limit)
        self.brave_lock = asyncio.Lock()

        # Entity graph lock (prevent concurrent modifications)
        self.entity_graph_lock = asyncio.Lock()

        # Results lock (prevent concurrent modifications)
        self.results_lock = asyncio.Lock()

    # Note: execute_with_rate_limit() removed per Codex recommendation
    # Explicit locks (brave_lock, entity_graph_lock, results_lock) are clearer and sufficient
    # If needed in future, database integrations already have their own rate limiting


class TaskStatus(Enum):
    """Task execution status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRY = "retry"


@dataclass
class ResearchTask:
    """A single research task."""
    id: int
    query: str
    rationale: str
    status: TaskStatus = TaskStatus.PENDING
    parent_task_id: Optional[int] = None
    retry_count: int = 0
    results: Optional[Dict] = None
    error: Optional[str] = None
    entities_found: List[str] = None
    param_adjustments: Dict[str, Dict] = field(default_factory=dict)
    accumulated_results: List[Dict] = field(default_factory=list)  # Priority 2: Accumulate results across attempts
    reasoning_notes: List[Dict] = field(default_factory=list)  # Phase 1: Store LLM reasoning breakdowns
    hypotheses: Optional[Dict] = None  # Phase 3A: Store generated investigative hypotheses
    hypothesis_runs: List[Dict] = field(default_factory=list)  # Phase 3B: Per-hypothesis execution summaries
    metadata: Dict[str, Any] = field(default_factory=dict)  # Phase 3C: Store coverage decisions and other metadata
    # Phase 4A: Task prioritization (Manager Agent)
    priority: int = 5  # 1=highest urgency, 10=lowest (default: medium)
    priority_reasoning: str = ""  # Why this priority level
    estimated_value: int = 50  # Expected information value 0-100
    estimated_redundancy: int = 50  # Expected overlap with existing findings 0-100

    def __post_init__(self):
        if self.entities_found is None:
            self.entities_found = []
        if self.param_adjustments is None:
            self.param_adjustments = {}
        if self.accumulated_results is None:
            self.accumulated_results = []
        if self.reasoning_notes is None:
            self.reasoning_notes = []


@dataclass
class ResearchProgress:
    """Progress update for live streaming."""
    timestamp: str
    event: str  # task_created, task_started, task_completed, task_failed, entity_discovered, etc.
    task_id: Optional[int]
    message: str
    data: Optional[Dict] = None


class SimpleDeepResearch(
    EntityAnalysisMixin,
    HypothesisMixin,
    QueryGenerationMixin,
    QueryReformulationMixin,
    ReportSynthesizerMixin,
    ResultFilterMixin,
    SourceExecutorMixin
):
    """
    Deep research engine with task decomposition and entity tracking.

    No external frameworks - builds on existing AdaptiveSearchEngine.

    Features:
    - Decomposes complex questions into subtasks
    - Retries failed searches with reformulated queries
    - Tracks entity relationships across tasks
    - Streams live progress for human course-correction
    - Configurable limits (max tasks, max time, max retries)

    Mixins:
    - EntityAnalysisMixin: Entity extraction and relationship graph
    - HypothesisMixin: Hypothesis generation and coverage assessment
    - QueryGenerationMixin: Query generation for hypothesis execution
    - QueryReformulationMixin: Query reformulation for improved results
    - ReportSynthesizerMixin: Report synthesis and formatting
    - ResultFilterMixin: Result validation and filtering
    - SourceExecutorMixin: Source and hypothesis execution
    """

    def __init__(
        self,
        max_tasks: Optional[int] = None,
        max_retries_per_task: Optional[int] = None,
        max_time_minutes: Optional[int] = None,
        min_results_per_task: Optional[int] = None,
        max_concurrent_tasks: Optional[int] = None,
        max_queries_per_source: Optional[Dict[str, int]] = None,
        max_time_per_source_seconds: Optional[int] = None,
        progress_callback: Optional[Callable[[ResearchProgress], None]] = None,
        save_output: bool = True,
        output_dir: str = "data/research_output"
    ):
        """
        Initialize deep research engine.

        Args:
            max_tasks: Maximum tasks to execute (prevents infinite loops). Defaults to config or 15.
            max_retries_per_task: Max retries for failed tasks. Defaults to config or 2.
            max_time_minutes: Maximum investigation time. Defaults to config or 120.
            min_results_per_task: Minimum results to consider task successful. Defaults to config or 3.
            max_concurrent_tasks: Maximum tasks to execute in parallel (1 = sequential, 3-5 = parallel). Defaults to config or 4.
            max_queries_per_source: Per-source query limits (e.g., {'SAM.gov': 10, 'Twitter': 3}). Defaults to config or standard limits.
            max_time_per_source_seconds: Maximum time per source (seconds). Defaults to config or 300.
            progress_callback: Function to call with progress updates
            save_output: Whether to automatically save output to files (default: True)
            output_dir: Base directory for saved output (default: data/research_output)
        """
        # Load config with fallbacks
        raw_config = config.get_raw_config()
        deep_config = raw_config.get("research", {}).get("deep_research", {})

        self.max_tasks = max_tasks if max_tasks is not None else deep_config.get("max_tasks", 15)
        self.max_retries_per_task = max_retries_per_task if max_retries_per_task is not None else deep_config.get("max_retries_per_task", 2)
        self.max_time_minutes = max_time_minutes if max_time_minutes is not None else deep_config.get("max_time_minutes", 120)
        self.min_results_per_task = min_results_per_task if min_results_per_task is not None else deep_config.get("min_results_per_task", 3)
        self.max_concurrent_tasks = max_concurrent_tasks if max_concurrent_tasks is not None else deep_config.get("max_concurrent_tasks", 4)

        # Phase 1: Query saturation configuration
        saturation_config = deep_config.get("query_saturation", {})
        self.query_saturation_enabled = saturation_config.get("enabled", False)  # Feature flag
        self.max_queries_per_source = max_queries_per_source or saturation_config.get("max_queries_per_source", {
            'SAM.gov': 10,
            'DVIDS': 5,
            'USAJobs': 5,
            'ClearanceJobs': 5,
            'Twitter': 3,
            'Reddit': 3,
            'Discord': 3,
            'Brave Search': 5
        })
        self.max_time_per_source_seconds = max_time_per_source_seconds if max_time_per_source_seconds is not None else saturation_config.get("max_time_per_source_seconds", 300)

        self.progress_callback = progress_callback
        self.save_output = save_output
        self.output_dir = output_dir

        # Resource management
        self.resource_manager = ResourceManager()

        # State
        self.task_queue: List[ResearchTask] = []
        self.completed_tasks: List[ResearchTask] = []
        self.failed_tasks: List[ResearchTask] = []
        self.entity_graph: Dict[str, List[str]] = {}  # entity -> related entities
        self.results_by_task: Dict[int, Dict] = {}
        self.start_time: Optional[datetime] = None
        self.critical_source_failures: List[str] = []  # Track failed critical sources
        self.rate_limited_sources: set = set()  # Track rate-limited sources (circuit breaker)
        self.logger = None  # Initialized later in research() if save_output=True

        # Hypothesis branching configuration (Phase 3A/3B)
        raw_config = config.get_raw_config()
        hyp_config = raw_config.get("research", {}).get("hypothesis_branching", {})

        # Handle legacy "enabled: true" (Phase 3A) with auto-upgrade
        if "enabled" in hyp_config and "mode" not in hyp_config:
            if hyp_config["enabled"]:
                self.hypothesis_mode = "planning"  # Legacy behavior preserved
                logger.warning("⚠️  hypothesis_branching.enabled is deprecated, use mode: 'planning' instead")
            else:
                self.hypothesis_mode = "off"
        else:
            # New "mode" config (Phase 3B)
            self.hypothesis_mode = hyp_config.get("mode", "off")  # off | planning | execution

        # Backward compatibility: set hypothesis_branching_enabled for existing code
        self.hypothesis_branching_enabled = self.hypothesis_mode in ("planning", "execution")
        self.max_hypotheses_per_task = hyp_config.get("max_hypotheses_per_task", 5)

        # Follow-up generation configuration
        self.max_follow_ups_per_task = deep_config.get("max_follow_ups_per_task", None)  # None = unlimited

        # Phase 4: Manager-Agent configuration (Task Prioritization + Saturation)
        manager_config = raw_config.get("research", {}).get("manager_agent", {})
        self.manager_enabled = manager_config.get("enabled", True)
        self.saturation_detection_enabled = manager_config.get("saturation_detection", True)
        self.saturation_check_interval = manager_config.get("saturation_check_interval", 3)
        self.saturation_confidence_threshold = manager_config.get("saturation_confidence_threshold", 70)
        self.allow_saturation_stop = manager_config.get("allow_saturation_stop", True)
        self.reprioritize_after_task = manager_config.get("reprioritize_after_task", True)
        self.last_saturation_check = None  # Will be set after first saturation check

        # Phase 3C: Coverage assessment configuration
        self.coverage_mode = hyp_config.get("coverage_mode", False)
        self.max_hypotheses_to_execute = hyp_config.get("max_hypotheses_to_execute", 5)
        # Phase 3C time budget for hypothesis execution (OPTIONAL - only used when coverage_mode: true)
        # This is SEPARATE from overall task timeout (task_timeout_seconds)
        # If not specified in config, defaults to 600s when coverage_mode: true, None otherwise
        time_budget = hyp_config.get("max_time_per_task_seconds", None)
        if self.coverage_mode and time_budget is None:
            # Auto-default to 600s when Phase 3C enabled (prevents None comparison crashes)
            self.max_time_per_task_seconds = 600
        else:
            self.max_time_per_task_seconds = time_budget

        # Load tools dynamically from registry (single source of truth)
        self._load_tools_from_registry()

    def _load_tools_from_registry(self):
        """
        Dynamically load all enabled integrations from the registry.

        This replaces hardcoded tool lists with a single source of truth.
        Registry contains all integrations (SAM, DVIDS, SEC EDGAR, Congress, etc.)
        and this method builds the necessary mapping dictionaries.

        Architecture:
        - All integrations loaded from registry (single source of truth)
        - Backward compatibility: Some integrations still use MCP servers
        - New integrations: Called directly through registry (no MCP)
        - Gradual migration: Old integrations will transition to direct calls
        """
        # Initialize data structures
        # NOTE: All name lookups use registry.get_display_name() and registry.normalize_source_name()
        # No parallel data structures needed - registry is single source of truth
        self.integrations = {}  # integration_id -> integration instance
        self.api_keys = {}  # integration_id -> API key from environment

        # NOTE: MCP servers (government_mcp, social_mcp) exist for EXTERNAL tool access
        # (Claude Desktop, etc.) but deep_research.py calls integrations DIRECTLY.
        # This eliminates redundant layer with zero internal benefit.
        #
        # MCP servers are still available at integrations/mcp/ for external use.

        # Build mcp_tools list for backward compatibility
        self.mcp_tools = []
        self.web_tools = []

        # Load all enabled integrations from registry
        enabled_integrations = registry.get_all_enabled()

        for integration_id, integration in enabled_integrations.items():
            metadata = integration.metadata

            # Store integration instance for direct access
            self.integrations[integration_id] = integration

            # Get API key from registry (uses api_key_env_var from metadata)
            self.api_keys[integration_id] = registry.get_api_key(integration_id)

            # Build tool config - all integrations use same structure now
            tool_config = {
                "name": integration_id,
                "server": None,  # ALL use direct integration calls
                "api_key_name": integration_id if metadata.requires_api_key else None,
                "integration_id": integration_id
            }

            # All tools go in mcp_tools now (web_tools distinction eliminated)
            self.mcp_tools.append(tool_config)

        # Log what was loaded
        logger.info(f"✅ Loaded {len(self.integrations)} integrations from registry (all use direct calls)")

        for integration_id, integration in self.integrations.items():
            display_name = registry.get_display_name(integration_id)
            api_key = self.api_keys.get(integration_id)
            api_status = "🔑" if integration.metadata.requires_api_key else "🆓"
            key_status = "✓" if api_key else "✗" if integration.metadata.requires_api_key else ""
            logger.info(f"  {api_status}{key_status} {display_name} ({integration_id})")

    def _emit_progress(self, event: str, message: str, task_id: Optional[int] = None, data: Optional[Dict] = None):
        """Emit progress update for live streaming."""
        progress = ResearchProgress(
            timestamp=datetime.now().isoformat(),
            event=event,
            task_id=task_id,
            message=message,
            data=data
        )

        if self.progress_callback:
            self.progress_callback(progress)

        # Always print to console for visibility
        print(f"[{progress.timestamp}] {event.upper()}: {message}")
        if data:
            print(f"  Data: {json.dumps(data, indent=2)}")

    def _check_time_limit(self) -> bool:
        """Check if time limit exceeded."""
        if not self.start_time:
            return False

        elapsed = (datetime.now() - self.start_time).total_seconds() / 60
        return elapsed >= self.max_time_minutes


    def _display_cost_estimate(self):
        """Display estimated LLM call count and cost before starting research."""
        # Load estimation parameters from config (user-configurable, not hardcoded)
        raw_config = config.get_raw_config()
        deep_config = raw_config.get("research", {}).get("deep_research", {})
        cost_config = deep_config.get("cost_estimation", {})

        # All estimation parameters come from config with sensible defaults
        avg_tasks = min(5, self.max_tasks)  # Typically 3-5 tasks decomposed
        avg_hypotheses_per_task = cost_config.get("avg_hypotheses_per_task", 4)
        avg_sources_per_hypothesis = cost_config.get("avg_sources_per_hypothesis", 6)
        avg_queries_per_source = cost_config.get("avg_queries_per_source", 5)
        avg_cost_per_call = cost_config.get("avg_cost_per_llm_call", 0.0005)

        # LLM call breakdown
        task_decomposition = 1
        manager_calls = avg_tasks  # Re-prioritize after each task
        hypothesis_generation = avg_tasks

        # Query generation + saturation: Each source execution involves multiple query cycles
        # Per source: initial query (1) + (avg_queries_per_source * 2 LLM calls per cycle)
        # Each cycle: saturation check (1) + next query gen (1) = 2 calls
        source_executions = avg_tasks * avg_hypotheses_per_task * avg_sources_per_hypothesis
        calls_per_source = avg_queries_per_source * 2  # Rough estimate
        query_and_saturation_total = source_executions * calls_per_source

        relevance_filtering = avg_tasks * avg_hypotheses_per_task
        coverage_assessment = avg_tasks
        follow_up_generation = avg_tasks
        entity_extraction = avg_tasks
        entity_filtering = 1
        synthesis = 1

        total_estimated_calls = (
            task_decomposition + manager_calls + hypothesis_generation +
            query_and_saturation_total + relevance_filtering +
            coverage_assessment + follow_up_generation + entity_extraction +
            entity_filtering + synthesis
        )

        # Cost estimation based on config
        estimated_cost = total_estimated_calls * avg_cost_per_call

        print("\n" + "="*60)
        print("📊 ESTIMATED RESEARCH SCOPE")
        print("="*60)
        print(f"Expected LLM calls: ~{total_estimated_calls:,}")
        print(f"Breakdown:")
        print(f"  • Query generation & saturation: ~{query_and_saturation_total:,}")
        print(f"  • Hypothesis generation: ~{hypothesis_generation}")
        print(f"  • Task management: ~{manager_calls + coverage_assessment + follow_up_generation}")
        print(f"  • Analysis & synthesis: ~{relevance_filtering + entity_extraction + entity_filtering + synthesis}")
        print(f"\nEstimated cost: ${estimated_cost:.2f} - ${estimated_cost * 2:.2f}")
        print(f"(Varies with query complexity, saturation behavior, and actual task count)")
        print(f"\nTime budget: {self.max_time_minutes} minutes")
        print(f"Task limit: {self.max_tasks} tasks")
        print(f"Avg queries per source: {avg_queries_per_source} (with new saturation logic)")
        print("="*60 + "\n")

    async def research(self, question: str) -> Dict:
        """
        Conduct deep research on complex question.

        Flow:
        1. Decompose question into initial tasks
        2. Execute tasks (with retries if needed)
        3. Create follow-up tasks based on findings
        4. Track entity relationships
        5. Synthesize final report

        Args:
            question: Complex research question

        Returns:
            Dict with:
            - report: Synthesized report (markdown)
            - tasks_executed: Number of tasks completed
            - entities_discovered: List of entities found
            - entity_relationships: Dict of entity connections
            - sources_searched: List of unique sources
            - total_results: Total results found
        """
        self.start_time = datetime.now()
        self.original_question = question  # Store for entity extraction context
        self.research_question = question  # Store for follow-up generation and hypothesis calls

        # Initialize execution logger (only if save_output is True)
        if self.save_output:
            # Create research_id: YYYY-MM-DD_HH-MM-SS_query_slug
            import re
            timestamp = self.start_time.strftime("%Y-%m-%d_%H-%M-%S")
            slug = re.sub(r'[^a-z0-9]+', '_', question.lower())[:50].strip('_')
            research_id = f"{timestamp}_{slug}"

            # Create output directory for this research run
            from pathlib import Path
            output_dir = Path(self.output_dir) / research_id
            output_dir.mkdir(parents=True, exist_ok=True)

            # Initialize logger
            self.logger = ExecutionLogger(research_id=research_id, output_dir=str(output_dir))

            # Log run start
            config_dict = {
                "max_tasks": self.max_tasks,
                "max_retries_per_task": self.max_retries_per_task,
                "max_time_minutes": self.max_time_minutes,
                "min_results_per_task": self.min_results_per_task,
                "max_concurrent_tasks": self.max_concurrent_tasks
            }
            self.logger.log_run_start(original_question=question, config=config_dict)
        else:
            self.logger = None

        self._emit_progress("research_started", f"Starting deep research: {question}")

        # Display cost estimate before starting
        self._display_cost_estimate()

        # Step 1: Decompose question into initial tasks
        try:
            self._emit_progress("decomposition_started", "Breaking question into research tasks...")
            self.task_queue = await self._decompose_question(question)
            self._emit_progress(
                "decomposition_complete",
                f"Created {len(self.task_queue)} initial tasks",
                data={"tasks": [{"id": t.id, "query": t.query} for t in self.task_queue]}
            )
        # Critical failure - task decomposition is required to proceed
        except Exception as e:
            # Critical failure - task decomposition is required to proceed
            import traceback
            logger.error(f"Failed to decompose question: {type(e).__name__}: {str(e)}", exc_info=True)
            error_msg = f"Failed to decompose question: {type(e).__name__}: {str(e)}"
            self._emit_progress(
                "decomposition_failed",
                error_msg,
                data={
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "traceback": traceback.format_exc()
                }
            )
            # Return empty result on decomposition failure
            return {
                "report": f"# Research Failed\n\nFailed to decompose question into tasks.\n\nError: {error_msg}",
                "tasks_executed": 0,
                "tasks_failed": 0,
                "entities_discovered": [],
                "entity_relationships": {},
                "sources_searched": [],
                "total_results": 0,
                "elapsed_minutes": 0,
                "error": error_msg
            }

        # Step 2: Execute tasks (parallel batch execution)
        task_counter = len(self.task_queue)

        while self.task_queue and len(self.completed_tasks) < self.max_tasks:
            # Check time limit
            if self._check_time_limit():
                self._emit_progress(
                    "time_limit_reached",
                    f"Time limit reached ({self.max_time_minutes} minutes)"
                )
                break

            # Phase 4B: Check saturation if enabled
            if (self.saturation_detection_enabled and
                len(self.completed_tasks) >= 3 and
                len(self.completed_tasks) % self.saturation_check_interval == 0):

                saturation_check = await self._is_saturated()
                self.last_saturation_check = saturation_check  # Store for checkpointing

                # Log saturation check
                if self.logger:
                    try:
                        self.logger.log_saturation_assessment(
                            completed_tasks=len(self.completed_tasks),
                            saturation_result=saturation_check
                        )
                    # Logging failure - non-critical, execution continues
                    except Exception as log_error:
                        logger.warning(f"Failed to log saturation assessment: {log_error}", exc_info=True)

                # Act on saturation decision (if stopping allowed)
                if (self.allow_saturation_stop and
                    saturation_check["saturated"] and
                    saturation_check["confidence"] >= self.saturation_confidence_threshold):

                    self._emit_progress(
                        "research_saturated",
                        f"Research saturated: {saturation_check['rationale']}",
                        data=saturation_check
                    )
                    print(f"\n✅ Research saturated - stopping investigation")
                    print(f"   Confidence: {saturation_check['confidence']}%")
                    print(f"   Threshold: {self.saturation_confidence_threshold}%")
                    print(f"   Completed: {len(self.completed_tasks)} tasks")
                    break
                elif saturation_check["recommendation"] == "continue_limited":
                    # Adjust max_tasks dynamically based on recommendation
                    recommended_total = len(self.completed_tasks) + saturation_check["recommended_additional_tasks"]
                    if recommended_total < self.max_tasks:
                        print(f"\n📊 Saturation approaching - limiting scope:")
                        print(f"   Original max_tasks: {self.max_tasks}")
                        print(f"   Recommended: {recommended_total} tasks")
                        print(f"   Rationale: {saturation_check['rationale']}")
                        self.max_tasks = recommended_total

            # Get batch of tasks (up to max_concurrent_tasks)
            batch_size = min(self.max_concurrent_tasks, len(self.task_queue))
            batch = [self.task_queue.pop(0) for _ in range(batch_size)]

            # Emit batch start
            self._emit_progress(
                "batch_started",
                f"Executing batch of {batch_size} tasks in parallel",
                data={"tasks": [{"id": t.id, "query": t.query} for t in batch]}
            )

            # Emit task_started for each task before parallel execution
            for task in batch:
                task.status = TaskStatus.IN_PROGRESS
                self._emit_progress("task_started", f"Executing: {task.query}", task_id=task.id)
                # Track selected sources on the task for later logging
                if hasattr(task, "selected_sources"):
                    task.selected_sources = list(set(task.selected_sources or []))

            # Timeout wraps entire task execution including all retry attempts
            # Single source of truth: deep_research.task_timeout_seconds
            raw_config = config.get_raw_config()
            deep_config = raw_config.get("research", {}).get("deep_research", {})
            task_timeout = deep_config.get("task_timeout_seconds", 600)

            results = await asyncio.gather(*[
                asyncio.wait_for(
                    self._execute_task_with_retry(task),
                    timeout=task_timeout
                )
                for task in batch
            ], return_exceptions=True)

            # Process results
            for task, success_or_exception in zip(batch, results):
                # Handle timeout exceptions
                if isinstance(success_or_exception, asyncio.TimeoutError):
                    error_msg = f"Task timed out after {task_timeout} seconds"
                    self._emit_progress(
                        "task_timeout",
                        error_msg,
                        task_id=task.id
                    )
                    task.status = TaskStatus.FAILED
                    task.error = error_msg
                    self.failed_tasks.append(task)
                    # Persist partial results if any
                    if self.logger and task.accumulated_results:
                        from pathlib import Path
                        raw_path = Path(self.logger.output_dir) / "raw"
                        raw_path.mkdir(exist_ok=True)
                        raw_file = raw_path / f"task_{task.id}_results.json"
                        accumulated_dict = {
                            "total_results": len(task.accumulated_results),
                            "results": task.accumulated_results,
                            "accumulated_count": len(task.accumulated_results),
                            "entities_discovered": [],
                            "sources": self._get_sources(task.accumulated_results)
                        }
                        try:
                            with open(raw_file, 'w', encoding='utf-8') as f:
                                json.dump(accumulated_dict, f, indent=2, ensure_ascii=False)
                            logger.info(f"Task {task.id} timed out; persisted partial results ({len(task.accumulated_results)}) to {raw_file}")
                        # Persistence failure - non-critical, data may be lost but execution continues
                        except Exception as persist_error:
                            logger.warning(f"Failed to persist partial results for timed-out task {task.id}: {persist_error}", exc_info=True)
                    # Log timeout as a task completion record
                    if self.logger:
                        try:
                            self.logger.log_task_complete(
                                task_id=task.id,
                                query=task.query,
                                status="TIMEOUT",
                                reason=error_msg,
                                total_results=len(task.accumulated_results),
                                sources_tried=list(set(getattr(task, "selected_sources", []) or [])),
                                sources_succeeded=self._get_sources(task.accumulated_results),
                                retry_count=task.retry_count,
                                elapsed_seconds=task_timeout
                            )
                        # Logging failure - non-critical, execution continues
                        except Exception as log_error:
                            logger.warning(f"Failed to log task timeout for task {task.id}: {log_error}", exc_info=True)
                    continue

                # Handle other exceptions
                if isinstance(success_or_exception, Exception):
                    self._emit_progress(
                        "task_exception",
                        f"Task {task.id} threw exception: {type(success_or_exception).__name__}: {str(success_or_exception)}",
                        task_id=task.id
                    )
                    task.status = TaskStatus.FAILED
                    task.error = str(success_or_exception)
                    self.failed_tasks.append(task)
                    # Persist partial results if any
                    if self.logger and task.accumulated_results:
                        from pathlib import Path
                        raw_path = Path(self.logger.output_dir) / "raw"
                        raw_path.mkdir(exist_ok=True)
                        raw_file = raw_path / f"task_{task.id}_results.json"
                        accumulated_dict = {
                            "total_results": len(task.accumulated_results),
                            "results": task.accumulated_results,
                            "accumulated_count": len(task.accumulated_results),
                            "entities_discovered": [],
                            "sources": self._get_sources(task.accumulated_results)
                        }
                        try:
                            with open(raw_file, 'w', encoding='utf-8') as f:
                                json.dump(accumulated_dict, f, indent=2, ensure_ascii=False)
                            logger.info(f"Task {task.id} exception; persisted partial results ({len(task.accumulated_results)}) to {raw_file}")
                        # Persistence failure - non-critical, data may be lost but execution continues
                        except Exception as persist_error:
                            logger.warning(f"Failed to persist partial results for errored task {task.id}: {persist_error}", exc_info=True)
                    # Log exception as task completion record
                    if self.logger:
                        try:
                            self.logger.log_task_complete(
                                task_id=task.id,
                                query=task.query,
                                status="FAILED",
                                reason=f"Exception: {type(success_or_exception).__name__}: {str(success_or_exception)}",
                                total_results=len(task.accumulated_results),
                                sources_tried=list(set(getattr(task, "selected_sources", []) or [])),
                                sources_succeeded=self._get_sources(task.accumulated_results),
                                retry_count=task.retry_count,
                                elapsed_seconds=0
                            )
                        # Logging failure - non-critical, execution continues
                        except Exception as log_error:
                            logger.warning(f"Failed to log task exception for task {task.id}: {log_error}", exc_info=True)
                    continue

                success = success_or_exception

                if success:
                    self.completed_tasks.append(task)

                    # Gap #4 Fix: Entity extraction OUTSIDE timeout boundary with error handling
                    # Extract from accumulated results (all retries combined)
                    # Wrapped in try/except so entity extraction errors don't retroactively fail the task
                    if task.accumulated_results:
                        try:
                            print(f"🔍 Extracting entities from {len(task.accumulated_results)} accumulated results...")
                            entities_found = await self._extract_entities(
                                task.accumulated_results,
                                research_question=self.original_question,
                                task_query=task.query
                            )
                            task.entities_found = entities_found
                            print(f"✓ Found {len(entities_found)} entities: {', '.join(entities_found[:5])}{'...' if len(entities_found) > 5 else ''}")

                            # Update entity graph with found entities
                            await self._update_entity_graph(entities_found)
                        # Entity extraction failure - non-critical, task can continue without entities
                        except Exception as entity_error:
                            # Log error but don't fail task - entity extraction is non-critical
                            logger.error(
                                f"Entity extraction failed for task {task.id}: {type(entity_error).__name__}: {str(entity_error)}",
                                exc_info=True
                            )
                            print(f"⚠️  Entity extraction failed (non-critical): {type(entity_error).__name__}: {str(entity_error)}")
                            # Task remains COMPLETED despite entity extraction failure
                            task.entities_found = []  # Empty list instead of None

                    # Check if we should create follow-up tasks
                    # NOTE: Codex fix - check TOTAL workload, not just completed tasks
                    total_pending_workload = len(self.task_queue) + len(batch) - (batch.index(task) + 1)
                    if self._should_create_follow_ups(task, total_pending_workload):
                        follow_ups = await self._create_follow_up_tasks(task, task_counter)

                        # Phase 3A: Generate hypotheses for follow-ups if branching enabled
                        if self.hypothesis_branching_enabled and follow_ups:
                            print(f"\n🔬 Generating hypotheses for {len(follow_ups)} follow-up task(s)...")
                            for follow_up in follow_ups:
                                try:
                                    hypotheses_result = await self._generate_hypotheses(
                                        task_query=follow_up.query,
                                        research_question=self.research_question,
                                        all_tasks=self.tasks,
                                        existing_hypotheses=[]  # New follow-up, no existing hypotheses yet
                                    )
                                    follow_up.hypotheses = hypotheses_result
                                    print(f"   ✓ Follow-up {follow_up.id}: Generated {len(hypotheses_result['hypotheses'])} hypothesis/hypotheses")
                                # LLM call failed - hypothesis generation is optional, can proceed without
                                except Exception as e:
                                    print(f"   ⚠️  Follow-up {follow_up.id}: Hypothesis generation failed - {type(e).__name__}: {e}")
                                    logger.warning(f"Hypothesis generation failed for follow-up {follow_up.id}: {type(e).__name__}: {e}", exc_info=True)
                                    # Continue without hypotheses - don't fail follow-up creation
                                    follow_up.hypotheses = None

                        task_counter += len(follow_ups)
                        self.task_queue.extend(follow_ups)
                        self._emit_progress(
                            "follow_ups_created",
                            f"Created {len(follow_ups)} follow-up tasks",
                            task_id=task.id,
                            data={
                                "follow_ups": [
                                    {
                                        "id": t.id,
                                        "query": t.query,
                                        "rationale": t.rationale,
                                        "parent_task_id": t.parent_task_id
                                    } for t in follow_ups
                                ]
                            }
                        )

                        # Phase 4A: Reprioritize queue after adding follow-ups (if enabled)
                        if self.reprioritize_after_task and len(self.task_queue) > 1:
                            print(f"\n🎯 Reprioritizing {len(self.task_queue)} pending tasks based on new findings...")
                            self.task_queue = await self._prioritize_tasks(
                                self.task_queue,
                                global_coverage_summary=self._generate_global_coverage_summary()
                            )
                            if self.task_queue:
                                print(f"   Next: P{self.task_queue[0].priority} - Task {self.task_queue[0].id}: {self.task_queue[0].query[:60]}...")
                else:
                    self.failed_tasks.append(task)

            # Emit batch complete
            successful_in_batch = sum(1 for r in results if r is True)
            self._emit_progress(
                "batch_complete",
                f"Batch complete: {successful_in_batch}/{batch_size} succeeded",
                data={
                    "successful": successful_in_batch,
                    "failed": batch_size - successful_in_batch
                }
            )

        # Step 3: Synthesize report
        try:
            self._emit_progress("synthesis_started", "Synthesizing final report...")
            report = await self._synthesize_report(question)
            self._emit_progress("synthesis_complete", "Report complete")
        # Critical failure - report synthesis is the final output
        except Exception as e:
            # Critical failure - report synthesis is the final output
            import traceback
            logger.error(f"Failed to synthesize report: {type(e).__name__}: {str(e)}", exc_info=True)
            error_msg = f"Failed to synthesize report: {type(e).__name__}: {str(e)}"
            self._emit_progress(
                "synthesis_failed",
                error_msg,
                data={
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "traceback": traceback.format_exc()
                }
            )
            report = f"# Research Report\n\nFailed to synthesize final report.\n\nError: {error_msg}\n\n## Raw Statistics\n\n- Tasks Executed: {len(self.completed_tasks)}\n- Tasks Failed: {len(self.failed_tasks)}\n"

        # Compile results
        all_results = []
        for results in self.results_by_task.values():
            all_results.extend(results.get('results', []))

        all_entities = set()
        for task in self.completed_tasks:
            # Codex Fix: Normalize entity names to lowercase before adding (same as entity_graph)
            # This prevents "Federal Government" and "Federal government" from appearing as separate entities
            normalized = [e.strip().lower() for e in task.entities_found if e.strip()]
            all_entities.update(normalized)

        # Task 2: Entity filtering moved to LLM-based synthesis (removed Python blacklist)

        # Compile failure details for debugging
        failure_details = []
        for task in self.failed_tasks:
            failure_details.append({
                "task_id": task.id,
                "query": task.query,
                "error": task.error,
                "retry_count": task.retry_count
            })

        result = {
            "report": report,
            "tasks_executed": len(self.completed_tasks),
            "tasks_failed": len(self.failed_tasks),
            "failure_details": failure_details,  # NEW: Detailed failure info
            "entities_discovered": list(all_entities),
            "entity_relationships": self.entity_graph,
            "sources_searched": list(set(r.get('source', 'Unknown') for r in all_results)),
            "total_results": len(all_results),
            "elapsed_minutes": (datetime.now() - self.start_time).total_seconds() / 60
        }

        # If we have merged tasks from raw files but no explicit completion records, infer sources_used
        inferred_sources = list(set(r.get('source', 'Unknown') for r in all_results if r.get('source')))
        if not result["sources_searched"] and inferred_sources:
            result["sources_searched"] = inferred_sources

        # Save output to files if enabled
        if self.save_output:
            try:
                output_path = self._save_research_output(question, result)
                result["output_directory"] = output_path
                print(f"\n💾 Research output saved to: {output_path}")
            # Output persistence failure - non-critical, research completed
            except Exception as e:
                logger.error(f"Failed to save research output: {type(e).__name__}: {str(e)}", exc_info=True)
                import traceback
                logger.error(traceback.format_exc(), exc_info=True)
                # Attempt a minimal fallback save to preserve artifacts
                try:
                    from pathlib import Path
                    import json as _json
                    slug = "fallback_" + datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                    output_path = Path(self.output_dir) / slug
                    output_path.mkdir(parents=True, exist_ok=True)
                    # Minimal report
                    report_file = output_path / "report.md"
                    report_file.write_text(result.get("report", "Report unavailable due to save error."), encoding="utf-8")
                    # Minimal results
                    results_file = output_path / "results.json"
                    _json.dump(result, results_file.open("w", encoding="utf-8"), indent=2, ensure_ascii=False)
                    # Minimal metadata
                    metadata_file = output_path / "metadata.json"
                    _json.dump({"error": f"{type(e).__name__}: {str(e)}", "research_question": question}, metadata_file.open("w", encoding="utf-8"), indent=2, ensure_ascii=False)
                    result["output_directory"] = str(output_path)
                    print(f"\n⚠️  Partial output saved to: {output_path}")
                # LLM fallback model failure - expected possibility, try next model in chain
                except Exception as fallback_error:
                    logger.error(f"Fallback save failed: {type(fallback_error).__name__}: {fallback_error}", exc_info=True)

        # Log run completion
        if self.logger:
            self.logger.log_run_complete(
                original_question=question,
                tasks_executed=len(self.completed_tasks),
                tasks_failed=len(self.failed_tasks),
                total_results=len(all_results),
                sources_searched=result["sources_searched"],
                elapsed_minutes=result["elapsed_minutes"],
                report_path=result.get("output_directory", "")
            )

        return result

    async def _decompose_question(self, question: str) -> List[ResearchTask]:
        """Use LLM to break question into 3-5 initial research tasks."""
        prompt = render_prompt(
            "deep_research/task_decomposition.j2",
            question=question
        )

        schema = {
            "type": "object",
            "properties": {
                "tasks": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Search query"},
                            "rationale": {"type": "string", "description": "Why this task matters"}
                        },
                        "required": ["query", "rationale"],
                        "additionalProperties": False
                    },
                    "minItems": 3,
                    "maxItems": 5
                }
            },
            "required": ["tasks"],
            "additionalProperties": False
        }

        response = await acompletion(
            model=config.get_model("query_generation"),
            messages=[{"role": "user", "content": prompt}],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "strict": True,
                    "name": "research_task_decomposition",
                    "schema": schema
                }
            }
        )

        result = json.loads(response.choices[0].message.content)

        tasks = []
        for i, task_data in enumerate(result["tasks"]):
            task = ResearchTask(
                id=i,
                query=task_data["query"],
                rationale=task_data["rationale"]
            )
            tasks.append(task)
            self._emit_progress("task_created", f"Task {i}: {task.query}", task_id=i)

        # Phase 3A: Generate hypotheses if enabled
        if self.hypothesis_branching_enabled:
            print(f"\n🔬 Hypothesis branching enabled - generating investigative hypotheses for {len(tasks)} tasks...")
            for task in tasks:
                try:
                    hypotheses_result = await self._generate_hypotheses(
                        task_query=task.query,
                        research_question=question,
                        all_tasks=tasks,  # Pass all tasks for diversity across tasks
                        existing_hypotheses=[]  # New task, no existing hypotheses yet
                    )
                    task.hypotheses = hypotheses_result
                    print(f"   ✓ Task {task.id}: Generated {len(hypotheses_result['hypotheses'])} hypothesis/hypotheses")
                # LLM call failed - hypothesis generation is optional, can proceed without
                except Exception as e:
                    # LLM call failed - hypothesis generation is optional, can proceed without
                    logger.warning(f"Hypothesis generation failed for task {task.id}: {type(e).__name__}: {e}", exc_info=True)
                    print(f"   ⚠️  Task {task.id}: Hypothesis generation failed - {type(e).__name__}: {e}")
                    # Continue without hypotheses - don't fail task creation
                    task.hypotheses = None

        # Phase 4A: Prioritize initial tasks (if manager enabled)
        if self.manager_enabled:
            print(f"\n🎯 Prioritizing {len(tasks)} initial tasks...")
            tasks = await self._prioritize_tasks(tasks, global_coverage_summary="Initial decomposition - no completed tasks yet")
            print(f"   Execution order: {', '.join([f'P{t.priority}(T{t.id})' for t in tasks])}")
        else:
            print(f"\n⏭️  Task prioritization disabled - using FIFO order")

        return tasks


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
        - Resource efficiency (simple vs complex queries)
        - Strategic value (unlocks follow-ups, validates findings)

        Args:
            tasks: List of pending tasks to prioritize
            global_coverage_summary: Optional global coverage context

        Returns:
            Same tasks with updated priority/reasoning fields, sorted by priority
        """
        if not tasks:
            return tasks

        if len(tasks) == 1:
            # Single task - no prioritization needed
            tasks[0].priority = 1
            tasks[0].priority_reasoning = "Only pending task"
            tasks[0].estimated_value = 70
            tasks[0].estimated_redundancy = 30
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
                "assessment": latest_coverage.get("assessment", "No assessment available"),
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
        total_unique = sum(len(t.accumulated_results) for t in self.completed_tasks)
        total_fetched_estimate = total_unique  # Conservative estimate (will be higher with raw data)
        # Try to get actual fetched count from results_by_task
        for task_id, result_dict in self.results_by_task.items():
            if "accumulated_count" in result_dict:
                # More accurate if available
                total_fetched_estimate = max(total_fetched_estimate, result_dict["accumulated_count"])

        dedup_rate = 0  # Default
        if total_unique > 0 and total_fetched_estimate > total_unique:
            dedup_rate = int((1 - total_unique / total_fetched_estimate) * 100)

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
            print(f"   Global: {result['global_coverage_assessment'][:120]}...")
            for task in sorted(tasks, key=lambda t: t.priority):
                print(f"   P{task.priority}: Task {task.id} - {task.query[:50]}...")
                print(f"       Value: {task.estimated_value}%, Redundancy: {task.estimated_redundancy}%")
                print(f"       Why: {task.priority_reasoning[:90]}...")

            # Sort tasks by priority (ascending - P1 executes first)
            tasks.sort(key=lambda t: (t.priority, t.id))

            return tasks

        # Task prioritization failure - acceptable to fall back to FIFO order
        except Exception as e:
            logger.error(f"Task prioritization failed: {type(e).__name__}: {e}", exc_info=True)
            print(f"⚠️  Prioritization failed, using default priority order")
            import traceback
            logger.error(traceback.format_exc(), exc_info=True)
            # On error, return tasks as-is (FIFO order)
            return tasks

    def _fuzzy_match_source(self, llm_name: str) -> Optional[str]:
        """
        Fuzzy match LLM-generated source name to registered source.

        Uses registry.normalize_source_name() which is the SINGLE source of truth
        for all source name normalization. Handles:
        - Integration IDs: "usaspending" → "usaspending"
        - Display names: "USASpending" → "usaspending"
        - Case variations: "GOVINFO" → "govinfo"
        - Common suffixes: "USASpending.gov" → "usaspending"

        Args:
            llm_name: Source name from LLM (any format)

        Returns:
            Matched integration_id, or None if no match
        """
        # Use registry's normalize function (single source of truth)
        return registry.normalize_source_name(llm_name)

    def _map_hypothesis_sources(self, hypothesis: Dict) -> List[str]:
        """
        Map hypothesis source display names to MCP tool names (Phase 3B).

        Args:
            hypothesis: Hypothesis dict with search_strategy.sources (display names)

        Returns:
            List of integration IDs (e.g., ["usajobs", "twitter"])

        Logs errors for unknown sources and skips them.
        """
        display_sources = hypothesis.get("search_strategy", {}).get("sources", [])
        tool_names = []

        for display_name in display_sources:
            # Try fuzzy matching (handles "USASpending.gov" → "USAspending")
            tool_name = self._fuzzy_match_source(display_name)
            if tool_name:
                tool_names.append(tool_name)
            else:
                logger.warning(f"⚠️  Hypothesis {hypothesis.get('id', '?')} specified unknown source '{display_name}' - skipping")

        return tool_names

    def _deduplicate_with_attribution(self, results: List[Dict], hypothesis_id: int) -> List[Dict]:
        """
        Deduplicate results with multi-attribution tracking (Phase 3B).

        Results from hypotheses may duplicate existing task results.
        Multi-tag duplicates with hypothesis_ids=[1,2,3] to show validation.

        Args:
            results: New results from hypothesis execution
            hypothesis_id: Current hypothesis ID (for tagging)

        Returns:
            Deduplicated results with multi-attribution tags
        """
        # For each new result, check if URL already exists in task.accumulated_results
        # If exists: Add hypothesis_id to existing result's hypothesis_ids array
        # If new: Tag with hypothesis_id field

        # Use dict for O(1) URL lookup instead of O(n) linear search
        url_to_result = {}  # Maps URL -> result dict
        deduplicated = []

        for result in results:
            url = result.get("url")
            if not url:
                # No URL to deduplicate on, keep as-is
                result["hypothesis_id"] = hypothesis_id
                deduplicated.append(result)
                continue

            # Check for duplicate URL in current batch (O(1) dict lookup)
            existing = url_to_result.get(url)

            if existing:
                # Duplicate within batch - add to hypothesis_ids
                if "hypothesis_ids" not in existing:
                    # Convert single hypothesis_id to array
                    existing["hypothesis_ids"] = [existing.pop("hypothesis_id", hypothesis_id), hypothesis_id]
                elif hypothesis_id not in existing["hypothesis_ids"]:
                    existing["hypothesis_ids"].append(hypothesis_id)
            else:
                # New result - tag with hypothesis_id and add to index
                result["hypothesis_id"] = hypothesis_id
                deduplicated.append(result)
                url_to_result[url] = result  # Index by URL for O(1) lookup

        return deduplicated

    def _compute_hypothesis_delta(
        self,
        task: ResearchTask,
        hypothesis: Dict,
        hypothesis_results: List[Dict]
    ) -> Dict[str, int]:
        """
        Compute delta metrics for a hypothesis execution (Phase 3C).

        Calculates how many new vs duplicate results/entities were discovered
        by this hypothesis compared to what was already found in the task.

        Args:
            task: Research task containing accumulated results/entities
            hypothesis: Hypothesis dict with id and statement
            hypothesis_results: Results from this hypothesis execution

        Returns:
            Dict with delta metrics:
            {
                "results_new": int,        # Results not in task.accumulated_results
                "results_duplicate": int,  # Results already in task.accumulated_results
                "entities_new": int,       # Entities not in task.entities_found
                "entities_duplicate": int, # Entities already in task.entities_found
                "total_results": int,      # Total results from this hypothesis
                "total_entities": int      # Total entities from this hypothesis
            }
        """
        # Build set of existing URLs for O(1) lookup
        existing_urls = set()
        for result in task.accumulated_results:
            url = result.get("url")
            if url:
                existing_urls.add(url)

        # Count new vs duplicate results
        results_new = 0
        results_duplicate = 0
        for result in hypothesis_results:
            url = result.get("url")
            if url:
                if url in existing_urls:
                    results_duplicate += 1
                else:
                    results_new += 1
            else:
                # No URL to check, count as new
                results_new += 1

        # Extract entities from hypothesis results
        hypothesis_entities = set()
        for result in hypothesis_results:
            # If result has entities field, use it
            if "entities" in result and isinstance(result["entities"], list):
                hypothesis_entities.update(result["entities"])

        # Count new vs duplicate entities
        existing_entities = set(task.entities_found) if task.entities_found else set()
        entities_new = len(hypothesis_entities - existing_entities)
        entities_duplicate = len(hypothesis_entities & existing_entities)

        return {
            "results_new": results_new,
            "results_duplicate": results_duplicate,
            "entities_new": entities_new,
            "entities_duplicate": entities_duplicate,
            "total_results": len(hypothesis_results),
            "total_entities": len(hypothesis_entities)
        }

    def _get_available_source_names(self) -> List[str]:
        """Get list of available database integration display names for hypothesis generation."""
        # Get display names from registry (single source of truth)
        display_names = [registry.get_display_name(id) for id in self.integrations]
        return sorted(set(display_names))  # Use set for dedup

    async def _search_brave(self, query: str, max_results: int = 20) -> List[Dict]:
        """
        Search open web using Brave Search API.

        Includes rate limiting (1 req/sec) and retry logic for HTTP 429 errors.
        Uses ResourceManager global lock to ensure rate limit respected across parallel tasks.
        """
        api_key = os.getenv('BRAVE_SEARCH_API_KEY')
        if not api_key:
            logger.warning("BRAVE_SEARCH_API_KEY not found, skipping web search")
            return []

        # Use ResourceManager to ensure only 1 Brave Search call at a time (1 req/sec limit)
        async with self.resource_manager.brave_lock:
            url = "https://api.search.brave.com/res/v1/web/search"
            headers = {
                "Accept": "application/json",
                "X-Subscription-Token": api_key
            }
            params = {
                "q": query,
                "count": max_results
            }

            # Retry logic for rate limits
            max_retries = 3
            retry_delays = [1.0, 2.0, 4.0]  # Exponential backoff (1s, 2s, 4s)

            for attempt in range(max_retries):
                try:
                    # Rate limiting: 1 request per second (Brave Search free tier limit)
                    if attempt > 0:
                        delay = retry_delays[attempt - 1]
                        logger.info(f"Brave Search: Waiting {delay}s before retry {attempt}/{max_retries}")
                        await asyncio.sleep(delay)
                    else:
                        # Always wait 1 second between calls to respect rate limit
                        await asyncio.sleep(1.0)

                    # Codex fix: Move aiohttp.ClientSession inside try block for proper error handling
                    async with aiohttp.ClientSession() as session:
                        async with session.get(url, headers=headers, params=params, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                            # Handle rate limiting
                            if resp.status == 429:
                                if attempt < max_retries - 1:
                                    logger.warning(f"Brave Search: HTTP 429 (rate limit), retry {attempt + 1}/{max_retries}")
                                    continue  # Retry with exponential backoff
                                else:
                                    logger.error(f"Brave Search: HTTP 429 after {max_retries} retries, giving up")
                                    return []

                            # Handle other errors
                            if resp.status != 200:
                                logger.error(f"Brave Search API error: HTTP {resp.status}")
                                return []

                            data = await resp.json()

                    # Convert Brave results to standard format
                    results = []
                    for item in data.get('web', {}).get('results', []):
                        description = item.get('description', '')
                        results.append({
                            'source': 'Brave Search',
                            'title': item.get('title', ''),
                            'description': description,  # Use 'description' for consistency
                            'snippet': description,      # Also include 'snippet' for backward compatibility
                            'url': item.get('url', ''),
                            'date': item.get('published_date')
                        })

                    logger.info(f"Brave Search: {len(results)} results for query: {query}")
                    return results

                except asyncio.TimeoutError:
                    logger.error(f"Brave Search timeout for query: {query}")
                    if attempt < max_retries - 1:
                        continue  # Retry
                    return []

                # Query reformulation failure - acceptable to proceed with existing query
                except Exception as e:
                    logger.error(f"Brave Search error: {type(e).__name__}: {str(e)}", exc_info=True)
                    if attempt < max_retries - 1:
                        continue  # Retry
                    return []

        # Should never reach here, but return empty if all retries exhausted
        return []

    async def _select_relevant_sources(self, query: str, task_id: Optional[int] = None) -> Tuple[List[str], str]:
        """
        Use a single LLM call to choose the most relevant sources (MCP tools + web tools) for this task.

        Args:
            query: Research question
            task_id: Task ID for logging (optional)

        Returns:
            Tuple of (selected_sources, reason):
            - selected_sources: List of integration IDs (e.g., ["dvids", "sam", "brave_search"])
            - reason: LLM's explanation for why these sources were selected
        """
        # All tools are in mcp_tools now (unified list)
        # Use registry for display names and descriptions (single source of truth)
        options_text = "\n".join([
            f"- {registry.get_display_name(tool['name'])} ({tool['name']}): {registry.get_metadata(tool['name']).description if registry.get_metadata(tool['name']) else ''}"
            for tool in self.mcp_tools
        ])

        prompt = render_prompt(
            "deep_research/source_selection.j2",
            research_question=self.original_question,
            query=query,
            options_text=options_text
        )

        schema = {
            "type": "object",
            "properties": {
                "sources": {
                    "type": "array",
                    "items": {"type": "string"},
                    "minItems": 1,  # Always return at least one source
                    "maxItems": len(self.mcp_tools)
                },
                "reason": {
                    "type": "string",
                    "description": "Brief explanation of why these sources were selected"
                }
            },
            "required": ["sources", "reason"],
            "additionalProperties": False
        }

        try:
            response = await acompletion(
                model=config.get_model("analysis"),
                messages=[{"role": "user", "content": prompt}],
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "strict": True,
                        "name": "source_selection",
                        "schema": schema
                    }
                }
            )

            result = json.loads(response.choices[0].message.content)
            selected_sources = result.get("sources", [])
            reason = result.get("reason", "")

            # Normalize source names to integration_id using registry (single source of truth)
            # Handles: integration_id, display_name, case variations, common suffixes
            valid_sources = []
            for source in selected_sources:
                normalized = registry.normalize_source_name(source)
                if normalized:
                    valid_sources.append(normalized)
                else:
                    logger.warning(f"Unknown source '{source}' returned by LLM - skipping")

            # Log sources that were NOT selected
            all_sources = list(self.integrations.keys())
            not_selected = [s for s in all_sources if s not in valid_sources]
            if not_selected and self.logger and task_id is not None:
                for source in not_selected:
                    source_display = registry.get_display_name(source)
                    try:
                        self.logger.log_source_skipped(
                            task_id=task_id,
                            hypothesis_id=None,
                            source_name=source_display,
                            reason="not_selected_by_llm",
                            stage="source_selection",
                            details={"selection_reasoning": reason}
                        )
                    # Logging failure - non-critical, execution continues
                    except Exception as log_error:
                        logger.warning(f"Failed to log source skipped: {log_error}", exc_info=True)

            if reason:
                logger.info(f"Source selection rationale: {reason}")
                print(f"📋 Source selection reasoning: {reason}")

            return (valid_sources, reason)

        # Exception caught - error logged, execution continues
        except Exception as e:
            logger.error(f"Source selection failed: {type(e).__name__}: {str(e)}", exc_info=True)
            # Fallback: return all MCP tools (downstream filtering will still apply)
            return ([tool["name"] for tool in self.mcp_tools], f"Error during source selection: {type(e).__name__}")

    async def _call_mcp_tool(
        self,
        tool_config: Dict,
        query: str,
        param_adjustments: Optional[Dict[str, Dict]] = None,
        task_id: Optional[int] = None,
        attempt: int = 0,
        exec_logger: Optional['ExecutionLogger'] = None
    ) -> Dict:
        """
        Call a single MCP tool (extracted as class method for reuse).

        Args:
            tool_config: MCP tool configuration dict with 'name', 'server', 'api_key_name'
            query: Search query
            param_adjustments: Optional param hints for source-specific adjustments
            task_id: Task ID for logging
            attempt: Retry attempt number
            exec_logger: Execution logger instance (ExecutionLogger)

        Returns:
            Dict with 'success', 'results', 'source', 'total', 'error' keys
        """
        tool_name = tool_config["name"]
        server = tool_config["server"]
        api_key_name = tool_config["api_key_name"]

        try:
            # Get API key if needed
            api_key = self.api_keys.get(api_key_name) if api_key_name else None

            # Get per-integration limit (Task 1: Per-Integration Limits)
            source_name = registry.get_display_name(tool_name)
            integration_limit = config.get_integration_limit(source_name.lower().replace('.', '').replace(' ', ''))

            # Build tool arguments
            args = {
                "research_question": query,
                "limit": integration_limit  # Use per-integration limit instead of hardcoded
            }
            if api_key:
                args["api_key"] = api_key

            # Add param_hints if available for this tool (Task 4: Twitter pagination control)
            # tool_name is now integration_id directly (e.g., "reddit", "twitter")
            if param_adjustments and tool_name in param_adjustments:
                args["param_hints"] = param_adjustments[tool_name]

            # Log API call
            source_name = registry.get_display_name(tool_name)
            if exec_logger and task_id is not None:
                try:
                    exec_logger.log_api_call(
                        task_id=task_id,
                        attempt=attempt,
                        source_name=source_name,
                        query_params=args,
                        timeout=30,
                        retry_count=0
                    )
                # Logging failure - non-critical, execution continues
                except Exception as log_error:
                    logger.warning(f"Failed to log API call: {log_error}", exc_info=True)

            # Call integration - two paths: MCP (old) vs Direct (new)
            start_time = time.time()

            if server is None:
                # NEW ARCHITECTURE: Direct integration call (no MCP)
                # Get integration from registry
                integration_id = tool_config.get("integration_id")
                if not integration_id:
                    raise ValueError(f"Tool {tool_name} has no server and no integration_id")

                integration = self.integrations.get(integration_id)
                if not integration:
                    raise ValueError(f"Integration {integration_id} not found in registry")

                # Call integration directly using DatabaseIntegration interface
                # 1. Check relevance
                is_relevant = await integration.is_relevant(query)
                if not is_relevant:
                    logging.warning(f"{source_name} not relevant for query: {query}")

                    # Log source skipped (Enhanced Structured Logging)
                    if exec_logger and task_id is not None:
                        try:
                            exec_logger.log_source_skipped(
                                task_id=task_id,
                                hypothesis_id=None,  # Set by caller if hypothesis execution
                                source_name=source_name,
                                reason="is_relevant_false",
                                stage="is_relevant",
                                details={"query": query}
                            )
                        # Logging failure - non-critical, execution continues
                        except Exception as log_error:
                            logger.warning(f"Failed to log source_skipped: {log_error}", exc_info=True)

                    result_data = {
                        "success": False,
                        "source": source_name,
                        "total": 0,
                        "results": [],
                        "error": "Source not relevant for this query"
                    }
                else:
                    # 2. Generate query parameters
                    query_gen_start = time.time()
                    query_params = await integration.generate_query(query)
                    query_gen_time_ms = int((time.time() - query_gen_start) * 1000)

                    # Log query generation timing (Enhanced Structured Logging)
                    if exec_logger and task_id is not None:
                        try:
                            exec_logger.log_time_breakdown(
                                task_id=task_id,
                                hypothesis_id=None,  # Set by caller if hypothesis execution
                                source_name=source_name,
                                operation="query_generation",
                                time_ms=query_gen_time_ms,
                                success=query_params is not None,
                                metadata={"tool_name": tool_name}
                            )
                        # Logging failure - non-critical, execution continues
                        except Exception as log_error:
                            logger.warning(f"Failed to log time breakdown: {log_error}", exc_info=True)

                    if not query_params:
                        logger.warning(f"{source_name} failed to generate query for: {query}")

                        # Log source skipped (Enhanced Structured Logging)
                        if exec_logger and task_id is not None:
                            try:
                                exec_logger.log_source_skipped(
                                    task_id=task_id,
                                    hypothesis_id=None,  # Set by caller if hypothesis execution
                                    source_name=source_name,
                                    reason="generate_query_none",
                                    stage="generate_query",
                                    details={"query": query}
                                )
                            # Logging failure - non-critical, execution continues
                            except Exception as log_error:
                                logger.warning(f"Failed to log source_skipped: {log_error}", exc_info=True)

                        result_data = {
                            "success": False,
                            "source": source_name,
                            "total": 0,
                            "results": [],
                            "error": "Failed to generate query parameters"
                        }
                    else:
                        # 3. Execute search
                        query_result = await integration.execute_search(
                            query_params=query_params,
                            api_key=api_key,
                            limit=integration_limit
                        )

                        # Convert QueryResult to dict format expected by caller
                        result_data = {
                            "success": query_result.success,
                            "source": query_result.source,
                            "total": query_result.total,
                            "results": query_result.results,
                            "error": query_result.error
                        }

                response_time_ms = (time.time() - start_time) * 1000

            else:
                # OLD ARCHITECTURE: MCP server call (backward compatibility)
                async with Client(server) as client:
                    result = await client.call_tool(tool_name, args)
                response_time_ms = (time.time() - start_time) * 1000

                # Parse result (FastMCP returns ToolResult with content)
                import json
                result_data = json.loads(result.content[0].text)

            # Log time breakdown for API call
            if exec_logger and task_id is not None:
                try:
                    exec_logger.log_time_breakdown(
                        task_id=task_id,
                        hypothesis_id=None,  # Set by caller if hypothesis execution
                        source_name=source_name,
                        operation="api_call",
                        time_ms=int(response_time_ms),
                        success=True,  # Will be updated if error found
                        metadata={"tool_name": tool_name, "attempt": attempt}
                    )
                # Logging failure - non-critical, execution continues
                except Exception as log_error:
                    logger.warning(f"Failed to log time breakdown: {log_error}", exc_info=True)

            # Get source name from result_data (may be overridden by integration)
            source_name = result_data.get("source", source_name)

            # Add source field to each individual result for proper tracking
            results_with_source = []
            for r in result_data.get("results", []):
                # Make a copy to avoid mutating original
                r_copy = dict(r)
                # Add source if not already present
                if "source" not in r_copy:
                    r_copy["source"] = source_name
                results_with_source.append(r_copy)

            # Log raw response
            success = result_data.get("success", False)
            error = result_data.get("error")
            if exec_logger and task_id is not None:
                try:
                    exec_logger.log_raw_response(
                        task_id=task_id,
                        attempt=attempt,
                        source_name=source_name,
                        success=success,
                        response_time_ms=response_time_ms,
                        results=results_with_source,
                        error=error
                    )
                # Logging failure - non-critical, execution continues
                except Exception as log_error:
                    logger.warning(f"Failed to log raw response: {log_error}", exc_info=True)

            # Circuit breaker: Detect 429 rate limits and check config before adding
            if error and ("429" in str(error) or "rate limit" in str(error).lower()):
                rate_config = config.get_rate_limit_config(source_name)

                if rate_config["use_circuit_breaker"]:
                    if not rate_config["is_critical"]:
                        self.rate_limited_sources.add(source_name)
                        logger.warning(f"⚠️  {source_name} rate limited - added to circuit breaker")
                        print(f"⚠️  {source_name} rate limited - skipping for remaining tasks")
                    else:
                        logger.warning(f"⚠️  {source_name} rate limited but CRITICAL - will continue retrying")
                        print(f"⚠️  {source_name} rate limited (CRITICAL - continuing retries)")
                else:
                    logger.info(f"ℹ️  {source_name} rate limited (no circuit breaker configured - will retry)")
                    print(f"ℹ️  {source_name} rate limited (will retry)")

            return {
                "tool": tool_name,
                "success": success,
                "source": source_name,  # Pass through source from wrapper
                "results": results_with_source,  # Individual results now have source
                "total": result_data.get("total", 0),
                "error": error
            }

        # Exception caught - error logged, execution continues
        except Exception as e:
            logging.error(f"MCP tool {tool_name} failed: {type(e).__name__}: {str(e)}", exc_info=True)

            # Log failed API call
            if exec_logger and task_id is not None:
                try:
                    source_name = registry.get_display_name(tool_name)
                    exec_logger.log_raw_response(
                        task_id=task_id,
                        attempt=attempt,
                        source_name=source_name,
                        success=False,
                        response_time_ms=0,
                        results=[],
                        error=str(e)
                    )
                # Logging failure - non-critical, execution continues
                except Exception as log_error:
                    logger.warning(f"Failed to log error response: {log_error}", exc_info=True)

            return {
                "tool": tool_name,
                "success": False,
                "results": [],
                "total": 0,
                "error": str(e)
            }

    async def _search_mcp_tools_selected(
        self,
        query: str,
        selected_tool_names: List[str],
        limit: int = 10,
        task_id: Optional[int] = None,
        attempt: int = 0,
        param_adjustments: Optional[Dict[str, Dict]] = None
    ) -> List[Dict]:
        """
        Search using pre-selected MCP tools (avoids duplicate LLM selection call).

        Args:
            query: Search query
            selected_tool_names: List of MCP tool names already selected by LLM
            limit: Max results per source
            task_id: Task ID for logging (optional)
            attempt: Retry attempt number for logging (optional)

        Returns:
            List of results with standardized format
        """
        # Use pre-selected tool names (already filtered by LLM)
        candidate_tools = [
            tool for tool in self.mcp_tools
            if tool["name"] in selected_tool_names
        ]

        if not candidate_tools:
            print("⊘ No MCP sources selected for this task. Skipping MCP search.")
            return []

        # Circuit breaker: Skip rate-limited sources
        skip_rate_limited_names = set()
        for tool in candidate_tools:
            source_display_name = registry.get_display_name(tool["name"])
            if source_display_name in self.rate_limited_sources:
                skip_rate_limited_names.add(tool["name"])

                # Log source skipped due to rate limiting
                if self.logger and task_id is not None:
                    try:
                        self.logger.log_source_skipped(
                            task_id=task_id,
                            hypothesis_id=None,  # Set by caller if hypothesis execution
                            source_name=source_display_name,
                            reason="rate_limited",
                            stage="execute_search",
                            details={"message": "Circuit breaker active - source previously rate limited"}
                        )
                    # Logging failure - non-critical, execution continues
                    except Exception as log_error:
                        logger.warning(f"Failed to log source skipped: {log_error}", exc_info=True)

        if skip_rate_limited_names:
            skipped_display = [registry.get_display_name(name) for name in skip_rate_limited_names]
            print(f"⊘ Skipping rate-limited sources (circuit breaker): {', '.join(skipped_display)}")

        # Filter tools to only those not rate-limited
        filtered_tools = [
            tool for tool in candidate_tools
            if tool["name"] not in skip_rate_limited_names
        ]

        if not filtered_tools:
            print("⊘ No MCP sources after filtering. Skipping MCP search.")
            return []

        # Emit progress: starting MCP tool searches
        display_names = [registry.get_display_name(tool["name"]) for tool in filtered_tools]
        print(f"🔍 Searching {len(filtered_tools)} MCP sources: {', '.join(display_names)}")

        all_results = []
        sources_count = {}

        # Call filtered MCP tools in parallel (skip irrelevant sources) using class method
        mcp_results = await asyncio.gather(*[
            self._call_mcp_tool(tool, query, param_adjustments, task_id=task_id, attempt=attempt, exec_logger=self.logger)
            for tool in filtered_tools
        ])

        # Combine results and track per-source counts
        for tool_result in mcp_results:
            if tool_result["success"]:
                tool_results = tool_result["results"]
                all_results.extend(tool_results)
                # Get source from wrapper level (now passed through from call_mcp_tool)
                source = tool_result.get("source", tool_result["tool"])
                sources_count[source] = sources_count.get(source, 0) + len(tool_results)
                # Log each successful source with counts
                print(f"  ✓ {source}: {len(tool_results)} results")
            else:
                # Log failed sources
                print(f"  ✗ {tool_result['tool']}: Failed - {tool_result.get('error', 'Unknown error')}")

        # Log summary with per-source breakdown
        print(f"\n✓ MCP tools complete: {len(all_results)} total results from {len(sources_count)} sources")
        if sources_count:
            print("  Per-source breakdown:")
            for source, count in sorted(sources_count.items(), key=lambda x: x[1], reverse=True):
                print(f"    • {source}: {count} results")

        return all_results



    async def _execute_task_with_retry(self, task: ResearchTask) -> bool:
        """
        Execute task with retry logic if it fails.

        Uses intelligent source selection (MCP tools + web search) based on query.

        Returns:
            True if task succeeded (eventually), False if exhausted retries
        """
        # Note: task.status already set to IN_PROGRESS in batch loop before parallel execution

        while task.retry_count <= self.max_retries_per_task:
            try:
                # Log task start (or retry)
                if self.logger:
                    self.logger.log_task_start(
                        task_id=task.id,
                        query=task.query,
                        attempt=task.retry_count
                    )

                # Phase 2: Check if LLM provided source adjustments on previous retry
                adjusted_sources = task.param_adjustments.get("_adjusted_sources")
                if adjusted_sources:
                    # Use LLM-adjusted sources (skip source selection LLM call)
                    selected_sources = adjusted_sources
                    source_selection_reason = f"Phase 2: Using LLM-adjusted sources from previous retry"
                    print(f"📋 Phase 2: Using adjusted sources: {', '.join([registry.get_display_name(s) for s in selected_sources])}")
                else:
                    # Get LLM-selected sources for this query (includes both MCP and web tools)
                    selected_sources, source_selection_reason = await self._select_relevant_sources(task.query, task_id=task.id)

                # Log source selection if logger enabled
                if self.logger:
                    # Get human-readable source names
                    selected_display_names = [registry.get_display_name(s) for s in selected_sources]
                    # Build tool_descriptions dict from registry (single source of truth)
                    tool_descs = {
                        id: registry.get_metadata(id).description
                        for id in self.integrations
                        if registry.get_metadata(id)
                    }
                    self.logger.log_source_selection(
                        task_id=task.id,
                        query=task.query,
                        tool_descriptions=tool_descs,
                        selected_sources=selected_display_names,
                        reasoning=source_selection_reason
                    )
                    # Emit progress for traceability
                    self._emit_progress(
                        "source_selection",
                        "LLM-selected sources",
                        task_id=task.id,
                        data={
                            "selected_sources": selected_display_names,
                            "reasoning": source_selection_reason
                        }
                    )

                # All selected sources are in mcp_tools now (no web_tools distinction)
                selected_tool_names = [s for s in selected_sources if s in [tool["name"] for tool in self.mcp_tools]]

                # Search all selected tools
                all_results = []
                if selected_tool_names:
                    all_results = await self._search_mcp_tools_selected(
                        task.query,
                        selected_tool_names,
                        limit=config.default_result_limit,
                        task_id=task.id,
                        attempt=task.retry_count,
                        param_adjustments=task.param_adjustments
                    )

                # Note: brave_search is now handled like any other integration in _search_mcp_tools_selected
                combined_total = len(all_results)

                # Validate result relevance, filter to relevant results, decide if continue
                # LLM makes 3 decisions: ACCEPT/REJECT, which indices to keep, continue searching?
                # Gemini 2.5 Flash has 65K token context - evaluate ALL results, no sampling needed
                print(f"🔍 Validating relevance of {len(all_results)} results...")

                # Track relevance filtering time (Enhanced Structured Logging)
                filtering_start = time.time()
                should_accept, relevance_reason, relevant_indices, should_continue, continuation_reason, reasoning_breakdown = await self._validate_result_relevance(
                    task_query=task.query,
                    research_question=self.original_question,
                    sample_results=all_results  # Send ALL results to LLM
                )
                filtering_time_ms = int((time.time() - filtering_start) * 1000)

                # Log relevance filtering timing (Enhanced Structured Logging)
                if self.logger and task.id is not None:
                    try:
                        self.logger.log_time_breakdown(
                            task_id=task.id,
                            hypothesis_id=None,
                            source_name="Multi-source",  # Combined MCP + web results
                            operation="relevance_filtering",
                            time_ms=filtering_time_ms,
                            success=True,
                            metadata={
                                "results_evaluated": len(all_results),
                                "results_kept": len(relevant_indices)
                            }
                        )
                    # Logging failure - non-critical, execution continues
                    except Exception as log_error:
                        logger.warning(f"Failed to log time breakdown: {log_error}", exc_info=True)

                decision_str = "ACCEPT" if should_accept else "REJECT"
                continue_str = "CONTINUE" if should_continue else "STOP"
                print(f"  Decision: {decision_str}")
                print(f"  Reason: {relevance_reason}")
                print(f"  Filtered: {len(relevant_indices)}/{len(all_results)} results kept")
                print(f"  Continuation: {continue_str}")
                print(f"  Continuation Reason: {continuation_reason}")

                # Phase 1: Store LLM reasoning breakdown for transparency
                if reasoning_breakdown:
                    task.reasoning_notes.append({
                        "attempt": task.retry_count,
                        "query": task.query,
                        "results_evaluated": len(all_results),
                        "decision": decision_str,
                        "reasoning_breakdown": reasoning_breakdown
                    })
                    # Log interesting decisions for visibility
                    interesting = reasoning_breakdown.get("interesting_decisions", [])
                    if interesting:
                        print(f"  💡 Interesting decisions: {len(interesting)} highlighted")
                        for decision_note in interesting[:3]:  # Show first 3
                            action = decision_note.get("action", "unknown")
                            idx = decision_note.get("result_index", -1)
                            reasoning = decision_note.get("reasoning", "")
                            print(f"     • Result #{idx} ({action}): {reasoning[:80]}{'...' if len(reasoning) > 80 else ''}")

                # Filter results to only keep relevant ones (per-result filtering)
                if should_accept and relevant_indices:
                    # Keep only the results LLM marked as relevant
                    filtered_results = [all_results[i] for i in relevant_indices if i < len(all_results)]
                    discarded_count = len(all_results) - len(filtered_results)
                    print(f"  ✓ Kept {len(filtered_results)} relevant results, discarded {discarded_count} junk results")

                    # Date validation: Reject results with future dates (2025-11-18 fix)
                    date_validated_results = self._validate_result_dates(filtered_results)

                    # ACCUMULATE IMMEDIATELY (whether CONTINUE or STOP) - fixes accumulation bug
                    task.accumulated_results.extend(date_validated_results)
                    print(f"  📊 Total accumulated so far: {len(task.accumulated_results)} results")
                else:
                    # REJECT: discard all results
                    filtered_results = []
                    discarded_count = len(all_results)
                    print(f"  ✗ Discarded all {discarded_count} results (off-topic)")

                # Log relevance decision if logger enabled
                if self.logger:
                    try:
                        # Use actual LLM reasoning (not generic f-string)
                        self.logger.log_relevance_scoring(
                            task_id=task.id,
                            attempt=task.retry_count,
                            source_name="Multi-source",  # Combined MCP + web results
                            original_query=self.original_question,
                            results_count=len(all_results),
                            llm_prompt=f"Evaluating relevance of {len(all_results)} results for query '{task.query}'",
                            llm_response={
                                "decision": decision_str,
                                "reasoning": relevance_reason,
                                "relevant_indices": relevant_indices,
                                "continue_searching": should_continue,
                                "continuation_reason": continuation_reason
                            },
                            threshold=None,  # No threshold anymore
                            passes=should_accept,
                            reasoning_breakdown=reasoning_breakdown  # Bug fix: include detailed reasoning
                        )
                    # Logging failure - non-critical, execution continues
                    except Exception as log_error:
                        logger.warning(f"Failed to log relevance scoring: {log_error}", exc_info=True)

                # LLM continuation decision: should we search for more?
                # Continue if: LLM says continue AND we have retries left
                # Stop if: LLM says stop OR no retries left
                if should_continue and task.retry_count < self.max_retries_per_task:
                    # LLM wants more results - reformulate and retry
                    task.status = TaskStatus.RETRY
                    task.retry_count += 1

                    # Log filter decision
                    if self.logger:
                        try:
                            self.logger.log_filter_decision(
                                task_id=task.id,
                                attempt=task.retry_count,
                                source_name="Multi-source",
                                decision="CONTINUE",
                                reason=f"LLM decided to continue searching: {relevance_reason}",
                                kept=len(filtered_results),
                                discarded=discarded_count
                            )
                        # Logging failure - non-critical, execution continues
                        except Exception as log_error:
                            logger.warning(f"Failed to log filter decision: {log_error}", exc_info=True)

                    self._emit_progress(
                        "task_retry",
                        f"LLM wants more results (found {len(filtered_results)}, continuing search)...",
                        task_id=task.id,
                        data={
                            "decision": decision_str,
                            "continue": should_continue,
                            "kept_results": len(filtered_results),
                            "total_results": combined_total
                        }
                    )

                    # Phase 0: Collect source context BEFORE reformulation (for instrumentation)
                    # This enables data-driven decision on whether param_hints are worth implementing
                    sources_with_errors = []
                    sources_with_zero_results = []
                    sources_with_low_quality = []

                    for source in selected_sources:
                        source_display = registry.get_display_name(source)
                        source_results = [r for r in all_results if r.get('source') == source_display]

                        if not source_results:
                            # Source returned no results - classify as zero results
                            # Note: We can't distinguish errors from empty results at this point
                            # since _search_mcp_tools_selected returns transformed results, not raw status
                            sources_with_zero_results.append(source_display)
                        else:
                            # Check if any results from this source were kept
                            source_has_kept_results = any(
                                i in relevant_indices
                                for i, r in enumerate(all_results)
                                if r.get('source') == source_display
                            )
                            if not source_has_kept_results:
                                sources_with_low_quality.append(source_display)

                    # Phase 2: Build source performance data for LLM source re-selection
                    source_performance = []
                    for source in selected_sources:
                        source_display = registry.get_display_name(source)
                        source_results = [r for r in all_results if r.get('source') == source_display]
                        kept_indices = [i for i, r in enumerate(all_results) if r.get('source') == source_display and i in relevant_indices]

                        # Categorize source status
                        if source_display in sources_with_errors:
                            status = "error"
                            error_type = "API failure, rate limit, or timeout"
                        elif not source_results:
                            status = "zero_results"
                            error_type = None
                        elif not kept_indices:
                            status = "low_quality"
                            error_type = None
                        else:
                            status = "success"
                            error_type = None

                        quality_rate = int((len(kept_indices) / len(source_results) * 100)) if source_results else 0

                        source_performance.append({
                            "name": source_display,
                            "status": status,
                            "results_returned": len(source_results),
                            "results_kept": len(kept_indices),
                            "quality_rate": quality_rate,
                            "error_type": error_type
                        })

                    # Get available sources (all tools minus rate-limited ones)
                    available_sources = [
                        registry.get_display_name(tool["name"])
                        for tool in self.mcp_tools
                        if registry.get_display_name(tool["name"]) not in self.rate_limited_sources
                    ]

                    # Reformulate query to find more results
                    reformulation = await self._reformulate_for_relevance(
                        original_query=task.query,
                        research_question=self.original_question,
                        results_count=len(filtered_results),
                        source_performance=source_performance,
                        available_sources=available_sources
                    )
                    new_query = reformulation["query"]
                    new_param_adjustments = reformulation.get("param_adjustments", {})

                    # Phase 2: Apply source re-selection if LLM provided adjustments
                    source_adjustments = reformulation.get("source_adjustments")
                    if source_adjustments:
                        # Log source adjustments
                        keep_sources = source_adjustments.get("keep", [])
                        drop_sources = source_adjustments.get("drop", [])
                        add_sources = source_adjustments.get("add", [])
                        reasoning = source_adjustments.get("reasoning", "")

                        print(f"📋 Source re-selection:")
                        print(f"  Keep: {', '.join(keep_sources) if keep_sources else 'none'}")
                        print(f"  Drop: {', '.join(drop_sources) if drop_sources else 'none'}")
                        print(f"  Add: {', '.join(add_sources) if add_sources else 'none'}")
                        print(f"  Reasoning: {reasoning}")

                        # Apply source adjustments for next retry
                        # Convert display names back to tool names for next source selection
                        adjusted_sources = []

                        # Add "keep" sources (use registry's normalize function)
                        for display_name in keep_sources:
                            tool_name = registry.normalize_source_name(display_name)
                            if tool_name:
                                adjusted_sources.append(tool_name)

                        # Add "add" sources (use registry's normalize function)
                        for display_name in add_sources:
                            tool_name = registry.normalize_source_name(display_name)
                            if tool_name and tool_name not in adjusted_sources:
                                adjusted_sources.append(tool_name)

                        # Override selected_sources for next retry (skip LLM source selection)
                        # Store adjusted sources in task metadata for next iteration
                        task.param_adjustments["_adjusted_sources"] = adjusted_sources
                        logger.info(f"Phase 2: Source re-selection applied - next retry will use: {[registry.get_display_name(s) for s in adjusted_sources]}")

                    # Phase 0: Log reformulation with full source context (for instrumentation)
                    if self.logger:
                        try:
                            self.logger.log_reformulation(
                                task_id=task.id,
                                attempt=task.retry_count,
                                trigger_reason="continue_searching",  # LLM decided to continue
                                original_query=task.query,
                                new_query=new_query,
                                param_adjustments=new_param_adjustments,
                                sources_with_errors=sources_with_errors,
                                sources_with_zero_results=sources_with_zero_results,
                                sources_with_low_quality=sources_with_low_quality
                            )
                        # Logging failure - non-critical, execution continues
                        except Exception as log_error:
                            logger.warning(f"Failed to log reformulation: {log_error}", exc_info=True)

                    # Update task with new query and params
                    task.query = new_query
                    task.param_adjustments = new_param_adjustments

                    self._emit_progress(
                        "query_reformulated",
                        f"New query: {task.query}",
                        task_id=task.id
                    )
                    continue  # Retry with new query

                # LLM says stop OR no retries left - finalize task
                # SUCCESS: We have accumulated results from at least one attempt
                if task.accumulated_results:
                    # Phase 3B: Execute hypotheses if mode is "execution"
                    if self.hypothesis_mode == "execution" and task.hypotheses:
                        print(f"\n🔬 Phase 3B: Executing hypotheses for Task {task.id}...")
                        try:
                            hypothesis_results = await self._execute_hypotheses(
                                task=task,
                                research_question=self.original_question
                            )

                            if hypothesis_results:
                                print(f"   ✓ Hypothesis execution added {len(hypothesis_results)} results")
                                # Add hypothesis results to accumulated results
                                task.accumulated_results.extend(hypothesis_results)
                            else:
                                print(f"   ⚠️  No hypothesis results found")

                        # Hypothesis processing failure - non-critical, continue with other hypotheses
                        except Exception as hyp_error:
                            # Log but don't fail task - hypothesis execution is supplementary
                            logger.error(f"❌ Hypothesis execution failed for Task {task.id}: {type(hyp_error).__name__}: {hyp_error}", exc_info=True)
                            print(f"   ⚠️  Hypothesis execution failed, continuing with normal results")

                    # Priority 2: Don't extract entities here, will do at end from accumulated results
                    task.status = TaskStatus.COMPLETED

                    # Log filter decision: STOP (with results)
                    if self.logger:
                        try:
                            self.logger.log_filter_decision(
                                task_id=task.id,
                                attempt=task.retry_count,
                                source_name="Multi-source",
                                decision="STOP_SUCCESS",
                                reason=f"LLM decided to stop: {relevance_reason}",
                                kept=len(filtered_results) if filtered_results else 0,
                                discarded=discarded_count
                            )
                        # Logging failure - non-critical, execution continues
                        except Exception as log_error:
                            logger.warning(f"Failed to log filter decision: {log_error}", exc_info=True)

                    # Use ALL accumulated results (not just last batch)
                    result_dict = {
                        "total_results": len(task.accumulated_results),
                        "results": task.accumulated_results,  # All accumulated results across retries
                        "accumulated_count": len(task.accumulated_results),
                        "entities_discovered": [],  # Will be extracted at end from accumulated
                        "sources": self._get_sources(task.accumulated_results)
                    }

                    task.results = result_dict

                    # Codex fix: Protect shared dict writes with lock
                    async with self.resource_manager.results_lock:
                        self.results_by_task[task.id] = result_dict

                # Flush accumulated results to disk immediately (survive timeout/cancel)
                if self.logger:
                    from pathlib import Path
                    raw_path = Path(self.logger.output_dir) / "raw"
                    raw_path.mkdir(exist_ok=True)
                    raw_file = raw_path / f"task_{task.id}_results.json"

                    accumulated_dict = {
                        "total_results": len(task.accumulated_results),
                        "results": task.accumulated_results,  # All attempts combined
                        "accumulated_count": len(task.accumulated_results),
                        "entities_discovered": [],
                        "sources": self._get_sources(task.accumulated_results)
                    }

                    try:
                        with open(raw_file, 'w', encoding='utf-8') as f:
                            json.dump(accumulated_dict, f, indent=2, ensure_ascii=False)
                        logger.info(f"Task {task.id} accumulated results ({len(task.accumulated_results)} total) persisted to {raw_file}")
                    # Persistence failure - non-critical, data may be lost but execution continues
                    except Exception as persist_error:
                        logger.warning(f"Failed to persist task {task.id} results: {persist_error}", exc_info=True)

                    # Priority 2: Entity extraction moved to end of task (after retry loop)
                    # Will extract from accumulated_results, not current batch

                    self._emit_progress(
                        "task_completed",
                        f"Task complete: {len(task.accumulated_results)} total results accumulated (across {task.retry_count + 1} attempts)",
                        task_id=task.id,
                        data={
                            "total_results": len(task.accumulated_results),
                            "kept": len(task.accumulated_results),
                            "discarded": discarded_count,
                            "accumulated_count": len(task.accumulated_results),
                            "sources": self._get_sources(task.accumulated_results)
                        }
                    )

                    # Log task completion if logger enabled
                    if self.logger:
                        sources_tried = list(set(
                            [registry.get_display_name(s) for s in selected_sources]
                        ))
                        sources_succeeded = self._get_sources(task.accumulated_results)
                        # Per-task timing not tracked (research-level timing in self.start_time)
                        # Task execution time varies based on retries, hypotheses, and source count
                        elapsed_seconds = 0

                        self.logger.log_task_complete(
                            task_id=task.id,
                            query=task.query,
                            status="SUCCESS",
                            reason=f"Accumulated {len(task.accumulated_results)} relevant results across {task.retry_count + 1} attempts: {relevance_reason}",
                            total_results=len(task.accumulated_results),
                            sources_tried=sources_tried,
                            sources_succeeded=sources_succeeded,
                            retry_count=task.retry_count,
                            elapsed_seconds=elapsed_seconds
                        )

                    # Priority 3: Entity extraction moved OUTSIDE timeout boundary
                    # Now happens after asyncio.wait_for() completes (lines 408-421)

                    return True

                else:
                    # FAILURE: Either REJECT decision OR no filtered results
                    task.status = TaskStatus.FAILED
                    if not should_accept:
                        task.error = f"LLM rejected all results: {relevance_reason}"
                    else:
                        task.error = f"No relevant results found after {task.retry_count} attempts"
                    self._emit_progress("task_failed", task.error, task_id=task.id)

                    # Log task failure
                    if self.logger:
                        sources_tried = list(set(
                            [registry.get_display_name(s) for s in selected_sources]
                        ))
                        self.logger.log_task_complete(
                            task_id=task.id,
                            query=task.query,
                            status="FAILED",
                            reason=task.error,
                            total_results=0,
                            sources_tried=sources_tried,
                            sources_succeeded=[],
                            retry_count=task.retry_count,
                            elapsed_seconds=0
                        )

                    return False

            # Exception caught - error logged, execution continues
            except Exception as e:
                # Task execution failure - log and potentially retry
                import traceback
                logger.error(f"Task {task.id} execution failed: {type(e).__name__}: {str(e)}", exc_info=True)
                error_details = {
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "traceback": traceback.format_exc(),
                    "query": task.query,
                    "retry_count": task.retry_count
                }

                if task.retry_count < self.max_retries_per_task:
                    task.status = TaskStatus.RETRY
                    task.retry_count += 1
                    self._emit_progress(
                        "task_error",
                        f"Error: {type(e).__name__}: {str(e)}, retrying...",
                        task_id=task.id,
                        data=error_details
                    )
                else:
                    task.status = TaskStatus.FAILED
                    task.error = str(e)
                    self._emit_progress(
                        "task_failed",
                        f"Failed after {task.retry_count} retries: {type(e).__name__}: {str(e)}",
                        task_id=task.id,
                        data=error_details
                    )

                    # Persist whatever has been accumulated so far for this task
                    if self.logger:
                        from pathlib import Path
                        raw_path = Path(self.logger.output_dir) / "raw"
                        raw_path.mkdir(exist_ok=True)
                        raw_file = raw_path / f"task_{task.id}_results.json"
                        accumulated_dict = {
                            "total_results": len(task.accumulated_results),
                            "results": task.accumulated_results,
                            "accumulated_count": len(task.accumulated_results),
                            "entities_discovered": [],
                            "sources": self._get_sources(task.accumulated_results)
                        }
                        try:
                            with open(raw_file, 'w', encoding='utf-8') as f:
                                json.dump(accumulated_dict, f, indent=2, ensure_ascii=False)
                            logger.info(f"Task {task.id} failed; persisted partial results ({len(task.accumulated_results)}) to {raw_file}")
                        # Persistence failure - non-critical, data may be lost but execution continues
                        except Exception as persist_error:
                            logger.warning(f"Failed to persist partial results for task {task.id}: {persist_error}", exc_info=True)

                    # Log task failure to execution logger for visibility
                    if self.logger:
                        sources_tried = list(set(task.selected_sources or [])) if hasattr(task, 'selected_sources') else []
                        try:
                            self.logger.log_task_complete(
                                task_id=task.id,
                                query=task.query,
                                status="FAILED",
                                reason=f"Exception: {type(e).__name__}: {str(e)}",
                                total_results=len(task.accumulated_results),
                                sources_tried=sources_tried,
                                sources_succeeded=self._get_sources(task.accumulated_results),
                                retry_count=task.retry_count,
                                elapsed_seconds=0
                            )
                        # Logging failure - non-critical, execution continues
                        except Exception as log_error:
                            logger.warning(f"Failed to log task failure for task {task.id}: {log_error}", exc_info=True)

                    return False

        return False

    # NOTE: _extract_entities moved to EntityAnalysisMixin

    def _get_sources(self, results: List[Dict]) -> List[str]:
        """Extract unique source names from results."""
        sources = set()
        for r in results:
            source = r.get("source", "Unknown")
            sources.add(source)
        return list(sources)

    # NOTE: _validate_result_relevance moved to ResultFilterMixin
    # NOTE: _update_entity_graph moved to EntityAnalysisMixin

    # NOTE: _validate_result_dates moved to ResultFilterMixin

    def _should_create_follow_ups(self, task: ResearchTask, total_pending_workload: int = 0) -> bool:
        """
        Decide if we should create follow-up tasks based on coverage quality.

        Improvements (2025-11-19):
        - Removed hardcoded heuristics (entities_found >= 3, total_results >= 5)
        - LLM decides if follow-ups needed based on coverage gaps (in _create_follow_up_tasks)
        - Only check: coverage score < 95% and room in workload
        - Aligns with "no hardcoded limits" design philosophy

        Args:
            task: Completed task to evaluate
            total_pending_workload: Total pending tasks (queue + currently executing batch)

        Returns:
            True if follow-ups should be created (LLM will decide actual count 0-N)
        """
        # Phase 5: Check if LLM assessment suggests coverage is excellent
        # No quantitative threshold - trust LLM qualitative assessment
        coverage_decisions = task.metadata.get("coverage_decisions", [])
        if coverage_decisions:
            latest_coverage = coverage_decisions[-1]
            # If LLM said "stop" with no gaps, coverage is likely sufficient
            decision = latest_coverage.get("decision", "continue")
            gaps = latest_coverage.get("gaps_identified", [])
            if decision == "stop" and not gaps:
                logger.info(f"Skipping follow-ups for task {task.id}: Coverage assessment shows sufficient coverage (no critical gaps)")
                return False

        # Codex fix: Check TOTAL workload (completed + pending + would-be follow-ups)
        # This prevents follow-up explosion when parallel execution creates many tasks at once
        # Use configured limit or reasonable default (3) to avoid blocking follow-ups
        max_follow_ups = self.max_follow_ups_per_task if self.max_follow_ups_per_task is not None else 3
        total_workload_if_created = (
            len(self.completed_tasks) +  # Already completed
            total_pending_workload +      # Queue + current batch remainder
            max_follow_ups                # Would-be follow-ups
        )

        # Only check if there's room in workload - LLM decides if follow-ups are actually needed
        return total_workload_if_created < self.max_tasks

    async def _create_follow_up_tasks(self, parent_task: ResearchTask, current_task_id: int) -> List[ResearchTask]:
        """
        Create follow-up tasks based on coverage gaps using LLM intelligence.

        Improvements (2025-11-19):
        - LLM-powered gap analysis (not hardcoded entity concatenation)
        - Focus on INFORMATION gaps (timeline, process, conditions) not entity permutations
        - 0-N follow-ups based on coverage quality (no hardcoded limits)
        - Context-based query generation (same principles as task_decomposition.j2)
        """
        from core.prompt_loader import render_prompt

        # Extract coverage data
        coverage_decisions = parent_task.metadata.get("coverage_decisions", [])
        if not coverage_decisions:
            # No coverage data available - skip follow-ups (can't do gap analysis)
            logger.info(f"No coverage data for task {parent_task.id} - skipping follow-ups")
            return []

        # Get latest coverage assessment
        latest_coverage = coverage_decisions[-1]
        assessment_text = latest_coverage.get("assessment", "")
        gaps_identified = latest_coverage.get("gaps_identified", [])

        # Consolidate gaps from all coverage decisions
        all_gaps = []
        for decision in coverage_decisions:
            all_gaps.extend(decision.get("gaps_identified", []))

        # Remove duplicate gaps
        unique_gaps = list(dict.fromkeys(all_gaps))  # Preserves order

        # Gather all existing tasks to avoid duplicates (completed + queue)
        # This gives the LLM full context about what's already been explored
        existing_tasks = []
        for t in self.completed_tasks:
            existing_tasks.append({
                "id": t.id,
                "query": t.query,
                "status": "completed"
            })
        for t in self.task_queue:
            existing_tasks.append({
                "id": t.id,
                "query": t.query,
                "status": "pending"
            })

        # Render follow-up generation prompt
        prompt = render_prompt(
            "deep_research/follow_up_generation.j2",
            research_question=self.research_question,
            parent_task=parent_task,
            coverage_decisions=coverage_decisions,
            gaps_identified=unique_gaps,
            latest_assessment=assessment_text,  # Phase 5: Use prose, not score
            existing_tasks=existing_tasks  # NEW: Give LLM global task context
        )

        # Call LLM to generate follow-ups
        try:
            schema = {
                "type": "object",
                "properties": {
                    "follow_up_tasks": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "query": {"type": "string"},
                                "rationale": {"type": "string"}
                            },
                            "required": ["query", "rationale"],
                            "additionalProperties": False
                        }
                    },
                    "decision_reasoning": {"type": "string"}
                },
                "required": ["follow_up_tasks", "decision_reasoning"],
                "additionalProperties": False
            }

            response = await acompletion(
                model=config.get_model("query_generation"),
                messages=[{"role": "user", "content": prompt}],
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "strict": True,
                        "name": "follow_up_generation",
                        "schema": schema
                    }
                }
            )

            result = json.loads(response.choices[0].message.content)
            logger.info(f"Follow-up generation for task {parent_task.id}: {result['decision_reasoning']}")

        # Follow-up generation failure - acceptable to continue without follow-ups
        except Exception as e:
            logger.error(f"Follow-up generation failed for task {parent_task.id}: {type(e).__name__}: {e}", exc_info=True)
            return []

        # Build set of existing queries for deduplication
        existing_queries = set()
        for task in self.task_queue + self.completed_tasks:
            existing_queries.add(task.query.lower())

        # Create ResearchTask objects from LLM output
        follow_ups = []
        for task_data in result["follow_up_tasks"]:
            # Skip if duplicate query already exists
            if task_data["query"].lower() in existing_queries:
                logger.info(f"Skipping duplicate follow-up query: {task_data['query']}")
                continue

            follow_up = ResearchTask(
                id=current_task_id + len(follow_ups),
                query=task_data["query"],
                rationale=task_data["rationale"],
                parent_task_id=parent_task.id
            )

            # Log individual follow-up creation with full details for auditing
            print(f"   📌 [FOLLOW_UP] Task {follow_up.id} (parent: {parent_task.id}): {follow_up.query[:80]}")

            follow_ups.append(follow_up)
            existing_queries.add(task_data["query"].lower())

        print(f"✓ Created {len(follow_ups)} follow-up task(s) for task {parent_task.id}")
        return follow_ups

    def _save_research_output(self, question: str, result: Dict) -> str:
        """
        Save research output to timestamped directory.

        Creates directory structure:
        data/research_output/YYYY-MM-DD_HH-MM-SS_query_slug/
            ├── results.json       # Complete structured results
            ├── report.md          # Final synthesized report
            └── metadata.json      # Research metadata

        Args:
            question: Original research question
            result: Complete research results dict

        Returns:
            Path to output directory
        """
        import re
        from pathlib import Path

        # Create slug from question (first 50 chars, alphanumeric + hyphens)
        slug = re.sub(r'[^a-z0-9]+', '_', question.lower())[:50].strip('_')

        # Use start_time (research start) instead of datetime.now() (save time)
        # This ensures _save_research_output() uses the SAME timestamp as ExecutionLogger
        timestamp = self.start_time.strftime("%Y-%m-%d_%H-%M-%S")
        dir_name = f"{timestamp}_{slug}"
        output_path = Path(self.output_dir) / dir_name
        output_path.mkdir(parents=True, exist_ok=True)

        # Priority 2 Fix: Load and aggregate raw task result files (survive timeout)
        # 1. Check for raw task files in output directory
        raw_path = output_path / "raw"
        aggregated_results_by_task = {}

        if raw_path.exists():
            for raw_file in sorted(raw_path.glob("task_*.json")):
                try:
                    task_id = int(raw_file.stem.split("_")[1])
                    with open(raw_file, 'r', encoding='utf-8') as f:
                        aggregated_results_by_task[task_id] = json.load(f)
                    logger.info(f"Loaded raw task file: {raw_file.name}")
                # Exception caught - error logged, execution continues
                except Exception as e:
                    logger.warning(f"Failed to load raw task file {raw_file.name}: {e}", exc_info=True)

        # Fallback: if a per-task raw file is missing, synthesize it from per-source files
        # This prevents losing data when a task never wrote task_{id}_results.json
        if raw_path.exists():
            # Candidate task_ids from completed/failed tasks and already-aggregated ones
            candidate_task_ids = set(aggregated_results_by_task.keys())
            candidate_task_ids.update([t.id for t in (self.completed_tasks + self.failed_tasks)])

            for task_id in candidate_task_ids:
                if task_id in aggregated_results_by_task:
                    continue  # already have a consolidated file

                merged_results = []
                for src_file in sorted(raw_path.glob(f"*task{task_id}_*.json")):
                    try:
                        with open(src_file, "r", encoding="utf-8") as f:
                            data = json.load(f)
                        # Per-source files can be arrays (list of results) or dicts with "results"
                        if isinstance(data, list):
                            merged_results.extend(data)
                        elif isinstance(data, dict) and "results" in data:
                            merged_results.extend(data.get("results", []))
                        else:
                            logging.debug(f"Skipping unrecognized raw format: {src_file.name}")
                    # Exception caught - error logged, execution continues
                    except Exception as e:
                        logger.warning(f"Failed to load per-source file {src_file.name}: {e}", exc_info=True)

                if merged_results:
                    aggregated_results_by_task[task_id] = {
                        "total_results": len(merged_results),
                        "results": merged_results
                    }
                    logger.info(f"Synthesized task_{task_id}_results from per-source files ({len(merged_results)} items)")

        # 2. Merge with results_by_task from memory (in case some tasks didn't write raw files)
        for task_id, result_dict in self.results_by_task.items():
            if task_id not in aggregated_results_by_task:
                aggregated_results_by_task[task_id] = result_dict
            else:
                # Merge new results (e.g., hypotheses) with raw file contents
                merged_results = aggregated_results_by_task[task_id].get("results", []) + result_dict.get("results", [])
                aggregated_results_by_task[task_id]["results"] = merged_results
                aggregated_results_by_task[task_id]["total_results"] = len(merged_results)

        # 3. Update result dict to use aggregated data
        aggregated_total = sum(
            r.get('total_results', 0) for r in aggregated_results_by_task.values()
        )
        aggregated_results_list = []
        for r in aggregated_results_by_task.values():
            aggregated_results_list.extend(r.get('results', []))

        # Codex Fix: Deduplicate results by (url, title) to avoid inflated counts
        seen = {}
        deduplicated_results_list = []
        for result_item in aggregated_results_list:
            # Create unique key from URL and title (both normalized)
            url = (result_item.get('url') or '').strip().lower()
            title = (result_item.get('title') or '').strip().lower()
            key = (url, title)

            # Merge attribution if duplicate encountered
            if (url or title) and key in seen:
                existing = seen[key]
                # Normalize attribution fields
                attrs = set()
                for res in (existing, result_item):
                    if "hypothesis_ids" in res:
                        attrs.update(res.get("hypothesis_ids") or [])
                    if "hypothesis_id" in res:
                        attrs.add(res["hypothesis_id"])
                if attrs:
                    existing["hypothesis_ids"] = sorted(list(attrs))
                    existing.pop("hypothesis_id", None)
            else:
                if url or title:
                    seen[key] = result_item
                deduplicated_results_list.append(result_item)

        # Log deduplication stats (Codex Fix #2: Add console output for visibility)
        duplicates_removed = len(aggregated_results_list) - len(deduplicated_results_list)
        if duplicates_removed > 0:
            logger.info(f"Deduplication: Removed {duplicates_removed} duplicate results ({len(aggregated_results_list)} → {len(deduplicated_results_list)})")
            print(f"\n📊 Deduplication: Removed {duplicates_removed} duplicates ({len(aggregated_results_list)} → {len(deduplicated_results_list)} unique results)")

        # Use deduplicated list for counts and output
        aggregated_results_list = deduplicated_results_list
        aggregated_total = len(deduplicated_results_list)

        # Gap #2 Fix: Update BOTH result_to_save AND the incoming result dict
        # This ensures CLI output matches results.json counts
        result["total_results"] = aggregated_total  # Sync in-memory with disk (deduplicated count)
        result["results_by_task"] = aggregated_results_by_task  # Add aggregated data
        result["duplicates_removed"] = duplicates_removed  # Codex Fix #2: Add dedup stats visibility
        result["results_before_dedup"] = len(aggregated_results_list) + duplicates_removed

        # Timeline: build from dated items in results (simple event list)
        timeline_out = result.get("timeline", []) or []
        if not timeline_out:
            dated_items = []
            for item in deduplicated_results_list:
                if item.get("date") and item.get("url"):
                    dated_items.append({
                        "date": item.get("date"),
                        "title": item.get("title", "") or item.get("snippet", "")[:80],
                        "url": item.get("url", "")
                    })
            # Keep top 10 by date order as provided
            timeline_out = dated_items[:10]
            result["timeline"] = timeline_out

        # Update result dict with aggregated counts
        # Phase 3B: collect hypotheses + execution summaries for persistence
        hypotheses_by_task = {}
        hypothesis_execution_summary = {}
        # Phase 3C+ evidence snapshots (use safe defaults to avoid UnboundLocal errors)
        key_documents = result.get("key_documents", []) or []
        source_counts_out = result.get("source_counts", {}) or {}
        hypothesis_findings_out = result.get("hypothesis_findings", []) or []
        for task in (self.completed_tasks + self.failed_tasks):
            if task.hypotheses:
                hypotheses_by_task[task.id] = task.hypotheses
            if task.hypothesis_runs:
                hypothesis_execution_summary[task.id] = task.hypothesis_runs

        result_to_save = {
            **result,
            "total_results": aggregated_total,
            "results_by_task": aggregated_results_by_task,
            "results": aggregated_results_list,  # Gap #3 Fix: Add flat results array for easy iteration
            "entity_relationships": {k: list(v) for k, v in result.get("entity_relationships", {}).items()},
            "hypotheses_by_task": hypotheses_by_task,
            "hypothesis_execution_summary": hypothesis_execution_summary,
            "key_documents": key_documents,
            "source_counts": source_counts_out,
            "hypothesis_findings": hypothesis_findings_out,
            "timeline": timeline_out
        }

        # 4. Save complete JSON results (for programmatic access)
        results_file = output_path / "results.json"
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(result_to_save, f, indent=2, ensure_ascii=False)

        # 2. Save markdown report (for human reading)
        report_file = output_path / "report.md"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(result.get("report", "Report unavailable."))

        # 3. Save metadata (research parameters + execution info)
        metadata_file = output_path / "metadata.json"
        metadata = {
            "research_question": question,
            "timestamp": timestamp,
            "engine_config": {
                "max_tasks": self.max_tasks,
                "max_retries_per_task": self.max_retries_per_task,
                "max_time_minutes": self.max_time_minutes,
                "min_results_per_task": self.min_results_per_task,
                "max_concurrent_tasks": self.max_concurrent_tasks,
                "hypothesis_branching_enabled": self.hypothesis_branching_enabled,
                "hypothesis_mode": getattr(self, "hypothesis_mode", "off"),
                "max_hypotheses_per_task": self.max_hypotheses_per_task,
                # Phase 4: Manager-Agent configuration
                "task_prioritization_enabled": self.manager_enabled,
                "saturation_detection_enabled": self.saturation_detection_enabled,
                "saturation_check_interval": self.saturation_check_interval,
                "saturation_confidence_threshold": self.saturation_confidence_threshold
            },
            # Phase 4A: Task execution order analysis
            "task_execution_order": [
                {
                    "task_id": task.id,
                    "query": task.query,
                    "priority": task.priority,
                    "priority_reasoning": task.priority_reasoning,
                    "estimated_value": task.estimated_value,
                    "estimated_redundancy": task.estimated_redundancy,
                    "actual_results": len(task.accumulated_results),
                    # Phase 5: Store qualitative assessment instead of numeric score
                    "final_assessment": task.metadata.get("coverage_decisions", [{}])[-1].get("assessment", "")[:200] if task.metadata.get("coverage_decisions") else None,
                    "final_gaps": task.metadata.get("coverage_decisions", [{}])[-1].get("gaps_identified", []) if task.metadata.get("coverage_decisions") else [],
                    "parent_task_id": task.parent_task_id
                }
                for task in (self.completed_tasks + self.failed_tasks)
            ],
            "execution_summary": {
                "tasks_executed": result["tasks_executed"],
                "tasks_failed": result["tasks_failed"],
                "total_results": result["total_results"],
                "elapsed_minutes": result["elapsed_minutes"],
                "sources_searched": result["sources_searched"],
                "entities_discovered_count": len(result["entities_discovered"]),
                "duplicates_removed": duplicates_removed,
                "results_before_dedup": len(aggregated_results_list) + duplicates_removed
            }
        }

        # Phase 3A/B: Add hypotheses and execution summaries if generated
        if self.hypothesis_branching_enabled:
            hypotheses_by_task = {}
            hypothesis_execution_summary = {}
            for task in (self.completed_tasks + self.failed_tasks):
                if task.hypotheses:
                    hypotheses_by_task[task.id] = task.hypotheses
                if task.hypothesis_runs:
                    hypothesis_execution_summary[task.id] = task.hypothesis_runs

            if hypotheses_by_task:
                metadata["hypotheses_by_task"] = hypotheses_by_task
            if hypothesis_execution_summary:
                metadata["hypothesis_execution_summary"] = hypothesis_execution_summary

        # Phase 3C: Add coverage decisions if available
        coverage_decisions_by_task = {}
        for task in (self.completed_tasks + self.failed_tasks):
            if task.metadata.get("coverage_decisions"):
                coverage_decisions_by_task[task.id] = task.metadata["coverage_decisions"]

        if coverage_decisions_by_task:
            metadata["coverage_decisions_by_task"] = coverage_decisions_by_task

        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

        logger.info(f"Research output saved to: {output_path}")
        return str(output_path)

    def _generate_global_coverage_summary(self) -> str:
        """
        Generate concise summary of overall research coverage (Phase 4A).

        Used for task prioritization context - helps manager LLM understand
        what's been found and what gaps remain.

        Returns:
            Text summary for prioritization/saturation context
        """
        if not self.completed_tasks:
            return "No tasks completed yet - initial decomposition."

        # Phase 5: Collect qualitative assessments instead of numeric scores
        recent_assessments = []
        for task in self.completed_tasks[-3:]:  # Last 3 tasks
            coverage_decisions = task.metadata.get("coverage_decisions", [])
            if coverage_decisions:
                latest = coverage_decisions[-1]
                assessment = latest.get("assessment", "")
                if assessment:
                    # Extract key phrases (first sentence or ~100 chars)
                    brief = assessment.split('.')[0][:100]
                    recent_assessments.append(f"Task {task.id}: {brief}")

        # Collect all gaps across tasks
        all_gaps = []
        for task in self.completed_tasks:
            coverage_decisions = task.metadata.get("coverage_decisions", [])
            for decision in coverage_decisions:
                all_gaps.extend(decision.get("gaps_identified", []))

        # Deduplicate gaps while preserving order
        unique_gaps = list(dict.fromkeys(all_gaps))[:5]  # Top 5 unique gaps

        # Calculate total results
        total_results = sum(len(t.accumulated_results) for t in self.completed_tasks)

        # Build qualitative summary
        summary_parts = [
            f"Completed {len(self.completed_tasks)} tasks, {total_results} results found"
        ]

        if recent_assessments:
            summary_parts.append(f"Recent progress: {'; '.join(recent_assessments[:2])}")

        if unique_gaps:
            summary_parts.append(f"Key gaps remaining: {'; '.join(unique_gaps[:3])}")

        return ". ".join(summary_parts) + "."

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
            - critical_gaps_remaining: List[str]
        """
        if len(self.completed_tasks) < 3:
            # Too early to assess saturation
            return {
                "saturated": False,
                "confidence": 100,
                "rationale": "Too few tasks completed to assess saturation (need 3+)",
                "recommendation": "continue_full",
                "recommended_additional_tasks": 5,
                "critical_gaps_remaining": ["Early stage - continue exploration"]
            }

        # Prepare recent task summaries (last 5 tasks)
        recent_tasks = []
        for task in self.completed_tasks[-5:]:
            coverage_decisions = task.metadata.get("coverage_decisions", [])
            latest_coverage = coverage_decisions[-1] if coverage_decisions else {}

            # Calculate new vs duplicate results from hypothesis runs
            # Bug #4 fix: Fallback to accumulated_results if no hypothesis runs
            if task.hypothesis_runs:
                total_results = sum(run.get("results_count", 0) for run in task.hypothesis_runs)
                new_results = sum(
                    run.get("delta_metrics", {}).get("results_new", 0)
                    for run in task.hypothesis_runs
                )
                duplicate_results = total_results - new_results
                incremental_value = int(new_results / total_results * 100) if total_results > 0 else 0
            else:
                # No hypothesis mode - use accumulated results
                total_results = len(task.accumulated_results)
                new_results = total_results  # Can't calculate delta without hypothesis metrics
                duplicate_results = 0
                incremental_value = 100  # Conservative: assume all new

            # Phase 5: Use qualitative assessment instead of numeric score
            assessment_text = latest_coverage.get("assessment", "No assessment available")
            gaps = latest_coverage.get("gaps_identified", [])

            recent_tasks.append({
                "id": task.id,
                "query": task.query,
                "results_count": len(task.accumulated_results),
                "new_results": new_results,
                "duplicate_results": duplicate_results,
                "assessment": assessment_text,
                "gaps_remaining": gaps,
                "incremental_value": incremental_value
            })

        # Prepare pending task summaries
        pending_summaries = [
            {
                "priority": t.priority,
                "query": t.query,
                "estimated_value": t.estimated_value,
                "estimated_redundancy": t.estimated_redundancy
            }
            for t in self.task_queue[:10]  # Top 10 pending
        ]

        # Calculate stats
        total_results = sum(len(t.accumulated_results) for t in self.completed_tasks)
        total_entities = len(set().union(*[set(t.entities_found or []) for t in self.completed_tasks]))

        # Phase 5: Collect qualitative assessments instead of numeric scores
        coverage_assessments = []
        for task in self.completed_tasks:
            coverage_decisions = task.metadata.get("coverage_decisions", [])
            if coverage_decisions:
                latest = coverage_decisions[-1]
                assessment = latest.get("assessment", "")
                gaps = latest.get("gaps_identified", [])
                if assessment:
                    coverage_assessments.append({
                        "task_id": task.id,
                        "assessment": assessment[:200],  # Truncate for brevity
                        "gaps": gaps
                    })

        elapsed_minutes = (datetime.now() - self.start_time).total_seconds() / 60

        # Render prompt
        prompt = render_prompt(
            "deep_research/saturation_detection.j2",
            research_question=self.research_question,
            completed_count=len(self.completed_tasks),
            total_results=total_results,
            total_entities=total_entities,
            coverage_assessments=coverage_assessments,
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
                "recommended_additional_tasks": {"type": "integer", "minimum": 0, "maximum": 10},
                "critical_gaps_remaining": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of critical gaps if not saturated"
                }
            },
            "required": ["saturated", "confidence", "rationale", "evidence", "recommendation", "recommended_additional_tasks", "critical_gaps_remaining"],
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
                if result['critical_gaps_remaining']:
                    print(f"   Critical gaps: {', '.join(result['critical_gaps_remaining'][:3])}")

            return result

        # Exception caught - error logged, execution continues
        except Exception as e:
            logger.error(f"Saturation detection failed: {type(e).__name__}: {e}", exc_info=True)
            print(f"⚠️  Saturation check failed, defaulting to continue")
            import traceback
            logger.error(traceback.format_exc(), exc_info=True)
            # On error, assume not saturated (continue research)
            return {
                "saturated": False,
                "confidence": 0,
                "rationale": f"Saturation check failed ({type(e).__name__}), defaulting to continue",
                "recommendation": "continue_full",
                "recommended_additional_tasks": 3,
                "critical_gaps_remaining": ["Saturation check error - continuing"]
            }

    # NOTE: _format_synthesis_json_to_markdown and _synthesize_report moved to ReportSynthesizerMixin


# Example usage
async def main():
    """Test deep research with complex question."""

    # Progress callback for live updates
    def show_progress(progress: ResearchProgress):
        """Display progress updates."""
        print(f"\n{'='*80}")
        print(f"[{progress.timestamp}] {progress.event.upper()}")
        print(f"Message: {progress.message}")
        if progress.task_id is not None:
            print(f"Task ID: {progress.task_id}")
        if progress.data:
            print(f"Data: {json.dumps(progress.data, indent=2)}")
        print('='*80)

    # Create engine
    engine = SimpleDeepResearch(
        max_tasks=10,
        max_retries_per_task=2,
        max_time_minutes=60,
        min_results_per_task=3,
        progress_callback=show_progress
    )

    # Test question (complex, multi-part)
    question = "What is the relationship between JSOC and CIA Title 50 operations?"

    print(f"\n{'#'*80}")
    print(f"# DEEP RESEARCH TEST")
    print(f"# Question: {question}")
    print(f"{'#'*80}\n")

    # Execute research
    result = await engine.research(question)

    # Display report
    print("\n" + "="*80)
    print("FINAL REPORT")
    print("="*80)
    print(result['report'])

    print("\n" + "="*80)
    print("RESEARCH STATISTICS")
    print("="*80)
    print(f"Tasks Executed: {result['tasks_executed']}")
    print(f"Tasks Failed: {result['tasks_failed']}")
    print(f"Total Results: {result['total_results']}")
    print(f"Entities Discovered: {len(result['entities_discovered'])}")
    print(f"Entity Relationships: {len(result['entity_relationships'])}")
    print(f"Sources Searched: {', '.join(result['sources_searched'])}")
    print(f"Elapsed Time: {result['elapsed_minutes']:.1f} minutes")

    print("\n" + "="*80)
    print("ENTITY NETWORK")
    print("="*80)
    for entity, related in list(result['entity_relationships'].items())[:10]:
        print(f"{entity}:")
        print(f"  → {', '.join(related[:5])}")


if __name__ == "__main__":
    asyncio.run(main())
