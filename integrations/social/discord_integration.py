#!/usr/bin/env python3
"""
Discord integration for the multi-database research system.

Unlike other integrations, this searches local exported JSON files rather than
calling an external API. Discord exports are generated via the backfill system
and stored in data/exports/.
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import asyncio

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from core.database_integration_base import (
    DatabaseIntegration,
    DatabaseMetadata,
    DatabaseCategory,
    QueryResult
)


class DiscordIntegration(DatabaseIntegration):
    """
    Discord integration that searches exported message history.

    Searches local JSON files exported from Discord servers (Bellingcat, Project OWL, etc.)
    using keyword matching. Provides fast access to Discord community discussions without
    requiring Discord API access or bot tokens.
    """

    def __init__(self, exports_dir: str = "data/exports"):
        """
        Initialize Discord integration.

        Args:
            exports_dir: Directory containing Discord export JSON files
        """
        self.exports_dir = Path(exports_dir)
        self._cache = None  # Lazy-loaded message cache
        self._cache_timestamp = None

    @property
    def metadata(self) -> DatabaseMetadata:
        """Return metadata about Discord integration."""
        return DatabaseMetadata(
            name="Discord",
            id="discord",
            category=DatabaseCategory.SOCIAL_GENERAL,
            requires_api_key=False,  # Searches local exports
            cost_per_query_estimate=0.0,  # Free (local search)
            typical_response_time=0.5,  # Fast (local files)
            rate_limit_daily=None,  # No limits (local)
            description="Discord community discussions from Bellingcat, Project OWL, and other OSINT servers"
        )

    async def is_relevant(self, research_question: str) -> bool:
        """
        Quick check if Discord might have relevant discussions.

        Discord is relevant for:
        - OSINT discussions (Bellingcat)
        - Geopolitical analysis (Project OWL)
        - Real-time breaking news reactions
        - Expert community discussions

        For MVP, we return True and let the LLM decide in generate_query().

        Args:
            research_question: The user's research question

        Returns:
            True (always search Discord for now)
        """
        # Always return True for MVP - Discord has broad coverage
        # In the future, could add keyword filtering here
        return True

    async def generate_query(self, research_question: str) -> Optional[Dict]:
        """
        Generate search parameters for Discord message search.

        Uses LLM to extract key phrases and terms that should be searched together.
        Preserves multi-word concepts like "domestic terrorism" as single search terms.

        Args:
            research_question: The user's research question

        Returns:
            Dict with:
            {
                "keywords": ["keyword or phrase 1", "keyword or phrase 2", ...],
                "servers": None,  # Optional server filter (future)
                "date_range": None  # Optional date filter (future)
            }
        """
        from llm_utils import acompletion
        import json

        # Use LLM to extract key search terms/phrases
        prompt = f"""Generate search parameters for Discord.

Discord provides: Community discussions from OSINT servers (Bellingcat, Project OWL, etc.) - local message archives.

API Parameters:
- keywords (array of strings, required):
    Key search terms or phrases. Messages must contain ALL keywords (AND search).
    Preserve multi-word concepts as single terms (e.g., "domestic terrorism", not separate words).
    Range: 2-5 terms recommended.

Research Question: {research_question}

Extract the most specific, distinctive terms or phrases for searching Discord messages.

