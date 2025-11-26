#!/usr/bin/env python3
"""
Compare v1 (SimpleDeepResearch) vs v2 (RecursiveResearchAgent) results.

Phase 4 of v2 migration - validates that v2 produces equivalent or better results.
"""

import asyncio
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Tuple

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

# Import both research engines
from research.deep_research import SimpleDeepResearch
from research.recursive_agent import RecursiveResearchAgent, Constraints, GoalStatus

# Test queries from migration plan
TEST_QUERIES = [
    ("Simple", "Find federal AI contracts awarded in 2024"),
    ("Company", "Palantir government contracts and controversies"),
    ("Topic", "DoD cybersecurity spending trends"),
    ("Multi-source", "Federal contractor lobbying activities"),
    ("Complex", "Investigative report on defense AI programs"),
]


async def run_v1(query: str, max_time_minutes: int = 3) -> Dict[str, Any]:
    """Run v1 research engine."""
    start = time.time()

    engine = SimpleDeepResearch(
        max_tasks=3,  # Limit for comparison
        max_time_minutes=max_time_minutes,
        max_retries_per_task=2,
        max_concurrent_tasks=3,
        save_output=True,
        output_dir="data/research_output"
    )

    result = await engine.research(query)
    duration = time.time() - start

    return {
        "version": "v1",
        "query": query,
        "duration_seconds": round(duration, 1),
        "tasks_executed": result.get("tasks_executed", 0),
        "total_results": result.get("total_results", 0),
        "unique_results": result.get("unique_results", 0),
        "has_report": bool(result.get("report")),
        "output_dir": result.get("output_dir"),
        "cost_estimate": result.get("cost_estimate", "N/A"),
    }


async def run_v2(query: str, max_time_seconds: int = 180) -> Dict[str, Any]:
    """Run v2 research engine."""
    start = time.time()

    agent = RecursiveResearchAgent(
        constraints=Constraints(
            max_depth=8,
            max_time_seconds=max_time_seconds,
            max_goals=20,
            max_cost_dollars=2.0,
            max_concurrent_tasks=5
        ),
        output_dir="data/research_v2"
    )

    result = await agent.research(query)
    duration = time.time() - start

    return {
        "version": "v2",
        "query": query,
        "duration_seconds": round(duration, 1),
        "status": result.status.value,
        "evidence_count": len(result.evidence),
        "sub_goals": len(result.sub_results),
        "confidence": round(result.confidence * 100),
        "has_synthesis": bool(result.synthesis),
        "depth_reached": result.depth,
        "cost_dollars": round(result.cost_dollars, 4),
    }


def print_comparison(v1_result: Dict, v2_result: Dict):
    """Print side-by-side comparison."""
    print("\n" + "=" * 70)
    print(f"COMPARISON: {v1_result['query'][:50]}...")
    print("=" * 70)

    print(f"\n{'Metric':<25} {'v1':<20} {'v2':<20}")
    print("-" * 65)

    # Duration
    v1_dur = v1_result.get('duration_seconds', 'N/A')
    v2_dur = v2_result.get('duration_seconds', 'N/A')
    winner = "v2 faster" if v2_dur < v1_dur else "v1 faster" if v1_dur < v2_dur else "tie"
    print(f"{'Duration (s)':<25} {v1_dur:<20} {v2_dur:<20} [{winner}]")

    # Results
    v1_results = v1_result.get('total_results', v1_result.get('unique_results', 0))
    v2_results = v2_result.get('evidence_count', 0)
    winner = "v2 more" if v2_results > v1_results else "v1 more" if v1_results > v2_results else "tie"
    print(f"{'Results/Evidence':<25} {v1_results:<20} {v2_results:<20} [{winner}]")

    # Tasks/Goals
    v1_tasks = v1_result.get('tasks_executed', 0)
    v2_goals = v2_result.get('sub_goals', 0)
    print(f"{'Tasks/Sub-goals':<25} {v1_tasks:<20} {v2_goals:<20}")

    # Report/Synthesis
    v1_report = "Yes" if v1_result.get('has_report') else "No"
    v2_synth = "Yes" if v2_result.get('has_synthesis') else "No"
    print(f"{'Report/Synthesis':<25} {v1_report:<20} {v2_synth:<20}")

    # Cost
    v1_cost = v1_result.get('cost_estimate', 'N/A')
    v2_cost = f"${v2_result.get('cost_dollars', 0)}"
    print(f"{'Cost':<25} {str(v1_cost):<20} {v2_cost:<20}")

    # v2-specific
    if v2_result.get('confidence'):
        print(f"{'Confidence':<25} {'N/A':<20} {v2_result['confidence']}%")
    if v2_result.get('status'):
        print(f"{'Status':<25} {'N/A':<20} {v2_result['status']:<20}")


async def run_comparison(query_name: str, query: str) -> Tuple[Dict, Dict]:
    """Run both engines and compare."""
    print(f"\n{'#' * 70}")
    print(f"# Test: {query_name}")
    print(f"# Query: {query}")
    print(f"{'#' * 70}")

    # Run v2 first (typically faster)
    print("\n[v2] Starting recursive agent...")
    v2_result = await run_v2(query)
    print(f"[v2] Complete: {v2_result['evidence_count']} evidence, {v2_result['duration_seconds']}s")

    # Run v1
    print("\n[v1] Starting deep research...")
    v1_result = await run_v1(query)
    print(f"[v1] Complete: {v1_result['total_results']} results, {v1_result['duration_seconds']}s")

    print_comparison(v1_result, v2_result)

    return v1_result, v2_result


async def main():
    """Run comparison tests."""
    print("=" * 70)
    print("V1 vs V2 COMPARISON TEST")
    print(f"Started: {datetime.now().isoformat()}")
    print("=" * 70)

    results = []

    # Run subset of queries (can be expanded)
    # Start with just 2 queries for quick validation
    test_subset = TEST_QUERIES[:2]  # Simple and Company queries

    for query_name, query in test_subset:
        try:
            v1_result, v2_result = await run_comparison(query_name, query)
            results.append({
                "name": query_name,
                "query": query,
                "v1": v1_result,
                "v2": v2_result
            })
        except Exception as e:
            print(f"\n[ERROR] {query_name}: {e}")
            import traceback
            traceback.print_exc()

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    v2_wins = 0
    v1_wins = 0

    for r in results:
        v1_results = r['v1'].get('total_results', r['v1'].get('unique_results', 0))
        v2_results = r['v2'].get('evidence_count', 0)
        v1_time = r['v1'].get('duration_seconds', 999)
        v2_time = r['v2'].get('duration_seconds', 999)

        # Score: more results and faster is better
        v2_better_results = v2_results >= v1_results
        v2_faster = v2_time <= v1_time

        if v2_better_results and v2_faster:
            v2_wins += 1
            verdict = "v2 BETTER"
        elif not v2_better_results and not v2_faster:
            v1_wins += 1
            verdict = "v1 BETTER"
        else:
            verdict = "MIXED"

        print(f"{r['name']:<15}: {verdict}")
        print(f"  v1: {v1_results} results in {v1_time}s")
        print(f"  v2: {v2_results} evidence in {v2_time}s")

    print(f"\nOverall: v2 wins={v2_wins}, v1 wins={v1_wins}, mixed={len(results)-v2_wins-v1_wins}")

    # Save results
    output_file = Path("data/comparison_results.json")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\nResults saved to: {output_file}")


if __name__ == "__main__":
    asyncio.run(main())
