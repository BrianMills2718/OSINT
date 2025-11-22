#!/usr/bin/env python3
"""
Test query generation across all sources with diverse queries.
Logs everything to help analyze and improve LLM prompts.
"""

import asyncio
import os
import sys
from pathlib import Path
from datetime import datetime
import json

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from integrations.registry import registry


# Diverse test queries covering different use cases
TEST_QUERIES = [
    # Intelligence/OSINT topics
    "SIGINT signals intelligence",
    "cyber threat intelligence",
    "North Korea weapons programs",

    # Government contracts
    "cybersecurity contracts",
    "AI machine learning contracts",

    # Jobs
    "intelligence analyst jobs",
    "cybersecurity jobs with clearance",

    # Current events
    "Ukraine war latest developments",
    "Middle East conflict",

    # Technical topics
    "malware analysis",
    "vulnerability research",

    # Hybrid queries (might confuse LLMs)
    "FBI counterterrorism operations",
    "NSA hiring",
    "defense contractor jobs",
]


async def test_single_query(query: str, output_file):
    """Test a single query across all sources and log results."""

    output_file.write(f"\n{'='*100}\n")
    output_file.write(f"QUERY: {query}\n")
    output_file.write(f"{'='*100}\n\n")

    # Get all sources
    all_sources = registry.get_all()

    for source_id, source_class in all_sources.items():
        output_file.write(f"\n{'-'*80}\n")
        output_file.write(f"SOURCE: {source_id}\n")
        output_file.write(f"{'-'*80}\n")

        try:
            # Instantiate integration
            integration = source_class()

            # Generate query parameters
            start = datetime.now()
            query_params = await integration.generate_query(query)
            generation_time = (datetime.now() - start).total_seconds()

            output_file.write(f"Query generation time: {generation_time:.2f}s\n\n")

            if not query_params:
                output_file.write(f"❌ LLM marked as NOT RELEVANT\n")
                output_file.write(f"Query params: None\n")
                continue

            output_file.write(f"✅ LLM marked as RELEVANT\n")
            output_file.write(f"Query params generated:\n")
            output_file.write(json.dumps(query_params, indent=2))
            output_file.write(f"\n\n")

            # Try to execute search (with API keys if available)
            api_keys = {
                "sam": os.getenv("SAM_GOV_API_KEY"),
                "dvids": os.getenv("DVIDS_API_KEY"),
                "usajobs": os.getenv("USAJOBS_API_KEY"),
                "twitter": os.getenv("RAPIDAPI_KEY"),
                "brave_search": os.getenv("BRAVE_SEARCH_API_KEY"),
            }

            api_key = api_keys.get(source_id)

            # Only execute if we have API key or source doesn't need one
            if not integration.metadata.requires_api_key or api_key:
                result = await integration.execute_search(query_params, api_key, limit=5)

                output_file.write(f"Search execution:\n")
                output_file.write(f"  Success: {result.success}\n")
                output_file.write(f"  Total results: {result.total}\n")
                output_file.write(f"  Response time: {result.response_time_ms:.0f}ms\n")

                if result.error:
                    output_file.write(f"  Error: {result.error}\n")

                if result.results:
                    output_file.write(f"\nFirst result sample:\n")
                    first = result.results[0]
                    # Show title or key field
                    title = (first.get('title') or
                            first.get('job_name') or
                            first.get('name') or
                            first.get('PositionTitle') or
                            str(first)[:100])
                    output_file.write(f"  {title}\n")
            else:
                output_file.write(f"⚠️  API key not configured - skipping execution\n")

        except Exception as e:
            output_file.write(f"❌ EXCEPTION: {str(e)}\n")
            import traceback
            output_file.write(traceback.format_exc())

        output_file.flush()  # Ensure written even if script crashes


async def main():
    """Run all test queries and save results."""

    # Create output file with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = Path(f"query_generation_analysis_{timestamp}.txt")

    print(f"Testing {len(TEST_QUERIES)} queries across all sources...")
    print(f"Output will be saved to: {output_path}")
    print(f"This will take several minutes (LLM calls for each source)...\n")

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("QUERY GENERATION ANALYSIS\n")
        f.write(f"Generated: {datetime.now().isoformat()}\n")
        f.write(f"Total queries: {len(TEST_QUERIES)}\n")
        f.write(f"Total sources: {len(registry.get_all())}\n")
        f.write("\n")

        for i, query in enumerate(TEST_QUERIES, 1):
            print(f"[{i}/{len(TEST_QUERIES)}] Testing: {query}")
            await test_single_query(query, f)

        f.write(f"\n{'='*100}\n")
        f.write("ANALYSIS COMPLETE\n")
        f.write(f"{'='*100}\n")

    print(f"\n✅ Analysis complete!")
    print(f"📄 Results saved to: {output_path}")
    print(f"\nReview the file to see:")
    print(f"  - Which sources marked queries as relevant/not relevant")
    print(f"  - What query parameters each source's LLM generated")
    print(f"  - Actual search results (total count + first result)")
    print(f"\nUse this to identify:")
    print(f"  - Sources that are too conservative (marking things not relevant)")
    print(f"  - Sources generating wrong query parameters")
    print(f"  - Sources that fail to find results despite good queries")


if __name__ == "__main__":
    asyncio.run(main())