Return JSON:
{{
  "terms": array of strings
}}
"""

        try:
            schema = {
                "type": "object",
                "properties": {
                    "terms": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Key search terms or phrases"
                    }
                },
                "required": ["terms"],
                "additionalProperties": False
            }

            response = await acompletion(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "strict": True,
                        "name": "discord_search_terms",
                        "schema": schema
                    }
                }
            )

            result = json.loads(response.choices[0].message.content)
            keywords = [term.lower() for term in result.get("terms", [])]

            if not keywords:
                # Fallback to simple extraction
                keywords = self._extract_keywords(research_question)

        except Exception as e:
            # Fallback to simple extraction on error
            print(f"Warning: LLM keyword extraction failed ({e}), using simple extraction")
            keywords = self._extract_keywords(research_question)

        if not keywords:
            return None

        return {
            "keywords": keywords,
            "servers": None,  # Search all servers
            "date_range": None  # Search all dates
        }

    async def execute_search(
        self,
        query_params: Dict,
        api_key: Optional[str] = None,
        limit: int = 10
    ) -> QueryResult:
        """
        Search local Discord exports for messages matching keywords.

        Args:
            query_params: Dict with 'keywords' list
            api_key: Not used (local search)
            limit: Maximum number of results to return

        Returns:
            QueryResult with matching Discord messages
        """
        start_time = datetime.now()

        try:
            keywords = query_params.get("keywords", [])
            if not keywords:
                return QueryResult(
                    success=False,
                    source="Discord",
                    total=0,
                    results=[],
                    query_params=query_params,
                    error="No keywords provided"
                )

            # Search messages
            matches = await self._search_messages(keywords, limit=limit)

            end_time = datetime.now()
            response_time_ms = (end_time - start_time).total_seconds() * 1000

            return QueryResult(
                success=True,
                source="Discord",
                total=len(matches),
                results=matches[:limit],
                query_params=query_params,
                response_time_ms=response_time_ms,
                metadata={
                    "servers_searched": self._get_unique_servers(matches),
                    "keywords": keywords
                }
            )

        except Exception as e:
            end_time = datetime.now()
            response_time_ms = (end_time - start_time).total_seconds() * 1000

            return QueryResult(
                success=False,
                source="Discord",
                total=0,
                results=[],
                query_params=query_params,
                error=str(e),
                response_time_ms=response_time_ms
            )

    def _extract_keywords(self, text: str) -> List[str]:
        """
        Extract keywords from research question.

        Simple implementation: split on whitespace, remove stopwords.

        Args:
            text: Research question

        Returns:
            List of keywords
        """
        # Common stopwords to exclude
        stopwords = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'about', 'as', 'is', 'are', 'was', 'were',
            'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did',
            'will', 'would', 'could', 'should', 'may', 'might', 'can', 'what',
            'where', 'when', 'who', 'why', 'how', 'which', 'this', 'that', 'these',
            'those', 'there', 'their', 'them', 'they'
        }

        # Extract words (alphanumeric sequences)
        words = re.findall(r'\b\w+\b', text.lower())

        # Filter stopwords and short words
        keywords = [w for w in words if len(w) > 2 and w not in stopwords]

        return keywords

    async def _search_messages(self, keywords: List[str], limit: int = 10) -> List[Dict]:
        """
        Search all Discord export files for messages containing keywords.

        Args:
            keywords: List of keywords to search for
            limit: Maximum number of results

        Returns:
            List of matching messages with metadata
        """
        matches = []

        # Get all export files
        if not self.exports_dir.exists():
            return []

        export_files = list(self.exports_dir.glob("*.json"))

        for export_file in export_files:
            try:
                with open(export_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                guild = data.get("guild", {})
                channel = data.get("channel", {})
                messages = data.get("messages", [])

                for msg in messages:
                    content = msg.get("content", "").lower()

                    # Check if ALL keywords match (AND search)
                    # This ensures we only get messages containing every keyword
                    if all(kw in content for kw in keywords):
                        # Calculate match score (how many keywords matched)
                        matched_keywords = [kw for kw in keywords if kw in content]
                        score = len(matched_keywords) / len(keywords)

                        matches.append({
                            "title": f"Discord message from {msg.get('author', {}).get('name', 'Unknown')}",
                            "content": msg.get("content", ""),
                            "url": f"https://discord.com/channels/{guild.get('id', '')}/{channel.get('id', '')}/{msg.get('id', '')}",
                            "timestamp": msg.get("timestamp", ""),
                            "author": msg.get("author", {}).get("name", "Unknown"),
                            "server": guild.get("name", "Unknown Server"),
                            "channel": channel.get("name", "Unknown Channel"),
                            "category": channel.get("category", ""),
                            "score": score,
                            "matched_keywords": matched_keywords
                        })

            except json.JSONDecodeError as e:
                # Skip corrupted files
                print(f"Warning: Could not parse {export_file}: {e}")
                continue
            except Exception as e:
                # Skip problematic files
                print(f"Warning: Error reading {export_file}: {e}")
                continue

        # Sort by score (best matches first), then by recency
        matches.sort(key=lambda x: (x["score"], x["timestamp"]), reverse=True)

        return matches

    def _get_unique_servers(self, matches: List[Dict]) -> List[str]:
        """
        Get list of unique servers from search results.

        Args:
            matches: List of search results

        Returns:
            List of unique server names
        """
        servers = {m.get("server", "Unknown") for m in matches}
        return sorted(list(servers))


# Test function for development
async def test_discord_integration():
    """Test Discord integration with sample query."""
    integration = DiscordIntegration()

    print("Testing Discord Integration...")
    print(f"Metadata: {integration.metadata.name}")
    print(f"Exports directory: {integration.exports_dir}")
    print(f"Exports exist: {integration.exports_dir.exists()}")

    # Test query generation
    query_params = await integration.generate_query("ukraine intelligence analysis")
    print(f"\nQuery params: {query_params}")

    # Test search
    if query_params:
        result = await integration.execute_search(query_params, limit=5)
        print(f"\nSearch results:")
        print(f"  Success: {result.success}")
        print(f"  Total: {result.total}")
        print(f"  Response time: {result.response_time_ms:.2f}ms")

        if result.success and result.results:
            print(f"\n  First result:")
            first = result.results[0]
            print(f"    Server: {first.get('server')}")
            print(f"    Channel: {first.get('channel')}")
            print(f"    Author: {first.get('author')}")
            print(f"    Content: {first.get('content')[:100]}...")
            print(f"    Matched keywords: {first.get('matched_keywords')}")


if __name__ == "__main__":
    asyncio.run(test_discord_integration())
