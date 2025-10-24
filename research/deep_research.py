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

            # Execute batch in parallel
            results = await asyncio.gather(*[
                self._execute_task_with_retry(task)
                for task in batch
            ], return_exceptions=True)

            # Process results
            for task, success_or_exception in zip(batch, results):
                # Handle exceptions
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

    async def _search_mcp_tools(self, query: str, limit: int = 10) -> List[Dict]:
        """
        Search using MCP tools (government + social sources).

        Returns:
            List of results with standardized format
        """
        # Emit progress: starting MCP tool searches
        print(f"🔍 Searching {len(self.mcp_tools)} databases via MCP tools...")

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

        # Call all MCP tools in parallel
        mcp_results = await asyncio.gather(*[
            call_mcp_tool(tool) for tool in self.mcp_tools
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

                # Extract entities from results
                print(f"🔍 Extracting entities from {len(all_results)} results...")
                entities_found = await self._extract_entities(all_results)
                print(f"✓ Found {len(entities_found)} entities: {', '.join(entities_found[:5])}{'...' if len(entities_found) > 5 else ''}")

                # Check if we got meaningful results
                if combined_total >= self.min_results_per_task:
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

    async def _extract_entities(self, results: List[Dict]) -> List[str]:
        """
        Extract entities from search results using LLM.

        Args:
            results: List of search results

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

Results:
{results_text}

Return a JSON list of entity names (3-10 entities). Focus on named entities that could be researched further.

Example: ["Joint Special Operations Command", "CIA", "Kabul attack", "Operation Cyclone"]
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

        return response.choices[0].message.content


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
