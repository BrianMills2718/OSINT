#!/usr/bin/env python3
"""
Content enrichment mixin for deep research.

Provides capability to fetch full page content for selected search results
using Jina Reader API. The LLM decides which URLs warrant full content
retrieval based on the research question and result snippets.

This mixin:
- Selects URLs for full content fetch via LLM
- Fetches content using Jina Reader
- Enriches search results with full page content
"""

import json
import logging
from typing import Dict, List, Optional, TYPE_CHECKING

from llm_utils import acompletion
from core.prompt_loader import render_prompt
from core.jina_reader import fetch_multiple_pages, enrich_search_results
from config_loader import config

if TYPE_CHECKING:
    from research.deep_research import SimpleDeepResearch

logger = logging.getLogger(__name__)


class ContentEnrichmentMixin:
    """
    Mixin providing full page content fetching for search results.

    Uses LLM to select which URLs warrant full content retrieval,
    then fetches and enriches results with Jina Reader.

    Requires host class to have:
        - self._emit_progress(event_type: str, message: str, task_id=None, data=None): method
        - self.execution_logger: ExecutionLogger instance (optional, for logging)
    """

    async def _select_urls_for_content_fetch(
        self: "SimpleDeepResearch",
        research_question: str,
        results: List[Dict],
        max_fetches: int
    ) -> List[str]:
        """
        Use LLM to select which URLs should have full content fetched.

        Args:
            research_question: The original research question
            results: Search results with url, title, snippet/description
            max_fetches: Maximum number of URLs to fetch (user budget)

        Returns:
            List of URLs to fetch full content for
        """
        if not results or max_fetches <= 0:
            return []

        # Filter to results that have URLs (some results may not)
        results_with_urls = [r for r in results if r.get('url')]
        if not results_with_urls:
            return []

        self._emit_progress(
            "content_selection_started",
            f"LLM selecting URLs for full content fetch (budget: {max_fetches})"
        )

        prompt = render_prompt(
            "deep_research/content_fetch_selection.j2",
            research_question=research_question,
            results=results_with_urls[:50],  # Limit to avoid prompt overflow
            max_fetches=max_fetches
        )

        schema = {
            "type": "object",
            "properties": {
                "selected_urls": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "url": {"type": "string"},
                            "reason": {"type": "string"}
                        },
                        "required": ["url", "reason"],
                        "additionalProperties": False
                    }
                },
                "skip_reasoning": {
                    "type": "string",
                    "description": "Explanation of selection strategy"
                }
            },
            "required": ["selected_urls", "skip_reasoning"],
            "additionalProperties": False
        }

        try:
            response = await acompletion(
                model=config.get_model("relevance_filtering"),
                messages=[{"role": "user", "content": prompt}],
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "strict": True,
                        "name": "content_fetch_selection",
                        "schema": schema
                    }
                }
            )

            result = json.loads(response.choices[0].message.content)
            selected = result.get("selected_urls", [])
            skip_reasoning = result.get("skip_reasoning", "")

            # Extract just the URLs
            urls = [item["url"] for item in selected if item.get("url")]

            # Log selection decisions
            if hasattr(self, 'execution_logger') and self.execution_logger:
                self.execution_logger.log_event("content_fetch_selection", {
                    "selected_count": len(urls),
                    "max_fetches": max_fetches,
                    "total_results": len(results_with_urls),
                    "skip_reasoning": skip_reasoning,
                    "selected_urls": [
                        {"url": item["url"], "reason": item["reason"]}
                        for item in selected
                    ]
                })

            self._emit_progress(
                "content_selection_complete",
                f"Selected {len(urls)}/{max_fetches} URLs for full content fetch",
                data={"selected_count": len(urls), "reasoning": skip_reasoning}
            )

            return urls

        except Exception as e:
            logger.error(f"Content fetch selection failed: {e}", exc_info=True)
            self._emit_progress(
                "content_selection_failed",
                f"Failed to select URLs: {e}"
            )
            return []

    async def _enrich_results_with_content(
        self: "SimpleDeepResearch",
        research_question: str,
        results: List[Dict],
        max_fetches: Optional[int] = None
    ) -> List[Dict]:
        """
        Enrich search results with full page content from selected URLs.

        This is the main entry point for content enrichment. It:
        1. Asks LLM to select which URLs warrant full fetch
        2. Fetches content using Jina Reader
        3. Merges full content back into results

        Args:
            research_question: The original research question
            results: Search results to potentially enrich
            max_fetches: Maximum URLs to fetch (defaults to config value)

        Returns:
            Results with 'full_content' field added where fetched
        """
        # Get max fetches from config if not specified
        if max_fetches is None:
            max_fetches = config.get_raw_config().get("research", {}).get("max_full_page_fetches", 10)

        if max_fetches <= 0:
            logger.info("Content enrichment disabled (max_full_page_fetches=0)")
            return results

        # Select URLs
        urls_to_fetch = await self._select_urls_for_content_fetch(
            research_question=research_question,
            results=results,
            max_fetches=max_fetches
        )

        if not urls_to_fetch:
            logger.info("No URLs selected for content fetch")
            return results

        # Fetch content
        self._emit_progress(
            "content_fetch_started",
            f"Fetching full content for {len(urls_to_fetch)} URLs via Jina Reader"
        )

        try:
            page_contents = await fetch_multiple_pages(
                urls=urls_to_fetch,
                max_concurrent=5,
                timeout=30,
                max_content_length=50000
            )

            # Count successes
            successful = sum(1 for pc in page_contents if pc.success)
            total_chars = sum(pc.content_length for pc in page_contents if pc.success)

            self._emit_progress(
                "content_fetch_complete",
                f"Fetched {successful}/{len(urls_to_fetch)} pages ({total_chars:,} chars)",
                data={
                    "successful": successful,
                    "failed": len(urls_to_fetch) - successful,
                    "total_chars": total_chars
                }
            )

            # Log to execution logger
            if hasattr(self, 'execution_logger') and self.execution_logger:
                self.execution_logger.log_event("content_fetch_complete", {
                    "urls_requested": len(urls_to_fetch),
                    "urls_successful": successful,
                    "total_content_chars": total_chars,
                    "fetch_details": [
                        {
                            "url": pc.url,
                            "success": pc.success,
                            "content_length": pc.content_length,
                            "fetch_time_ms": pc.fetch_time_ms,
                            "error": pc.error
                        }
                        for pc in page_contents
                    ]
                })

            # Enrich results
            enriched = enrich_search_results(results, page_contents)

            enriched_count = sum(1 for r in enriched if r.get('full_content'))
            logger.info(f"Enriched {enriched_count} results with full page content")

            return enriched

        except Exception as e:
            logger.error(f"Content fetch failed: {e}", exc_info=True)
            self._emit_progress(
                "content_fetch_failed",
                f"Failed to fetch content: {e}"
            )
            return results
