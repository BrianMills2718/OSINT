#!/usr/bin/env python3
"""
Test LLM Source Selection Accuracy

Validates that metadata descriptions are clear enough for the LLM to select
appropriate sources for different query types.

This tests the INTEGRATION POINT between:
- Integration metadata descriptions (what we tell the LLM about each source)
- LLM source selection logic (how the LLM interprets those descriptions)
"""

import asyncio
import sys
import os
from typing import List, Set

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from research.deep_research import SimpleDeepResearch
from dotenv import load_dotenv
import json

load_dotenv()


# Define test cases: query → expected sources
TEST_CASES = [
    {
        "query": "Lockheed Martin offshore financial structures and foreign subsidiaries",
        "must_include": ["SEC EDGAR", "ICIJ Offshore Leaks"],
        "should_include": ["CourtListener"],  # Tax litigation
        "should_not_include": ["DVIDS", "USAJobs", "ClearanceJobs"],  # Irrelevant
        "rationale": "SEC EDGAR has 10-K subsidiary disclosures, ICIJ has known offshore entities"
    },
    {
        "query": "Defense contract awards to Boeing for F-15 fighter jets",
        "must_include": ["SAM.gov", "USAspending"],
        "should_include": ["Federal Register", "NewsAPI"],
        "should_not_include": ["SEC EDGAR", "FEC", "ICIJ Offshore Leaks"],
        "rationale": "SAM/USAspending have contract data, not corporate filings or campaign finance"
    },
    {
        "query": "Political donations from Raytheon executives to Armed Services Committee members",
        "must_include": ["FEC"],
        "should_include": ["ProPublica", "NewsAPI"],
        "should_not_include": ["SAM.gov", "DVIDS", "USAJobs"],
        "rationale": "FEC has campaign finance data, not contracts or media"
    },
    {
        "query": "CIA declassified documents about Operation Mockingbird",
        "must_include": ["CIA CREST (Selenium)"],
        "should_include": ["FBI Vault", "Wayback Machine"],
        "should_not_include": ["SAM.gov", "Congress.gov", "FEC"],
        "rationale": "CREST has CIA docs, not legislative or contract data"
    },
    {
        "query": "Federal job openings for intelligence analysts with TS/SCI clearance",
        "must_include": ["USAJobs", "ClearanceJobs"],
        "should_include": [],
        "should_not_include": ["SAM.gov", "SEC EDGAR", "DVIDS"],
        "rationale": "Job databases only - not contracts, filings, or media"
    },
    {
        "query": "Bellingcat OSINT investigations into Russian military movements",
        "must_include": ["Discord", "Twitter"],
        "should_include": ["Reddit", "Brave Search"],
        "should_not_include": ["SAM.gov", "Congress.gov", "FEC"],
        "rationale": "Social media and OSINT communities, not government databases"
    },
    {
        "query": "Legal challenges to DoD contract awards in Court of Federal Claims",
        "must_include": ["CourtListener"],
        "should_include": ["SAM.gov", "NewsAPI"],
        "should_not_include": ["DVIDS", "USAJobs", "Twitter"],
        "rationale": "Court opinions for legal cases, contracts for context"
    },
    {
        "query": "Nonprofit think tank funding from defense contractors",
        "must_include": ["ProPublica Nonprofit Explorer"],
        "should_include": ["SEC EDGAR", "NewsAPI"],  # Corporate disclosures
        "should_not_include": ["DVIDS", "USAJobs", "Federal Register"],
        "rationale": "Nonprofit data + corporate philanthropy disclosures"
    }
]


