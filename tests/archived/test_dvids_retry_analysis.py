#!/usr/bin/env python3
"""
DVIDS Retry Analysis - Determine if 403 errors are transient

Tests to determine if retry mechanism would solve 403 errors:
1. Retry same query 5 times - Does same query fail consistently?
2. Rapid-fire 10 queries - Does rate limiting trigger 403s?
3. Delayed sequential queries - Do delays prevent 403s?
4. Track timing patterns - When do 403s occur?

AGENT2 - Retry Mechanism Investigation
"""

import asyncio
import os
import sys
from pathlib import Path
from datetime import datetime
import time

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from integrations.government.dvids_integration import DVIDSIntegration

async def test_retry_analysis():
    """Comprehensive retry analysis to determine if 403s are transient."""

    integration = DVIDSIntegration()
    api_key = os.getenv("DVIDS_API_KEY")

    if not api_key:
        print("❌ DVIDS_API_KEY not found")
        return None

    print("=" * 80)
    print("DVIDS RETRY ANALYSIS - Determine if 403 errors are transient")
    print("=" * 80)
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    results = {}

    # TEST 1: Retry same query 5 times (tests if 403 is query-specific or transient)
    print("=" * 80)
    print("TEST 1: Retry Same Query 5 Times")
    print("=" * 80)
    print("Hypothesis: If 403 is transient, retries will succeed")
    print("Query: 'JSOC mission and role in U.S. special operations'")
    print()

    test_query = "JSOC mission and role in U.S. special operations"
    params = await integration.generate_query(test_query)

    retry_results = []
    for attempt in range(1, 6):
        start_time = time.time()
        result = await integration.execute_search(params, api_key, limit=5)
        elapsed = time.time() - start_time

        retry_results.append({
            'attempt': attempt,
            'success': result.success,
            'error': str(result.error) if result.error else None,
            'has_403': '403' in str(result.error or ''),
            'elapsed': elapsed,
            'timestamp': datetime.now().strftime('%H:%M:%S.%f')[:-3]
        })

        status = "✅ SUCCESS" if result.success else f"❌ FAILED - {result.error}"
        print(f"  Attempt {attempt} ({elapsed:.2f}s): {status}")

        # Small delay between retries
        await asyncio.sleep(1)

    retry_success = sum(1 for r in retry_results if r['success'])
    retry_403 = sum(1 for r in retry_results if r['has_403'])

    print(f"\nResult: {retry_success}/5 succeeded, {retry_403}/5 got 403")
    results['retry_same_query'] = {
        'attempts': retry_results,
        'success_count': retry_success,
        'fail_403_count': retry_403,
        'pattern': 'consistent' if retry_success == 0 or retry_success == 5 else 'intermittent'
    }

    # TEST 2: Rapid-fire 10 different queries (tests rate limiting)
    print("\n" + "=" * 80)
    print("TEST 2: Rapid-Fire 10 Different Queries (No Delays)")
    print("=" * 80)
    print("Hypothesis: If rate limiting exists, rapid queries will trigger 403s")
    print()

    rapid_queries = [
        "Air Force training exercises",
        "Navy ship deployments",
        "Army equipment maintenance",
        "Marine Corps readiness",
        "Space Force operations",
        "Coast Guard missions",
        "National Guard deployments",
        "Reserve component training",
        "Joint military exercises",
        "Defense logistics operations"
    ]

    rapid_results = []
    start_batch = time.time()

    for i, query in enumerate(rapid_queries, 1):
        params = await integration.generate_query(query)
        start_time = time.time()
        result = await integration.execute_search(params, api_key, limit=5)
        elapsed = time.time() - start_time

        rapid_results.append({
            'query_num': i,
            'query': query,
            'success': result.success,
            'error': str(result.error) if result.error else None,
            'has_403': '403' in str(result.error or ''),
            'elapsed': elapsed,
            'timestamp': datetime.now().strftime('%H:%M:%S.%f')[:-3]
        })

        status = "✅" if result.success else "❌"
        print(f"  Query {i:2d} ({elapsed:.2f}s): {status} - {query[:40]}")

    total_batch_time = time.time() - start_batch
    rapid_success = sum(1 for r in rapid_results if r['success'])
    rapid_403 = sum(1 for r in rapid_results if r['has_403'])

    print(f"\nResult: {rapid_success}/10 succeeded, {rapid_403}/10 got 403 in {total_batch_time:.1f}s")

    # Check if 403s cluster at beginning or end
    first_half_403 = sum(1 for r in rapid_results[:5] if r['has_403'])
    second_half_403 = sum(1 for r in rapid_results[5:] if r['has_403'])

    results['rapid_fire'] = {
        'queries': rapid_results,
        'success_count': rapid_success,
        'fail_403_count': rapid_403,
        'total_time': total_batch_time,
        'first_half_403': first_half_403,
        'second_half_403': second_half_403
    }

    # TEST 3: Delayed sequential queries (tests if delays help)
    print("\n" + "=" * 80)
    print("TEST 3: 10 Different Queries with 3-Second Delays")
    print("=" * 80)
    print("Hypothesis: If rate limiting is time-based, delays will prevent 403s")
    print()

    delayed_queries = [
        "cybersecurity training programs",
        "intelligence operations briefings",
        "special operations missions",
        "counterterrorism activities",
        "humanitarian assistance operations",
        "disaster response deployments",
        "peacekeeping missions",
        "training exchange programs",
        "equipment modernization",
        "force readiness assessments"
    ]

    delayed_results = []
    start_batch = time.time()

    for i, query in enumerate(delayed_queries, 1):
        params = await integration.generate_query(query)
        start_time = time.time()
        result = await integration.execute_search(params, api_key, limit=5)
        elapsed = time.time() - start_time

        delayed_results.append({
            'query_num': i,
            'query': query,
            'success': result.success,
            'error': str(result.error) if result.error else None,
            'has_403': '403' in str(result.error or ''),
            'elapsed': elapsed,
            'timestamp': datetime.now().strftime('%H:%M:%S.%f')[:-3]
        })

        status = "✅" if result.success else "❌"
        print(f"  Query {i:2d} ({elapsed:.2f}s): {status} - {query[:40]}")

        # 3-second delay between queries
        if i < len(delayed_queries):
            await asyncio.sleep(3)

    total_batch_time = time.time() - start_batch
    delayed_success = sum(1 for r in delayed_results if r['success'])
    delayed_403 = sum(1 for r in delayed_results if r['has_403'])

    print(f"\nResult: {delayed_success}/10 succeeded, {delayed_403}/10 got 403 in {total_batch_time:.1f}s")

    results['delayed_sequential'] = {
        'queries': delayed_results,
        'success_count': delayed_success,
        'fail_403_count': delayed_403,
        'total_time': total_batch_time
    }

    # ANALYSIS
    print("\n" + "=" * 80)
    print("ANALYSIS - RETRY MECHANISM RECOMMENDATIONS")
    print("=" * 80)

    print("\nTest Results Summary:")
    print(f"  1. Retry Same Query:    {results['retry_same_query']['success_count']}/5 success, pattern: {results['retry_same_query']['pattern']}")
    print(f"  2. Rapid-Fire Queries:  {results['rapid_fire']['success_count']}/10 success, {results['rapid_fire']['fail_403_count']} x 403")
    print(f"  3. Delayed Queries:     {results['delayed_sequential']['success_count']}/10 success, {results['delayed_sequential']['fail_403_count']} x 403")

    print("\n" + "=" * 80)
    print("CONCLUSIONS")
    print("=" * 80)
    print()

    # Analyze retry pattern
    if results['retry_same_query']['pattern'] == 'consistent':
        if results['retry_same_query']['success_count'] == 0:
            print("❌ RETRY WON'T HELP: Same query fails consistently")
            print("   - 403 appears to be query-specific or persistent API issue")
            print("   - Retry mechanism would not improve success rate")
        else:
            print("✅ NO 403 ERRORS: All retry attempts succeeded")
            print("   - Original 403 may have been transient or resolved")
    else:
        print("⚠️ RETRY MAY HELP: Same query shows intermittent success")
        print(f"   - {results['retry_same_query']['success_count']}/5 attempts succeeded")
        print("   - Retry mechanism could improve reliability")

    # Analyze rate limiting
    if results['rapid_fire']['fail_403_count'] > results['delayed_sequential']['fail_403_count']:
        print("\n⚠️ RATE LIMITING DETECTED: Delays reduce 403 errors")
        print(f"   - Rapid-fire: {results['rapid_fire']['fail_403_count']}/10 got 403")
        print(f"   - Delayed: {results['delayed_sequential']['fail_403_count']}/10 got 403")
        print("   - Recommend adding delays between requests")

    # Check if 403s cluster
    if results['rapid_fire']['first_half_403'] > results['rapid_fire']['second_half_403']:
        print("\n⚠️ QUOTA PATTERN: More failures at start of batch")
        print(f"   - First 5 queries: {results['rapid_fire']['first_half_403']} x 403")
        print(f"   - Last 5 queries: {results['rapid_fire']['second_half_403']} x 403")
        print("   - May indicate quota reset during test")
    elif results['rapid_fire']['second_half_403'] > results['rapid_fire']['first_half_403']:
        print("\n⚠️ QUOTA EXHAUSTION: More failures at end of batch")
        print(f"   - First 5 queries: {results['rapid_fire']['first_half_403']} x 403")
        print(f"   - Last 5 queries: {results['rapid_fire']['second_half_403']} x 403")
        print("   - May indicate quota being exhausted")

    # Final recommendation
    print("\n" + "=" * 80)
    print("RECOMMENDATION")
    print("=" * 80)
    print()

    total_403s = results['retry_same_query']['fail_403_count'] + results['rapid_fire']['fail_403_count'] + results['delayed_sequential']['fail_403_count']
    total_queries = 5 + 10 + 10

    if total_403s == 0:
        print("✅ NO 403 ERRORS DETECTED in this test run")
        print("   - All 25 queries succeeded")
        print("   - Original 403s may have been transient or time-specific")
        print("   - Monitor in production to see if pattern recurs")
        recommendation = "monitor"
    elif results['retry_same_query']['pattern'] == 'intermittent':
        print("✅ IMPLEMENT RETRY MECHANISM")
        print("   - Same query shows intermittent success on retry")
        print("   - Recommend: 2-3 retries with exponential backoff")
        print("   - Suggest: 1s, 2s, 4s delays between retries")
        recommendation = "retry"
    elif results['rapid_fire']['fail_403_count'] > results['delayed_sequential']['fail_403_count']:
        print("✅ IMPLEMENT RATE LIMITING")
        print("   - Delays between requests reduce 403 errors")
        print("   - Recommend: 2-3 second delay between DVIDS requests")
        print("   - Consider retry mechanism as secondary defense")
        recommendation = "rate_limit"
    else:
        print("⚠️ INSUFFICIENT EVIDENCE")
        print(f"   - {total_403s}/{total_queries} queries got 403")
        print("   - Pattern unclear from this test")
        print("   - Recommend: Run test at different times of day")
        print("   - May be time-based quota or API maintenance window")
        recommendation = "inconclusive"

    print("\n" + "=" * 80)

    return recommendation, results

