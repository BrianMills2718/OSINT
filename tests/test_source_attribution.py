#!/usr/bin/env python3
"""
Test Deep Investigation source attribution fix.
Verifies that sources are properly tracked and displayed.
"""

import asyncio
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import Deep Investigation engine
from research.deep_research import SimpleDeepResearch

async def test_source_attribution():
    """Test that source attribution works correctly."""

    print("=" * 80)
    print("TESTING: Deep Investigation Source Attribution Fix")
    print("=" * 80)

    # Initialize engine
    engine = SimpleDeepResearch()

    # Test query
    query = "military special operations JSOC"
    print(f"\n📋 Query: {query}")
    print("\n" + "=" * 80)

    # Run investigation
    print("\n🔍 Running Deep Investigation...\n")
    final_report = await engine.research(question=query)

    # Extract results from report
    results = final_report.get("all_results", [])

    # Check results
    print("\n" + "=" * 80)
    print("VALIDATION RESULTS")
    print("=" * 80)

    if results:
        print(f"\n✓ Total results: {len(results)}")

        # Count sources
        sources = set()
        source_counts = {}

        for result in results:
            source = result.get("source", "Unknown")
            sources.add(source)
            source_counts[source] = source_counts.get(source, 0) + 1

        print(f"\n✓ Unique sources: {len(sources)}")
        print(f"✓ Source list: {', '.join(sorted(sources))}")

        print("\n✓ Per-source breakdown:")
        for source, count in sorted(source_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"    • {source}: {count} results")

        # Check for "Unknown" sources
        if "Unknown" in sources:
            print("\n❌ FAIL: Found 'Unknown' sources (bug not fixed)")
            print("\nSample 'Unknown' results:")
            for result in results[:3]:
                if result.get("source") == "Unknown":
                    print(f"  - {result.get('title', 'No title')[:60]}...")
            return False
        else:
            print("\n✅ PASS: No 'Unknown' sources found (bug fixed!)")
            return True
    else:
        print("\n⚠️ WARNING: No results returned")
        return None

if __name__ == "__main__":
    success = asyncio.run(test_source_attribution())

    if success:
        print("\n" + "=" * 80)
        print("✅ SOURCE ATTRIBUTION FIX: VERIFIED")
        print("=" * 80)
        sys.exit(0)
    elif success is False:
        print("\n" + "=" * 80)
        print("❌ SOURCE ATTRIBUTION FIX: FAILED")
        print("=" * 80)
        sys.exit(1)
    else:
        print("\n" + "=" * 80)
        print("⚠️ SOURCE ATTRIBUTION FIX: INCONCLUSIVE")
        print("=" * 80)
        sys.exit(2)
