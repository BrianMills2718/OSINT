#!/usr/bin/env python3
"""
Telegram integration for the multi-database research system.

Uses Telethon library to search public Telegram channels, get messages from
specific channels, and track discussions. Provides OSINT capabilities for
Telegram-based news sources, leak channels, and community discussions.
"""

import json
import os
import asyncio
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dotenv import load_dotenv
import logging

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from core.database_integration_base import (
    DatabaseIntegration,
    DatabaseMetadata,
    DatabaseCategory,
    QueryResult
)
from core.result_builder import SearchResultBuilder
from core.prompt_loader import render_prompt
from llm_utils import acompletion

# Load environment variables
load_dotenv()

# Set up logger for this module
logger = logging.getLogger(__name__)

# Lazy import Telethon (only when needed)
TelegramClient = None
functions = None
types = None


def _import_telethon() -> None:
    """Lazy import Telethon to avoid import errors if not installed."""
    global TelegramClient, functions, types
    if TelegramClient is None:
        from telethon import TelegramClient as TC, functions as funcs, types as tp
        TelegramClient = TC
        functions = funcs
        types = tp


# Query patterns for different Telegram search types
QUERY_PATTERNS = {
    "channel_search": {
        "description": "Search for public channels by name or username",
        "use_case": "Finding relevant Telegram channels",
        "required_params": ["query"]
    },
    "channel_messages": {
        "description": "Get recent messages from a specific channel",
        "use_case": "Monitoring a known channel (e.g., @bellingcat, @CITeam_en)",
        "required_params": ["channel_username"]
    },
    "global_search": {
        "description": "Search for messages across channels by keywords",
        "use_case": "Finding discussions on a topic",
        "required_params": ["keywords"]
    },
    "channel_info": {
        "description": "Get details about a specific channel",
        "use_case": "Channel verification and metadata",
        "required_params": ["channel_username"]
    }
}


