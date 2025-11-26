#!/usr/bin/env python3
"""
MCP tool execution mixin for deep research.

Provides MCP tool calling, source selection, and search execution.
Extracted from SimpleDeepResearch to reduce god class complexity.
"""

import asyncio
import json
import logging
import time
from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING

from core.prompt_loader import render_prompt
from config_loader import config
from llm_utils import acompletion
from integrations.registry import registry

if TYPE_CHECKING:
    from research.deep_research import SimpleDeepResearch
    from research.execution_logger import ExecutionLogger

logger = logging.getLogger(__name__)


class MCPToolMixin:
    """
    Mixin providing MCP tool execution and source selection.

    Requires host class to have:
        - self.mcp_tools: List of MCP tool configs
        - self.integrations: Dict of integration instances
        - self.api_keys: Dict of API keys
        - self.rate_limited_sources: Set of rate-limited source names
        - self.logger: ExecutionLogger instance
        - self.original_question: str
    """

    async def _select_relevant_sources(
        self: "SimpleDeepResearch",
        query: str,
        task_id: Optional[int] = None
    ) -> Tuple[List[str], str]:
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
        self: "SimpleDeepResearch",
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
        # Parameter validation guards
        if not tool_config or not isinstance(tool_config, dict):
            return {"success": False, "results": [], "source": "unknown", "total": 0, "error": "Invalid tool_config"}
        if not query or not isinstance(query, str):
            return {"success": False, "results": [], "source": tool_config.get("name", "unknown"), "total": 0, "error": "Invalid query"}

        tool_name = tool_config.get("name")
        if not tool_name:
            return {"success": False, "results": [], "source": "unknown", "total": 0, "error": "Missing tool name"}

        server = tool_config.get("server")
        api_key_name = tool_config.get("api_key_name")

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

                        # 4. ERROR REFORMULATION: If validation error, try to fix and retry
                        if not query_result.success and query_result.error:
                            error_str = str(query_result.error)
                            # Detect validation errors (HTTP 400, 422) that LLM might fix
                            is_validation_error = any(code in error_str for code in ["400", "422", "validation", "invalid"])

                            if is_validation_error:
                                # Extract error code if present
                                error_code = None
                                for code in ["422", "400"]:
                                    if code in error_str:
                                        error_code = int(code)
                                        break

                                # Try to reformulate the query
                                print(f"🔄 {source_name}: Validation error detected, attempting LLM reformulation...")
                                logger.info(f"[RETRY] {source_name}: Attempting error-based reformulation")
                                fixed_params = await self._reformulate_on_api_error(
                                    source_name=source_name,
                                    research_question=query,
                                    original_params=query_params,
                                    error_message=error_str,
                                    error_code=error_code
                                )

                                if fixed_params:
                                    # Retry with fixed parameters
                                    print(f"🔄 {source_name}: Retrying with reformulated query...")
                                    logger.info(f"[RETRY] {source_name}: Retrying with reformulated query")
                                    retry_result = await integration.execute_search(
                                        query_params=fixed_params,
                                        api_key=api_key,
                                        limit=integration_limit
                                    )

                                    # Use retry result if successful
                                    if retry_result.success:
                                        result_data = {
                                            "success": retry_result.success,
                                            "source": retry_result.source,
                                            "total": retry_result.total,
                                            "results": retry_result.results,
                                            "error": None
                                        }
                                        print(f"✅ {source_name}: Reformulation successful - {retry_result.total} results")
                                        logger.info(f"[RETRY] {source_name}: Reformulation successful - {retry_result.total} results")
                                    else:
                                        print(f"❌ {source_name}: Reformulation retry also failed")
                                        logger.warning(f"[RETRY] {source_name}: Reformulation failed - {retry_result.error}")
                                else:
                                    print(f"❌ {source_name}: LLM could not fix the query")

                response_time_ms = (time.time() - start_time) * 1000

            else:
                # OLD ARCHITECTURE: MCP server call (backward compatibility)
                from mcp import Client
                async with Client(server) as client:
                    result = await client.call_tool(tool_name, args)
                response_time_ms = (time.time() - start_time) * 1000

                # Parse result (FastMCP returns ToolResult with content)
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

                # Use metadata-driven decision: retry_within_session determines behavior
                if rate_config["is_critical"]:
                    # Critical sources always retry
                    logger.warning(f"⚠️  {source_name} rate limited but CRITICAL - will continue retrying")
                    print(f"⚠️  {source_name} rate limited (CRITICAL - continuing retries)")
                elif not rate_config["retry_within_session"]:
                    # Source metadata says don't retry within session (e.g., SAM.gov ~1 day recovery)
                    self.rate_limited_sources.add(source_name)
                    cooldown_hours = rate_config["cooldown_seconds"] / 3600
                    logger.warning(f"⚠️  {source_name} rate limited - circuit breaker active (recovery ~{cooldown_hours:.1f}h)")
                    print(f"⚠️  {source_name} rate limited - skipping for remaining tasks (recovery ~{cooldown_hours:.1f}h)")
                elif rate_config["use_circuit_breaker"]:
                    # Config.yaml explicitly enables circuit breaker
                    self.rate_limited_sources.add(source_name)
                    logger.warning(f"⚠️  {source_name} rate limited - added to circuit breaker")
                    print(f"⚠️  {source_name} rate limited - skipping for remaining tasks")
                else:
                    # Source says retry is worthwhile (e.g., Brave ~2 min recovery)
                    cooldown_secs = rate_config["cooldown_seconds"]
                    logger.info(f"ℹ️  {source_name} rate limited (will retry after ~{cooldown_secs}s)")
                    print(f"ℹ️  {source_name} rate limited (will retry after ~{cooldown_secs}s)")

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
        self: "SimpleDeepResearch",
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
        # Parameter validation guards
        if not query or not isinstance(query, str):
            logger.warning("_search_mcp_tools_selected called with empty/invalid query")
            return []
        if not selected_tool_names or not isinstance(selected_tool_names, list):
            logger.warning("_search_mcp_tools_selected called with empty/invalid tool names")
            return []
        if limit < 1:
            limit = 10  # Reset to default

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

        # Track source execution status for relevance filter decision
        source_execution_status = {}

        # Combine results and track per-source counts
        for tool_result in mcp_results:
            source = tool_result.get("source", registry.get_display_name(tool_result["tool"]))
            if tool_result["success"]:
                tool_results = tool_result["results"]
                all_results.extend(tool_results)
                sources_count[source] = sources_count.get(source, 0) + len(tool_results)
                # Log each successful source with counts
                print(f"  ✓ {source}: {len(tool_results)} results")
                # Track success
                source_execution_status[source] = {
                    "status": "success",
                    "results_count": len(tool_results)
                }
            else:
                # Log failed sources
                error_msg = tool_result.get('error', 'Unknown error')
                print(f"  ✗ {source}: Failed - {error_msg}")
                # Track failure with error type
                source_execution_status[source] = {
                    "status": "error",
                    "error": error_msg[:100]  # Truncate long errors
                }

        # Log summary with per-source breakdown
        print(f"\n✓ MCP tools complete: {len(all_results)} total results from {len(sources_count)} sources")
        if sources_count:
            print("  Per-source breakdown:")
            for source, count in sorted(sources_count.items(), key=lambda x: x[1], reverse=True):
                print(f"    • {source}: {count} results")

        return all_results, source_execution_status
