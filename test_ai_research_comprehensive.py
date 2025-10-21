#!/usr/bin/env python3
"""
Test AI Research comprehensive search without UI.
Logs all query parameters and results for analysis.
"""

import asyncio
import sys
from pathlib import Path
from dotenv import load_dotenv
import os

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

load_dotenv()

# Import the search functions
from apps.ai_research import generate_search_queries, execute_search_via_registry

async def test_comprehensive_search():
    """Test comprehensive search with detailed logging."""

    research_question = "i am looking for all recent activity and conversation related to domestic counterterrorism and JTTF etc"

    print("=" * 80)
    print("AI RESEARCH - COMPREHENSIVE SEARCH TEST")
    print("=" * 80)
    print(f"\nResearch Question: {research_question}")
    print()

    # Step 1: Generate search strategy
    print("[STEP 1] Generating search strategy (comprehensive mode)...")
    queries = generate_search_queries(research_question, comprehensive_mode=True)

    print(f"\n✅ Search strategy generated")
    print(f"\nOverall Strategy: {queries['research_strategy']}")
    print(f"\nSelected Sources: {len(queries['selected_sources'])}")
    for idx, source in enumerate(queries['selected_sources'], 1):
        print(f"\n{idx}. {source['source_id']}")
        print(f"   Keywords: {source['keywords']}")
        print(f"   Reasoning: {source['reasoning']}")

    # Step 2: Execute searches
    print("\n" + "=" * 80)
    print("[STEP 2] Executing searches across all sources...")
    print("=" * 80)

    # Build API key dict
    api_keys = {
        "dvids": os.getenv('DVIDS_API_KEY'),
        "sam": os.getenv('SAM_GOV_API_KEY'),
        "usajobs": os.getenv('USAJOBS_API_KEY'),
        "twitter": os.getenv('RAPIDAPI_KEY'),
    }

    # Execute searches in parallel
    async def search_all_sources():
        tasks = []
        for selected in queries['selected_sources']:
            source_id = selected['source_id']
            task = execute_search_via_registry(source_id, research_question, api_keys, limit=10)
            tasks.append(task)

        return await asyncio.gather(*tasks)

    results_list = await search_all_sources()

    # Step 3: Display results summary
    print("\n" + "=" * 80)
    print("[STEP 3] RESULTS SUMMARY")
    print("=" * 80)

    all_results = {}
    for result in results_list:
        source_name = result.get('source', 'Unknown')
        all_results[source_name] = result

        print(f"\n{source_name}:")
        print(f"  Success: {result['success']}")
        print(f"  Total: {result.get('total', 0)}")
        print(f"  Returned: {len(result.get('results', []))}")
        print(f"  Response time: {result.get('response_time_ms', 0):.0f}ms")

        if result.get('query_params'):
            print(f"  Query params: {result['query_params']}")

        if result.get('error'):
            print(f"  ❌ Error: {result['error']}")

    # Step 4: Analysis
    print("\n" + "=" * 80)
    print("[STEP 4] ANALYSIS")
    print("=" * 80)

    successful = [s for s, r in all_results.items() if r['success']]
    failed = [s for s, r in all_results.items() if not r['success']]
    with_results = [s for s, r in all_results.items() if r['success'] and r['total'] > 0]
    no_results = [s for s, r in all_results.items() if r['success'] and r['total'] == 0]

    print(f"\nSources queried: {len(all_results)}")
    print(f"Successful: {len(successful)}")
    print(f"Failed: {len(failed)}")
    print(f"With results: {len(with_results)}")
    print(f"No results (but successful): {len(no_results)}")

    if with_results:
        print(f"\n✅ Sources with results:")
        for source in with_results:
            print(f"   - {source}: {all_results[source]['total']} results")

    if no_results:
        print(f"\n⚠️  Sources with 0 results (query may be too restrictive):")
        for source in no_results:
            if all_results[source].get('query_params'):
                print(f"   - {source}: {all_results[source]['query_params']}")

    if failed:
        print(f"\n❌ Failed sources:")
        for source in failed:
            print(f"   - {source}: {all_results[source].get('error', 'Unknown error')}")

    # Step 5: Sample results
    print("\n" + "=" * 80)
    print("[STEP 5] SAMPLE RESULTS (first 3 from each source)")
    print("=" * 80)

    for source_name, result in all_results.items():
        if result['success'] and result.get('results'):
            print(f"\n{source_name} ({len(result['results'])} results):")
            for idx, item in enumerate(result['results'][:3], 1):
                title = (item.get('title') or
                        item.get('job_name') or
                        item.get('name') or
                        'Untitled')
                print(f"\n  {idx}. {title[:80]}...")
                if item.get('url'):
                    print(f"     URL: {item['url']}")
                if item.get('date'):
                    print(f"     Date: {item['date']}")

    print("\n" + "=" * 80)
    print("TEST COMPLETE - Check ai_research_queries.log for detailed query parameters")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(test_comprehensive_search())