if __name__ == "__main__":
    print(f"Starting DVIDS retry analysis at {datetime.now()}")
    print()

    recommendation, results = asyncio.run(test_retry_analysis())

    print(f"\n✅ RETRY ANALYSIS COMPLETE")
    print(f"Recommendation: {recommendation}")

    # Save detailed results
    with open('dvids_retry_analysis_results.txt', 'w') as f:
        f.write(f"DVIDS Retry Analysis - {datetime.now()}\n")
        f.write(f"=" * 80 + "\n\n")
        f.write(f"Recommendation: {recommendation}\n\n")

        f.write("Test 1 - Retry Same Query:\n")
        f.write(f"  Success: {results['retry_same_query']['success_count']}/5\n")
        f.write(f"  Pattern: {results['retry_same_query']['pattern']}\n")
        f.write(f"  403 Errors: {results['retry_same_query']['fail_403_count']}/5\n\n")

        f.write("Test 2 - Rapid-Fire Queries:\n")
        f.write(f"  Success: {results['rapid_fire']['success_count']}/10\n")
        f.write(f"  403 Errors: {results['rapid_fire']['fail_403_count']}/10\n")
        f.write(f"  First half 403s: {results['rapid_fire']['first_half_403']}\n")
        f.write(f"  Second half 403s: {results['rapid_fire']['second_half_403']}\n\n")

        f.write("Test 3 - Delayed Sequential:\n")
        f.write(f"  Success: {results['delayed_sequential']['success_count']}/10\n")
        f.write(f"  403 Errors: {results['delayed_sequential']['fail_403_count']}/10\n")

    print(f"\nDetailed results saved to: dvids_retry_analysis_results.txt")
    print(f"End time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
