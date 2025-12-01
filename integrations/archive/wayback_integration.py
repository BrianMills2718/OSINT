#!/usr/bin/env python3
"""
Wayback Machine (Archive.org) integration.

Provides access to historical snapshots of web pages via the Internet Archive
Wayback Machine. Supports checking if URLs are archived and retrieving specific
historical snapshots.
"""

import json
import logging
from typing import Dict, Optional, List
from datetime import datetime
import requests
from llm_utils import acompletion
from core.prompt_loader import render_prompt

from core.database_integration_base import (
    DatabaseIntegration,
    DatabaseMetadata,
    DatabaseCategory,
    QueryResult
)
from core.result_builder import SearchResultBuilder
from core.api_request_tracker import log_request
from config_loader import config

# Set up logger for this module
logger = logging.getLogger(__name__)


class WaybackMachineIntegration(DatabaseIntegration):
    """
    Integration for Internet Archive Wayback Machine - Historical web page snapshots.

    The Wayback Machine archives web pages over time, allowing retrieval of
    historical versions of websites. Useful for tracking changes, recovering
    deleted content, and accountability research.

    API Features:
    - Check if URL is archived
    - Get closest snapshot to a specific date
    - Retrieve archived snapshots (read-only, can't archive new pages via API)
    - 736 billion pages archived since 1996
    - Completely free, no API key required

    API Documentation:
    - https://archive.org/help/wayback_api.php
    - Availability API: http://archive.org/wayback/available
    """

    @property
    def metadata(self) -> DatabaseMetadata:
        """Return metadata describing this integration."""
        return DatabaseMetadata(
            name="Wayback Machine",
            id="wayback_machine",
            category=DatabaseCategory.GENERAL,  # Web archive doesn't fit other categories
            requires_api_key=False,  # Completely free, no auth
            cost_per_query_estimate=0.001,  # LLM cost only
            typical_response_time=1.5,      # seconds
            rate_limit_daily=None,          # No rate limit
            description="Historical web page snapshots from Internet Archive (736B pages since 1996)"
        )

    async def is_relevant(self, research_question: str) -> bool:
        """
        LLM-based relevance check for Wayback Machine.

        Uses LLM to determine if Wayback Machine might have relevant historical
        web page data for the research question.

        Args:
            research_question: The user's research question

        Returns:
            True if relevant, False otherwise
        """
        from llm_utils import acompletion
        from dotenv import load_dotenv

        load_dotenv()

        prompt = f"""Is the Wayback Machine relevant for researching this question?

RESEARCH QUESTION:
{research_question}

WAYBACK MACHINE CHARACTERISTICS:
Strengths:
- Historical snapshots of websites (what a site looked like in the past)
- Recover deleted or changed content
- Track how websites evolved over time
- Accountability (prove what was said/published)
- 736 billion pages archived since 1996
- Great for: "What did [website] say about X in [year]?", "Show me deleted content", "How has their stance changed?"

Limitations:
- Web pages only (not government documents, filings, or databases)
- Snapshots may be incomplete (not all resources captured)
- Not all websites are archived (robots.txt can block archiving)
- Cannot archive new pages on demand (archiving happens independently)
- Point-in-time snapshots, not real-time monitoring

DECISION CRITERIA:
- Is relevant: If seeking historical website content, deleted pages, or tracking changes over time
- NOT relevant: If ONLY seeking current data, government filings, news articles, or structured data

Return JSON:
{{
  "relevant": true/false,
  "reasoning": "1-2 sentences explaining why Wayback Machine is/isn't relevant"
}}"""

        try:
            response = await acompletion(
                model=config.default_model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )

            result = json.loads(response.choices[0].message.content)
            return result.get("relevant", True)  # Default to True on parsing failure

        except Exception as e:
            # Wayback Machine relevance check failed - non-critical, default to True
            logger.warning(f"Wayback Machine relevance check failed: {e}, defaulting to True", exc_info=True)
            return True

    async def generate_query(self, research_question: str) -> Optional[Dict]:
        """
        Generate Wayback Machine query parameters using LLM.

        Uses GPT-4o-mini to understand the research question and generate
        appropriate URLs and timestamps to check.

        Args:
            research_question: The user's research question

        Returns:
            Dict with query parameters, or None if not relevant

        Example Return:
            {
                "urls": ["https://example.com", "https://example.com/about"],
                "timestamp": "20200101",
                "description": "Checking Example Corp website from January 2020"
            }
        """

        prompt = render_prompt(
            "integrations/wayback_query.j2",
            research_question=research_question
        )

        schema = {
            "name": "wayback_query",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {
                    "relevant": {
                        "type": "boolean",
                        "description": "Is this question relevant for Wayback Machine?"
                    },
                    "reasoning": {
                        "type": "string",
                        "description": "Why is/isn't this relevant for Wayback Machine?"
                    },
                    "urls": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "URLs to check in Wayback Machine (full URLs with http/https)"
                    },
                    "timestamp": {
                        "type": "string",
                        "description": "Optional timestamp in YYYYMMDD format to find snapshots near this date (optional)"
                    },
                    "description": {
                        "type": "string",
                        "description": "Brief description of what we're looking for"
                    }
                },
                "required": ["relevant", "reasoning", "urls", "description"],
                "additionalProperties": False
            }
        }

        response = await acompletion(
            model=config.default_model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_schema", "json_schema": schema}
        )

        result = json.loads(response.choices[0].message.content)

        if not result.get("relevant", False):
            return None

        # Limit to reasonable number of URLs
        urls = result.get("urls", [])[:10]

        return {
            "urls": urls,
            "timestamp": result.get("timestamp"),
            "description": result.get("description", "")
        }

    async def execute_search(
        self,
        query_params: Dict,
        api_key: Optional[str] = None,
        limit: int = 10
    ) -> QueryResult:
        """
        Execute Wayback Machine availability check for URLs.

        Args:
            query_params: Query parameters from generate_query()
            api_key: Not used (Wayback Machine is free)
            limit: Maximum snapshots to return

        Returns:
            QueryResult with archived snapshots found
        """
        urls = query_params.get("urls", [])
        timestamp = query_params.get("timestamp")
        description = query_params.get("description", "")

        if not urls:
            return QueryResult(
                success=False,
                source="Wayback Machine",
                total=0,
                results=[],
                query_params=query_params,
                error="No URLs provided to check in Wayback Machine",
                http_code=None  # Non-HTTP error
            )

        try:
            documents = []

            for url in urls[:limit]:  # Limit to avoid excessive requests
                # Build request to Wayback Availability API
                api_url = "http://archive.org/wayback/available"
                query_params = {"url": url}

                # Add timestamp if specified
                if timestamp:
                    query_params["timestamp"] = timestamp

                # Make request
                response = requests.get(
                    api_url,
                    params=query_params,
                    timeout=10
                )

                response.raise_for_status()
                data = response.json()

                # Check if archived
                archived_snapshots = data.get("archived_snapshots", {})
                closest = archived_snapshots.get("closest", {})

                if closest.get("available"):
                    # Extract snapshot data
                    snapshot_url = closest.get("url", "")
                    snapshot_timestamp = closest.get("timestamp", "")
                    snapshot_status = closest.get("status", "")

                    # Format timestamp for display
                    if snapshot_timestamp:
                        try:
                            # Parse timestamp (YYYYMMDDhhmmss)
                            dt = datetime.strptime(snapshot_timestamp[:14], "%Y%m%d%H%M%S")
                            formatted_date = dt.strftime("%Y-%m-%d %H:%M:%S UTC")
                        except Exception as e:
                            # Timestamp parsing error - use raw value
                            logger.warning(f"Failed to parse Wayback timestamp '{snapshot_timestamp}': {e}", exc_info=True)
                            formatted_date = snapshot_timestamp
                    else:
                        formatted_date = "Unknown date"

                    # Build document using defensive builder
                    doc = (SearchResultBuilder()
                        .title(f"Archived Snapshot: {url}", default="Wayback Archive")
                        .url(snapshot_url)
                        .snippet(f"Snapshot from {formatted_date} (HTTP {snapshot_status})")
                        .date(snapshot_timestamp[:8] if snapshot_timestamp else None)
                        .metadata({
                            "original_url": url,
                            "archive_url": snapshot_url,
                            "snapshot_timestamp": snapshot_timestamp,
                            "snapshot_date": formatted_date,
                            "http_status": snapshot_status,
                            "requested_timestamp": timestamp
                        })
                        .build())
                    documents.append(doc)

            if not documents:
                return QueryResult(
                    success=True,
                    source="Wayback Machine",
                    total=0,
                    results=[],
                    query_params=query_params,
                    metadata={"note": "None of the requested URLs have archived snapshots available"}
                )

            return QueryResult(
                success=True,
                source="Wayback Machine",
                total=len(documents),
                results=documents,
                query_params=query_params,
                response_time_ms=int(response.elapsed.total_seconds() * 1000) if response else 0
            )

        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code if e.response else None
            # Wayback Machine HTTP error
            logger.error(f"Wayback Machine HTTP error: {e}", exc_info=True)
            return QueryResult(
                success=False,
                source="Wayback Machine",
                total=0,
                results=[],
                query_params=query_params,
                error=f"Wayback Machine HTTP error: {str(e,
                http_code=status_code)}"
            )

        except Exception as e:
            # Wayback Machine search failed
            logger.error(f"Wayback Machine search failed: {e}", exc_info=True)
            return QueryResult(
                success=False,
                source="Wayback Machine",
                total=0,
                results=[],
                query_params=query_params,
                error=f"Wayback Machine search failed: {str(e,
                http_code=None  # Non-HTTP error)}"
            )
