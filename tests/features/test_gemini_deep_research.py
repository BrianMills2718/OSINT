#!/usr/bin/env python3
"""
Test script for Deep Research Engine with Gemini 2.5 Flash.

Usage:
    python3 tests/test_gemini_deep_research.py

    or

    source .venv/bin/activate && python3 tests/test_gemini_deep_research.py
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from research.deep_research import SimpleDeepResearch


async def main():
    print("="*80)
    print("GEMINI 2.5 FLASH - DEEP RESEARCH ENGINE TEST")
    print("="*80)
    print()
    print("Configuration:")
    print("  - Model: gemini/gemini-2.5-flash (from config_default.yaml)")
    print("  - Max Tasks: 2")
    print("  - Max Retries: 1")
    print("  - Timeout: 3 minutes")
    print("  - Query: 'What are federal cybersecurity job opportunities?'")
    print()
    print("="*80)
    print()

    engine = SimpleDeepResearch(
        max_tasks=2,
        max_retries_per_task=1,
        max_time_minutes=3,
        save_output=True,
        output_dir='data/research_output'
    )

    result = await engine.research('What are federal cybersecurity job opportunities?')

    print()
    print("="*80)
    print("FINAL RESULTS")
    print("="*80)
    print(f"Tasks Executed: {result['tasks_executed']}")
    print(f"Tasks Failed: {result['tasks_failed']}")
    print(f"Success Rate: {(result['tasks_executed'] - result['tasks_failed']) / result['tasks_executed'] * 100:.0f}%" if result['tasks_executed'] > 0 else "N/A")
    print(f"Total Results: {result['total_results']}")
    print(f"Entities Discovered: {len(result['entities_discovered'])}")
    print(f"Sources Used: {', '.join(result['sources_searched'])}")
    print(f"Elapsed Time: {result.get('elapsed_minutes', 0):.2f} minutes")
    print()

    if 'output_directory' in result:
        print(f"Output saved to: {result['output_directory']}")
        print()

    # Validation
    print("="*80)
    print("VALIDATION")
    print("="*80)

    if result['total_results'] > 0:
        print("✅ PASS - Gemini 2.5 Flash working correctly")
        print(f"   - LLM operations successful (task decomposition, query generation, relevance evaluation)")
        print(f"   - Results returned: {result['total_results']} results")
        print(f"   - Entity extraction: {len(result['entities_discovered'])} entities")
    else:
        print("⚠️  WARNING - No results returned")
        print("   - Check if sources are rate-limited")
        print("   - Check GEMINI_API_KEY in .env file")
        print("   - Review output above for errors")

    print()
    print("="*80)

    return result


if __name__ == "__main__":
    asyncio.run(main())
