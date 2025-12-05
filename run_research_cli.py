#!/usr/bin/env python3
"""Simple CLI for running recursive research (v2).

This is the main entry point for CLI-based research.
Uses the v2 RecursiveResearchAgent architecture.
"""

import asyncio
import argparse
import logging
from datetime import datetime
from pathlib import Path

from research.recursive_agent import RecursiveResearchAgent, Constraints, GoalStatus
from config_loader import config
from dotenv import load_dotenv

load_dotenv()

# Configure logging to show INFO level
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s:%(name)s:%(message)s'
)


async def main():
    parser = argparse.ArgumentParser(description='Run recursive research with configurable parameters')
    parser.add_argument('question', help='Research question to investigate')

    # v2 arguments (map to Constraints)
    parser.add_argument('--max-depth', type=int, help='Maximum recursion depth (overrides config.yaml)')
    parser.add_argument('--max-time-minutes', type=int, help='Maximum time in minutes (overrides config.yaml)')
    parser.add_argument('--max-time', type=int, help='Maximum time in SECONDS (common CLI convention, overrides config.yaml)')
    parser.add_argument('--max-goals', type=int, help='Maximum total goals to pursue (overrides config.yaml)')
    parser.add_argument('--max-cost', type=float, help='Maximum cost in dollars (overrides config.yaml)')
    parser.add_argument('--max-concurrent', type=int, help='Max concurrent tasks (overrides config.yaml)')

    # Legacy v1 arguments (for backward compatibility - map to v2 equivalents)
    parser.add_argument('--max-tasks', type=int, help='Legacy: maps to --max-goals')
    parser.add_argument('--max-retries', type=int, help='Legacy: ignored in v2 (automatic retry logic)')

    # Export options
    parser.add_argument('--export', nargs='*', choices=['pdf', 'docx', 'word'],
                        metavar='FORMAT',
                        help='Export report to PDF/Word. Use without args for both, or specify: --export pdf docx')

    args = parser.parse_args()

    print(f"v2 Recursive Research Agent")
    print(f"=" * 50)
    print(f"Question: {args.question}\n")

    # Load config from config.yaml
    raw_config = config.get_raw_config()
    v2_config = raw_config.get("research", {}).get("recursive_agent", {})

    # Fall back to v1 config for backward compatibility
    v1_config = raw_config.get("research", {}).get("deep_research", {})

    # Build constraints - CLI args override config, with legacy fallbacks
    # Core limits (can be overridden by CLI args)
    max_goals = (
        args.max_goals if args.max_goals is not None
        else args.max_tasks if args.max_tasks is not None  # Legacy mapping
        else v2_config.get("max_goals", v1_config.get("max_tasks", 50))
    )

    # Handle time: --max-time is in SECONDS, --max-time-minutes is in minutes
    # We compute max_time_seconds directly to avoid precision loss
    if args.max_time is not None:
        # Exact seconds from CLI
        max_time_seconds = args.max_time
        max_time_minutes = max_time_seconds / 60  # For display only
    elif args.max_time_minutes is not None:
        max_time_minutes = args.max_time_minutes
        max_time_seconds = max_time_minutes * 60
    else:
        max_time_minutes = v2_config.get("max_time_minutes", v1_config.get("max_time_minutes", 30))
        max_time_seconds = max_time_minutes * 60

    max_depth = (
        args.max_depth if args.max_depth is not None
        else v2_config.get("max_depth", 15)
    )

    max_cost = (
        args.max_cost if args.max_cost is not None
        else v2_config.get("max_cost_dollars", 5.0)
    )

    max_concurrent = (
        args.max_concurrent if args.max_concurrent is not None
        else v2_config.get("max_concurrent_tasks", v1_config.get("max_concurrent_tasks", 5))
    )

    # Build constraints with ALL configurable fields from config.yaml
    constraints = Constraints(
        # Core limits
        max_depth=max_depth,
        max_time_seconds=max_time_seconds,
        max_goals=max_goals,
        max_cost_dollars=max_cost,
        max_results_per_source=v2_config.get("max_results_per_source", 20),
        max_concurrent_tasks=max_concurrent,

        # Prompt context limits
        max_sources_in_prompt=v2_config.get("max_sources_in_prompt", 20),
        max_evidence_in_prompt=v2_config.get("max_evidence_in_prompt", 10),
        max_evidence_for_analysis=v2_config.get("max_evidence_for_analysis", 20),
        max_sources_in_decompose=v2_config.get("max_sources_in_decompose", 15),
        max_goals_in_prompt=v2_config.get("max_goals_in_prompt", 10),
        max_evidence_for_synthesis=v2_config.get("max_evidence_for_synthesis", 30),
        max_content_chars_in_synthesis=v2_config.get("max_content_chars_in_synthesis", 500),

        # LLM cost estimates
        cost_per_assessment=v2_config.get("cost_per_assessment", 0.0002),
        cost_per_analysis=v2_config.get("cost_per_analysis", 0.0003),
        cost_per_decomposition=v2_config.get("cost_per_decomposition", 0.0003),
        cost_per_achievement_check=v2_config.get("cost_per_achievement_check", 0.0001),
        cost_per_synthesis=v2_config.get("cost_per_synthesis", 0.0005),
        cost_per_filter=v2_config.get("cost_per_filter", 0.0002),
        cost_per_reformulation=v2_config.get("cost_per_reformulation", 0.0002),

        # Early exit thresholds
        min_evidence_for_achievement_check=v2_config.get("min_evidence_for_achievement_check", 5),
        min_successes_for_achievement_check=v2_config.get("min_successes_for_achievement_check", 2),
        min_results_to_filter=v2_config.get("min_results_to_filter", 3),

        # Output limits
        max_evidence_in_saved_result=v2_config.get("max_evidence_in_saved_result", 50),
        max_evidence_per_source_in_report=v2_config.get("max_evidence_per_source_in_report", 5),
        max_content_chars_in_report=v2_config.get("max_content_chars_in_report", 200),
    )

    print(f"Constraints:")
    print(f"  Max depth: {constraints.max_depth}")
    print(f"  Max time: {max_time_seconds}s ({max_time_minutes:.1f} minutes)")
    print(f"  Max goals: {constraints.max_goals}")
    print(f"  Max cost: ${constraints.max_cost_dollars:.2f}")
    print(f"  Max concurrent: {constraints.max_concurrent_tasks}")
    print()

    # Create output directory
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    clean_question = "".join(c if c.isalnum() or c == " " else "_" for c in args.question[:50])
    clean_question = "_".join(clean_question.split())
    output_dir = Path("data/research_v2") / f"{timestamp}_{clean_question}"
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Output: {output_dir}")
    print()

    # Create agent and run research
    agent = RecursiveResearchAgent(
        constraints=constraints,
        output_dir=str(output_dir)
    )

    result = await agent.research(args.question)

    print("\n" + "=" * 50)
    print("RESEARCH COMPLETE")
    print("=" * 50)
    print(f"Status: {result.status.value}")
    print(f"Confidence: {int(result.confidence * 100)}%")
    print(f"Evidence: {len(result.evidence)} pieces")
    print(f"Sub-goals: {len(result.sub_results)}")
    print(f"Duration: {result.duration_seconds:.1f}s")
    print(f"Cost: ${result.cost_dollars:.4f}")
    print(f"\nOutput saved to: {output_dir}")

    # Show synthesis preview
    if result.synthesis:
        print("\n--- Synthesis Preview ---")
        preview = result.synthesis[:500] + "..." if len(result.synthesis) > 500 else result.synthesis
        print(preview)

    # Export to PDF/Word if requested
    if args.export is not None:
        from core.report_exporter import ReportExporter

        # Default to both formats if --export used without args
        formats = args.export if args.export else ['pdf', 'docx']
        # Normalize 'word' to 'docx'
        formats = ['docx' if f == 'word' else f for f in formats]

        report_md = output_dir / "report.md"
        if report_md.exists():
            print("\n--- Exporting Report ---")
            exporter = ReportExporter()
            export_results = exporter.export_all(
                source=report_md,
                output_dir=output_dir,
                base_name="report",
                formats=formats
            )
            for fmt, path in export_results.items():
                print(f"  {fmt.upper()}: {path}")
        else:
            print("\nWarning: No report.md found, skipping export")

    return 0 if result.status == GoalStatus.COMPLETED else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
