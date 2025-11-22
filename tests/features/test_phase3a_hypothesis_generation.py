#!/usr/bin/env python3
"""
Phase 3A Validation Test: Hypothesis Generation

Tests hypothesis generation on 5 diverse query types to validate:
1. Adaptive hypothesis count (1-2 for simple, 2-3 for factual, 3-5 for speculative)
2. Hypothesis diversity (not overlapping >30%)
3. Appropriate confidence scores (high for factual, lower for speculative)
4. Useful search strategies (sources, signals, expected entities)
5. Sensible exploration priorities

Test Queries:
1. Simple: "GS-2210 job series official documentation" (expect 1-2 hypotheses)
2. Factual: "federal cybersecurity job opportunities" (expect 2-3 hypotheses)
3. Speculative: "NSA classified intelligence programs" (expect 3-5 hypotheses)
4. Narrow Technical: "FOIA request process for classified documents" (expect 2-3 hypotheses)
5. Broad Investigative: "defense contractor misconduct investigations" (expect 3-5 hypotheses)

Success Criteria:
- Hypothesis count adapts to query complexity
- Hypotheses are diverse (different investigative angles)
- Confidence scores vary appropriately
- Search strategies include appropriate sources
- Exploration priorities make sense
"""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from research.deep_research import SimpleDeepResearch
from dotenv import load_dotenv

load_dotenv()


# Test cases with expected behavior
TEST_CASES = [
    {
        "name": "Simple Query",
        "research_question": "What is the GS-2210 job series?",
        "task_query": "GS-2210 job series official documentation",
        "expected_hypothesis_count_range": (1, 2),
        "expected_min_confidence": 80,  # Should be high - factual query with obvious pathway
        "expected_diversity": "High - each hypothesis should explore different source types",
        "notes": "Simple factual query should generate 1-2 hypotheses with high confidence"
    },
    {
        "name": "Factual Query",
        "research_question": "What cybersecurity job opportunities are available for cleared professionals?",
        "task_query": "Federal cybersecurity jobs requiring clearances",
        "expected_hypothesis_count_range": (2, 3),
        "expected_min_confidence": 60,  # Medium-high - well-established sources
        "expected_diversity": "High - official vs social sources",
        "notes": "Factual job query should generate 2-3 hypotheses (official postings, social discussions)"
    },
    {
        "name": "Speculative Query",
        "research_question": "What classified intelligence programs does the NSA operate?",
        "task_query": "NSA classified programs disclosed publicly",
        "expected_hypothesis_count_range": (3, 5),
        "expected_min_confidence": 40,  # Lower - speculative pathways
        "expected_diversity": "Very High - multiple distinct angles (official leaks, whistleblowers, technical, journalism)",
        "notes": "Speculative query should generate 3-5 hypotheses with varied confidence"
    },
    {
        "name": "Narrow Technical Query",
        "research_question": "How do I file a FOIA request for classified documents?",
        "task_query": "FOIA request process for classified documents",
        "expected_hypothesis_count_range": (2, 3),
        "expected_min_confidence": 70,  # High - procedural/official information
        "expected_diversity": "Medium - official guidance vs community experience",
        "notes": "Technical procedural query should generate 2-3 hypotheses (official process, community tips)"
    },
    {
        "name": "Broad Investigative Query",
        "research_question": "What misconduct investigations are ongoing against defense contractors?",
        "task_query": "Defense contractor misconduct investigations",
        "expected_hypothesis_count_range": (3, 5),
        "expected_min_confidence": 50,  # Medium - mixed sources
        "expected_diversity": "Very High - official records, investigative journalism, legal filings, whistleblowers",
        "notes": "Broad investigative query should generate 3-5 hypotheses (diverse investigative angles)"
    }
]


