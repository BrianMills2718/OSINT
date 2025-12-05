#!/usr/bin/env python3
"""
TEMPLATE: New Database Integration

Copy this file to integrations/government/ or integrations/social/
Rename to <source_name>_integration.py (e.g., newsource_integration.py)

1. Replace all "NewSource" with your source name
2. Fill in metadata() with actual values
3. Implement is_relevant() with keyword check
4. Create Jinja2 prompt template in prompts/integrations/
5. Implement generate_query() using the template
6. Implement execute_search() with field transformation
7. Register in integrations/registry.py
8. Create test file: tests/integrations/test_<source>_live.py
9. Run tests: python3 tests/test_verification.py
"""

import json
import logging
from typing import Dict, Optional
from datetime import datetime
import asyncio
import requests
from llm_utils import acompletion
from core.prompt_loader import render_prompt

from core.database_integration_base import (
    DatabaseIntegration,
    DatabaseMetadata,
    DatabaseCategory,
    QueryResult
)
from core.api_request_tracker import log_request
from core.result_builder import SearchResultBuilder  # REQUIRED: Defensive data transformation
from config_loader import config

# Set up logger for this module
logger = logging.getLogger(__name__)


class NewSourceIntegration(DatabaseIntegration):
    """
    Integration for NewSource API.

    [REPLACE WITH DESCRIPTION OF YOUR DATA SOURCE]

    API Features:
    - [List API capabilities]
    - [Authentication requirements]
    - [Special parameters]

    Rate Limits:
    - [Document rate limits if known]
    """

    @property
    def metadata(self) -> DatabaseMetadata:
        """Return metadata describing this integration."""
        return DatabaseMetadata(
            name="NewSource",              # Display name
            id="newsource",                 # Unique ID (lowercase, no spaces)
            category=DatabaseCategory.GOV_GENERAL,  # Choose appropriate category
            requires_api_key=True,          # True if API key required
            cost_per_query_estimate=0.001,  # LLM cost only (API usually free)
            typical_response_time=2.0,      # Typical response time in seconds
            description="Brief 1-sentence description of data source",
            requires_stealth=False,         # True if bot detection bypass needed
            stealth_method=None,            # "playwright" | "selenium" | None
            rate_limit_daily=None,          # Daily limit, None if unknown
            # Stealth method selection:
            # - None: No bot detection (standard HTTP/API)
            # - "playwright": Fast headless automation (playwright-stealth)
            #   Use for: Moderate bot detection (basic Cloudflare, etc.)
            # - "selenium": Visible browser automation (undetected-chromedriver)
            #   Use for: Aggressive bot detection (Akamai Bot Manager, etc.)
            #   Note: Slower (~3x) but more reliable for strict protections
        )

    async def is_relevant(self, research_question: str) -> bool:
        """
        Quick relevance check using keyword matching.

        This is a FAST check to avoid expensive LLM calls for obviously
        irrelevant queries. Use simple keyword matching only.

        Args:
            research_question: The user's research question

        Returns:
            True to proceed to LLM query generation, False to skip
        """
        question_lower = research_question.lower()

        # CUSTOMIZE: Add keywords that indicate this source is relevant
        relevant_keywords = [
            "keyword1", "keyword2", "keyword3"
        ]

        # Skip if query contains irrelevant keywords
        # Example: Skip contract database for job queries
        irrelevant_keywords = [
            # "job", "employment", "career"
        ]

        # Check for irrelevant keywords first
        if any(kw in question_lower for kw in irrelevant_keywords):
            return False

        # Check for relevant keywords
        return any(kw in question_lower for kw in relevant_keywords)

    async def generate_query(self, research_question: str) -> Optional[Dict]:
        """
        Generate query parameters using LLM.

        Uses LLM to understand the research question and generate
        appropriate search parameters for this API.

        CRITICAL: You must create a Jinja2 prompt template at:
        prompts/integrations/newsource_query_generation.j2

        Args:
            research_question: The user's research question

        Returns:
            Dict with query parameters, or None if not relevant

        Example Return:
            {
                "keywords": "search terms",
                "param1": "value1",
                "param2": None,
                "date_range": 30
            }
        """

        # CUSTOMIZE: Load your Jinja2 prompt template
        prompt = render_prompt(
            "integrations/newsource_query_generation.j2",
            research_question=research_question
        )

        # CUSTOMIZE: Define your JSON schema for query parameters
        schema = {
            "type": "object",
            "properties": {
                "keywords": {
                    "type": "string",
                    "description": "Search keywords"
                },
                "param1": {
                    "type": ["string", "null"],
                    "description": "Optional parameter 1"
                },
                "param2": {
                    "type": "integer",
                    "description": "Numeric parameter 2"
                },
                "reasoning": {
                    "type": "string",
                    "description": "Brief explanation of query strategy"
                }
            },
            "required": ["keywords", "param1", "param2", "reasoning"],
            "additionalProperties": False
        }

        response = await acompletion(
            model=config.get_model("query_generation"),
            messages=[{"role": "user", "content": prompt}],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "strict": True,
                    "name": "newsource_query",
                    "schema": schema
                }
            }
        )

        result = json.loads(response.choices[0].message.content)

        # Return query parameters (excluding metadata like 'reasoning')
        return {
            "keywords": result["keywords"],
            "param1": result["param1"],
            "param2": result["param2"]
        }

    async def execute_search(self,
                           query_params: Dict,
                           api_key: Optional[str] = None,
                           limit: int = 10) -> QueryResult:
        """
        Execute API search with generated parameters.

        CRITICAL: Must return results in standardized format:
        - title (required): Human-readable title
        - url (required): Link to full result
        - snippet (optional): Brief excerpt (max 500 chars)
        - metadata (optional): Source-specific data

        Results are validated using Pydantic - missing fields will raise ValueError!

        Args:
            query_params: Parameters from generate_query()
            api_key: API key if required
            limit: Maximum number of results to return

        Returns:
            QueryResult with standardized format
        """
        start_time = datetime.now()
        endpoint = "https://api.newsource.gov/search"  # CUSTOMIZE: API endpoint

        # CUSTOMIZE: Check for API key if required
        if not api_key:
            return QueryResult(
                success=False,
                source="NewSource",
                total=0,
                results=[],
                query_params=query_params,
                error="API key required for NewSource"
            )

        try:
            # CUSTOMIZE: Build request parameters for your API
            params = {
                "q": query_params.get("keywords"),
                "param1": query_params.get("param1"),
                "param2": query_params.get("param2"),
                "limit": min(limit, 100)  # CUSTOMIZE: API's max limit
            }

            # CUSTOMIZE: Add headers if required
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Accept": "application/json"
            }

            # Execute API call (async-safe using thread pool)
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: requests.get(
                    endpoint,
                    params=params,
                    headers=headers,
                    timeout=config.get_database_config("newsource")["timeout"]
                )
            )
            response.raise_for_status()
            response_time_ms = (datetime.now() - start_time).total_seconds() * 1000

            # Parse API response
            data = response.json()
            raw_results = data.get("results", [])  # CUSTOMIZE: Path to results
            total = data.get("total_count", len(raw_results))  # CUSTOMIZE: Path to count

            # CRITICAL: Use SearchResultBuilder for defensive data transformation
            # The builder handles None values, type mismatches, and edge cases
            # Three-tier model: preserve full content with build_with_raw()
            transformed_results = []
            for doc in raw_results[:limit]:
                # CUSTOMIZE: Map API fields using the builder
                # Builder methods safely handle None/invalid values
                transformed = (SearchResultBuilder()
                    .title(doc.get("api_title_field"))  # safe_text handles None
                    .url(doc.get("api_url_field"))      # safe_url validates URLs
                    .snippet(doc.get("api_summary_field"), max_length=500)  # truncates safely
                    .raw_content(doc.get("api_summary_field"))  # Full content, never truncated
                    .date(doc.get("publish_date"))      # safe_date normalizes dates
                    .api_response(doc)  # Preserve complete API response
                    .metadata({
                        # CUSTOMIZE: Add source-specific fields here
                        "doc_id": doc.get("id"),
                        "author": doc.get("author")
                    })
                    .build_with_raw())  # Use build_with_raw() to include raw_content field
                transformed_results.append(transformed)

                # For amounts/currency, use format_amount() which never crashes on None:
                # title = f"{SearchResultBuilder.format_amount(doc.get('amount'))} contract"

            # Log successful request
            log_request(
                api_name="NewSource",
                endpoint=endpoint,
                status_code=response.status_code,
                response_time_ms=response_time_ms,
                error_message=None,
                request_params=params
            )

            return QueryResult(
                success=True,
                source="NewSource",
                total=total,
                results=transformed_results,  # ← Must be transformed format!
                query_params=query_params,
                response_time_ms=response_time_ms,
                metadata={
                    "api_url": endpoint,
                    # CUSTOMIZE: Add API-specific metadata
                    "next_page": data.get("next_page_url")
                }
            )

        except requests.HTTPError as e:
            # NewSource HTTP error
            logger.error(f"NewSource HTTP error: {e}", exc_info=True)
            response_time_ms = (datetime.now() - start_time).total_seconds() * 1000
            status_code = e.response.status_code if e.response else 0

            # Log failed request
            log_request(
                api_name="NewSource",
                endpoint=endpoint,
                status_code=status_code,
                response_time_ms=response_time_ms,
                error_message=str(e),
                request_params=query_params
            )

            return QueryResult(
                success=False,
                source="NewSource",
                total=0,
                results=[],
                query_params=query_params,
                error=f"HTTP {status_code}: {str(e)}",
                response_time_ms=response_time_ms
            )

        except Exception as e:
            # NewSource search failed
            logger.error(f"NewSource search failed: {e}", exc_info=True)
            response_time_ms = (datetime.now() - start_time).total_seconds() * 1000

            # Log failed request
            log_request(
                api_name="NewSource",
                endpoint=endpoint,
                status_code=0,
                response_time_ms=response_time_ms,
                error_message=str(e),
                request_params=query_params
            )

            return QueryResult(
                success=False,
                source="NewSource",
                total=0,
                results=[],
                query_params=query_params,
                error=str(e),
                response_time_ms=response_time_ms
            )