async def test_source_selection(query: str, expected: dict) -> dict:
    """
    Test LLM source selection for a single query.

    Args:
        query: Research query
        expected: Expected source selections

    Returns:
        Dict with test results
    """
    # Create research instance (this loads all integrations and builds descriptions)
    research = SimpleDeepResearch()

    # Set original_question (normally set in research() method)
    research.original_question = query

    # Call the ACTUAL source selection method used by deep_research
    selected_sources, reason = await research._select_relevant_sources(query)

    # Convert tool names to display names for easier comparison
    selected_display = [
        research.tool_name_to_display.get(tool_name, tool_name)
        for tool_name in selected_sources
    ]

    # Validate expectations
    results = {
        "query": query,
        "selected": selected_display,
        "reasoning": reason,
        "validations": []
    }

    # Check MUST_INCLUDE
    for source in expected["must_include"]:
        if source in selected_display:
            results["validations"].append({
                "type": "MUST_INCLUDE",
                "source": source,
                "status": "PASS",
                "message": f"✅ Correctly included {source}"
            })
        else:
            results["validations"].append({
                "type": "MUST_INCLUDE",
                "source": source,
                "status": "FAIL",
                "message": f"❌ MISSING {source} - metadata description may be unclear"
            })

    # Check SHOULD_NOT_INCLUDE
    for source in expected["should_not_include"]:
        if source not in selected_display:
            results["validations"].append({
                "type": "SHOULD_NOT_INCLUDE",
                "source": source,
                "status": "PASS",
                "message": f"✅ Correctly excluded {source}"
            })
        else:
            results["validations"].append({
                "type": "SHOULD_NOT_INCLUDE",
                "source": source,
                "status": "FAIL",
                "message": f"❌ INCORRECTLY INCLUDED {source} - metadata too generic?"
            })

    # Check SHOULD_INCLUDE (warnings, not failures)
    for source in expected["should_include"]:
        if source in selected_display:
            results["validations"].append({
                "type": "SHOULD_INCLUDE",
                "source": source,
                "status": "PASS",
                "message": f"✅ Included recommended source {source}"
            })
        else:
            results["validations"].append({
                "type": "SHOULD_INCLUDE",
                "source": source,
                "status": "WARN",
                "message": f"⚠️  Skipped {source} (recommended but not required)"
            })

    return results


async def run_all_tests():
    """Run all source selection tests and report results."""

    print("=" * 80)
    print("LLM SOURCE SELECTION ACCURACY TEST")
    print("=" * 80)
    print()
    print("Testing whether metadata descriptions are clear enough for LLM")
    print("to select appropriate sources for different query types.")
    print()

    all_results = []
    total_tests = len(TEST_CASES)
    passed_tests = 0

    for i, test_case in enumerate(TEST_CASES, 1):
        print(f"[Test {i}/{total_tests}] {test_case['query'][:60]}...")
        print(f"Rationale: {test_case['rationale']}")
        print()

        try:
            result = await test_source_selection(test_case["query"], test_case)
            all_results.append(result)

            # Print results
            print(f"Selected sources: {', '.join(result['selected'])}")
            print(f"LLM reasoning: {result['reasoning'][:100]}...")
            print()

            # Print validations
            failures = 0
            for validation in result["validations"]:
                print(f"  {validation['message']}")
                if validation["status"] == "FAIL":
                    failures += 1

            if failures == 0:
                print()
                print("  ✅ TEST PASSED")
                passed_tests += 1
            else:
                print()
                print(f"  ❌ TEST FAILED ({failures} validation failures)")

        except Exception as e:
            print(f"  ❌ ERROR: {e}")
            all_results.append({
                "query": test_case["query"],
                "error": str(e)
            })

        print()
        print("-" * 80)
        print()

    # Final summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Tests passed: {passed_tests}/{total_tests}")
    print()

    if passed_tests == total_tests:
        print("✅ ALL TESTS PASSED")
        print("Metadata descriptions are clear and LLM selects sources accurately.")
        return 0
    else:
        print("❌ SOME TESTS FAILED")
        print()
        print("FAILED TESTS indicate metadata descriptions may need improvement:")
        print()

        for result in all_results:
            if "validations" in result:
                failed = [v for v in result["validations"] if v["status"] == "FAIL"]
                if failed:
                    print(f"Query: {result['query'][:60]}...")
                    for failure in failed:
                        print(f"  - {failure['message']}")
                        print(f"    → Check {failure['source']} metadata.description")
                    print()

        print("RECOMMENDATIONS:")
        print("1. Review failed source metadata descriptions")
        print("2. Add keywords that help LLM understand when to select source")
        print("3. Be specific about what data the source contains")
        print("4. Re-run this test after updating descriptions")

        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(run_all_tests())
    sys.exit(exit_code)