class TelegramIntegration(DatabaseIntegration):
    """
    Telegram integration using Telethon library.

    Searches public Telegram channels and messages for OSINT research.
    Requires Telegram API credentials from my.telegram.org.

    First run requires phone verification (SMS code).
    """

    def __init__(self) -> None:
        """Initialize Telegram integration."""
        _import_telethon()

        self.api_id = os.getenv("TELEGRAM_API_ID")
        self.api_hash = os.getenv("TELEGRAM_API_HASH")
        self.phone = os.getenv("TELEGRAM_PHONE")

        self.session_dir = Path("data/telegram_sessions")
        self.session_dir.mkdir(parents=True, exist_ok=True)

        self.client = None
        self._authenticated = False

    @property
    def metadata(self) -> DatabaseMetadata:
        """Return metadata about Telegram integration."""
        return DatabaseMetadata(
            name="Telegram",
            id="telegram",
            category=DatabaseCategory.SOCIAL_GENERAL,
            requires_api_key=True,  # Requires TELEGRAM_API_ID and TELEGRAM_API_HASH
            api_key_env_var="TELEGRAM_API_ID",  # Also requires TELEGRAM_API_HASH
            cost_per_query_estimate=0.0,  # Free (Telegram API has no costs)
            typical_response_time=2.0,
            rate_limit_daily=None,  # No official limits, but reasonable use expected
            description="Telegram channels and messages: news sources, leak channels, OSINT communities"
        )

    async def _ensure_client(self) -> None:
        """Ensure Telegram client is connected and authenticated."""
        if self.client is not None and self._authenticated:
            return

        if not self.api_id or not self.api_hash:
            raise ValueError("TELEGRAM_API_ID and TELEGRAM_API_HASH must be set in .env")

        session_file = self.session_dir / "sigint_research"

        self.client = TelegramClient(
            str(session_file),
            int(self.api_id),
            self.api_hash
        )

        await self.client.start(phone=self.phone)
        self._authenticated = True

    async def is_relevant(self, research_question: str) -> bool:
        """
        LLM-based relevance check for Telegram.

        Telegram is relevant for:
        - Breaking news and leaks
        - Official government/military channels
        - OSINT community discussions
        - Uncensored information sources

        Args:
            research_question: The user's research question

        Returns:
            True if Telegram likely has relevant content
        """
        prompt = f"""Is Telegram relevant for researching this question?

RESEARCH QUESTION:
{research_question}

TELEGRAM CHARACTERISTICS:
Strengths:
- Breaking news channels (many governments, media, military have official channels)
- Leak channels and whistleblower platforms
- OSINT community channels (similar to Discord but different audience)
- Uncensored discussions (less moderation than mainstream platforms)
- Popular in conflict zones, Eastern Europe, Middle East

Limitations:
- Not a job/career platform (use USAJobs/ClearanceJobs for that)
- Limited historical search (messages are ephemeral)
- Fewer Western users than Twitter/Reddit

DECISION CRITERIA:
- Is relevant: If looking for breaking news, leaks, official channels, OSINT discussions
- NOT relevant: If ONLY seeking job postings, historical contracts, or US-centric social media

Return JSON:
{{
  "relevant": true/false,
  "reasoning": "1-2 sentences explaining why"
}}"""

        try:
            response = await acompletion(
                model=config.default_model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )

            result = json.loads(response.choices[0].message.content)
            return result.get("relevant", True)

        except Exception as e:
            # Catch-all at integration boundary - acceptable to return default instead of crashing
            logger.error(f"Telegram relevance check failed: {e}, defaulting to True", exc_info=True)
            print(f"[WARN] Telegram relevance check failed: {e}, defaulting to True")
            return True

    async def generate_query(self, research_question: str) -> Optional[Dict]:
        """
        Generate Telegram query parameters using LLM.

        LLM selects the appropriate query pattern based on the research question.

        Args:
            research_question: The user's research question

        Returns:
            Dict with pattern, params, and reasoning
        """
        prompt = render_prompt(
            "integrations/telegram_query_generation.j2",
            research_question=research_question
        )

        # Define JSON schema for structured output
        schema = {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "enum": ["channel_search", "channel_messages", "global_search", "channel_info"]
                },
                "params": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "channel_username": {"type": "string"},
                        "keywords": {
                            "type": "array",
                            "items": {"type": "string"}
                        },
                        "limit": {"type": "integer", "minimum": 10, "maximum": 100}
                    },
                    "additionalProperties": True
                },
                "reasoning": {"type": "string"}
            },
            "required": ["pattern", "params", "reasoning"],
            "additionalProperties": False
        }

        try:
            response = await acompletion(
                model=config.default_model,
                messages=[{"role": "user", "content": prompt}],
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "strict": True,
                        "name": "telegram_query_schema",
                        "schema": schema
                    }
                }
            )

            result = json.loads(response.choices[0].message.content)

            # Validate pattern exists
            if result["pattern"] not in QUERY_PATTERNS:
                print(f"[WARN] Invalid pattern '{result['pattern']}', falling back to global_search")
                result["pattern"] = "global_search"

            return result

        except Exception as e:
            # Catch-all at integration boundary - acceptable to return None instead of crashing
            logger.error(f"Telegram query generation failed: {e}", exc_info=True)
            print(f"[ERROR] Telegram query generation failed: {e}")
            return None

    async def execute_search(
        self,
        query_params: Dict,
        api_key: Optional[str],
        limit: int
    ) -> QueryResult:
        """
        Execute Telegram search based on query pattern.

        Args:
            query_params: Query parameters from generate_query()
            api_key: Not used (credentials come from .env)
            limit: Maximum results to return

        Returns:
            QueryResult with standardized results
        """
        start_time = datetime.now()

        try:
            await self._ensure_client()

            pattern = query_params.get("pattern", "global_search")
            params = query_params.get("params", {})

            # Route to appropriate search method
            if pattern == "channel_search":
                results = await self._search_channels(params, limit)
            elif pattern == "channel_messages":
                results = await self._get_channel_messages(params, limit)
            elif pattern == "global_search":
                results = await self._global_search(params, limit)
            elif pattern == "channel_info":
                results = await self._get_channel_info(params)
            else:
                return QueryResult(
                    success=False,
                    source="Telegram",
                    total=0,
                    results=[],
                    query_params=query_params,
                    error=f"Unknown pattern: {pattern}",
                    http_code=None,  # Non-HTTP error
                    response_time_ms=(datetime.now() - start_time).total_seconds() * 1000
                )

            response_time_ms = (datetime.now() - start_time).total_seconds() * 1000

            return QueryResult(
                success=True,
                source="Telegram",
                total=len(results),
                results=results[:limit],
                query_params=query_params,
                response_time_ms=response_time_ms
            )

        except Exception as e:
            # Catch-all at integration boundary - acceptable to return error instead of crashing
            response_time_ms = (datetime.now() - start_time).total_seconds() * 1000
            logger.error(f"Telegram search failed: {e}", exc_info=True)
            return QueryResult(
                success=False,
                source="Telegram",
                total=0,
                results=[],
                query_params=query_params,
                error=str(e),
                http_code=None,  # Non-HTTP error
                response_time_ms=response_time_ms
            )

    async def _search_channels(self, params: Dict, limit: int) -> List[Dict]:
        """Search for public channels by query."""
        query = params.get("query", "")

        if not query:
            return []

        results = []

        try:
            # Search for channels using Telegram's global search
            search_result = await self.client(functions.contacts.SearchRequest(
                q=query,
                limit=limit
            ))

            # Extract channel information using defensive builder
            for chat in search_result.chats:
                if hasattr(chat, 'username') and chat.username:
                    title = SearchResultBuilder.safe_text(getattr(chat, 'title', ''), default="Telegram Channel")
                    members = getattr(chat, 'participants_count', 'Unknown')
                    # Three-tier model: preserve full content with build_with_raw()
                    snippet_text = f"Members: {members}"
                    results.append(SearchResultBuilder()
                        .title(title, default="Telegram Channel")
                        .url(f"https://t.me/{chat.username}")
                        .snippet(snippet_text)
                        .raw_content(snippet_text)  # Full content
                        .api_response({
                            "id": chat.id,
                            "username": chat.username,
                            "title": title,
                            "members": members
                        })  # Preserve channel data
                        .metadata({
                            "channel_id": chat.id,
                            "username": chat.username,
                            "members": members if members != 'Unknown' else None,
                            "verified": getattr(chat, 'verified', False)
                        })
                        .build_with_raw())

        except Exception as e:
            # Catch-all at integration boundary - acceptable to return partial results instead of crashing
            logger.error(f"Telegram channel search failed: {e}", exc_info=True)
            print(f"[WARN] Channel search failed: {e}")

        return results

    async def _get_channel_messages(self, params: Dict, limit: int) -> List[Dict]:
        """Get recent messages from a specific channel."""
        channel_username = params.get("channel_username", "").replace("@", "")

        if not channel_username:
            return []

        results = []

        try:
            # Get channel entity
            channel = await self.client.get_entity(channel_username)

            # Get recent messages
            messages = await self.client.get_messages(channel, limit=limit)

            for msg in messages:
                if msg.message:  # Skip empty messages
                    msg_text = SearchResultBuilder.safe_text(msg.message)
                    # Three-tier model: preserve full content with build_with_raw()
                    results.append(SearchResultBuilder()
                        .title(f"@{channel_username}: {msg_text[:100]}..." if msg_text else "Telegram Message",
                               default="Telegram Message")
                        .url(f"https://t.me/{channel_username}/{msg.id}")
                        .snippet(msg_text[:500] if msg_text else "")
                        .raw_content(msg_text)  # Full content, never truncated
                        .date(msg.date.isoformat() if msg.date else None)
                        .api_response({
                            "id": msg.id,
                            "message": msg_text,
                            "date": msg.date.isoformat() if msg.date else None,
                            "channel": channel_username
                        })  # Preserve message data
                        .metadata({
                            "message_id": msg.id,
                            "channel": channel_username,
                            "views": getattr(msg, 'views', None),
                            "forwards": getattr(msg, 'forwards', None)
                        })
                        .build_with_raw())

        except Exception as e:
            # Catch-all at integration boundary - acceptable to return empty results instead of crashing
            logger.error(f"Telegram failed to get messages from @{channel_username}: {e}", exc_info=True)
            print(f"[WARN] Failed to get messages from @{channel_username}: {e}")

        return results

    async def _global_search(self, params: Dict, limit: int) -> List[Dict]:
        """Search for messages across channels by keywords."""
        keywords = params.get("keywords", [])

        if not keywords:
            return []

        # Telegram doesn't have a direct global message search API
        # Strategy: Search for channels related to keywords, then get messages
        results = []
        channels_checked = set()

        for keyword in keywords[:3]:  # Limit to first 3 keywords to avoid overload
            try:
                # Search for channels matching keyword
                search_result = await self.client(functions.contacts.SearchRequest(
                    q=keyword,
                    limit=5
                ))

                # Get messages from found channels
                for chat in search_result.chats:
                    if hasattr(chat, 'username') and chat.username and chat.username not in channels_checked:
                        channels_checked.add(chat.username)

                        try:
                            messages = await self.client.get_messages(chat, limit=10, search=keyword)

                            for msg in messages:
                                if msg.message and any(kw.lower() in msg.message.lower() for kw in keywords):
                                    msg_text = SearchResultBuilder.safe_text(msg.message)
                                    # Three-tier model: preserve full content with build_with_raw()
                                    results.append(SearchResultBuilder()
                                        .title(f"@{chat.username}: {msg_text[:100]}..." if msg_text else "Telegram Message",
                                               default="Telegram Message")
                                        .url(f"https://t.me/{chat.username}/{msg.id}")
                                        .snippet(msg_text[:500] if msg_text else "")
                                        .raw_content(msg_text)  # Full content, never truncated
                                        .date(msg.date.isoformat() if msg.date else None)
                                        .api_response({
                                            "id": msg.id,
                                            "message": msg_text,
                                            "date": msg.date.isoformat() if msg.date else None,
                                            "channel": chat.username
                                        })  # Preserve message data
                                        .metadata({
                                            "message_id": msg.id,
                                            "channel": chat.username,
                                            "keyword_match": keyword,
                                            "views": getattr(msg, 'views', None)
                                        })
                                        .build_with_raw())

                                    if len(results) >= limit:
                                        break
                        except Exception as e:
                            # Catch-all for individual channel failures - acceptable to continue with other channels
                            logger.error(f"Telegram failed to search channel {chat.username}: {e}", exc_info=True)
                            continue

                    if len(results) >= limit:
                        break
            except Exception as e:
                # Catch-all for keyword search failures - acceptable to continue with other keywords
                logger.error(f"Telegram failed to search keyword {keyword}: {e}", exc_info=True)
                continue

        return results[:limit]

    async def _get_channel_info(self, params: Dict) -> List[Dict]:
        """Get information about a specific channel."""
        channel_username = params.get("channel_username", "").replace("@", "")

        if not channel_username:
            return []

        try:
            channel = await self.client.get_entity(channel_username)

            # Get full channel info
            full_channel = await self.client(functions.channels.GetFullChannelRequest(
                channel=channel
            ))

            channel_title = SearchResultBuilder.safe_text(getattr(channel, 'title', ''), default=channel_username)
            description = SearchResultBuilder.safe_text(full_channel.full_chat.about, default="No description")
            # Three-tier model: preserve full content with build_with_raw()
            return [SearchResultBuilder()
                .title(f"Telegram Channel: @{channel_username}", default="Telegram Channel")
                .url(f"https://t.me/{channel_username}")
                .snippet(description)
                .raw_content(description)  # Full content, never truncated
                .api_response({  # Preserve channel data
                    "channel_id": channel.id,
                    "username": channel_username,
                    "title": channel_title,
                    "members": getattr(channel, 'participants_count', None),
                    "verified": getattr(channel, 'verified', False),
                    "description": getattr(full_channel.full_chat, 'about', '')
                })
                .metadata({
                    "channel_id": channel.id,
                    "username": channel_username,
                    "title": channel_title,
                    "members": getattr(channel, 'participants_count', None),
                    "verified": getattr(channel, 'verified', False),
                    "description": description
                })
                .build_with_raw()]

        except Exception as e:
            # Catch-all at integration boundary - acceptable to return empty results instead of crashing
            logger.error(f"Telegram failed to get info for @{channel_username}: {e}", exc_info=True)
            print(f"[WARN] Failed to get info for @{channel_username}: {e}")
            return []

    def __del__(self) -> None:
        """Cleanup: disconnect Telegram client."""
        if self.client and self._authenticated:
            try:
                asyncio.get_event_loop().run_until_complete(self.client.disconnect())
            except Exception as e:
                # Don't raise in __del__ - can cause interpreter crashes
                logging.error(f"Telegram client disconnect failed in __del__: {e}", exc_info=True)