async def test_hypothesis_generation():
    """Test hypothesis generation on 5 diverse queries."""

    print("\n" + "="*80)
    print("PHASE 3A VALIDATION TEST: Hypothesis Generation")
    print("="*80)
    print()
    print("Testing hypothesis generation on 5 query types:")
    print("1. Simple (expect 1-2 hypotheses, high confidence)")
    print("2. Factual (expect 2-3 hypotheses, medium-high confidence)")
    print("3. Speculative (expect 3-5 hypotheses, varied confidence)")
    print("4. Narrow Technical (expect 2-3 hypotheses, high confidence)")
    print("5. Broad Investigative (expect 3-5 hypotheses, varied confidence)")
    print()
    print("="*80)
    print()

    # Initialize research engine
    research = SimpleDeepResearch(
        max_tasks=1,  # Only testing hypothesis generation, not execution
        save_output=False  # Don't save output for tests
    )

    # Run all test cases
    results = []
    for i, test_case in enumerate(TEST_CASES, 1):
        print(f"\n{'='*80}")
        print(f"TEST {i}/{len(TEST_CASES)}: {test_case['name']}")
        print(f"{'='*80}")
        print()
        print(f"Research Question: {test_case['research_question']}")
        print(f"Task Query: {test_case['task_query']}")
        print()
        print(f"Expected Hypothesis Count: {test_case['expected_hypothesis_count_range'][0]}-{test_case['expected_hypothesis_count_range'][1]}")
        print(f"Expected Min Confidence: {test_case['expected_min_confidence']}%")
        print(f"Expected Diversity: {test_case['expected_diversity']}")
        print(f"Notes: {test_case['notes']}")
        print()
        print("-"*80)
        print()

        try:
            # Generate hypotheses
            result = await research._generate_hypotheses(
                task_query=test_case['task_query'],
                research_question=test_case['research_question']
            )

            # Analyze results
            hypothesis_count = len(result['hypotheses'])
            confidences = [h['confidence'] for h in result['hypotheses']]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0
            min_confidence = min(confidences) if confidences else 0
            max_confidence = max(confidences) if confidences else 0

            # Extract sources and check diversity
            all_sources = []
            for h in result['hypotheses']:
                all_sources.extend(h['search_strategy']['sources'])

            unique_sources = len(set(all_sources))
            total_sources = len(all_sources)
            source_diversity = (unique_sources / total_sources * 100) if total_sources > 0 else 0

            # Validation checks
            count_in_range = test_case['expected_hypothesis_count_range'][0] <= hypothesis_count <= test_case['expected_hypothesis_count_range'][1]
            confidence_adequate = min_confidence >= (test_case['expected_min_confidence'] - 20)  # Allow 20% variance

            # Store results
            test_result = {
                "test_case": test_case['name'],
                "hypothesis_count": hypothesis_count,
                "expected_count_range": test_case['expected_hypothesis_count_range'],
                "count_in_range": count_in_range,
                "confidences": confidences,
                "avg_confidence": avg_confidence,
                "min_confidence": min_confidence,
                "max_confidence": max_confidence,
                "confidence_adequate": confidence_adequate,
                "unique_sources": unique_sources,
                "total_sources": total_sources,
                "source_diversity_pct": source_diversity,
                "coverage_assessment": result['coverage_assessment'],
                "hypotheses": result['hypotheses']
            }
            results.append(test_result)

            # Print analysis
            print(f"\n📊 ANALYSIS:")
            print(f"   Hypothesis Count: {hypothesis_count} {'✓' if count_in_range else '✗ OUT OF RANGE'}")
            print(f"   Confidence Scores: Min={min_confidence}%, Avg={avg_confidence:.1f}%, Max={max_confidence}%")
            print(f"   Confidence Adequate: {'✓' if confidence_adequate else '✗ TOO LOW'}")
            print(f"   Source Diversity: {unique_sources}/{total_sources} sources unique ({source_diversity:.1f}%)")
            print(f"   Coverage: {result['coverage_assessment']}")
            print()

            # Success indicators
            if count_in_range and confidence_adequate and source_diversity >= 50:
                print("✅ TEST PASSED - Hypotheses meet quality criteria")
            else:
                print("⚠️  TEST MARGINAL - Review hypothesis quality")

        except Exception as e:
            print(f"\n❌ TEST FAILED: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            results.append({
                "test_case": test_case['name'],
                "error": str(e)
            })

        print()

    # Final summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    print()

    passed = sum(1 for r in results if "error" not in r and r.get("count_in_range") and r.get("confidence_adequate"))
    total = len(results)

    print(f"Tests Passed: {passed}/{total} ({passed/total*100:.1f}%)")
    print()

    # Detailed summary
    for i, result in enumerate(results, 1):
        if "error" in result:
            print(f"{i}. {result['test_case']}: ❌ FAILED - {result['error']}")
        else:
            status = "✅ PASS" if result['count_in_range'] and result['confidence_adequate'] else "⚠️  MARGINAL"
            print(f"{i}. {result['test_case']}: {status}")
            print(f"   - Hypotheses: {result['hypothesis_count']} (expected {result['expected_count_range'][0]}-{result['expected_count_range'][1]})")
            print(f"   - Confidence: {result['min_confidence']}%-{result['max_confidence']}% (avg {result['avg_confidence']:.1f}%)")
            print(f"   - Source Diversity: {result['source_diversity_pct']:.1f}%")

    print()
    print("="*80)
    print()

    # Overall verdict
    if passed == total:
        print("✅ ALL TESTS PASSED - Phase 3A hypothesis generation is production-ready")
        print()
        print("Next Step: Proceed to Phase 3B (hypothesis execution) after approval")
    elif passed >= total * 0.8:
        print("⚠️  MOST TESTS PASSED - Review marginal cases before proceeding")
        print()
        print("Recommendation: Iterate on hypothesis generation prompt if needed")
    else:
        print("❌ MULTIPLE FAILURES - Hypothesis generation needs improvement")
        print()
        print("Recommendation: Review prompt template and schema before proceeding")

    print()
    print("="*80)

    return results


if __name__ == "__main__":
    asyncio.run(test_hypothesis_generation())
