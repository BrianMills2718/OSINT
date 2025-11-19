#!/usr/bin/env python3
"""
Parallel executor for database queries.

This module handles the parallel execution of queries across multiple databases,
including relevance checking, query generation, and search execution.
"""

import asyncio
import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from core.database_integration_base import DatabaseIntegration, QueryResult
from core.api_request_tracker import log_request


class ParallelExecutor:
    """
    Execute database queries in parallel for maximum performance.

    This class orchestrates the three-phase process:
    1. Relevance check (fast keyword filtering)
    2. Query generation (parallel LLM calls)
    3. Search execution (parallel API calls)

    Usage:
        executor = ParallelExecutor(max_concurrent=5)
        results = await executor.execute_all(
            research_question="What cybersecurity jobs are available?",
            databases=[db1, db2, db3],
            api_keys={"db1": "key1", "db2": "key2"},
            limit=10
        )
    """

    def __init__(self, max_concurrent: int = 10):
        """
        Initialize the parallel executor.

        Args:
            max_concurrent: Maximum number of concurrent API calls.
                           Set lower to avoid rate limits, higher for speed.
        """
        self.max_concurrent = max_concurrent

    async def execute_all(self,
                          research_question: str,
                          databases: List[DatabaseIntegration],
                          api_keys: Dict[str, str],
                          limit: int = 10) -> Dict[str, QueryResult]:
        """
        Execute queries across all databases in parallel.

        This is the main entry point for parallel database queries. It handles
        the full pipeline: relevance → query generation → execution.

        Args:
            research_question: The user's research question
            databases: List of DatabaseIntegration instances to query
            api_keys: Dict mapping database IDs to API keys
            limit: Maximum results per database

        Returns:
            Dict mapping database ID to QueryResult

        Example:
            results = await executor.execute_all(
                "What AI contracts are available?",
                [clearancejobs_db, sam_db, usajobs_db],
                {"sam": "SAM-key-123"},
                limit=20
            )

            for db_id, result in results.items():
                if result.success:
                    print(f"{result.source}: {result.total} results")
        """

        if not databases:
            return {}

        print(f"🔍 Researching across {len(databases)} databases...")
        start_time = datetime.now()

        # Phase 1: Relevance check (parallel, fast)
        print(f"  Phase 1: Checking relevance...")
        relevant_dbs = await self._filter_relevant(research_question, databases)
        print(f"  ✓ {len(relevant_dbs)}/{len(databases)} databases are relevant")

        if not relevant_dbs:
            print("  No relevant databases found")
            return {}

        # Phase 2: Generate queries (parallel LLM calls)
        print(f"  Phase 2: Generating queries...")
        db_query_pairs = await self._generate_all_queries(research_question, relevant_dbs)
        print(f"  ✓ Generated {len(db_query_pairs)} queries")

        if not db_query_pairs:
            print("  No queries generated")
            return {}

        # Phase 3: Execute searches (parallel with rate limiting)
        print(f"  Phase 3: Executing searches...")
        result_dict = await self._execute_all_searches(db_query_pairs, api_keys, limit)

        total_time = (datetime.now() - start_time).total_seconds()
        print(f"✓ Completed in {total_time:.1f}s")

        return result_dict

    async def execute_with_sources(self,
                                   research_question: str,
                                   source_ids: List[str],
                                   limit: int = 10) -> Dict:
        """
        Execute research using only specified sources.

        Used by ResearchSupervisor for selective source routing.
        This is a convenience wrapper around execute_all() that filters
        to only the requested sources.

        Args:
            research_question: The user's research question
            source_ids: List of source IDs to query (e.g., ["sam_gov", "twitter"])
            limit: Maximum results per source

        Returns:
            Dict with results from requested sources

        Example:
            # Query only government sources
            results = await executor.execute_with_sources(
                "What AI contracts exist?",
                source_ids=["sam_gov", "usajobs"],
                limit=10
            )
        """
        # Note: This method needs to be called from IntelligentExecutor
        # which has access to the registry and API keys
        # For now, return a placeholder - will be properly implemented
        # when wiring everything together in Phase 1E

        logging.info(
            f"execute_with_sources called with {len(source_ids)} sources: {source_ids}"
        )

        return {
            "research_question": research_question,
            "source_ids": source_ids,
            "results": {},
            "note": "Implementation pending Phase 1E integration"
        }

    async def _filter_relevant(self,
                               research_question: str,
                               databases: List[DatabaseIntegration]) -> List[DatabaseIntegration]:
        """
        Phase 1: Filter databases by relevance.

        Runs relevance checks in parallel using fast keyword matching.
        Databases that return False are excluded from further processing.

        Args:
            research_question: The research question
            databases: List of all databases

        Returns:
            List of relevant databases
        """
        tasks = [
            self._check_relevance(db, research_question)
            for db in databases
        ]

        relevance_results = await asyncio.gather(*tasks, return_exceptions=True)

        relevant_dbs = []
        for db, is_relevant in zip(databases, relevance_results):
            if isinstance(is_relevant, Exception):
                print(f"    ⚠️  {db.metadata.name}: Relevance check failed ({is_relevant})")
                continue

            if is_relevant:
                relevant_dbs.append(db)
            else:
                print(f"    ⊘ {db.metadata.name}: Not relevant, skipping")

        return relevant_dbs

    async def _check_relevance(self,
                               db: DatabaseIntegration,
                               question: str) -> bool:
        """
        Check if a single database is relevant.

        Args:
            db: Database to check
            question: Research question

        Returns:
            True if relevant, False otherwise
        """
        try:
            return await db.is_relevant(question)
        except Exception as e:
            print(f"⚠️ Relevance check failed for {db.metadata.name}: {e}")
            return False

    async def _generate_all_queries(self,
                                    research_question: str,
                                    databases: List[DatabaseIntegration]
                                    ) -> List[Tuple[DatabaseIntegration, Dict]]:
        """
        Phase 2: Generate queries for all relevant databases.

        Runs LLM query generation in parallel for maximum speed.

        Args:
            research_question: The research question
            databases: List of relevant databases

        Returns:
            List of (database, query_params) tuples
        """
        tasks = [
            self._generate_query(db, research_question)
            for db in databases
        ]

        query_results = await asyncio.gather(*tasks, return_exceptions=True)

        db_query_pairs = []
        for db, enriched in zip(databases, query_results):
            if isinstance(enriched, Exception):
                print(f"    ⚠️  {db.metadata.name}: Query generation failed ({enriched})")
                continue

            if enriched is None:
                print(f"    ✗ {db.metadata.name}: ERROR - generate_query_with_reasoning() returned None (uncaught exception)")
                logging.error(
                    f"CRITICAL: Integration {db.metadata.name} returned None for query: '{research_question}'. "
                    f"This should NEVER happen - indicates uncaught exception in wrapper or integration. "
                    f"Check integration code and wrapper implementation."
                )
                continue

            # Handle rejection (LLM determined not relevant)
            if not enriched.get("relevant", False):
                rejection_reason = enriched.get("rejection_reason", "No reason provided")
                suggested = enriched.get("suggested_reformulation")

                print(f"    ⊘ {db.metadata.name}: Not relevant - {rejection_reason}")
                if suggested:
                    print(f"      Suggestion: {suggested}")

                logging.info(
                    f"Integration {db.metadata.name} rejected query: '{research_question}'. "
                    f"Reason: {rejection_reason}. Suggested reformulation: {suggested or 'None'}"
                )
                continue

            # Relevant query - extract clean params for execute_search()
            params = enriched.get("query_params")
            if params is None:
                print(f"    ✗ {db.metadata.name}: ERROR - Relevant but query_params is None (wrapper bug)")
                logging.error(
                    f"CRITICAL: Integration {db.metadata.name} returned relevant=True but query_params=None. "
                    f"This indicates a bug in the wrapper or integration implementation."
                )
                continue

            print(f"    ✓ {db.metadata.name}: Query generated")
            db_query_pairs.append((db, params))

        return db_query_pairs

    async def _generate_query(self,
                             db: DatabaseIntegration,
                             question: str) -> Optional[Dict]:
        """
        Generate query for a single database using LLM with rejection reasoning.

        Args:
            db: Database integration
            question: Research question

        Returns:
            Enriched dict with {"relevant": bool, "query_params": dict|None,
            "rejection_reason": str|None, "suggested_reformulation": str|None},
            or None on error
        """
        try:
            start = datetime.now()
            enriched = await db.generate_query_with_reasoning(question)
            duration_ms = (datetime.now() - start).total_seconds() * 1000

            # Log LLM call for cost tracking with rejection reasoning
            log_request(
                api_name=f"{db.metadata.name}_QueryGen",
                endpoint="LLM",
                status_code=200,
                response_time_ms=duration_ms,
                error_message=enriched.get("rejection_reason") if not enriched.get("relevant") else None,
                request_params={
                    "question_length": len(question),
                    "relevant": enriched.get("relevant"),
                    "suggested_reformulation": enriched.get("suggested_reformulation")
                }
            )

            return enriched

        except Exception as e:
            print(f"⚠️ Query generation error for {db.metadata.name}: {e}")
            return None

    async def _execute_all_searches(self,
                                    db_query_pairs: List[Tuple[DatabaseIntegration, Dict]],
                                    api_keys: Dict[str, str],
                                    limit: int) -> Dict[str, QueryResult]:
        """
        Phase 3: Execute all searches in parallel with rate limiting.

        Uses a semaphore to limit concurrent API calls, preventing rate limit issues.

        Args:
            db_query_pairs: List of (database, query_params) tuples
            api_keys: API keys dict
            limit: Result limit per database

        Returns:
            Dict mapping database ID to QueryResult
        """
        semaphore = asyncio.Semaphore(self.max_concurrent)

        async def execute_with_semaphore(db: DatabaseIntegration, params: Dict):
            """Execute with semaphore to limit concurrency."""
            async with semaphore:
                return await self._execute_search(db, params, api_keys, limit)

        tasks = [
            execute_with_semaphore(db, params)
            for db, params in db_query_pairs
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Build result dict
        result_dict = {}
        for (db, params), result in zip(db_query_pairs, results):
            if isinstance(result, Exception):
                # Create error result
                print(f"    ✗ {db.metadata.name}: Search failed ({result})")
                result_dict[db.metadata.id] = QueryResult(
                    success=False,
                    source=db.metadata.name,
                    total=0,
                    results=[],
                    query_params=params,
                    error=str(result)
                )
            else:
                status = "✓" if result.success else "✗"
                print(f"    {status} {db.metadata.name}: {result.total} results ({result.response_time_ms:.0f}ms)")
                result_dict[db.metadata.id] = result

        return result_dict

    async def _execute_search(self,
                             db: DatabaseIntegration,
                             params: Dict,
                             api_keys: Dict[str, str],
                             limit: int) -> QueryResult:
        """
        Execute search for a single database.

        Args:
            db: Database integration
            params: Query parameters
            api_keys: API keys dict
            limit: Result limit

        Returns:
            QueryResult
        """
        api_key = api_keys.get(db.metadata.id)

        try:
            return await db.execute_search(params, api_key, limit)
        except Exception as e:
            # Catch any uncaught exceptions and return error result
            return QueryResult(
                success=False,
                source=db.metadata.name,
                total=0,
                results=[],
                query_params=params,
                error=f"Execution error: {str(e)}"
            )
