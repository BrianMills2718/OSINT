#!/usr/bin/env python3
"""
Agentic executor for self-improving database queries.

Extends ParallelExecutor with automatic result evaluation and query refinement.
Uses an agent loop to iteratively improve search results when they're poor.

Architecture:
    Phase 1-3: Same as ParallelExecutor (relevance → generate → execute)
    Phase 4: Evaluate results quality
    Phase 5: Refine poor queries and re-execute (max iterations)
"""

import asyncio
import json
from typing import Dict, List, Tuple, Optional
from datetime import datetime
from llm_utils import acompletion

from parallel_executor import ParallelExecutor
from database_integration_base import DatabaseIntegration, QueryResult
from api_request_tracker import log_request


class AgenticExecutor(ParallelExecutor):
    """
    Self-improving search executor using agent-based refinement.

    Inherits all parallel execution logic from ParallelExecutor and adds:
    - Automatic result quality evaluation
    - LLM-powered query refinement
    - Iterative improvement (bounded by max_refinements)

    Usage:
        executor = AgenticExecutor(max_concurrent=5, max_refinements=2)
        results = await executor.execute_all(
            research_question="What cybersecurity jobs are available?",
            databases=[db1, db2, db3],
            api_keys={"db1": "key1"},
            limit=10
        )

    The executor will:
    1. Execute initial searches (parallel)
    2. Evaluate result quality
    3. Refine poor queries and re-execute (parallel, up to max_refinements times)
    4. Return best results
    """

    def __init__(self, max_concurrent: int = 10, max_refinements: int = 2):
        """
        Initialize the agentic executor.

        Args:
            max_concurrent: Maximum number of concurrent API calls
            max_refinements: Maximum refinement iterations per database (1-3 recommended)
        """
        super().__init__(max_concurrent)
        self.max_refinements = max(1, min(max_refinements, 3))  # Clamp 1-3

    async def execute_all(self,
                          research_question: str,
                          databases: List[DatabaseIntegration],
                          api_keys: Dict[str, str],
                          limit: int = 10) -> Dict[str, QueryResult]:
        """
        Execute queries with automatic refinement.

        This extends the base execute_all() with an additional refinement phase.

        Args:
            research_question: The user's research question
            databases: List of DatabaseIntegration instances to query
            api_keys: Dict mapping database IDs to API keys
            limit: Maximum results per database

        Returns:
            Dict mapping database ID to QueryResult (best attempt for each database)
        """

        if not databases:
            return {}

        print(f"🤖 Agentic search across {len(databases)} databases...")
        start_time = datetime.now()

        # Phase 1-3: Initial execution (inherited from ParallelExecutor)
        print(f"  Phase 1-3: Initial search...")
        results = await super().execute_all(research_question, databases, api_keys, limit)

        if not results:
            print("  No initial results")
            return {}

        # Phase 4: Evaluate and refine (NEW)
        refined_results = await self._evaluate_and_refine(
            results=results,
            research_question=research_question,
            databases=databases,
            api_keys=api_keys,
            limit=limit
        )

        total_time = (datetime.now() - start_time).total_seconds()
        print(f"✓ Agentic search completed in {total_time:.1f}s")

        return refined_results

    async def _evaluate_and_refine(self,
                                   results: Dict[str, QueryResult],
                                   research_question: str,
                                   databases: List[DatabaseIntegration],
                                   api_keys: Dict[str, str],
                                   limit: int) -> Dict[str, QueryResult]:
        """
        Evaluate result quality and refine poor results iteratively.

        Args:
            results: Initial search results
            research_question: Original research question
            databases: List of databases
            api_keys: API keys
            limit: Result limit

        Returns:
            Refined results (or original if no refinement needed)
        """

        print(f"  Phase 4: Evaluating results...")

        # Track which databases need refinement
        refinement_candidates = []

        for db_id, result in results.items():
            needs_refinement, reason = self._assess_result_quality(result)

            if needs_refinement:
                # Find the database object
                db = next((d for d in databases if d.metadata.id == db_id), None)
                if db:
                    refinement_candidates.append((db, result, reason))
                    print(f"    🔄 {result.source}: Needs refinement ({reason})")
            else:
                print(f"    ✓ {result.source}: Quality acceptable")

        if not refinement_candidates:
            print("  ✓ All results satisfactory")
            return results

        # Iterative refinement loop
        print(f"  Phase 5: Refining {len(refinement_candidates)} databases...")

        for iteration in range(self.max_refinements):
            print(f"    Refinement iteration {iteration + 1}/{self.max_refinements}...")

            # Refine all candidates in parallel
            refined_results_batch = await self._refine_all_parallel(
                refinement_candidates=refinement_candidates,
                research_question=research_question,
                api_keys=api_keys,
                limit=limit,
                iteration=iteration
            )

            # Update results with better ones
            new_candidates = []

            for db, old_result, refined_result in refined_results_batch:
                db_id = db.metadata.id

                # Compare: is refined better than original?
                if self._is_better_result(refined_result, old_result):
                    results[db_id] = refined_result
                    print(f"      ✓ {db.metadata.name}: Improved ({old_result.total} → {refined_result.total} results)")

                    # Check if still needs more refinement
                    needs_more, reason = self._assess_result_quality(refined_result)
                    if needs_more and iteration < self.max_refinements - 1:
                        new_candidates.append((db, refined_result, reason))
                        print(f"      🔄 {db.metadata.name}: Still needs refinement ({reason})")
                else:
                    print(f"      ⊘ {db.metadata.name}: No improvement, keeping original")

            # Update candidates for next iteration
            refinement_candidates = new_candidates

            if not refinement_candidates:
                print(f"    ✓ All refinements successful, stopping early")
                break

        if refinement_candidates:
            print(f"    ⚠️  {len(refinement_candidates)} databases still poor after {self.max_refinements} iterations")

        return results

    def _assess_result_quality(self, result: QueryResult) -> Tuple[bool, str]:
        """
        Quick heuristic evaluation of result quality.

        Uses simple rules to determine if refinement is needed:
        - Zero results → definitely needs refinement
        - Very few results (< 3) → probably needs refinement
        - Failed search → needs refinement

        Args:
            result: Query result to evaluate

        Returns:
            (needs_refinement: bool, reason: str)
        """

        # Failed search
        if not result.success:
            return (True, "search failed")

        # Zero results
        if result.total == 0:
            return (True, "zero results")

        # Very few results
        if result.total < 3:
            return (True, f"only {result.total} results")

        # TODO: Could add more sophisticated checks:
        # - Keyword relevance analysis
        # - Result diversity check
        # - Recency check (for time-sensitive queries)

        return (False, "acceptable")

    def _is_better_result(self, new_result: QueryResult, old_result: QueryResult) -> bool:
        """
        Compare two results and determine if new is better than old.

        Args:
            new_result: Refined result
            old_result: Original result

        Returns:
            True if new result is better, False otherwise
        """

        # Success is always better than failure
        if new_result.success and not old_result.success:
            return True

        if not new_result.success:
            return False

        # More results is generally better
        if new_result.total > old_result.total:
            return True

        return False

    async def _refine_all_parallel(self,
                                   refinement_candidates: List[Tuple[DatabaseIntegration, QueryResult, str]],
                                   research_question: str,
                                   api_keys: Dict[str, str],
                                   limit: int,
                                   iteration: int) -> List[Tuple[DatabaseIntegration, QueryResult, QueryResult]]:
        """
        Refine multiple databases in parallel.

        Args:
            refinement_candidates: List of (database, result, reason) tuples
            research_question: Original research question
            api_keys: API keys
            limit: Result limit
            iteration: Current iteration number

        Returns:
            List of (database, old_result, new_result) tuples
        """

        # Generate refined queries in parallel
        tasks = [
            self._refine_single_database(db, result, reason, research_question, api_keys, limit, iteration)
            for db, result, reason in refinement_candidates
        ]

        refined_results = await asyncio.gather(*tasks, return_exceptions=True)

        # Build result list
        results = []
        for (db, old_result, reason), new_result in zip(refinement_candidates, refined_results):
            if isinstance(new_result, Exception):
                print(f"      ⚠️  {db.metadata.name}: Refinement failed ({new_result})")
                # Keep old result
                results.append((db, old_result, old_result))
            else:
                results.append((db, old_result, new_result))

        return results

    async def _refine_single_database(self,
                                      db: DatabaseIntegration,
                                      old_result: QueryResult,
                                      reason: str,
                                      research_question: str,
                                      api_keys: Dict[str, str],
                                      limit: int,
                                      iteration: int) -> QueryResult:
        """
        Refine a single database query using LLM agent.

        Args:
            db: Database to refine
            old_result: Previous result
            reason: Why refinement is needed
            research_question: Original question
            api_keys: API keys
            limit: Result limit
            iteration: Refinement iteration number

        Returns:
            New QueryResult from refined search
        """

        try:
            # Step 1: Generate refined query using LLM
            start = datetime.now()
            refined_params = await self._generate_refined_query(
                db=db,
                old_params=old_result.query_params,
                old_result_count=old_result.total,
                reason=reason,
                research_question=research_question
            )
            duration_ms = (datetime.now() - start).total_seconds() * 1000

            # Log LLM call
            log_request(
                api_name=f"{db.metadata.name}_Refinement",
                endpoint="LLM",
                status_code=200,
                response_time_ms=duration_ms,
                error_message=None,
                request_params={"iteration": iteration, "reason": reason}
            )

            if not refined_params:
                # LLM couldn't generate refinement
                return old_result

            # Step 2: Execute refined search
            api_key = api_keys.get(db.metadata.id)
            new_result = await db.execute_search(refined_params, api_key, limit)

            return new_result

        except Exception as e:
            print(f"      ⚠️  {db.metadata.name}: Refinement error: {e}")
            return old_result

    async def _generate_refined_query(self,
                                     db: DatabaseIntegration,
                                     old_params: Dict,
                                     old_result_count: int,
                                     reason: str,
                                     research_question: str) -> Optional[Dict]:
        """
        Use LLM to generate a refined query based on poor results.

        The agent analyzes why the previous search failed and suggests improvements.

        Args:
            db: Database integration
            old_params: Previous query parameters
            old_result_count: Number of results from previous search
            reason: Why refinement is needed
            research_question: Original research question

        Returns:
            Refined query parameters, or None if unable to refine
        """

        prompt = f"""You are a search refinement agent for {db.metadata.name}.

Original research question: "{research_question}"

Previous search parameters: {json.dumps(old_params, indent=2)}

Previous search resulted in: {old_result_count} results
Problem: {reason}

Your task: Generate REFINED search parameters that will likely yield better results.

Refinement strategies to consider:
- If zero/few results → BROADEN the search:
  * Use more general keywords (e.g., "cyber security" → "security")
  * Remove or relax filters
  * Expand date ranges
  * Try alternative terminology

- If results seem off-topic → REFINE the search:
  * Use more specific keywords
  * Add relevant filters
  * Try domain-specific terms

Guidelines:
- Make ONE meaningful change from the original query
- Keep the same query structure as original
- Don't make queries overly broad (quality > quantity)
- If original query seems optimal, return it unchanged

Return your response as JSON with refined query parameters in the SAME format as the original query.
Include a "refinement_reasoning" field explaining your change.
"""

        try:
            # Use the database's own generate_query method to ensure correct schema
            # But provide context about the refinement
            response = await acompletion(
                model="gpt-5-mini",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )

            result = json.loads(response.choices[0].message.content)

            # Extract refinement reasoning if provided
            reasoning = result.pop("refinement_reasoning", "No reasoning provided")
            print(f"        Refinement: {reasoning}")

            return result

        except Exception as e:
            print(f"        ⚠️  LLM refinement failed: {e}")
            return None
