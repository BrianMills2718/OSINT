#!/usr/bin/env python3
"""
CLI for v2 recursive research agent.

Usage:
    python3 apps/recursive_research.py "Research question here"
    python3 apps/recursive_research.py "Research question" --max-depth 5 --max-time 10

See docs/V2_RECURSIVE_AGENT_MIGRATION_PLAN.md for architecture details.
"""

import asyncio
import argparse
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from research.recursive_agent import RecursiveResearchAgent, Constraints, GoalStatus
from config_loader import config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s:%(name)s:%(message)s'
)
logger = logging.getLogger('RecursiveResearch')

# Load environment
load_dotenv()


def create_output_dir(question: str) -> Path:
    """Create timestamped output directory for research results."""
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    # Clean question for directory name (first 50 chars, alphanumeric + spaces)
    clean_question = "".join(c if c.isalnum() or c == " " else "_" for c in question[:50])
    clean_question = "_".join(clean_question.split())  # Replace multiple spaces

    output_dir = Path("data/research_v2") / f"{timestamp}_{clean_question}"
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def save_results(result, output_dir: Path, question: str):
    """Save research results to output directory."""
    # Save metadata
    metadata = {
        "question": question,
        "status": result.status.value,
        "confidence": result.confidence,
        "evidence_count": len(result.evidence),
        "sub_results_count": len(result.sub_results),
        "depth": result.depth,
        "duration_seconds": result.duration_seconds,
        "cost_dollars": result.cost_dollars,
        "timestamp": datetime.now().isoformat()
    }

    with open(output_dir / "metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)

    # Save evidence as JSON
    evidence_data = []
    for e in result.evidence:
        evidence_data.append({
            "title": e.title,
            "url": e.url,
            "content": e.content,
            "source": e.source,
            "relevance_score": e.relevance_score,
            "metadata": e.metadata
        })

    with open(output_dir / "evidence.json", "w") as f:
        json.dump(evidence_data, f, indent=2)

    # Save markdown report
    report = generate_report(result, question)
    with open(output_dir / "report.md", "w") as f:
        f.write(report)

    return metadata


def generate_report(result, question: str) -> str:
    """Generate markdown report from results."""
    lines = [
        "# Research Report",
        "",
        f"**Objective:** {question}",
        "",
        f"**Status:** {result.status.value}",
        f"**Confidence:** {int(result.confidence * 100)}%",
        f"**Duration:** {result.duration_seconds:.1f}s",
        f"**Cost:** ${result.cost_dollars:.4f}",
        f"**Evidence:** {len(result.evidence)} pieces",
        "",
    ]

    # Add synthesis if available
    if result.synthesis:
        lines.extend([
            "## Summary",
            "",
            result.synthesis,
            "",
        ])

    # Group evidence by source
    evidence_by_source = {}
    for e in result.evidence:
        source = e.source or "Unknown"
        if source not in evidence_by_source:
            evidence_by_source[source] = []
        evidence_by_source[source].append(e)

    # Add evidence sections
    if evidence_by_source:
        lines.extend([
            "## Evidence Sources",
            "",
        ])

        for source, evidence_list in evidence_by_source.items():
            lines.append(f"### {source} ({len(evidence_list)} results)")
            lines.append("")

            for e in evidence_list[:10]:  # Limit to 10 per source for readability
                lines.append(f"- **{e.title}**")
                if e.url:
                    lines.append(f"  - URL: {e.url}")
                if e.content:
                    lines.append(f"  - {e.content[:200]}...")
                lines.append("")

    # Add sub-results summary if any
    if result.sub_results:
        lines.extend([
            "## Sub-Goals",
            "",
        ])
        for i, sub in enumerate(result.sub_results, 1):
            status_icon = "✅" if sub.status == GoalStatus.COMPLETED else "❌"
            lines.append(f"{i}. {status_icon} {sub.goal[:100]}...")
            lines.append(f"   - Evidence: {len(sub.evidence)}, Confidence: {int(sub.confidence * 100)}%")
            lines.append("")

    return "\n".join(lines)


async def main():
    parser = argparse.ArgumentParser(
        description='v2 Recursive Research Agent - LLM-driven goal decomposition',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python3 apps/recursive_research.py "Find federal AI contracts awarded in 2024"
    python3 apps/recursive_research.py "Investigate company X" --max-depth 5 --max-time 10
    python3 apps/recursive_research.py "Complex topic" --max-goals 30 --max-cost 1.0
        """
    )

    # Required argument
    parser.add_argument('question', help='Research question to investigate')

    # v2-specific arguments
    parser.add_argument('--max-depth', type=int, default=10,
                        help='Maximum recursion depth (default: 10)')
    parser.add_argument('--max-time', type=int, default=30,
                        help='Maximum time in minutes (default: 30)')
    parser.add_argument('--max-goals', type=int, default=50,
                        help='Maximum total goals to pursue (default: 50)')
    parser.add_argument('--max-cost', type=float, default=5.0,
                        help='Maximum cost in dollars (default: $5.00)')
    parser.add_argument('--max-concurrent', type=int, default=5,
                        help='Maximum concurrent tasks (default: 5)')

    # Output options
    parser.add_argument('--output-dir', type=str, default=None,
                        help='Custom output directory (default: auto-generated)')
    parser.add_argument('--quiet', action='store_true',
                        help='Suppress progress output')

    args = parser.parse_args()

    # Load any config overrides from config.yaml
    raw_config = config.get_raw_config()
    v2_config = raw_config.get("research", {}).get("recursive_agent", {})

    # Build constraints (CLI args override config)
    constraints = Constraints(
        max_depth=args.max_depth or v2_config.get("max_depth", 10),
        max_time_seconds=(args.max_time or v2_config.get("max_time_minutes", 30)) * 60,
        max_goals=args.max_goals or v2_config.get("max_goals", 50),
        max_cost_dollars=args.max_cost or v2_config.get("max_cost_dollars", 5.0),
        max_concurrent_tasks=args.max_concurrent or v2_config.get("max_concurrent_tasks", 5)
    )

    # Create output directory
    if args.output_dir:
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
    else:
        output_dir = create_output_dir(args.question)

    if not args.quiet:
        print(f"v2 Recursive Research Agent")
        print(f"=" * 50)
        print(f"Question: {args.question}")
        print(f"Output: {output_dir}")
        print(f"\nConstraints:")
        print(f"  Max depth: {constraints.max_depth}")
        print(f"  Max time: {constraints.max_time_seconds // 60} minutes")
        print(f"  Max goals: {constraints.max_goals}")
        print(f"  Max cost: ${constraints.max_cost_dollars:.2f}")
        print(f"  Max concurrent: {constraints.max_concurrent_tasks}")
        print(f"\nStarting research...\n")

    # Create agent and run research
    agent = RecursiveResearchAgent(
        constraints=constraints,
        output_dir=str(output_dir)
    )

    try:
        result = await agent.research(args.question)

        # Save results
        metadata = save_results(result, output_dir, args.question)

        # Print summary
        print(f"\n{'=' * 50}")
        print(f"RESEARCH COMPLETE")
        print(f"{'=' * 50}")
        print(f"Status: {result.status.value}")
        print(f"Confidence: {int(result.confidence * 100)}%")
        print(f"Evidence: {len(result.evidence)} pieces")
        print(f"Sub-goals: {len(result.sub_results)}")
        print(f"Duration: {result.duration_seconds:.1f}s")
        print(f"Cost: ${result.cost_dollars:.4f}")
        print(f"\nOutput saved to: {output_dir}")
        print(f"  - report.md")
        print(f"  - evidence.json")
        print(f"  - metadata.json")
        print(f"  - execution_log.jsonl")

        # Show synthesis preview
        if result.synthesis:
            print(f"\n--- Synthesis Preview ---")
            print(result.synthesis[:500] + "..." if len(result.synthesis) > 500 else result.synthesis)

        return 0 if result.status == GoalStatus.COMPLETED else 1

    except KeyboardInterrupt:
        print("\n\nResearch interrupted by user")
        return 130
    except Exception as e:
        logger.exception("Research failed with error")
        print(f"\nERROR: {e}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
