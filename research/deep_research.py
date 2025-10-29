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
from typing import List, Dict, Optional, Callable
from datetime import datetime
from dataclasses import dataclass, asdict
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

    def __post_init__(self):
        if self.entities_found is None:
            self.entities_found = []


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
        max_tasks: int = 15,
        max_retries_per_task: int = 2,
        max_time_minutes: int = 120,
        min_results_per_task: int = 3,
        max_concurrent_tasks: int = 3,
        progress_callback: Optional[Callable[[ResearchProgress], None]] = None
    ):
        """
        Initialize deep research engine.

        Args:
            max_tasks: Maximum tasks to execute (prevents infinite loops)
            max_retries_per_task: Max retries for failed tasks
            max_time_minutes: Maximum investigation time
            min_results_per_task: Minimum results to consider task successful
            max_concurrent_tasks: Maximum tasks to execute in parallel (1 = sequential, 3-5 = parallel)
            progress_callback: Function to call with progress updates
        """
        self.max_tasks = max_tasks
        self.max_retries_per_task = max_retries_per_task
        self.max_time_minutes = max_time_minutes
        self.min_results_per_task = min_results_per_task
        self.max_concurrent_tasks = max_concurrent_tasks
        self.progress_callback = progress_callback

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

        # Human-friendly labels and descriptions for each MCP tool
        self.tool_name_to_display = {
            "search_sam": "SAM.gov",
            "search_dvids": "DVIDS",
            "search_usajobs": "USAJobs",
            "search_clearancejobs": "ClearanceJobs",
            "search_twitter": "Twitter",
            "search_reddit": "Reddit",
            "search_discord": "Discord"
        }
        self.tool_display_to_name = {v: k for k, v in self.tool_name_to_display.items()}
        self.tool_descriptions = {
            "search_sam": "U.S. federal contracting opportunities and solicitations.",
            "search_dvids": "Military multimedia library (photos, videos, B-roll, news releases).",
            "search_usajobs": "Official U.S. federal civilian job listings.",
            "search_clearancejobs": "Private-sector jobs requiring security clearances.",
            "search_twitter": "Social media posts and announcements (public chatter).",
            "search_reddit": "Community and OSINT discussions.",
            "search_discord": "OSINT community server archives."
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

    def _identify_critical_sources(self, research_question: str) -> List[str]:
        """
        Identify which sources are critical for this research question using keyword rules.

        Args:
            research_question: Original research question

        Returns:
            List of critical source IDs (e.g., ["sam", "dvids", "usajobs"])
        """
        q_lower = research_question.lower()
        critical = []

        # SAM.gov for contract/procurement queries
        if any(kw in q_lower for kw in ["contract", "award", "procurement", "solicitation"]):
            critical.append("SAM.gov")

        # DVIDS for military/DoD queries
        if any(kw in q_lower for kw in ["dvids", "defense", "military", "dod"]):
            critical.append("DVIDS")

        # USAJobs for jobs/employment queries
        if any(kw in q_lower for kw in ["job", "position", "hiring", "employment"]):
            critical.append("USAJobs")

        return critical

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

            # Get batch of tasks (up to max_concurrent_tasks)
            batch_size = min(self.max_concurrent_tasks, len(self.task_queue))
            batch = [self.task_queue.pop(0) for _ in range(batch_size)]

            # Emit batch start
            self._emit_progress(
                "batch_started",
                f"Executing batch of {batch_size} tasks in parallel",
                data={"tasks": [{"id": t.id, "query": t.query} for t in batch]}
            )

            # Codex fix: Emit task_started for each task before parallel execution
            for task in batch:
                task.status = TaskStatus.IN_PROGRESS
                self._emit_progress("task_started", f"Executing: {task.query}", task_id=task.id)

            # Execute batch in parallel with per-task timeout (180s = 3 minutes covers all retries)
            # Timeout wraps entire task execution including all retry attempts
            task_timeout = 180  # 3 minutes per task (50s per attempt × 3 attempts + buffer)
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
                    continue

                success = success_or_exception

                if success:
                    self.completed_tasks.append(task)

                    # Check if we should create follow-up tasks
                    # NOTE: Codex fix - check TOTAL workload, not just completed tasks
                    total_pending_workload = len(self.task_queue) + len(batch) - (batch.index(task) + 1)
                    if self._should_create_follow_ups(task, total_pending_workload):
                        follow_ups = await self._create_follow_up_tasks(task, task_counter)
                        task_counter += len(follow_ups)
                        self.task_queue.extend(follow_ups)
                        self._emit_progress(
                            "follow_ups_created",
                            f"Created {len(follow_ups)} follow-up tasks",
                            task_id=task.id,
                            data={"follow_ups": [{"id": t.id, "query": t.query} for t in follow_ups]}
                        )
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
            all_entities.update(task.entities_found)

        # Compile failure details for debugging
        failure_details = []
        for task in self.failed_tasks:
            failure_details.append({
                "task_id": task.id,
                "query": task.query,
                "error": task.error,
                "retry_count": task.retry_count
            })

        return {
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

    async def _decompose_question(self, question: str) -> List[ResearchTask]:
        """Use LLM to break question into 3-5 initial research tasks."""
        prompt = f"""Break this complex research question into 3-5 specific, focused search tasks.

Research Question: {question}

Each task should be:
- A clear, searchable query (can be used with database search or web search)
- Focused on one aspect of the overall question
- Likely to return concrete results (not too broad, not too narrow)
- Simple keyword-based queries (avoid complex Boolean operators like OR, AND, NOT)
- No site filters (site:gov) or date ranges (2015..2025) - these reduce results
- Natural language queries work best (e.g., "government surveillance contracts Palantir" instead of "site:gov contract Palantir OR Clearview")

Return tasks in priority order (most important first).
"""

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

        return tasks

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

    def _should_skip_source(self, tool_name: str, query: str) -> bool:
        """
        Determine if a source should be skipped for this query.

        Args:
            tool_name: Name of the MCP tool
            query: Current task query

        Returns:
            True if source should be skipped (not relevant)
        """
        query_lower = query.lower()
        research_lower = self.original_question.lower()

        # Skip ClearanceJobs for non-job queries
        if tool_name == "search_clearancejobs":
            job_keywords = ["job", "position", "hiring", "employment", "career", "clearance", "security officer"]
            if not any(kw in query_lower or kw in research_lower for kw in job_keywords):
                return True  # Skip - not a job query

        # Skip Discord for definitional/informational queries
        if tool_name == "search_discord":
            definitional_keywords = ["what is", "what are", "definition", "explain", "describe", "overview"]
            if any(kw in query_lower or kw in research_lower for kw in definitional_keywords):
                return True  # Skip - Discord is not authoritative for definitions

        return False  # Don't skip

    async def _select_relevant_sources(self, query: str) -> List[str]:
        """
        Use a single LLM call to choose the most relevant MCP sources for this task.

        Returns:
            List of MCP tool names (e.g., ["search_dvids", "search_sam"])
        """
        options_text = "\n".join([
            f"- {self.tool_name_to_display[tool['name']]} ({tool['name']}): {self.tool_descriptions[tool['name']]}"
            for tool in self.mcp_tools
        ])

        prompt = f"""Select which MCP sources should be queried for this research subtask.

Original research question: "{self.original_question}"
Task query: "{query}"

Available sources:
{options_text}

Return a JSON list of tool names (e.g., "search_dvids"). Include only sources likely to provide meaningful evidence for this task."""

        schema = {
            "type": "object",
            "properties": {
                "sources": {
                    "type": "array",
                    "items": {"type": "string"},
                    "minItems": 0,
                    "maxItems": len(self.mcp_tools)
                },
                "reason": {
                    "type": "string",
                    "description": "Brief explanation of why these sources were selected"
                }
            },
            "required": ["sources"],
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

            # Keep only valid MCP tool names
            valid_sources = [
                source for source in selected_sources
                if source in self.tool_name_to_display
            ]

            # Always include critical sources (e.g., SAM.gov for contract queries)
            critical_sources = self._identify_critical_sources(self.original_question)
            for critical in critical_sources:
                tool_name = self.tool_display_to_name.get(critical)
                if tool_name and tool_name not in valid_sources:
                    valid_sources.append(tool_name)

            if reason:
                logging.info(f"Source selection rationale: {reason}")

            return valid_sources

        except Exception as e:
            logging.error(f"Source selection failed: {type(e).__name__}: {str(e)}")
            # Fallback: return all MCP tools (downstream filtering will still apply)
            return [tool["name"] for tool in self.mcp_tools]

    async def _search_mcp_tools(self, query: str, limit: int = 10) -> List[Dict]:
        """
        Search using MCP tools (government + social sources).

        Uses LLM to intelligently select relevant sources for each query.

        Returns:
            List of results with standardized format
        """
        # Use LLM to select relevant sources for this query
        selected_tool_names = await self._select_relevant_sources(query)

        if selected_tool_names:
            candidate_tools = [
                tool for tool in self.mcp_tools
                if tool["name"] in selected_tool_names
            ]
            skipped_by_llm = [
                self.tool_name_to_display[tool["name"]]
                for tool in self.mcp_tools
                if tool["name"] not in selected_tool_names
            ]
            if skipped_by_llm:
                print(f"⊘ LLM skipped sources: {', '.join(skipped_by_llm)}")
        else:
            candidate_tools = list(self.mcp_tools)

        # Apply lightweight keyword-based skipping as an additional guardrail
        skip_keyword_names = set()
        for tool in candidate_tools:
            if self._should_skip_source(tool["name"], query):
                skip_keyword_names.add(tool["name"])

        filtered_tools = [
            tool for tool in candidate_tools
            if tool["name"] not in skip_keyword_names
        ]

        if skip_keyword_names:
            skipped_display = [self.tool_name_to_display[name] for name in skip_keyword_names]
            print(f"⊘ Skipping keyword-irrelevant sources: {', '.join(skipped_display)}")

        # If all sources were filtered out, revert to the LLM-selected set to avoid empty searches
        if not filtered_tools and candidate_tools:
            filtered_tools = candidate_tools
            print("ℹ️  Reinstating LLM-selected sources (keyword filtering removed all options).")

        if not filtered_tools:
            print("⊘ No MCP sources selected for this task. Skipping MCP search.")
            return []

        # Emit progress: starting MCP tool searches
        display_names = [self.tool_name_to_display[tool["name"]] for tool in filtered_tools]
        print(f"🔍 Searching {len(filtered_tools)} MCP sources: {', '.join(display_names)}")

        # Identify critical sources for this research question
        critical_sources = self._identify_critical_sources(self.original_question)

        all_results = []
        sources_count = {}

        # Execute MCP tool searches in parallel
        async def call_mcp_tool(tool_config: Dict) -> Dict:
            """Call a single MCP tool."""
            tool_name = tool_config["name"]
            server = tool_config["server"]
            api_key_name = tool_config["api_key_name"]

            try:
                # Get API key if needed
                api_key = self.api_keys.get(api_key_name) if api_key_name else None

                # Build tool arguments
                args = {
                    "research_question": query,
                    "limit": limit
                }
                if api_key:
                    args["api_key"] = api_key

                # Call MCP tool via in-memory client
                async with Client(server) as client:
                    result = await client.call_tool(tool_name, args)

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

                    return {
                        "tool": tool_name,
                        "success": result_data.get("success", False),
                        "source": source_name,  # Pass through source from wrapper
                        "results": results_with_source,  # Individual results now have source
                        "total": result_data.get("total", 0),
                        "error": result_data.get("error")
                    }

            except Exception as e:
                logging.error(f"MCP tool {tool_name} failed: {type(e).__name__}: {str(e)}")
                return {
                    "tool": tool_name,
                    "success": False,
                    "results": [],
                    "total": 0,
                    "error": str(e)
                }

        # Call filtered MCP tools in parallel (skip irrelevant sources)
        mcp_results = await asyncio.gather(*[
            call_mcp_tool(tool) for tool in filtered_tools
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

        # Check for critical source failures (Fix 3)
        for critical_source in critical_sources:
            source_result_count = sources_count.get(critical_source, 0)
            if source_result_count == 0:
                # Critical source returned 0 results - emit warnings in 4 channels
                warning_msg = f"WARNING: {critical_source} returned 0 results (rate limited or unavailable)"

                # Channel 1: Console (print)
                print(f"\n⚠️  {warning_msg}")

                # Channel 2: Logging (warning level)
                logging.warning(warning_msg)

                # Channel 3: Progress events (for Streamlit UI)
                self._emit_progress(
                    "critical_source_failure",
                    warning_msg,
                    data={"source": critical_source, "research_question": self.original_question}
                )

                # Channel 4: Track for synthesis report (will be added to report limitations section)
                if critical_source not in self.critical_source_failures:
                    self.critical_source_failures.append(critical_source)

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

        Uses MCP tools for government and social searches.

        Returns:
            True if task succeeded (eventually), False if exhausted retries
        """
        # Note: task.status already set to IN_PROGRESS in batch loop before parallel execution

        while task.retry_count <= self.max_retries_per_task:
            try:
                # Search using MCP tools (government + social sources)
                mcp_results = await self._search_mcp_tools(task.query, limit=10)

                # Also search web with Brave Search
                web_results = await self._search_brave(task.query, max_results=20)

                # Combine MCP results with web results
                all_results = mcp_results + web_results
                combined_total = len(all_results)

                # Validate result relevance BEFORE accepting as successful
                print(f"🔍 Validating relevance of {len(all_results)} results...")
                relevance_score = await self._validate_result_relevance(
                    task_query=task.query,
                    research_question=self.original_question,
                    sample_results=all_results[:10]
                )
                print(f"  Relevance score: {relevance_score}/10")

                # If results are off-topic (score < 3), reformulate and retry
                # Lowered from 5 to 3 to match success threshold (consistent retry logic)
                if combined_total >= self.min_results_per_task and relevance_score < 3:
                    if task.retry_count < self.max_retries_per_task:
                        task.status = TaskStatus.RETRY
                        task.retry_count += 1

                        self._emit_progress(
                            "task_retry",
                            f"Results off-topic (relevance {relevance_score}/10), reformulating query...",
                            task_id=task.id,
                            data={
                                "relevance_score": relevance_score,
                                "total_results": combined_total
                            }
                        )

                        # Reformulate for relevance (not volume)
                        task.query = await self._reformulate_for_relevance(
                            original_query=task.query,
                            research_question=self.original_question,
                            results_count=combined_total
                        )
                        self._emit_progress(
                            "query_reformulated",
                            f"New query: {task.query}",
                            task_id=task.id
                        )
                        continue  # Retry with new query
                    else:
                        # Exhausted retries
                        task.status = TaskStatus.FAILED
                        task.error = f"Results off-topic (relevance {relevance_score}/10) after {task.retry_count} retries"
                        self._emit_progress("task_failed", task.error, task_id=task.id)
                        return False

                # Extract entities from results
                print(f"🔍 Extracting entities from {len(all_results)} results...")
                entities_found = await self._extract_entities(
                    all_results,
                    research_question=self.original_question,
                    task_query=task.query
                )
                print(f"✓ Found {len(entities_found)} entities: {', '.join(entities_found[:5])}{'...' if len(entities_found) > 5 else ''}")

                # Check if we got meaningful results with sufficient relevance
                # Lowered threshold from 5 to 3 based on CLI testing (Fix: relevance too aggressive)
                # 3/10 = "somewhat relevant, worth including" vs previous 5/10 rejecting 75% of valid tasks
                if combined_total >= self.min_results_per_task and relevance_score >= 3:
                    # Success!
                    task.status = TaskStatus.COMPLETED
                    task.entities_found = entities_found

                    result_dict = {
                        "total_results": combined_total,
                        "results": all_results,
                        "entities_discovered": entities_found,
                        "sources": self._get_sources(all_results)
                    }

                    task.results = result_dict

                    # Codex fix: Protect shared dict writes with lock
                    async with self.resource_manager.results_lock:
                        self.results_by_task[task.id] = result_dict

                    # Update entity graph (with lock for concurrent safety)
                    await self._update_entity_graph(entities_found)

                    self._emit_progress(
                        "task_completed",
                        f"Found {combined_total} results ({len(mcp_results)} MCP tools + {len(web_results)} web)",
                        task_id=task.id,
                        data={
                            "total_results": combined_total,
                            "mcp_results": len(mcp_results),
                            "web_results": len(web_results),
                            "entities": entities_found,
                            "sources": self._get_sources(all_results)
                        }
                    )
                    return True

                else:
                    # Insufficient results - retry with reformulated query
                    if task.retry_count < self.max_retries_per_task:
                        task.status = TaskStatus.RETRY
                        task.retry_count += 1

                        self._emit_progress(
                            "task_retry",
                            f"Only {combined_total} results ({len(mcp_results)} MCP + {len(web_results)} web), reformulating query...",
                            task_id=task.id,
                            data={
                                "total_results": combined_total,
                                "mcp_results": len(mcp_results),
                                "web_results": len(web_results)
                            }
                        )

                        # Reformulate query
                        task.query = await self._reformulate_query_simple(task.query, combined_total)
                        self._emit_progress(
                            "query_reformulated",
                            f"New query: {task.query}",
                            task_id=task.id
                        )
                    else:
                        # Exhausted retries
                        task.status = TaskStatus.FAILED
                        task.error = f"Insufficient results after {task.retry_count} retries"
                        self._emit_progress("task_failed", task.error, task_id=task.id)
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

        # Sample up to 10 results for entity extraction
        sample = results[:10]

        # Build prompt with result titles and snippets
        results_text = "\n\n".join([
            f"Title: {r.get('title', '')}\nSnippet: {r.get('snippet', r.get('description', ''))[:200]}"
            for r in sample
        ])

        prompt = f"""Extract key entities (people, organizations, programs, operations) from these search results.

CONTEXT:
- Original research question: "{research_question}"
- Search query used: "{task_query}"

Use the context to disambiguate acronyms and focus on entities relevant to the research question.

Results:
{results_text}

Return a JSON list of entity names (3-10 entities). Focus on named entities that:
1. Are RELEVANT to the research question
2. Could be researched further
3. Match the domain of the research question (e.g., if researching cybersecurity contracts, focus on companies, agencies, programs in that domain)

Examples (matching the research domain):
- Research question about "JSOC operations" → ["Joint Special Operations Command", "CIA", "Operation Cyclone"]
- Research question about "NSA cybersecurity contracts" → ["National Security Agency", "Palantir", "Booz Allen Hamilton", "Leidos"]
- Research question about "FBI surveillance programs" → ["Federal Bureau of Investigation", "PRISM", "FISA Court"]

DO NOT extract generic entities unrelated to the research question.
"""

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
    ) -> int:
        """
        Validate that search results are actually relevant to the research question.

        Args:
            task_query: Query that generated these results
            research_question: Original research question
            sample_results: Sample of results to evaluate (first 10)

        Returns:
            Relevance score 0-10 (0 = completely off-topic, 10 = highly relevant)
        """
        if not sample_results:
            return 0

        # Build sample text from titles and snippets
        results_text = "\n\n".join([
            f"Title: {r.get('title', '')}\nSnippet: {r.get('snippet', r.get('description', ''))[:200]}"
            for r in sample_results
        ])

        prompt = f"""Evaluate whether these search results are relevant to the research question.

Original Research Question: "{research_question}"
Search Query Used: "{task_query}"

Sample Results:
{results_text}

Score the relevance of these results on a scale of 0-10:
- 10: Highly relevant - directly answers the research question
- 7-9: Relevant - related to the topic but may be indirect
- 4-6: Somewhat relevant - mentions key terms but not focused on the topic
- 1-3: Barely relevant - only tangentially related
- 0: Completely off-topic - wrong domain or subject matter entirely

IMPORTANT:
- If the results are about a DIFFERENT entity with the same acronym (e.g., "Naval Support Activity" when asked about "National Security Agency"), score 0-2 (wrong entity).
- If the results are in the wrong domain (e.g., military logistics when asked about cybersecurity contracts), score 0-3.

Return the relevance score and a brief reason.
"""

        schema = {
            "type": "object",
            "properties": {
                "relevance_score": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 10,
                    "description": "Relevance score 0-10"
                },
                "reason": {
                    "type": "string",
                    "description": "Brief explanation of the score"
                }
            },
            "required": ["relevance_score", "reason"],
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
            score = result.get("relevance_score", 0)
            reason = result.get("reason", "")

            logging.info(f"Result relevance: {score}/10 - {reason}")
            return score

        except Exception as e:
            logging.error(f"Relevance validation failed: {type(e).__name__}: {str(e)}")
            # On error, assume relevant (don't want to fail good results due to validation error)
            return 7

    async def _reformulate_for_relevance(
        self,
        original_query: str,
        research_question: str,
        results_count: int
    ) -> str:
        """Reformulate query to get MORE RELEVANT results."""
        prompt = f"""The search query returned results that are OFF-TOPIC for the research question.

Original Research Question: "{research_question}"
Current Query: "{original_query}"
Results Found: {results_count} (but not relevant)

Reformulate the query to find results that are DIRECTLY RELEVANT to the research question.

Guidelines:
- Add SPECIFIC terms from the research question to disambiguate
- If the research question mentions a specific entity (e.g., "NSA"), clarify which one (e.g., "National Security Agency" not "Naval Support Activity")
- Focus on the core topic (e.g., if researching "cybersecurity contracts", include both terms)
- Remove generic terms that cause topic drift

Examples:
- Research: "NSA cybersecurity contracts" / Current: "NSA contracts" → "National Security Agency cybersecurity contracts"
- Research: "JSOC operations Iraq" / Current: "JSOC" → "Joint Special Operations Command Iraq operations"

Return ONLY the new query text.
"""

        response = await acompletion(
            model=config.get_model("query_generation"),
            messages=[{"role": "user", "content": prompt}]
        )

        return response.choices[0].message.content.strip().strip('"')

    async def _reformulate_query_simple(self, original_query: str, results_count: int) -> str:
        """Reformulate query when it returns insufficient results."""
        prompt = f"""The search query returned insufficient results. Reformulate it to be more effective.

Original Query: {original_query}
Results Found: {results_count}

Reformulate the query to:
- Be BROADER and SIMPLER to get more results
- Remove complex Boolean operators (OR, AND, NOT) if present
- Remove site filters (site:gov) or date ranges (2015..2025) if present
- Use natural language keywords instead of structured queries
- Try different terminology or synonyms
- Focus on core concepts, not specific details

Examples:
- "site:gov contract (Palantir OR Clearview)" → "government contracts Palantir Clearview surveillance"
- "investigation report lawsuit 2018..2025" → "investigation reports lawsuits surveillance privacy"

Return ONLY the new query text, nothing else. Keep it simple and broad.
"""

        response = await acompletion(
            model=config.get_model("query_generation"),
            messages=[{"role": "user", "content": prompt}]
        )

        return response.choices[0].message.content.strip().strip('"')

    async def _update_entity_graph(self, entities: List[str]):
        """
        Update entity relationship graph.

        Uses ResourceManager lock to prevent concurrent modification races.
        """
        async with self.resource_manager.entity_graph_lock:
            # For now, simple co-occurrence tracking
            # TODO: Use LLM to extract actual relationships
            for i, entity1 in enumerate(entities):
                if entity1 not in self.entity_graph:
                    self.entity_graph[entity1] = []

                for entity2 in entities[i+1:]:
                    if entity2 not in self.entity_graph[entity1]:
                        self.entity_graph[entity1].append(entity2)
                        self._emit_progress(
                            "relationship_discovered",
                            f"Connected: {entity1} <-> {entity2}"
                        )

    def _should_create_follow_ups(self, task: ResearchTask, total_pending_workload: int = 0) -> bool:
        """
        Decide if we should create follow-up tasks based on results.

        Args:
            task: Completed task to evaluate
            total_pending_workload: Total pending tasks (queue + currently executing batch)

        Returns:
            True if follow-ups should be created
        """
        if not task.results:
            return False

        results = task.results
        total_results = results.get('total_results', 0)
        entities_found = len(task.entities_found)

        # Codex fix: Check TOTAL workload (completed + pending + would-be follow-ups)
        # This prevents follow-up explosion when parallel execution creates many tasks at once
        max_follow_ups = 2  # We create up to 2 follow-ups per task
        total_workload_if_created = (
            len(self.completed_tasks) +  # Already completed
            total_pending_workload +      # Queue + current batch remainder
            max_follow_ups                # Would-be follow-ups
        )

        # Create follow-ups if we found interesting entities and good results AND room in workload
        return (
            total_results >= 5 and                      # Found meaningful results
            entities_found >= 3 and                     # Discovered multiple entities
            total_workload_if_created < self.max_tasks  # Room for follow-ups in total workload
        )

    async def _create_follow_up_tasks(self, parent_task: ResearchTask, current_task_id: int) -> List[ResearchTask]:
        """Create follow-up tasks to explore entities discovered."""
        # Pick top entities not in original query
        parent_query_lower = parent_task.query.lower()
        new_entities = [
            e for e in parent_task.entities_found
            if e.lower() not in parent_query_lower
        ][:3]  # Max 3 entities

        follow_ups = []
        for i, entity in enumerate(new_entities[:2]):  # Max 2 follow-ups per task
            follow_up = ResearchTask(
                id=current_task_id + i,
                query=f"{entity}",  # Search for entity directly
                rationale=f"Deep dive on entity discovered in task {parent_task.id}: {entity}",
                parent_task_id=parent_task.id
            )
            follow_ups.append(follow_up)

        return follow_ups

    async def _synthesize_report(self, original_question: str) -> str:
        """Synthesize all findings into comprehensive report."""
        # Collect all results
        all_results = []
        for task_id, result in self.results_by_task.items():
            task = next((t for t in self.completed_tasks if t.id == task_id), None)
            if task:
                for r in result.get('results', [])[:5]:  # Top 5 from each task
                    all_results.append({
                        'task_query': task.query,
                        'title': r.get('title', ''),
                        'source': r.get('source', ''),
                        'snippet': r.get('snippet', r.get('description', ''))[:300],
                        'url': r.get('url', '')
                    })

        # Compile entity relationships
        relationship_summary = []
        for entity, related in list(self.entity_graph.items())[:10]:  # Top 10
            relationship_summary.append(f"- {entity}: connected to {', '.join(related[:3])}")

        prompt = f"""Synthesize these research findings into a comprehensive report.

Original Question: {original_question}

Research Summary:
- Tasks Executed: {len(self.completed_tasks)}
- Total Results: {len(all_results)}
- Entities Discovered: {len(self.entity_graph)}

Entity Relationships:
{chr(10).join(relationship_summary)}

Top Findings (from {len(all_results)} results):
{json.dumps(all_results[:20], indent=2)}

Create a detailed markdown report with:

# Research Report: [Title based on question]

## Executive Summary
[3-5 sentences summarizing key findings]

## Key Findings
[Bullet points of most important discoveries]

## Detailed Analysis
[2-3 paragraphs analyzing the findings, connecting entities, explaining relationships]

## Entity Network
[Description of key entities and their relationships]

## Sources
[List of unique sources consulted]

## Methodology
[Brief note on research approach - {len(self.completed_tasks)} tasks, {len(all_results)} results]

Make the report insightful and well-structured. Focus on connections and relationships, not just listing results.
"""

        response = await acompletion(
            model=config.get_model("synthesis"),  # Use best model for synthesis
            messages=[{"role": "user", "content": prompt}]
        )

        report = response.choices[0].message.content

        # Add limitations section if critical sources failed (Fix 3 - Channel 4)
        if self.critical_source_failures:
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
