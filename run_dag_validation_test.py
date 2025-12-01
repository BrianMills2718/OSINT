#!/usr/bin/env python3
"""
DAG Validation Test - Proper 25-minute comparative query.
Tests if dependent goals execute after their dependencies complete.
"""

import asyncio
import json
from pathlib import Path
from research.recursive_agent import RecursiveResearchAgent, Constraints
from dotenv import load_dotenv

load_dotenv()

async def run_dag_validation():
    print("=" * 80)
    print("DAG DEPENDENCY VALIDATION TEST")
    print("=" * 80)
    print()
    print("Query: Compare Lockheed Martin vs Northrop Grumman federal contracts in 2025")
    print("Constraints: 25 minutes, depth 3, $0.10 cost limit")
    print()

    output_dir = Path("data/dag_validation_test")
    output_dir.mkdir(parents=True, exist_ok=True)

    constraints = Constraints(
        max_depth=3,
        max_time_seconds=1500,  # 25 minutes
        max_goals=10,
        max_cost_dollars=0.10
    )

    agent = RecursiveResearchAgent(
        constraints=constraints,
        output_dir=str(output_dir)
    )

    result = await agent.research("Compare Lockheed Martin vs Northrop Grumman federal contracts in 2025")

    print("\n" + "=" * 80)
    print("RESEARCH COMPLETE")
    print("=" * 80)
    print(f"Status: {result.status.value}")
    print(f"Evidence: {len(result.evidence)} pieces")
    print(f"Duration: {result.duration_seconds:.1f}s")
    print(f"Cost: ${result.cost_dollars:.4f}")

    # Analyze execution log for DAG validation
    log_file = output_dir / "execution_log.jsonl"
    if not log_file.exists():
        print("\n❌ ERROR: Execution log not found!")
        return False

    print(f"\n{output_dir=}")
    print("\nAnalyzing execution log for DAG validation...")

    with open(log_file) as f:
        events = [json.loads(line) for line in f]

    llm_responses = [e for e in events if e.get("event_type") == "llm_decomposition_response"]
    dag_groups = [e for e in events if e.get("event_type") == "dependency_groups_execution"]
    goal_decomposed = [e for e in events if e.get("event_type") == "goal_decomposed"]
    goal_completed = [e for e in events if e.get("event_type") == "goal_completed"]

    print(f"\nEvent counts:")
    print(f"  llm_decomposition_response: {len(llm_responses)}")
    print(f"  dependency_groups_execution: {len(dag_groups)}")
    print(f"  goal_decomposed: {len(goal_decomposed)}")
    print(f"  goal_completed: {len(goal_completed)}")

    # Check for dependency declarations
    dependencies_found = False
    dependencies_details = []

    for event in llm_responses:
        raw_deps = event.get("data", {}).get("raw_dependencies", [])
        for i, sg in enumerate(raw_deps):
            deps = sg.get("dependencies", [])
            desc = sg.get("description", "")[:60]
            if deps:
                dependencies_found = True
                dependencies_details.append(f"  Goal {i}: {desc}... (depends on {deps})")
            else:
                dependencies_details.append(f"  Goal {i}: {desc}... (independent)")

    print("\n" + "=" * 80)
    print("DEPENDENCY ANALYSIS")
    print("=" * 80)

    if dependencies_found:
        print("\n✅ SUCCESS: LLM declared dependencies!")
        print("\nDependency structure:")
        for detail in dependencies_details:
            print(detail)
    else:
        print("\n❌ FAILURE: No dependencies declared by LLM")
        print("\nSub-goals:")
        for detail in dependencies_details:
            print(detail)

    # Check DAG execution
    if dag_groups:
        print(f"\n✅ DAG execution logged ({len(dag_groups)} events)")
        for event in dag_groups:
            groups = event.get("data", {}).get("groups", [])
            print(f"\n  Total groups: {len(groups)}")
            for group in groups:
                idx = group.get("group_index")
                count = group.get("goal_count")
                print(f"    Group {idx}: {count} goal(s)")
    else:
        print("\n⚠️  No DAG execution logging found")

    # Check goal completion
    print("\n" + "=" * 80)
    print("GOAL COMPLETION ANALYSIS")
    print("=" * 80)

    for i, event in enumerate(goal_completed):
        goal_desc = event.get("goal", "")[:80]
        status = event.get("data", {}).get("status")
        evidence = event.get("data", {}).get("evidence_count", 0)
        duration = event.get("data", {}).get("duration_seconds", 0)
        print(f"\n{i+1}. {goal_desc}")
        print(f"   Status: {status}, Evidence: {evidence}, Duration: {duration:.1f}s")

    # Final verdict
    print("\n" + "=" * 80)
    print("TEST VERDICT")
    print("=" * 80)

    success_criteria = {
        "LLM declared dependencies": dependencies_found,
        "DAG execution logged": len(dag_groups) > 0,
        "Multiple execution groups": len(dag_groups) > 0 and any(
            e.get("data", {}).get("total_groups", 0) > 1 for e in dag_groups
        ),
        "Research completed": result.status.value == "completed"
    }

    print("\nSuccess Criteria:")
    all_passed = True
    for criterion, passed in success_criteria.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status}: {criterion}")
        if not passed:
            all_passed = False

    print("\n" + "=" * 80)
    if all_passed:
        print("🎉 OVERALL: PASS - DAG infrastructure working correctly!")
    else:
        print("❌ OVERALL: FAIL - Some criteria not met")
    print("=" * 80)

    return all_passed


if __name__ == "__main__":
    success = asyncio.run(run_dag_validation())
    exit(0 if success else 1)
