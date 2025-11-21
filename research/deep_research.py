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

# MCP imports
from fastmcp import Client
from integrations.mcp import government_mcp, social_mcp

# Execution logging
from research.execution_logger import ExecutionLogger

# Jinja2 prompts
from core.prompt_loader import render_prompt

load_dotenv()


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


class SimpleDeepResearch:
    """
    Deep research engine with task decomposition and entity tracking.

    No external frameworks - builds on existing AdaptiveSearchEngine.

    Features:
    - Decomposes complex questions into subtasks
    - Retries failed searches with reformulated queries
    - Tracks entity relationships across tasks
    - Streams live progress for human course-correction
    - Configurable limits (max tasks, max time, max retries)
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
                logging.warning("⚠️  hypothesis_branching.enabled is deprecated, use mode: 'planning' instead")
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

        # Load API keys from environment
        self.api_keys = {
            "sam": os.getenv("SAM_GOV_API_KEY"),
            "dvids": os.getenv("DVIDS_API_KEY"),
            "usajobs": os.getenv("USAJOBS_API_KEY"),
            "brave_search": os.getenv("BRAVE_SEARCH_API_KEY"),
        }

        # MCP tool configuration
        self.mcp_tools = [
            {"name": "search_sam", "server": government_mcp.mcp, "api_key_name": "sam"},
            {"name": "search_dvids", "server": government_mcp.mcp, "api_key_name": "dvids"},
            {"name": "search_usajobs", "server": government_mcp.mcp, "api_key_name": "usajobs"},
            {"name": "search_clearancejobs", "server": government_mcp.mcp, "api_key_name": None},
            {"name": "search_twitter", "server": social_mcp.mcp, "api_key_name": None},
            {"name": "search_reddit", "server": social_mcp.mcp, "api_key_name": None},
            {"name": "search_discord", "server": social_mcp.mcp, "api_key_name": None},
        ]

        # Web search tools (non-MCP)
        self.web_tools = [
            {"name": "brave_search", "type": "web", "api_key_name": "brave_search"}
        ]

        # Human-friendly labels and descriptions for each tool
        self.tool_name_to_display = {
            "search_sam": "SAM.gov",
            "search_dvids": "DVIDS",
            "search_usajobs": "USAJobs",
            "search_clearancejobs": "ClearanceJobs",
            "search_twitter": "Twitter",
            "search_reddit": "Reddit",
            "search_discord": "Discord",
            "brave_search": "Brave Search"
        }
        self.tool_display_to_name = {v: k for k, v in self.tool_name_to_display.items()}

        # Build reverse source map: display name → tool name (Phase 3B)
        self.display_to_tool_map = {
            display: tool_name
            for tool_name, display in self.tool_name_to_display.items()
        }
        self.tool_descriptions = {
            "search_sam": "U.S. federal contracting opportunities and awards. Search government procurement, RFPs, solicitations, contract listings.",
            "search_dvids": "Military multimedia archive with photos and videos of military operations, ceremonies, exercises.",
            "search_usajobs": "Federal job listings. Current government positions and hiring announcements.",
            "search_clearancejobs": "Defense contractor jobs requiring security clearances. Private sector positions at aerospace and defense companies.",
            "search_twitter": "Social media posts and announcements from official accounts and public figures. Good for real-time updates and official statements.",
            "search_reddit": "Community discussions and OSINT analysis. Good for investigative threads, technical discussions, and community insights on government programs and contractors.",
            "search_discord": "OSINT community knowledge and technical tips from specialized servers. Good for specialized OSINT techniques and community expertise.",
            "brave_search": "General web search. Good for official documentation, reference articles, news, and background information."
        }

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

        # Step 1: Decompose question into initial tasks
        try:
            self._emit_progress("decomposition_started", "Breaking question into research tasks...")
            self.task_queue = await self._decompose_question(question)
            self._emit_progress(
                "decomposition_complete",
                f"Created {len(self.task_queue)} initial tasks",
                data={"tasks": [{"id": t.id, "query": t.query} for t in self.task_queue]}
            )
        except Exception as e:
            import traceback
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
                    except Exception as log_error:
                        logging.warning(f"Failed to log saturation assessment: {log_error}")

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
                            logging.info(f"Task {task.id} timed out; persisted partial results ({len(task.accumulated_results)}) to {raw_file}")
                        except Exception as persist_error:
                            logging.warning(f"Failed to persist partial results for timed-out task {task.id}: {persist_error}")
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
                        except Exception as log_error:
                            logging.warning(f"Failed to log task timeout for task {task.id}: {log_error}")
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
                            logging.info(f"Task {task.id} exception; persisted partial results ({len(task.accumulated_results)}) to {raw_file}")
                        except Exception as persist_error:
                            logging.warning(f"Failed to persist partial results for errored task {task.id}: {persist_error}")
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
                        except Exception as log_error:
                            logging.warning(f"Failed to log task exception for task {task.id}: {log_error}")
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
                        except Exception as entity_error:
                            # Log error but don't fail task - entity extraction is non-critical
                            import traceback
                            logging.error(
                                f"Entity extraction failed for task {task.id}: {type(entity_error).__name__}: {str(entity_error)}\n"
                                f"Traceback: {traceback.format_exc()}"
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
                                        research_question=self.research_question
                                    )
                                    follow_up.hypotheses = hypotheses_result
                                    print(f"   ✓ Follow-up {follow_up.id}: Generated {len(hypotheses_result['hypotheses'])} hypothesis/hypotheses")
                                except Exception as e:
                                    print(f"   ⚠️  Follow-up {follow_up.id}: Hypothesis generation failed - {type(e).__name__}: {e}")
                                    logging.warning(f"Hypothesis generation failed for follow-up {follow_up.id}: {type(e).__name__}: {e}")
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
        except Exception as e:
            import traceback
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
            except Exception as e:
                logging.error(f"Failed to save research output: {type(e).__name__}: {str(e)}")
                import traceback
                logging.error(traceback.format_exc())
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
                except Exception as fallback_error:
                    logging.error(f"Fallback save failed: {type(fallback_error).__name__}: {fallback_error}")

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
                        research_question=question
                    )
                    task.hypotheses = hypotheses_result
                    print(f"   ✓ Task {task.id}: Generated {len(hypotheses_result['hypotheses'])} hypothesis/hypotheses")
                except Exception as e:
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

    async def _generate_hypotheses(self, task_query: str, research_question: str) -> Dict[str, Any]:
        """
        Generate 1-5 investigative hypotheses for a research subtask.

        Phase 3A: Foundation - Hypothesis generation only (no execution yet)

        Args:
            task_query: The specific subtask query to generate hypotheses for
            research_question: The original user research question (for context)

        Returns:
            Dict containing:
                - hypotheses: List of hypothesis objects (1-5 items)
                - coverage_assessment: Why this set provides sufficient coverage
        """
        # Get available sources for hypothesis generation
        available_sources = self._get_available_source_names()

        # Render hypothesis generation prompt
        prompt = render_prompt(
            "deep_research/hypothesis_generation.j2",
            research_question=research_question,
            task_query=task_query,
            available_sources=available_sources,
            max_hypotheses=self.max_hypotheses_per_task
        )

        # Define JSON schema for hypothesis structure
        schema = {
            "type": "object",
            "properties": {
                "hypotheses": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": self.max_hypotheses_per_task,
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "integer", "description": "Hypothesis ID (1, 2, 3, ...)"},
                            "statement": {"type": "string", "description": "What this hypothesis is looking for (1-2 sentences)"},
                            "confidence": {"type": "integer", "minimum": 0, "maximum": 100, "description": "Confidence this pathway will yield results (0-100%)"},
                            "confidence_reasoning": {"type": "string", "description": "Why this confidence level (1 sentence)"},
                            "search_strategy": {
                                "type": "object",
                                "properties": {
                                    "sources": {
                                        "type": "array",
                                        "items": {"type": "string"},
                                        "description": "List of database integration names to query"
                                    },
                                    "signals": {
                                        "type": "array",
                                        "items": {"type": "string"},
                                        "description": "Keywords/patterns that indicate relevance"
                                    },
                                    "expected_entities": {
                                        "type": "array",
                                        "items": {"type": "string"},
                                        "description": "Organizations/people/programs/technologies expected if hypothesis succeeds"
                                    }
                                },
                                "required": ["sources", "signals", "expected_entities"],
                                "additionalProperties": False
                            },
                            "exploration_priority": {"type": "integer", "minimum": 1, "description": "Order to explore (1=first, 2=second, etc.)"},
                            "priority_reasoning": {"type": "string", "description": "Why this exploration order (1 sentence)"}
                        },
                        "required": ["id", "statement", "confidence", "confidence_reasoning", "search_strategy", "exploration_priority", "priority_reasoning"],
                        "additionalProperties": False
                    },
                    "minItems": 1,
                    "maxItems": 5
                },
                "coverage_assessment": {
                    "type": "string",
                    "description": "Why this set of hypotheses provides sufficient coverage"
                }
            },
            "required": ["hypotheses", "coverage_assessment"],
            "additionalProperties": False
        }

        # Call LLM with hypothesis generation prompt
        response = await acompletion(
            model=config.get_model("task_decomposition"),  # Use same model as task decomposition
            messages=[{"role": "user", "content": prompt}],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "strict": True,
                    "name": "hypothesis_generation",
                    "schema": schema
                }
            }
        )

        # Parse response
        result = json.loads(response.choices[0].message.content)

        # Log hypothesis generation
        hypothesis_count = len(result["hypotheses"])
        print(f"\n🔬 Generated {hypothesis_count} investigative hypothesis/hypotheses:")
        for hyp in result["hypotheses"]:
            print(f"   Hypothesis {hyp['id']}: {hyp['statement']}")
            print(f"   → Confidence: {hyp['confidence']}% - {hyp['confidence_reasoning']}")
            print(f"   → Priority: {hyp['exploration_priority']} - {hyp['priority_reasoning']}")
            print(f"   → Sources: {', '.join(hyp['search_strategy']['sources'])}")
            print()

        print(f"📊 Coverage Assessment: {result['coverage_assessment']}\n")

        return result

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

        except Exception as e:
            logging.error(f"Task prioritization failed: {type(e).__name__}: {e}")
            print(f"⚠️  Prioritization failed, using default priority order")
            import traceback
            logging.error(traceback.format_exc())
            # On error, return tasks as-is (FIFO order)
            return tasks

    def _map_hypothesis_sources(self, hypothesis: Dict) -> List[str]:
        """
        Map hypothesis source display names to MCP tool names (Phase 3B).

        Args:
            hypothesis: Hypothesis dict with search_strategy.sources (display names)

        Returns:
            List of MCP tool names (e.g., ["search_usajobs", "search_twitter"])

        Logs errors for unknown sources and skips them.
        """
        display_sources = hypothesis.get("search_strategy", {}).get("sources", [])
        tool_names = []

        for display_name in display_sources:
            tool_name = self.display_to_tool_map.get(display_name)
            if tool_name:
                tool_names.append(tool_name)
            else:
                logging.warning(f"⚠️  Hypothesis {hypothesis.get('id', '?')} specified unknown source '{display_name}' - skipping")

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

        deduplicated = []
        for result in results:
            url = result.get("url")
            if not url:
                # No URL to deduplicate on, keep as-is
                result["hypothesis_id"] = hypothesis_id
                deduplicated.append(result)
                continue

            # Check for duplicate URL in current batch
            existing = None
            for r in deduplicated:
                if r.get("url") == url:
                    existing = r
                    break

            if existing:
                # Duplicate within batch - add to hypothesis_ids
                if "hypothesis_ids" not in existing:
                    # Convert single hypothesis_id to array
                    existing["hypothesis_ids"] = [existing.pop("hypothesis_id", hypothesis_id), hypothesis_id]
                elif hypothesis_id not in existing["hypothesis_ids"]:
                    existing["hypothesis_ids"].append(hypothesis_id)
            else:
                # New result - tag with hypothesis_id
                result["hypothesis_id"] = hypothesis_id
                deduplicated.append(result)

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

    async def _generate_hypothesis_query(
        self,
        hypothesis: Dict,
        source_tool_name: str,
        research_question: str,
        task_query: str,
        task: 'ResearchTask'
    ) -> Optional[str]:
        """
        Generate source-specific query for hypothesis execution (Phase 3B).

        Args:
            hypothesis: Hypothesis dict with statement, confidence, search_strategy
            source_tool_name: MCP tool name (e.g., "search_usajobs")
            research_question: Original research question
            task_query: Task query this hypothesis belongs to

        Returns:
            Query string optimized for this source, or None on error
        """
        source_display_name = self.tool_name_to_display.get(source_tool_name, source_tool_name)

        # Render prompt with hypothesis context
        prompt = render_prompt(
            "deep_research/hypothesis_query_generation.j2",
            hypothesis_statement=hypothesis["statement"],
            research_question=research_question,
            task_query=task_query,
            hypothesis_confidence=hypothesis["confidence"],
            hypothesis_sources=hypothesis["search_strategy"]["sources"],
            hypothesis_signals=hypothesis["search_strategy"]["signals"],
            hypothesis_entities=hypothesis["search_strategy"]["expected_entities"],
            source_display_name=source_display_name
        )

        # Define JSON schema for query generation
        schema = {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The optimized search query string"
                },
                "reasoning": {
                    "type": "string",
                    "description": "1-2 sentences explaining why this query will test the hypothesis"
                }
            },
            "required": ["query", "reasoning"],
            "additionalProperties": False
        }

        try:
            # Call LLM to generate query
            response = await acompletion(
                model=config.get_model("query_generation"),
                messages=[{"role": "user", "content": prompt}],
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "hypothesis_query",
                        "strict": True,
                        "schema": schema
                    }
                }
            )

            result = json.loads(response.choices[0].message.content)

            # Log to structured log
            if self.logger:
                self.logger.log_hypothesis_query_generation(
                    task_id=task.id,
                    hypothesis_id=hypothesis['id'],
                    source_name=source_display_name,
                    query=result['query'],
                    reasoning=result['reasoning']
                )

            # Also print for real-time visibility
            print(f"      Query: '{result['query']}'")
            print(f"      Reasoning: {result['reasoning']}")

            return result["query"]

        except Exception as e:
            logging.error(f"❌ Hypothesis {hypothesis['id']} query generation failed for {source_display_name}: {type(e).__name__}: {e}")
            return None

    async def _generate_initial_query(
        self,
        hypothesis: Dict[str, Any],
        source_name: str,
        source_metadata: Dict[str, Any]
    ) -> Dict[str, str]:
        """
        Generate first query from hypothesis (no query history yet).

        This is separate from _generate_next_query_or_stop because:
        - First query has no history to reason from
        - Uses hypothesis statement + source metadata only
        - Simpler prompt without saturation decision

        Args:
            hypothesis: Hypothesis dictionary
            source_name: Name of the source
            source_metadata: Metadata about the source

        Returns:
            {
                "query": str,
                "reasoning": str
            }
        """
        from core.prompt_loader import render_prompt

        # Use existing hypothesis query generation prompt
        prompt = render_prompt(
            'deep_research/hypothesis_query_generation.j2',
            hypothesis_statement=hypothesis['statement'],
            source_name=source_name,
            source_metadata=source_metadata,
            search_strategy=hypothesis.get('search_strategy', {}),
            information_gaps=hypothesis.get('information_gaps', [])
        )

        response = await acompletion(
            model=config.get_model("query_generation"),
            messages=[{"role": "user", "content": prompt}],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "initial_query",
                    "strict": True,
                    "schema": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string"},
                            "reasoning": {"type": "string"}
                        },
                        "required": ["query", "reasoning"]
                    }
                }
            }
        )

        result = json.loads(response.choices[0].message.content)
        return result

    async def _generate_next_query_or_stop(
        self,
        task: ResearchTask,
        hypothesis: Dict[str, Any],
        source_name: str,
        query_history: List[Dict],
        source_metadata: Dict,
        total_results_accepted: int
    ) -> Dict[str, Any]:
        """
        LLM decides: continue with next query or stop (saturated).

        Args:
            task: Research task
            hypothesis: Hypothesis dictionary
            source_name: Name of the source
            query_history: List of previous query attempts
            source_metadata: Metadata about the source
            total_results_accepted: Total results accepted so far

        Returns:
            {
                "decision": "SATURATED" | "CONTINUE",
                "reasoning": "...",
                "confidence": 0-100,
                "existence_confidence": 0-100,
                "next_query_suggestion": "...",  # if CONTINUE
                "next_query_reasoning": "...",   # if CONTINUE
                "expected_value": "high" | "medium" | "low",
                "remaining_gaps": [...]  # Updated list of info gaps
            }
        """
        from core.prompt_loader import render_prompt

        # NOTE: information_gaps should be updated dynamically:
        # - Initial gaps from hypothesis generation
        # - LLM updates "remaining_gaps" field after each query
        # - Caller updates hypothesis['information_gaps'] with remaining_gaps
        # This enables adaptive query generation targeting unaddressed gaps

        # Render saturation prompt
        prompt = render_prompt(
            'deep_research/source_saturation.j2',
            hypothesis_statement=hypothesis['statement'],
            source_name=source_name,
            source_metadata=source_metadata,
            query_history=query_history,
            total_results_accepted=total_results_accepted,
            information_gaps=hypothesis.get('information_gaps', [])
        )

        # LLM decision
        response = await acompletion(
            model=config.get_model("query_generation"),
            messages=[{"role": "user", "content": prompt}],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "saturation_decision",
                    "strict": True,
                    "schema": {
                        "type": "object",
                        "properties": {
                            "decision": {"type": "string", "enum": ["SATURATED", "CONTINUE"]},
                            "reasoning": {"type": "string"},
                            "confidence": {"type": "integer", "minimum": 0, "maximum": 100},
                            "existence_confidence": {"type": "integer", "minimum": 0, "maximum": 100},
                            "next_query_suggestion": {"type": "string"},
                            "next_query_reasoning": {"type": "string"},
                            "expected_value": {"type": "string", "enum": ["high", "medium", "low"]},
                            "remaining_gaps": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Updated list of information gaps still unaddressed"
                            }
                        },
                        "required": ["decision", "reasoning", "confidence"]
                    }
                }
            }
        )

        decision = json.loads(response.choices[0].message.content)
        return decision

    async def _execute_source_with_saturation(
        self,
        task_id: int,
        task: ResearchTask,
        hypothesis: Dict[str, Any],
        source_name: str
    ) -> List[Dict[str, Any]]:
        """
        Execute queries against single source until saturated.

        Args:
            task_id: Task ID
            task: Research task
            hypothesis: Hypothesis dictionary
            source_name: Name of the source

        Returns:
            List of accepted results from all queries
        """
        from integrations.source_metadata import SOURCE_METADATA

        query_history = []
        all_results = []
        seen_result_urls = set()  # Track URLs for within-source deduplication
        start_time = time.time()

        # Get source-specific limits
        max_queries = self.max_queries_per_source.get(source_name, 5)
        max_time = self.max_time_per_source_seconds
        source_metadata = SOURCE_METADATA.get(source_name, {})

        # Log saturation start
        if self.logger:
            self.logger.log_source_saturation_start(
                task_id=task_id,
                hypothesis_id=hypothesis.get('id'),
                source_name=source_name,
                max_queries=max_queries,
                max_time_seconds=max_time
            )

        while True:  # ✅ No hardcoded loop count
            query_num = len(query_history) + 1

            try:
                # FIRST QUERY: Different logic than subsequent queries
                if len(query_history) == 0:
                    # Generate initial query from hypothesis (no history yet)
                    initial = await self._generate_initial_query(
                        hypothesis=hypothesis,
                        source_name=source_name,
                        source_metadata=source_metadata
                    )
                    query_decision = {
                        'decision': 'CONTINUE',
                        'reasoning': 'Initial query for hypothesis',
                        'next_query_suggestion': initial['query'],
                        'next_query_reasoning': initial['reasoning'],
                        'confidence': 100,
                        'expected_value': 'high'
                    }
                else:
                    # SUBSEQUENT QUERIES: Check saturation and generate next query
                    query_decision = await self._generate_next_query_or_stop(
                        task=task,
                        hypothesis=hypothesis,
                        source_name=source_name,
                        query_history=query_history,
                        source_metadata=source_metadata,
                        total_results_accepted=len(all_results)
                    )

                    # Update hypothesis information_gaps dynamically (if provided)
                    if 'remaining_gaps' in query_decision:
                        hypothesis['information_gaps'] = query_decision['remaining_gaps']

                    # PRIMARY EXIT: LLM says saturated
                    if query_decision['decision'] == 'SATURATED':
                        if self.logger:
                            self.logger.log_source_saturation_complete(
                                task_id=task_id,
                                hypothesis_id=hypothesis.get('id'),
                                source_name=source_name,
                                exit_reason='llm_saturated',
                                queries_executed=len(query_history),
                                results_accepted=len(all_results),
                                saturation_reasoning=query_decision['reasoning'],
                                decision_confidence=query_decision.get('confidence', 0)
                            )
                        break

            except Exception as e:
                logging.error(f"Error generating query for {source_name}: {e}")
                if self.logger:
                    self.logger.log_source_saturation_complete(
                        task_id=task_id,
                        hypothesis_id=hypothesis.get('id'),
                        source_name=source_name,
                        exit_reason='query_generation_error',
                        queries_executed=len(query_history),
                        results_accepted=len(all_results),
                        saturation_reasoning=f"Query generation failed: {str(e)}"
                    )
                break

            # Validate query suggestion exists
            query = query_decision.get('next_query_suggestion', '').strip()
            if not query:
                logging.warning(f"Empty query suggestion from LLM for {source_name}")
                if self.logger:
                    self.logger.log_source_saturation_complete(
                        task_id=task_id,
                        hypothesis_id=hypothesis.get('id'),
                        source_name=source_name,
                        exit_reason='empty_query_suggestion',
                        queries_executed=len(query_history),
                        results_accepted=len(all_results),
                        saturation_reasoning="LLM suggested empty query"
                    )
                break

            query_reasoning = query_decision.get('next_query_reasoning', '')

            if self.logger:
                self.logger.log_query_attempt(
                    task_id=task_id,
                    hypothesis_id=hypothesis.get('id'),
                    source_name=source_name,
                    query_num=query_num,
                    query=query,
                    reasoning=query_reasoning,
                    expected_value=query_decision.get('expected_value', 'unknown')
                )

            try:
                # Call source API using existing infrastructure
                # Map display name → tool name
                tool_name = self.tool_display_to_name.get(source_name)
                if not tool_name:
                    logging.error(f"Unknown source: {source_name}")
                    query_history.append({
                        'query': query,
                        'reasoning': query_reasoning,
                        'results_total': 0,
                        'results_accepted': 0,
                        'results_rejected': 0,
                        'error': f"Unknown source: {source_name}",
                        'effectiveness': 0
                    })
                    continue

                # Get limit from config
                limit = config.get_integration_limit(source_name)

                # Execute based on source type
                results = []
                if tool_name in [t["name"] for t in self.mcp_tools]:
                    # MCP tool path (SAM, DVIDS, USAJobs, etc.)
                    mcp_tool = next(t for t in self.mcp_tools if t["name"] == tool_name)
                    tool_result = await self._call_mcp_tool(
                        tool_config=mcp_tool,
                        query=query,
                        param_adjustments=None,
                        task_id=task_id,
                        attempt=0,
                        logger=self.logger
                    )
                    if tool_result.get("success"):
                        results = tool_result.get("results", [])
                    else:
                        error_msg = tool_result.get('error', 'Unknown error')
                        logging.error(f"MCP tool {source_name} failed: {error_msg}")
                        query_history.append({
                            'query': query,
                            'reasoning': query_reasoning,
                            'results_total': 0,
                            'results_accepted': 0,
                            'results_rejected': 0,
                            'error': error_msg,
                            'effectiveness': 0
                        })
                        continue

                elif tool_name == "brave_search":
                    # Brave search path (non-MCP)
                    results = await self._search_brave(query, max_results=limit)

            except Exception as e:
                logging.error(f"Source query failed for {source_name}: {e}")
                # Track failed attempt and continue
                query_history.append({
                    'query': query,
                    'reasoning': query_reasoning,
                    'results_total': 0,
                    'results_accepted': 0,
                    'results_rejected': 0,
                    'error': str(e),
                    'effectiveness': 0
                })
                continue  # Try next query

            # Filter results using EXISTING relevance evaluation
            if results:
                # Use hypothesis statement as the query context for filtering
                should_accept, relevance_reason, relevant_indices, should_continue, continuation_reason, reasoning_breakdown = await self._validate_result_relevance(
                    task_query=hypothesis['statement'],  # Use hypothesis statement
                    research_question=task.query,  # Parent task query
                    sample_results=results
                )

                # Transform to expected format
                filtered = {
                    'accepted_results': [results[i] for i in relevant_indices if i < len(results)] if should_accept else [],
                    'rejection_themes': [relevance_reason] if not should_accept else []
                }
            else:
                filtered = {'accepted_results': [], 'rejection_themes': []}

            # Deduplicate within source (track URLs seen)
            accepted = filtered.get('accepted_results', [])
            new_results = []
            duplicate_count = 0

            for result in accepted:
                result_url = result.get('url', '') or result.get('id', '')
                if result_url and result_url not in seen_result_urls:
                    new_results.append(result)
                    seen_result_urls.add(result_url)
                else:
                    duplicate_count += 1

            all_results.extend(new_results)

            # Track query attempt
            query_history.append({
                'query': query,
                'reasoning': query_reasoning,
                'results_total': len(results),
                'results_accepted': len(new_results),
                'results_rejected': len(results) - len(accepted),
                'results_duplicate': duplicate_count,
                'rejection_themes': filtered.get('rejection_themes', []),
                'effectiveness': len(new_results) / len(results) if results else 0
            })

            # SECONDARY EXIT: User-configured query limit
            if len(query_history) >= max_queries:
                if self.logger:
                    self.logger.log_source_saturation_complete(
                        task_id=task_id,
                        hypothesis_id=hypothesis.get('id'),
                        source_name=source_name,
                        exit_reason='max_queries_reached',
                        queries_executed=len(query_history),
                        results_accepted=len(all_results),
                        saturation_reasoning=f"Reached user-configured limit: {max_queries} queries"
                    )
                break

            # TERTIARY EXIT: User-configured time limit
            elapsed = time.time() - start_time
            if elapsed > max_time:
                if self.logger:
                    self.logger.log_source_saturation_complete(
                        task_id=task_id,
                        hypothesis_id=hypothesis.get('id'),
                        source_name=source_name,
                        exit_reason='time_limit_reached',
                        queries_executed=len(query_history),
                        results_accepted=len(all_results),
                        saturation_reasoning=f"Reached time limit: {max_time}s"
                    )
                break

        return all_results

    async def _execute_hypothesis(
        self,
        hypothesis: Dict,
        task: ResearchTask,
        research_question: str
    ) -> List[Dict]:
        """
        Execute a single hypothesis with its search strategy (Phase 3B).

        Args:
            hypothesis: Hypothesis dict with id, statement, search_strategy
            task: Parent task this hypothesis belongs to
            research_question: Original research question

        Returns:
            List of results with hypothesis_id tagging
        """
        hypothesis_id = hypothesis["id"]
        print(f"\n🔬 Executing Hypothesis {hypothesis_id}: {hypothesis['statement']}")

        # Map hypothesis sources (display names → tool names)
        source_tool_names = self._map_hypothesis_sources(hypothesis)
        if not source_tool_names:
            logging.warning(f"⚠️  Hypothesis {hypothesis_id}: No valid sources to search")
            return []

        # Execute sources (saturation mode or single-shot mode)
        all_results = []

        if self.query_saturation_enabled:
            # NEW: Query saturation mode (iterative querying per source)
            print(f"   🔄 Query saturation enabled - iterative querying per source")
            for tool_name in source_tool_names:
                try:
                    source_display = self.tool_name_to_display.get(tool_name, tool_name)
                    print(f"   🔍 Saturating {source_display}...")

                    # Execute with saturation (multiple queries until LLM determines saturation)
                    source_results = await self._execute_source_with_saturation(
                        task_id=task.id,
                        task=task,
                        hypothesis=hypothesis,
                        source_name=source_display
                    )

                    print(f"   ✓ {source_display}: {len(source_results)} results (after saturation)")
                    all_results.extend(source_results)

                except Exception as e:
                    logging.error(f"❌ Hypothesis {hypothesis_id} saturation failed for {source_display}: {type(e).__name__}: {e}")
                    continue  # Continue with other sources
        else:
            # OLD: Single-shot mode (one query per source)
            for tool_name in source_tool_names:
                try:
                    # Generate source-specific query
                    query = await self._generate_hypothesis_query(
                        hypothesis=hypothesis,
                        source_tool_name=tool_name,
                        research_question=research_question,
                        task_query=task.query,
                        task=task
                    )

                    if not query:
                        continue  # Query generation failed, skip this source

                    # Execute search (single-shot, no retries)
                    source_display = self.tool_name_to_display.get(tool_name, tool_name)
                    print(f"   🔍 Searching {source_display}: '{query}'")

                    # Use existing search infrastructure
                    # Get limit from config
                    limit = config.get_integration_limit(source_display)

                    # Execute MCP search
                    if tool_name in [t["name"] for t in self.mcp_tools]:
                        mcp_tool = next(t for t in self.mcp_tools if t["name"] == tool_name)

                        # Call MCP tool using class method
                        tool_result = await self._call_mcp_tool(
                            tool_config=mcp_tool,
                            query=query,
                            param_adjustments=None,  # No param hints in direct hypothesis execution
                            task_id=task.id,
                            attempt=0,
                            logger=self.logger
                        )

                        if tool_result.get("success"):
                            results = tool_result.get("results", [])
                            print(f"   ✓ {source_display}: {len(results)} results")
                            all_results.extend(results)
                        else:
                            print(f"   ⚠️  {source_display}: {tool_result.get('error', 'Unknown error')}")
                    elif tool_name == "brave_search":
                        # Web search (non-MCP)
                        results = await self._search_brave(query, max_results=limit)
                        print(f"   ✓ {source_display}: {len(results)} results")
                        all_results.extend(results)

                except Exception as e:
                    logging.error(f"❌ Hypothesis {hypothesis_id} search failed for {source_display}: {type(e).__name__}: {e}")
                    continue  # Continue with other sources

        # Filter hypothesis results for relevance (only in single-shot mode)
        # In saturation mode, results are already filtered per-query
        if all_results and not self.query_saturation_enabled:
            print(f"   🔍 Validating relevance of {len(all_results)} hypothesis results...")
            should_accept, relevance_reason, relevant_indices, should_continue, continuation_reason, reasoning_breakdown = await self._validate_result_relevance(
                task_query=hypothesis['statement'],  # Use hypothesis statement as query context
                research_question=research_question,
                sample_results=all_results
            )

            decision_str = "ACCEPT" if should_accept else "REJECT"
            print(f"   Decision: {decision_str}")
            print(f"   Reason: {relevance_reason}")
            print(f"   Filtered: {len(relevant_indices)}/{len(all_results)} results kept")

            # Filter to only relevant results
            if should_accept and relevant_indices:
                filtered_results = [all_results[i] for i in relevant_indices if i < len(all_results)]
                discarded_count = len(all_results) - len(filtered_results)
                print(f"   ✓ Kept {len(filtered_results)} relevant results, discarded {discarded_count} junk")
                all_results = filtered_results
            elif not should_accept:
                # Reject all results
                print(f"   ✗ Rejected all {len(all_results)} results as off-topic")
                all_results = []

        # Deduplicate results with hypothesis tagging
        deduplicated = self._deduplicate_with_attribution(all_results, hypothesis_id)
        print(f"   📊 Hypothesis {hypothesis_id}: {len(deduplicated)} unique results")

        # Compute delta metrics for coverage assessment (Phase 3C)
        delta_metrics = self._compute_hypothesis_delta(task, hypothesis, deduplicated)

        # Record execution summary for reporting/metadata
        try:
            task.hypothesis_runs.append({
                "hypothesis_id": hypothesis_id,
                "statement": hypothesis.get("statement", ""),
                "results_count": len(deduplicated),
                "sources": [self.tool_name_to_display.get(s, s) for s in source_tool_names],
                # Phase 3C: Add delta metrics
                "delta_metrics": delta_metrics
            })
        except Exception as e:
            logging.warning(f"Failed to record hypothesis run summary for {hypothesis_id}: {e}")

        return deduplicated

    async def _assess_coverage(
        self,
        task: ResearchTask,
        research_question: str,
        start_time: float
    ) -> Dict:
        """
        LLM-driven coverage assessment (Phase 3C).

        Decides whether to continue executing hypotheses or stop based on:
        - Incremental gain (new vs duplicate results)
        - Coverage gaps (unexplored angles)
        - Information sufficiency (total results/entities)
        - Resource budget (time/hypotheses remaining)
        - Hypothesis quality (remaining hypotheses)

        Args:
            task: Task with executed hypotheses so far
            research_question: Original research question
            start_time: Task start timestamp (for time budget tracking)

        Returns:
            Dict with LLM coverage decision:
            {
                "decision": "continue" | "stop",
                "assessment": str,  # Qualitative prose assessment
                "gaps_identified": List[str],
                "facts": {  # Auto-injected by system
                    "results_new": int,
                    "results_duplicate": int,
                    "incremental_gain_last_pct": int,
                    ...
                }
            }
        """
        from core.prompt_loader import render_prompt

        # Prepare hypothesis execution summary
        hypotheses_all = task.hypotheses.get("hypotheses", [])
        executed_count = len(task.hypothesis_runs)

        # Build executed hypotheses with delta metrics
        hypotheses_executed = []
        for run in task.hypothesis_runs:
            hypotheses_executed.append({
                "hypothesis_id": run["hypothesis_id"],
                "statement": run["statement"],
                "priority": run.get("priority", "N/A"),
                "confidence": run.get("confidence", "N/A"),
                "delta_metrics": run["delta_metrics"],
                "sources": run["sources"]
            })

        # Build remaining hypotheses list
        executed_ids = {run["hypothesis_id"] for run in task.hypothesis_runs}
        hypotheses_remaining = []
        for hyp in hypotheses_all:
            hyp_id = hyp.get("id", "unknown")
            if hyp_id not in executed_ids:
                hypotheses_remaining.append({
                    "id": hyp_id,
                    "statement": hyp.get("statement", ""),
                    "exploration_priority": hyp.get("exploration_priority", "N/A"),
                    "confidence": hyp.get("confidence", "N/A")
                })

        # Calculate time elapsed
        time_elapsed_seconds = int(time.time() - start_time)

        # Render coverage assessment prompt
        prompt = render_prompt(
            "deep_research/coverage_assessment.j2",
            research_question=research_question,
            task_query=task.query,
            task_id=task.id,
            hypotheses_executed=hypotheses_executed,
            executed_count=executed_count,
            total_hypotheses=len(hypotheses_all),
            hypotheses_remaining=hypotheses_remaining,
            task_total_results=len(task.accumulated_results),
            task_total_entities=len(task.entities_found) if task.entities_found else 0,
            time_elapsed_seconds=time_elapsed_seconds,
            max_time_seconds=self.max_time_per_task_seconds,
            max_hypotheses=self.max_hypotheses_to_execute
        )

        # Define schema for coverage decision
        schema = {
            "type": "object",
            "properties": {
                "decision": {
                    "type": "string",
                    "enum": ["continue", "stop"],
                    "description": "Whether to continue executing hypotheses or stop"
                },
                "assessment": {
                    "type": "string",
                    "description": "2-4 sentences explaining coverage achieved, gaps remaining, and reasoning for decision. Be specific and reference actual findings."
                },
                "gaps_identified": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Specific remaining gaps (1-3 items if decision is continue, empty if stop)"
                }
            },
            "required": ["decision", "assessment", "gaps_identified"],
            "additionalProperties": False
        }

        # Call LLM for coverage assessment
        try:
            response = await acompletion(
                model=config.get_model("analysis"),
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_schema", "json_schema": {"name": "coverage_decision", "strict": True, "schema": schema}}
            )

            decision = json.loads(response.choices[0].message.content)

            # Phase 5: Auto-inject facts (system calculates, LLM doesn't)
            # Calculate incremental gain from last hypothesis
            if task.hypothesis_runs:
                last_run = task.hypothesis_runs[-1]
                delta = last_run.get("delta_metrics", {})
                incremental_gain_pct = int(delta.get("results_new", 0) / delta.get("total_results", 1) * 100) if delta.get("total_results", 0) > 0 else 0
            else:
                incremental_gain_pct = 0

            decision["facts"] = {
                "results_new": sum(run.get("delta_metrics", {}).get("results_new", 0) for run in task.hypothesis_runs),
                "results_duplicate": sum(run.get("delta_metrics", {}).get("results_duplicate", 0) for run in task.hypothesis_runs),
                "incremental_gain_last_pct": incremental_gain_pct,
                "entities_new": sum(run.get("delta_metrics", {}).get("entities_new", 0) for run in task.hypothesis_runs),
                "hypotheses_executed": executed_count,
                "hypotheses_remaining": len(hypotheses_all) - executed_count,
                "time_elapsed_seconds": time_elapsed_seconds,
                "time_remaining_seconds": self.max_time_per_task_seconds - time_elapsed_seconds
            }

            # Log coverage decision
            logging.info(f"📊 Coverage assessment (Task {task.id}):")
            logging.info(f"   Decision: {decision['decision'].upper()}")
            logging.info(f"   Assessment: {decision['assessment'][:150]}...")
            logging.info(f"   Facts: {decision['facts']['results_new']} new, {decision['facts']['results_duplicate']} dup")

            return decision

        except Exception as e:
            logging.error(f"❌ Coverage assessment failed: {type(e).__name__}: {e}")
            # Fallback: continue if under hard ceilings
            return {
                "decision": "continue" if (executed_count < self.max_hypotheses_to_execute and time_elapsed_seconds < self.max_time_per_task_seconds) else "stop",
                "assessment": f"Coverage assessment failed ({type(e).__name__}). Defaulting to hard ceiling logic: continuing if hypotheses remaining and time allows.",
                "gaps_identified": ["Coverage assessment error - using fallback logic"],
                "facts": {  # Minimal facts for failed assessment
                    "results_new": 0,
                    "results_duplicate": 0,
                    "incremental_gain_last_pct": 0,
                    "entities_new": 0,
                    "hypotheses_executed": executed_count,
                    "hypotheses_remaining": len(hypotheses_all) - executed_count,
                    "time_elapsed_seconds": time_elapsed_seconds,
                    "time_remaining_seconds": self.max_time_per_task_seconds - time_elapsed_seconds
                }
            }

    async def _execute_hypotheses(
        self,
        task: ResearchTask,
        research_question: str
    ) -> List[Dict]:
        """
        Execute hypotheses for a task.

        Mode behavior:
        - coverage_mode: false → Parallel execution (Phase 3B)
        - coverage_mode: true → Sequential with adaptive stopping (Phase 3C)

        Args:
            task: Task with hypotheses to execute
            research_question: Original research question

        Returns:
            Combined deduplicated results from all hypotheses
        """
        if not task.hypotheses or not task.hypotheses.get("hypotheses"):
            return []

        hypotheses = task.hypotheses["hypotheses"]

        # Phase 3C: Sequential execution with coverage assessment
        if self.coverage_mode:
            return await self._execute_hypotheses_sequential(task, research_question, hypotheses)

        # Phase 3B: Parallel execution (backward compatible)
        else:
            return await self._execute_hypotheses_parallel(task, research_question, hypotheses)

    async def _execute_hypotheses_parallel(
        self,
        task: ResearchTask,
        research_question: str,
        hypotheses: List[Dict]
    ) -> List[Dict]:
        """
        Execute all hypotheses in parallel (Phase 3B - default).

        Args:
            task: Task with hypotheses
            research_question: Original research question
            hypotheses: List of hypotheses to execute

        Returns:
            Combined deduplicated results from all hypotheses
        """
        print(f"\n🚀 Executing {len(hypotheses)} hypothesis/hypotheses in parallel...")

        # Execute all hypotheses in parallel
        hypothesis_tasks = [
            self._execute_hypothesis(hyp, task, research_question)
            for hyp in hypotheses
        ]

        try:
            results_by_hypothesis = await asyncio.gather(*hypothesis_tasks, return_exceptions=True)

            # Combine all results, filtering out exceptions
            all_results = []
            for i, result in enumerate(results_by_hypothesis):
                if isinstance(result, Exception):
                    logging.error(f"❌ Hypothesis {i+1} execution failed: {type(result).__name__}: {result}")
                else:
                    all_results.extend(result)

            # Cross-hypothesis deduplication (results may appear across hypotheses)
            # This is already handled by _deduplicate_with_attribution in _execute_hypothesis
            # But we need to deduplicate across hypotheses too
            deduplicated = []
            url_map = {}  # url -> result with hypothesis_ids

            for result in all_results:
                url = result.get("url")
                if not url:
                    deduplicated.append(result)
                    continue

                if url in url_map:
                    # Merge hypothesis attribution
                    existing = url_map[url]
                    if "hypothesis_ids" in existing:
                        # Already multi-attributed
                        if "hypothesis_id" in result:
                            if result["hypothesis_id"] not in existing["hypothesis_ids"]:
                                existing["hypothesis_ids"].append(result["hypothesis_id"])
                        elif "hypothesis_ids" in result:
                            for hid in result["hypothesis_ids"]:
                                if hid not in existing["hypothesis_ids"]:
                                    existing["hypothesis_ids"].append(hid)
                    else:
                        # Convert to multi-attribution
                        existing["hypothesis_ids"] = [existing.pop("hypothesis_id")]
                        if "hypothesis_id" in result:
                            if result["hypothesis_id"] not in existing["hypothesis_ids"]:
                                existing["hypothesis_ids"].append(result["hypothesis_id"])
                        elif "hypothesis_ids" in result:
                            for hid in result["hypothesis_ids"]:
                                if hid not in existing["hypothesis_ids"]:
                                    existing["hypothesis_ids"].append(hid)
                else:
                    url_map[url] = result
                    deduplicated.append(result)

            print(f"\n✅ Hypothesis execution complete: {len(deduplicated)} total unique results")
            return deduplicated

        except Exception as e:
            logging.error(f"❌ Hypothesis execution failed: {type(e).__name__}: {e}")
            return []

    async def _execute_hypotheses_sequential(
        self,
        task: ResearchTask,
        research_question: str,
        hypotheses: List[Dict]
    ) -> List[Dict]:
        """
        Execute hypotheses sequentially with coverage-based stopping (Phase 3C).

        Args:
            task: Task with hypotheses
            research_question: Original research question
            hypotheses: List of hypotheses to execute (sorted by priority)

        Returns:
            Combined deduplicated results from executed hypotheses
        """
        print(f"\n🔄 Executing hypotheses sequentially with coverage assessment...")
        print(f"   Max hypotheses: {self.max_hypotheses_to_execute}")
        print(f"   Time budget: {self.max_time_per_task_seconds}s")

        start_time = time.time()
        all_results = []
        url_map = {}  # For cross-hypothesis deduplication
        coverage_decisions = []  # Store all coverage decisions

        for i, hypothesis in enumerate(hypotheses):
            # Check hard ceilings BEFORE executing
            executed_count = len(task.hypothesis_runs)
            time_elapsed = int(time.time() - start_time)

            if executed_count >= self.max_hypotheses_to_execute:
                print(f"\n⏹️  Stopping: Reached hypothesis ceiling ({self.max_hypotheses_to_execute})")
                break

            if time_elapsed >= self.max_time_per_task_seconds:
                print(f"\n⏹️  Stopping: Time budget exhausted ({self.max_time_per_task_seconds}s)")
                break

            # Execute hypothesis
            print(f"\n📍 Hypothesis {i+1}/{len(hypotheses)}: {hypothesis.get('statement', 'unknown')[:80]}...")

            try:
                hypothesis_results = await self._execute_hypothesis(hypothesis, task, research_question)

                # Cross-hypothesis deduplication
                for result in hypothesis_results:
                    url = result.get("url")
                    if not url:
                        all_results.append(result)
                        continue

                    if url in url_map:
                        # Merge attribution (same logic as parallel mode)
                        existing = url_map[url]
                        if "hypothesis_ids" in existing:
                            if "hypothesis_id" in result and result["hypothesis_id"] not in existing["hypothesis_ids"]:
                                existing["hypothesis_ids"].append(result["hypothesis_id"])
                            elif "hypothesis_ids" in result:
                                for hid in result["hypothesis_ids"]:
                                    if hid not in existing["hypothesis_ids"]:
                                        existing["hypothesis_ids"].append(hid)
                        else:
                            existing["hypothesis_ids"] = [existing.pop("hypothesis_id")]
                            if "hypothesis_id" in result and result["hypothesis_id"] not in existing["hypothesis_ids"]:
                                existing["hypothesis_ids"].append(result["hypothesis_id"])
                            elif "hypothesis_ids" in result:
                                for hid in result["hypothesis_ids"]:
                                    if hid not in existing["hypothesis_ids"]:
                                        existing["hypothesis_ids"].append(hid)
                    else:
                        url_map[url] = result
                        all_results.append(result)

                print(f"   Results: {len(hypothesis_results)} from hypothesis ({len(all_results)} total unique)")

            except Exception as e:
                logging.error(f"❌ Hypothesis {i+1} execution failed: {type(e).__name__}: {e}")
                continue

            # Skip coverage assessment for first hypothesis (need baseline)
            if i == 0:
                print(f"   Coverage: Skipping assessment (establishing baseline)")
                continue

            # Coverage assessment (Phase 3C)
            try:
                decision = await self._assess_coverage(task, research_question, start_time)
                coverage_decisions.append(decision)

                # Log coverage decision to execution log
                if self.logger:
                    self.logger.log_coverage_assessment(
                        task_id=task.id,
                        hypothesis_id=hypothesis.get("id", "unknown"),
                        executed_count=len(task.hypothesis_runs),
                        total_hypotheses=len(hypotheses),
                        coverage_decision=decision,
                        time_elapsed_seconds=int(time.time() - start_time),
                        time_budget_seconds=self.max_time_per_task_seconds
                    )

                if decision["decision"] == "stop":
                    print(f"\n✋ Coverage assessment: STOP")
                    print(f"   Assessment: {decision['assessment'][:100]}...")
                    print(f"   Hypotheses executed: {executed_count + 1}/{len(hypotheses)}")
                    break
                else:
                    print(f"   Coverage assessment: CONTINUE")
                    print(f"   Assessment: {decision['assessment'][:100]}...")

            except Exception as e:
                logging.error(f"❌ Coverage assessment failed: {type(e).__name__}: {e}")
                # Continue execution on assessment error (don't block progress)

        # Store coverage decisions in task metadata for reporting
        if coverage_decisions:
            task.metadata["coverage_decisions"] = coverage_decisions

        print(f"\n✅ Sequential execution complete: {len(all_results)} total unique results")
        return all_results

    def _get_available_source_names(self) -> List[str]:
        """Get list of available database integration display names for hypothesis generation."""
        # Map MCP tool names to display names (used in prompts)
        display_names = []
        for tool_name in self.tool_name_to_display.values():
            if tool_name not in display_names:
                display_names.append(tool_name)
        return sorted(display_names)

    async def _search_brave(self, query: str, max_results: int = 20) -> List[Dict]:
        """
        Search open web using Brave Search API.

        Includes rate limiting (1 req/sec) and retry logic for HTTP 429 errors.
        Uses ResourceManager global lock to ensure rate limit respected across parallel tasks.
        """
        api_key = os.getenv('BRAVE_SEARCH_API_KEY')
        if not api_key:
            logging.warning("BRAVE_SEARCH_API_KEY not found, skipping web search")
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
                        logging.info(f"Brave Search: Waiting {delay}s before retry {attempt}/{max_retries}")
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
                                    logging.warning(f"Brave Search: HTTP 429 (rate limit), retry {attempt + 1}/{max_retries}")
                                    continue  # Retry with exponential backoff
                                else:
                                    logging.error(f"Brave Search: HTTP 429 after {max_retries} retries, giving up")
                                    return []

                            # Handle other errors
                            if resp.status != 200:
                                logging.error(f"Brave Search API error: HTTP {resp.status}")
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

                    logging.info(f"Brave Search: {len(results)} results for query: {query}")
                    return results

                except asyncio.TimeoutError:
                    logging.error(f"Brave Search timeout for query: {query}")
                    if attempt < max_retries - 1:
                        continue  # Retry
                    return []

                except Exception as e:
                    logging.error(f"Brave Search error: {type(e).__name__}: {str(e)}")
                    if attempt < max_retries - 1:
                        continue  # Retry
                    return []

        # Should never reach here, but return empty if all retries exhausted
        return []

    async def _select_relevant_sources(self, query: str) -> Tuple[List[str], str]:
        """
        Use a single LLM call to choose the most relevant sources (MCP tools + web tools) for this task.

        Returns:
            Tuple of (selected_sources, reason):
            - selected_sources: List of tool names (e.g., ["search_dvids", "search_sam", "brave_search"])
            - reason: LLM's explanation for why these sources were selected
        """
        # Combine MCP tools and web tools for LLM selection
        all_selectable_tools = self.mcp_tools + self.web_tools

        options_text = "\n".join([
            f"- {self.tool_name_to_display[tool['name']]} ({tool['name']}): {self.tool_descriptions[tool['name']]}"
            for tool in all_selectable_tools
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
                    "maxItems": len(all_selectable_tools)
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

            # Keep only valid tool names (both MCP and web)
            valid_sources = [
                source for source in selected_sources
                if source in self.tool_name_to_display
            ]

            if reason:
                logging.info(f"Source selection rationale: {reason}")
                print(f"📋 Source selection reasoning: {reason}")

            return (valid_sources, reason)

        except Exception as e:
            logging.error(f"Source selection failed: {type(e).__name__}: {str(e)}")
            # Fallback: return all MCP tools (downstream filtering will still apply)
            return ([tool["name"] for tool in self.mcp_tools], f"Error during source selection: {type(e).__name__}")

    async def _call_mcp_tool(
        self,
        tool_config: Dict,
        query: str,
        param_adjustments: Optional[Dict[str, Dict]] = None,
        task_id: Optional[int] = None,
        attempt: int = 0,
        logger: Optional['ExecutionLogger'] = None
    ) -> Dict:
        """
        Call a single MCP tool (extracted as class method for reuse).

        Args:
            tool_config: MCP tool configuration dict with 'name', 'server', 'api_key_name'
            query: Search query
            param_adjustments: Optional param hints for source-specific adjustments
            task_id: Task ID for logging
            attempt: Retry attempt number
            logger: Execution logger instance

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
            source_name = self.tool_name_to_display.get(tool_name, tool_name)
            integration_limit = config.get_integration_limit(source_name.lower().replace('.', '').replace(' ', ''))

            # Build tool arguments
            args = {
                "research_question": query,
                "limit": integration_limit  # Use per-integration limit instead of hardcoded
            }
            if api_key:
                args["api_key"] = api_key

            # Add param_hints if available for this tool (Task 4: Twitter pagination control)
            if param_adjustments:
                # Map source keys to tool names
                source_map = {
                    "reddit": "search_reddit",
                    "usajobs": "search_usajobs",
                    "twitter": "search_twitter"  # Task 4: Added Twitter pagination control
                }
                # Find matching hints for this tool
                for source_key, tool_name_key in source_map.items():
                    if tool_name == tool_name_key and source_key in param_adjustments:
                        args["param_hints"] = param_adjustments[source_key]
                        break

            # Log API call
            source_name = self.tool_name_to_display.get(tool_name, tool_name)
            if logger and task_id is not None:
                try:
                    logger.log_api_call(
                        task_id=task_id,
                        attempt=attempt,
                        source_name=source_name,
                        query_params=args,
                        timeout=30,
                        retry_count=0
                    )
                except Exception as log_error:
                    logging.warning(f"Failed to log API call: {log_error}")

            # Call MCP tool via in-memory client and measure response time
            start_time = time.time()
            async with Client(server) as client:
                result = await client.call_tool(tool_name, args)
            response_time_ms = (time.time() - start_time) * 1000

            # Parse result (FastMCP returns ToolResult with content)
            import json
            result_data = json.loads(result.content[0].text)

            # Get source name from result_data
            source_name = result_data.get("source", tool_name)

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
            if logger and task_id is not None:
                try:
                    logger.log_raw_response(
                        task_id=task_id,
                        attempt=attempt,
                        source_name=source_name,
                        success=success,
                        response_time_ms=response_time_ms,
                        results=results_with_source,
                        error=error
                    )
                except Exception as log_error:
                    logging.warning(f"Failed to log raw response: {log_error}")

            # Circuit breaker: Detect 429 rate limits and check config before adding
            if error and ("429" in str(error) or "rate limit" in str(error).lower()):
                rate_config = config.get_rate_limit_config(source_name)

                if rate_config["use_circuit_breaker"]:
                    if not rate_config["is_critical"]:
                        self.rate_limited_sources.add(source_name)
                        logging.warning(f"⚠️  {source_name} rate limited - added to circuit breaker")
                        print(f"⚠️  {source_name} rate limited - skipping for remaining tasks")
                    else:
                        logging.warning(f"⚠️  {source_name} rate limited but CRITICAL - will continue retrying")
                        print(f"⚠️  {source_name} rate limited (CRITICAL - continuing retries)")
                else:
                    logging.info(f"ℹ️  {source_name} rate limited (no circuit breaker configured - will retry)")
                    print(f"ℹ️  {source_name} rate limited (will retry)")

            return {
                "tool": tool_name,
                "success": success,
                "source": source_name,  # Pass through source from wrapper
                "results": results_with_source,  # Individual results now have source
                "total": result_data.get("total", 0),
                "error": error
            }

        except Exception as e:
            logging.error(f"MCP tool {tool_name} failed: {type(e).__name__}: {str(e)}")

            # Log failed API call
            if logger and task_id is not None:
                try:
                    source_name = self.tool_name_to_display.get(tool_name, tool_name)
                    logger.log_raw_response(
                        task_id=task_id,
                        attempt=attempt,
                        source_name=source_name,
                        success=False,
                        response_time_ms=0,
                        results=[],
                        error=str(e)
                    )
                except Exception as log_error:
                    logging.warning(f"Failed to log error response: {log_error}")

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
            source_display_name = self.tool_name_to_display.get(tool["name"], tool["name"])
            if source_display_name in self.rate_limited_sources:
                skip_rate_limited_names.add(tool["name"])

        if skip_rate_limited_names:
            skipped_display = [self.tool_name_to_display[name] for name in skip_rate_limited_names]
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
        display_names = [self.tool_name_to_display[tool["name"]] for tool in filtered_tools]
        print(f"🔍 Searching {len(filtered_tools)} MCP sources: {', '.join(display_names)}")

        all_results = []
        sources_count = {}

        # Call filtered MCP tools in parallel (skip irrelevant sources) using class method
        mcp_results = await asyncio.gather(*[
            self._call_mcp_tool(tool, query, param_adjustments, task_id=task_id, attempt=attempt, logger=self.logger)
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
                    print(f"📋 Phase 2: Using adjusted sources: {', '.join([self.tool_name_to_display.get(s, s) for s in selected_sources])}")
                else:
                    # Get LLM-selected sources for this query (includes both MCP and web tools)
                    selected_sources, source_selection_reason = await self._select_relevant_sources(task.query)

                # Log source selection if logger enabled
                if self.logger:
                    # Get human-readable source names
                    selected_display_names = [self.tool_name_to_display.get(s, s) for s in selected_sources]
                    self.logger.log_source_selection(
                        task_id=task.id,
                        query=task.query,
                        tool_descriptions=self.tool_descriptions,
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

                # Separate MCP tools from web tools
                selected_mcp_tools = [s for s in selected_sources if s in [tool["name"] for tool in self.mcp_tools]]
                selected_web_tools = [s for s in selected_sources if s in [tool["name"] for tool in self.web_tools]]

                # Search MCP tools if any selected
                mcp_results = []
                if selected_mcp_tools:
                    # Pass selected MCP tool names to avoid duplicate selection call
                    # Use default limit (will be overridden per-tool in _search_mcp_tools_selected)
                    mcp_results = await self._search_mcp_tools_selected(
                        task.query,
                        selected_mcp_tools,
                        limit=config.default_result_limit,
                        task_id=task.id,
                        attempt=task.retry_count,
                        param_adjustments=task.param_adjustments
                    )

                # Conditionally search Brave if selected by LLM
                web_results = []
                if "brave_search" in selected_web_tools:
                    print(f"🌐 Brave Search selected by LLM, executing web search...")
                    brave_limit = config.get_integration_limit('bravesearch')  # Task 1: Use per-integration limit
                    web_results = await self._search_brave(task.query, max_results=brave_limit)
                else:
                    print(f"⊘ Brave Search not selected for this task")

                # Combine MCP results with web results
                all_results = mcp_results + web_results
                combined_total = len(all_results)

                # Validate result relevance, filter to relevant results, decide if continue
                # LLM makes 3 decisions: ACCEPT/REJECT, which indices to keep, continue searching?
                # Gemini 2.5 Flash has 65K token context - evaluate ALL results, no sampling needed
                print(f"🔍 Validating relevance of {len(all_results)} results...")
                should_accept, relevance_reason, relevant_indices, should_continue, continuation_reason, reasoning_breakdown = await self._validate_result_relevance(
                    task_query=task.query,
                    research_question=self.original_question,
                    sample_results=all_results  # Send ALL results to LLM
                )
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
                    except Exception as log_error:
                        logging.warning(f"Failed to log relevance scoring: {log_error}")

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
                        except Exception as log_error:
                            logging.warning(f"Failed to log filter decision: {log_error}")

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
                        source_display = self.tool_name_to_display.get(source, source)
                        source_results = [r for r in all_results if r.get('source') == source_display]

                        if not source_results:
                            # Check if error or just no results
                            # mcp_results is from _search_mcp_tools_selected() - check if this source failed
                            if source in selected_mcp_tools:
                                # Find this source in mcp_results (parallel gather results)
                                # Guard against missing 'tool' key (can happen with malformed MCP responses)
                                source_failed = any(
                                    tool_result.get("tool") == source and not tool_result.get("success", False)
                                    for tool_result in mcp_results
                                    if isinstance(tool_result, dict)  # Ensure it's a dict
                                )
                                if source_failed:
                                    sources_with_errors.append(source_display)
                                else:
                                    sources_with_zero_results.append(source_display)
                            else:
                                # Web search returned zero results
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
                        source_display = self.tool_name_to_display.get(source, source)
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
                        self.tool_name_to_display[tool["name"]]
                        for tool in (self.mcp_tools + self.web_tools)
                        if self.tool_name_to_display.get(tool["name"], tool["name"]) not in self.rate_limited_sources
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

                        # Add "keep" sources
                        for display_name in keep_sources:
                            tool_name = self.tool_display_to_name.get(display_name)
                            if tool_name:
                                adjusted_sources.append(tool_name)

                        # Add "add" sources
                        for display_name in add_sources:
                            tool_name = self.tool_display_to_name.get(display_name)
                            if tool_name and tool_name not in adjusted_sources:
                                adjusted_sources.append(tool_name)

                        # Override selected_sources for next retry (skip LLM source selection)
                        # Store adjusted sources in task metadata for next iteration
                        task.param_adjustments["_adjusted_sources"] = adjusted_sources
                        logging.info(f"Phase 2: Source re-selection applied - next retry will use: {[self.tool_name_to_display.get(s, s) for s in adjusted_sources]}")

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
                        except Exception as log_error:
                            logging.warning(f"Failed to log reformulation: {log_error}")

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

                        except Exception as hyp_error:
                            # Log but don't fail task - hypothesis execution is supplementary
                            logging.error(f"❌ Hypothesis execution failed for Task {task.id}: {type(hyp_error).__name__}: {hyp_error}")
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
                        except Exception as log_error:
                            logging.warning(f"Failed to log filter decision: {log_error}")

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
                        logging.info(f"Task {task.id} accumulated results ({len(task.accumulated_results)} total) persisted to {raw_file}")
                    except Exception as persist_error:
                        logging.warning(f"Failed to persist task {task.id} results: {persist_error}")

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
                            [self.tool_name_to_display.get(s, s) for s in selected_sources]
                        ))
                        sources_succeeded = self._get_sources(task.accumulated_results)
                        elapsed_seconds = 0  # TODO: Track per-task timing

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
                            [self.tool_name_to_display.get(s, s) for s in selected_sources]
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

            except Exception as e:
                # Execution error - capture full traceback for debugging
                import traceback
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
                            logging.info(f"Task {task.id} failed; persisted partial results ({len(task.accumulated_results)}) to {raw_file}")
                        except Exception as persist_error:
                            logging.warning(f"Failed to persist partial results for task {task.id}: {persist_error}")

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
                        except Exception as log_error:
                            logging.warning(f"Failed to log task failure for task {task.id}: {log_error}")

                    return False

        return False

    async def _extract_entities(
        self,
        results: List[Dict],
        research_question: str,
        task_query: str
    ) -> List[str]:
        """
        Extract entities from search results using LLM.

        Args:
            results: List of search results
            research_question: Original research question (for context)
            task_query: Task query that generated these results

        Returns:
            List of entity names found
        """
        if not results:
            return []

        # Use ALL results for entity extraction (LLM has 1M token context, will prioritize most important)
        sample = results

        # Build prompt with result titles and snippets
        results_text = "\n\n".join([
            f"Title: {r.get('title', '')}\nSnippet: {r.get('snippet', r.get('description', ''))[:200]}"
            for r in sample
        ])

        prompt = render_prompt(
            "deep_research/entity_extraction.j2",
            research_question=research_question,
            task_query=task_query,
            results_text=results_text
        )

        schema = {
            "type": "object",
            "properties": {
                "entities": {
                    "type": "array",
                    "items": {"type": "string"},
                    "minItems": 0,
                    "maxItems": 10
                }
            },
            "required": ["entities"],
            "additionalProperties": False
        }

        try:
            response = await acompletion(
                model=config.get_model("query_generation"),
                messages=[{"role": "user", "content": prompt}],
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "strict": True,
                        "name": "entity_extraction",
                        "schema": schema
                    }
                }
            )

            import json
            result = json.loads(response.choices[0].message.content)
            return result.get("entities", [])

        except Exception as e:
            logging.error(f"Entity extraction failed: {type(e).__name__}: {str(e)}")
            return []

    def _get_sources(self, results: List[Dict]) -> List[str]:
        """Extract unique source names from results."""
        sources = set()
        for r in results:
            source = r.get("source", "Unknown")
            sources.add(source)
        return list(sources)

    async def _validate_result_relevance(
        self,
        task_query: str,
        research_question: str,
        sample_results: List[Dict]
    ) -> Tuple[bool, str, List[int], bool, Dict]:
        """
        Validate result relevance, filter to best results, and decide if more searching needed.

        LLM makes FOUR parts: ACCEPT/REJECT, which indices to keep, continue searching?, reasoning breakdown

        Args:
            task_query: Query that generated these results
            research_question: Original research question
            sample_results: All results to evaluate (Gemini 2.5 Flash has 65K token context)

        Returns:
            Tuple of (should_accept, reason, relevant_indices, should_continue, reasoning_breakdown):
            - should_accept: True to ACCEPT results, False to REJECT
            - reason: LLM's explanation for accept/reject decision
            - relevant_indices: List of result indices to keep (e.g., [0, 2, 5])
            - should_continue: True to search for more results, False to stop
            - reasoning_breakdown: Dict with filtering_strategy, interesting_decisions, patterns_noticed
        """
        if not sample_results:
            return (False, "No results to evaluate", [], False, {})

        # Build numbered sample text (Result #0, Result #1, etc.)
        results_text = "\n\n".join([
            f"Result #{i}:\nTitle: {r.get('title', '')}\nSnippet: {r.get('snippet', r.get('description', ''))[:200]}"
            for i, r in enumerate(sample_results)
        ])

        prompt = render_prompt(
            "deep_research/relevance_evaluation.j2",
            research_question=research_question,
            task_query=task_query,
            results_text=results_text
        )

        schema = {
            "type": "object",
            "properties": {
                "decision": {
                    "type": "string",
                    "enum": ["ACCEPT", "REJECT"],
                    "description": "Decision: ACCEPT if any results relevant, REJECT if all off-topic"
                },
                "reason": {
                    "type": "string",
                    "description": "Brief explanation of accept/reject decision"
                },
                "relevant_indices": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "description": "List of result indices to keep (e.g., [0, 2, 5]). Empty list if REJECT."
                },
                "continue_searching": {
                    "type": "boolean",
                    "description": "true = search for more results, false = sufficient coverage"
                },
                "continuation_reason": {
                    "type": "string",
                    "description": "Brief explanation of why to continue or stop searching"
                },
                "reasoning_breakdown": {
                    "type": "object",
                    "properties": {
                        "filtering_strategy": {
                            "type": "string",
                            "description": "Overall approach to filtering this batch"
                        },
                        "interesting_decisions": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "result_index": {"type": "integer"},
                                    "action": {
                                        "type": "string",
                                        "enum": ["kept", "rejected"]
                                    },
                                    "reasoning": {"type": "string"}
                                },
                                "required": ["result_index", "action", "reasoning"],
                                "additionalProperties": False
                            }
                        },
                        "patterns_noticed": {
                            "type": "string",
                            "description": "Patterns or trends observed across results"
                        }
                    },
                    "required": ["filtering_strategy", "interesting_decisions", "patterns_noticed"],
                    "additionalProperties": False
                }
            },
            "required": ["decision", "reason", "relevant_indices", "continue_searching", "continuation_reason", "reasoning_breakdown"],
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
                        "name": "relevance_validation",
                        "schema": schema
                    }
                }
            )

            result = json.loads(response.choices[0].message.content)
            decision = result.get("decision", "REJECT")
            reason = result.get("reason", "")
            relevant_indices = result.get("relevant_indices", [])
            should_continue = result.get("continue_searching", True)
            continuation_reason = result.get("continuation_reason", "")
            reasoning_breakdown = result.get("reasoning_breakdown", {})

            should_accept = (decision == "ACCEPT")

            logging.info(f"Result relevance: {decision} - {reason}")
            logging.info(f"Filtered indices: {relevant_indices} ({len(relevant_indices)} results kept)")
            logging.info(f"Continue searching: {should_continue} - {continuation_reason}")
            # Emit reasoning trace for transparency
            self._emit_progress(
                "relevance_scoring",
                f"Decision: {decision}",
                data={
                    "reason": reason,
                    "relevant_indices": relevant_indices,
                    "continue_searching": should_continue,
                    "continuation_reason": continuation_reason,
                    "reasoning_breakdown": reasoning_breakdown
                }
            )

            return (should_accept, reason, relevant_indices, should_continue, continuation_reason, reasoning_breakdown)

        except Exception as e:
            logging.error(f"Relevance validation failed: {type(e).__name__}: {str(e)}")
            # On error, assume relevant and keep all results (don't want to fail good results)
            # But still allow continuation to try finding better results
            all_indices = list(range(len(sample_results)))
            return (True, f"Error during validation: {type(e).__name__}", all_indices, True, "Error during validation", {})

    async def _reformulate_for_relevance(
        self,
        original_query: str,
        research_question: str,
        results_count: int,
        source_performance: Optional[List[Dict]] = None,
        available_sources: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Reformulate query to get MORE RELEVANT results.

        Phase 2: LLM intelligently re-selects sources based on performance.

        Args:
            original_query: Current query
            research_question: Original research question
            results_count: Number of results found
            source_performance: List of dicts with source performance data (name, status, results_returned, results_kept, quality_rate, error_type)
            available_sources: List of available source names (all sources minus rate-limited)

        Returns Dict with:
        - query: New query text
        - param_adjustments: Dict of source-specific parameter hints (e.g., {"reddit": {"time_filter": "year"}})
        - source_adjustments: (Optional) Dict with keep/drop/add lists for source re-selection
        """
        prompt = render_prompt(
            "deep_research/query_reformulation_relevance.j2",
            research_question=research_question,
            original_query=original_query,
            results_count=results_count,
            source_performance=source_performance or [],
            available_sources=available_sources or []
        )

        schema = {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Reformulated query text"
                },
                "source_adjustments": {
                    "type": "object",
                    "description": "Phase 2: Optional source re-selection based on performance",
                    "properties": {
                        "keep": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Sources that performed well (high quality, keep querying)"
                        },
                        "drop": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Sources with poor performance (0% quality, errors, off-topic - stop querying)"
                        },
                        "add": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Sources not yet tried that might perform better"
                        },
                        "reasoning": {
                            "type": "string",
                            "description": "Why you made these source selection decisions"
                        }
                    },
                    "required": ["keep", "drop", "add", "reasoning"],
                    "additionalProperties": False
                },
                "param_adjustments": {
                    "type": "object",
                    "description": "Source-specific parameter hints",
                    "properties": {
                        "reddit": {
                            "type": "object",
                            "properties": {
                                "time_filter": {
                                    "type": "string",
                                    "enum": ["hour", "day", "week", "month", "year", "all"]
                                }
                            },
                            "required": ["time_filter"],
                            "additionalProperties": False
                        },
                        "usajobs": {
                            "type": "object",
                            "properties": {
                                "keywords": {"type": "string"}
                            },
                            "required": ["keywords"],
                            "additionalProperties": False
                        },
                        "twitter": {
                            "type": "object",
                            "properties": {
                                "search_type": {
                                    "type": "string",
                                    "enum": ["Latest", "Top", "People", "Photos", "Videos"]
                                },
                                "max_pages": {
                                    "type": "integer",
                                    "minimum": 1,
                                    "maximum": 3
                                }
                            },
                            "required": ["search_type", "max_pages"],
                            "additionalProperties": False
                        }
                    },
                    "required": ["reddit", "usajobs", "twitter"],
                    "additionalProperties": False
                }
            },
            "required": ["query", "param_adjustments"],
            "additionalProperties": False
        }

        response = await acompletion(
            model=config.get_model("query_generation"),
            messages=[{"role": "user", "content": prompt}],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "strict": True,
                    "name": "query_reformulation_relevance",
                    "schema": schema
                }
            }
        )

        return json.loads(response.choices[0].message.content)

    async def _reformulate_query_simple(self, original_query: str, results_count: int) -> Dict[str, Any]:
        """
        Reformulate query when it returns insufficient results.

        Returns Dict with:
        - query: New query text
        - param_adjustments: Dict of source-specific parameter hints
        """
        prompt = render_prompt(
            "deep_research/query_reformulation_simple.j2",
            original_query=original_query,
            results_count=results_count
        )

        schema = {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Reformulated query text (broader and simpler)"
                },
                "param_adjustments": {
                    "type": "object",
                    "description": "Source-specific parameter hints",
                    "properties": {
                        "reddit": {
                            "type": "object",
                            "properties": {
                                "time_filter": {
                                    "type": "string",
                                    "enum": ["hour", "day", "week", "month", "year", "all"]
                                }
                            },
                            "required": ["time_filter"],
                            "additionalProperties": False
                        },
                        "usajobs": {
                            "type": "object",
                            "properties": {
                                "keywords": {"type": "string"}
                            },
                            "required": ["keywords"],
                            "additionalProperties": False
                        },
                        "twitter": {
                            "type": "object",
                            "properties": {
                                "search_type": {
                                    "type": "string",
                                    "enum": ["Latest", "Top", "People", "Photos", "Videos"]
                                },
                                "max_pages": {
                                    "type": "integer",
                                    "minimum": 1,
                                    "maximum": 3
                                }
                            },
                            "required": ["search_type", "max_pages"],
                            "additionalProperties": False
                        }
                    },
                    "required": ["reddit", "usajobs", "twitter"],
                    "additionalProperties": False
                }
            },
            "required": ["query", "param_adjustments"],
            "additionalProperties": False
        }

        response = await acompletion(
            model=config.get_model("query_generation"),
            messages=[{"role": "user", "content": prompt}],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "strict": True,
                    "name": "query_reformulation_simple",
                    "schema": schema
                }
            }
        )

        return json.loads(response.choices[0].message.content)

    async def _update_entity_graph(self, entities: List[str]):
        """
        Update entity relationship graph.

        Uses ResourceManager lock to prevent concurrent modification races.
        Normalizes entity names to lowercase to prevent case-variant duplicates.
        """
        async with self.resource_manager.entity_graph_lock:
            # Codex Fix #3: Normalize entity names to lowercase to prevent duplicates
            # Convert "2210 Series" and "2210 series" to the same key
            normalized_entities = [e.strip().lower() for e in entities if e.strip()]

            # For now, simple co-occurrence tracking
            # TODO: Use LLM to extract actual relationships
            for i, entity1 in enumerate(normalized_entities):
                if entity1 not in self.entity_graph:
                    self.entity_graph[entity1] = []

                for entity2 in normalized_entities[i+1:]:
                    if entity2 not in self.entity_graph[entity1]:
                        self.entity_graph[entity1].append(entity2)
                        self._emit_progress(
                            "relationship_discovered",
                            f"Connected: {entity1} <-> {entity2}"
                        )

    def _validate_result_dates(self, results: List[Dict]) -> List[Dict]:
        """
        Validate and filter results with suspicious dates.

        Rejects results with future dates (accounting for timezone differences).
        Adds warning flags for borderline cases.

        Args:
            results: List of result dicts

        Returns:
            Filtered list with valid dates, suspicious results flagged

        Added: 2025-11-18 (Codex recommendation)
        """
        from datetime import datetime, timedelta
        import re
        import logging

        # Timezone buffer: Allow dates up to 1 day in future (accounts for UTC offsets)
        now = datetime.utcnow()
        max_valid_date = now + timedelta(days=1)

        validated_results = []
        rejected_count = 0

        for result in results:
            # Check various date fields
            date_str = result.get('published_date') or result.get('date') or result.get('age')

            if not date_str:
                # No date found - keep result but flag
                result['_date_warning'] = 'no_date_found'
                validated_results.append(result)
                continue

            # Try to parse date from various formats
            future_date_found = False
            try:
                # Common formats: "Nov 17, 2025", "2025-11-17", "November 17, 2025"
                for fmt in ["%b %d, %Y", "%Y-%m-%d", "%B %d, %Y", "%Y/%m/%d"]:
                    try:
                        parsed_date = datetime.strptime(date_str.strip(), fmt)
                        if parsed_date > max_valid_date:
                            future_date_found = True
                            break
                    except ValueError:
                        continue
            except Exception:
                # Date parsing failed - keep result but flag
                result['_date_warning'] = 'date_parse_failed'
                validated_results.append(result)
                continue

            if future_date_found:
                # Reject future-dated result
                rejected_count += 1
                logging.warning(
                    f"Rejected result with future date: '{date_str}' in '{result.get('title', 'Unknown')}' "
                    f"(source: {result.get('source', 'Unknown')})"
                )
                continue

            # Valid date - keep result
            validated_results.append(result)

        if rejected_count > 0:
            logging.info(f"📅 Date validation: Rejected {rejected_count}/{len(results)} results with future dates")

        return validated_results

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
                logging.info(f"Skipping follow-ups for task {task.id}: Coverage assessment shows sufficient coverage (no critical gaps)")
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
            logging.info(f"No coverage data for task {parent_task.id} - skipping follow-ups")
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

        # Render follow-up generation prompt
        prompt = render_prompt(
            "deep_research/follow_up_generation.j2",
            research_question=self.research_question,
            parent_task=parent_task,
            coverage_decisions=coverage_decisions,
            gaps_identified=unique_gaps,
            latest_assessment=assessment_text  # Phase 5: Use prose, not score
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
            logging.info(f"Follow-up generation for task {parent_task.id}: {result['decision_reasoning']}")

        except Exception as e:
            logging.error(f"Follow-up generation failed for task {parent_task.id}: {type(e).__name__}: {e}")
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
                logging.info(f"Skipping duplicate follow-up query: {task_data['query']}")
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
                    logging.info(f"Loaded raw task file: {raw_file.name}")
                except Exception as e:
                    logging.warning(f"Failed to load raw task file {raw_file.name}: {e}")

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
                    except Exception as e:
                        logging.warning(f"Failed to load per-source file {src_file.name}: {e}")

                if merged_results:
                    aggregated_results_by_task[task_id] = {
                        "total_results": len(merged_results),
                        "results": merged_results
                    }
                    logging.info(f"Synthesized task_{task_id}_results from per-source files ({len(merged_results)} items)")

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
            logging.info(f"Deduplication: Removed {duplicates_removed} duplicate results ({len(aggregated_results_list)} → {len(deduplicated_results_list)})")
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

        logging.info(f"Research output saved to: {output_path}")
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

        except Exception as e:
            logging.error(f"Saturation detection failed: {type(e).__name__}: {e}")
            print(f"⚠️  Saturation check failed, defaulting to continue")
            import traceback
            logging.error(traceback.format_exc())
            # On error, assume not saturated (continue research)
            return {
                "saturated": False,
                "confidence": 0,
                "rationale": f"Saturation check failed ({type(e).__name__}), defaulting to continue",
                "recommendation": "continue_full",
                "recommended_additional_tasks": 3,
                "critical_gaps_remaining": ["Saturation check error - continuing"]
            }

    async def _synthesize_report(self, original_question: str) -> str:
        """Synthesize all findings into comprehensive report."""
        # Collect all results
        all_results = []
        for task_id, result in self.results_by_task.items():
            task = next((t for t in self.completed_tasks if t.id == task_id), None)
            if task:
                for r in result.get('results', []):  # Send ALL results to synthesis (no sampling)
                    all_results.append({
                        'task_query': task.query,
                        'title': r.get('title', ''),
                        'source': r.get('source', ''),
                        'snippet': r.get('snippet', r.get('description', ''))[:300],
                        'url': r.get('url', '')
                    })

        # Task 2: LLM-based entity filtering (replaces Python blacklist)
        # Count entity occurrences across tasks for filtering
        entity_task_counts = {}
        for task in self.completed_tasks:
            task_entities = set(e.strip().lower() for e in task.entities_found if e.strip())
            for entity in task_entities:
                entity_task_counts[entity] = entity_task_counts.get(entity, 0) + 1

        # Format entities with counts for LLM filtering
        entities_with_counts = "\n".join([
            f"- {entity} (appeared in {count} task{'s' if count > 1 else ''})"
            for entity, count in sorted(entity_task_counts.items(), key=lambda x: x[1], reverse=True)
        ])

        # Call LLM to filter entities
        all_entities_list = list(self.entity_graph.keys())
        if all_entities_list:
            try:
                print(f"🔍 Filtering {len(all_entities_list)} entities using LLM...")
                entity_filter_prompt = render_prompt(
                    "deep_research/entity_filtering.j2",
                    research_question=self.original_question,
                    tasks_completed=len(self.completed_tasks),
                    total_entities=len(all_entities_list),
                    entities_with_counts=entities_with_counts
                )

                entity_filter_schema = {
                    "type": "object",
                    "properties": {
                        "filtered_entities": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of entities to KEEP (exclude low-value/generic ones)"
                        },
                        "reasoning": {
                            "type": "string",
                            "description": "Brief explanation of filtering decisions"
                        }
                    },
                    "required": ["filtered_entities", "reasoning"],
                    "additionalProperties": False
                }

                entity_filter_response = await acompletion(
                    model=config.get_model("analysis"),
                    messages=[{"role": "user", "content": entity_filter_prompt}],
                    response_format={
                        "type": "json_schema",
                        "json_schema": {
                            "strict": True,
                            "name": "entity_filtering",
                            "schema": entity_filter_schema
                        }
                    }
                )

                filter_result = json.loads(entity_filter_response.choices[0].message.content)
                filtered_entity_names = set(e.lower() for e in filter_result.get("filtered_entities", []))
                filter_reasoning = filter_result.get("reasoning", "")

                # Update entity_graph to only include filtered entities
                filtered_entity_graph = {
                    entity: related
                    for entity, related in self.entity_graph.items()
                    if entity.lower() in filtered_entity_names
                }

                entities_filtered_out = len(self.entity_graph) - len(filtered_entity_graph)
                print(f"✓ Entity filtering: Removed {entities_filtered_out} entities ({len(self.entity_graph)} → {len(filtered_entity_graph)} kept)")
                print(f"  Reasoning: {filter_reasoning}")

                # Replace entity graph with filtered version
                self.entity_graph = filtered_entity_graph

            except Exception as e:
                logging.error(f"Entity filtering failed: {type(e).__name__}: {str(e)}")
                print(f"⚠️  Entity filtering failed (using all entities): {type(e).__name__}")
                # On error, keep all entities (don't want to lose valid data)

        # Compile entity relationships (send filtered entities to synthesis)
        relationship_summary = []
        for entity, related in list(self.entity_graph.items()):  # Filtered entities only
            relationship_summary.append(f"- {entity}: connected to {', '.join(related)}")  # All relationships

        # Task 2A Fix: Use actual total_results from results_by_task instead of len(all_results[:20])
        actual_total_results = sum(r.get('total_results', 0) for r in self.results_by_task.values())

        # Task 2B: Separate integrations from discovered websites
        all_sources = list(set(r.get('source', 'Unknown') for r in all_results))
        integration_names = list(self.tool_name_to_display.values())

        integrations_used = [s for s in all_sources if s in integration_names]
        websites_found = [s for s in all_sources if s not in integration_names and s != 'Unknown']

        # Coverage snapshot: per-source result counts
        source_counts = {}
        for r in all_results:
            source = r.get('source', 'Unknown')
            source_counts[source] = source_counts.get(source, 0) + 1

        # Phase 1: Collect task diagnostics WITH reasoning notes
        task_diagnostics = []
        for task in self.completed_tasks:
            task_result = self.results_by_task.get(task.id, {})
            task_diagnostics.append({
                "id": task.id,
                "query": task.query,
                "status": "COMPLETED",
                "results_kept": task_result.get('total_results', 0),
                "results_total": task.accumulated_results and len(task.accumulated_results) or 0,
                "continuation_reason": "Task completed successfully",
                "reasoning_notes": task.reasoning_notes  # Phase 1: Include LLM reasoning breakdowns
            })

        # Sanity metrics: lightweight counts to spot regressions quickly
        sanity_metrics = []
        for task in self.completed_tasks:
            task_result = self.results_by_task.get(task.id, {})
            hypo_runs = getattr(task, "hypothesis_runs", []) or []
            sanity_metrics.append({
                "id": task.id,
                "query": task.query,
                "total_results": task_result.get('total_results', 0),
                "hypotheses_executed": len(hypo_runs),
                "hypothesis_result_counts": [run.get("results_count", 0) for run in hypo_runs]
            })

        # Phase 3A/B/C: Collect hypotheses and coverage decisions if enabled
        hypotheses_by_task = {}
        task_queries = {}
        hypothesis_execution_summary = {}
        coverage_decisions_by_task = {}  # Phase 3C
        hypothesis_id_to_statement = {}
        if self.hypothesis_branching_enabled:
            for task in (self.completed_tasks + self.failed_tasks):
                task_queries[task.id] = task.query
                if task.hypotheses:
                    hypotheses_by_task[task.id] = task.hypotheses
                    for hyp in task.hypotheses.get("hypotheses", []):
                        hypothesis_id_to_statement[hyp.get("id")] = hyp.get("statement", "")
                if task.hypothesis_runs:
                    hypothesis_execution_summary[task.id] = task.hypothesis_runs
                # Phase 3C: Collect coverage decisions
                if hasattr(task, 'metadata') and 'coverage_decisions' in task.metadata:
                    coverage_decisions_by_task[task.id] = task.metadata['coverage_decisions']

        # Build hypothesis findings: counts and sample links per hypothesis_id
        hypothesis_findings = []
        if hypothesis_id_to_statement:
            results_by_hypothesis = {}
            for r in all_results:
                hyp_ids = []
                if "hypothesis_ids" in r:
                    hyp_ids.extend(r.get("hypothesis_ids", []))
                if "hypothesis_id" in r:
                    hyp_ids.append(r.get("hypothesis_id"))
                if not hyp_ids:
                    continue
                for hid in hyp_ids:
                    results_by_hypothesis.setdefault(hid, []).append(r)

            for hid, res_list in results_by_hypothesis.items():
                samples = []
                for item in res_list[:3]:
                    if item.get("url"):
                        samples.append({
                            "title": item.get("title", "") or item.get("snippet", "")[:80],
                            "url": item.get("url", ""),
                            "source": item.get("source", "Unknown"),
                            "date": item.get("date")
                        })
                hypothesis_findings.append({
                    "hypothesis_id": hid,
                    "statement": hypothesis_id_to_statement.get(hid, ""),
                    "total_results": len(res_list),
                    "sample_results": samples
                })

        # Key documents: top results with URLs for quick access (default to empty safe values)
        key_documents = []
        for item in all_results:
            if item.get("url"):
                key_documents.append({
                    "title": item.get("title", "") or item.get("snippet", "")[:80],
                    "url": item.get("url", ""),
                    "source": item.get("source", "Unknown"),
                    "date": item.get("date")
                })
            if len(key_documents) >= 5:
                break

        # Basic timeline from dated items (if any)
        timeline = []
        for item in all_results:
            if item.get("date") and item.get("url"):
                timeline.append({
                    "date": item.get("date"),
                    "title": item.get("title", "") or item.get("snippet", "")[:80],
                    "url": item.get("url", "")
                })
            if len(timeline) >= 5:
                break

        prompt = render_prompt(
            "deep_research/report_synthesis.j2",
            original_question=original_question,
            tasks_executed=len(self.completed_tasks),
            total_results=actual_total_results,
            entities_discovered=len(entity_task_counts),
            relationship_summary=chr(10).join(relationship_summary),
            top_findings_json=json.dumps(all_results, indent=2),  # Send ALL findings to synthesis
            integrations_used=integrations_used,
            websites_found=websites_found,
            task_diagnostics=task_diagnostics,
            hypotheses_by_task=hypotheses_by_task,  # Phase 3A
            task_queries=task_queries,  # Phase 3A
            hypothesis_execution_summary=hypothesis_execution_summary,  # Phase 3B
            coverage_decisions_by_task=coverage_decisions_by_task,  # Phase 3C
            sanity_metrics=sanity_metrics,  # Sanity checks
            source_counts=source_counts,  # Coverage snapshot
            hypothesis_findings=hypothesis_findings,
            key_documents=key_documents,
            timeline=timeline,
            current_date=datetime.utcnow().date().isoformat()
        )

        report = None
        try:
            response = await acompletion(
                model=config.get_model("synthesis"),  # Use best model for synthesis
                messages=[{"role": "user", "content": prompt}]
            )
            report = response.choices[0].message.content
        except Exception as e:
            logging.error(f"Synthesis failed: {type(e).__name__}: {e}")
            report = f"# Research Report\n\nFailed to synthesize final report.\n\nError: {type(e).__name__}: {e}\n\n## Raw Statistics\n\n- Tasks Executed: {len(self.completed_tasks)}\n- Tasks Failed: {len(self.failed_tasks)}\n"

        # Add limitations section if critical sources failed (Fix 3 - Channel 4)
        if self.critical_source_failures and report:
            report += "\n\n## Research Limitations\n\n"
            report += "The following critical sources were unavailable during this research:\n\n"
            for source in self.critical_source_failures:
                report += f"- **{source}**: Returned 0 results (rate limited or unavailable)\n"
            report += "\n**Impact**: This research may be incomplete due to missing data from these authoritative sources. "
            report += "Results should be verified against these sources when they become available.\n"

        return report


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
