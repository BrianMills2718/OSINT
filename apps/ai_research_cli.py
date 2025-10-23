#!/usr/bin/env python3
"""
CLI for AI-powered research across multiple databases.

Usage:
    python3 apps/ai_research_cli.py "your research question"
    python3 apps/ai_research_cli.py "cyber threat intelligence" --limit 5
    python3 apps/ai_research_cli.py "military training" --sources dvids,sam --json

This is the core CLI that Streamlit and other UIs should use.
"""

import asyncio
import argparse
import json
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

from integrations.registry import registry


async def search_source(source_id: str, research_question: str, api_keys: dict, limit: int = 10) -> dict:
    """
    Search a single source.

    Args:
        source_id: Database ID (e.g., "dvids", "sam", "discord")
        research_question: Research question
        api_keys: Dict mapping source_id to API key
        limit: Max results

    Returns:
        Dict with search results
    """
    start_time = datetime.now()

    try:
        # Get integration from registry
        integration_class = registry.get(source_id)
        if not integration_class:
            return {
                "success": False,
                "source": source_id,
                "total": 0,
                "results": [],
                "error": f"Unknown source: {source_id}"
            }

        # Create integration instance
        integration = integration_class()

        # Get API key if needed
        api_key = None
        if integration.metadata.requires_api_key:
            api_key = api_keys.get(source_id)
            if not api_key:
                return {
                    "success": False,
                    "source": integration.metadata.name,
                    "total": 0,
                    "results": [],
                    "error": f"API key required for {integration.metadata.name}"
                }

        # Generate query parameters
        query_params = await integration.generate_query(research_question)

        if not query_params:
            # Source determined not relevant
            return {
                "success": True,
                "source": integration.metadata.name,
                "total": 0,
                "results": [],
                "not_relevant": True,
                "query_params": None
            }

        # Execute search
        result = await integration.execute_search(query_params, api_key, limit)

        response_time_ms = (datetime.now() - start_time).total_seconds() * 1000

        # Convert QueryResult to dict
        return {
            "success": result.success,
            "source": result.source,
            "total": result.total,
            "results": result.results,
            "error": result.error,
            "response_time_ms": response_time_ms,
            "query_params": query_params
        }

    except Exception as e:
        response_time_ms = (datetime.now() - start_time).total_seconds() * 1000
        return {
            "success": False,
            "source": source_id,
            "total": 0,
            "results": [],
            "error": str(e),
            "response_time_ms": response_time_ms
        }


async def search_all(research_question: str, source_ids: list = None, limit: int = 10) -> dict:
    """
    Search all sources (or specified sources).

    Args:
        research_question: Research question
        source_ids: List of source IDs to search (None = all sources)
        limit: Max results per source

    Returns:
        Dict with results from all sources
    """
    # Build API keys dict
    api_keys = {
        "sam": os.getenv("SAM_GOV_API_KEY"),
        "dvids": os.getenv("DVIDS_API_KEY"),
        "usajobs": os.getenv("USAJOBS_API_KEY"),
        "twitter": os.getenv("RAPIDAPI_KEY"),
        "brave_search": os.getenv("BRAVE_SEARCH_API_KEY"),
    }

    # Get sources to search
    if source_ids:
        sources = source_ids
    else:
        # Get all registered sources
        sources = list(registry.get_all().keys())

    # Search all sources in parallel
    tasks = [search_source(source_id, research_question, api_keys, limit) for source_id in sources]
    results_list = await asyncio.gather(*tasks)

    # Convert to dict keyed by source
    results = {}
    for result in results_list:
        source_name = result.get("source", "Unknown")
        results[source_name] = result

    return results


def print_results(results: dict, output_json: bool = False):
    """Print results to stdout."""
    if output_json:
        # JSON output
        print(json.dumps(results, indent=2, default=str))
    else:
        # Human-readable output
        print("\n" + "="*80)
        print("SEARCH RESULTS")
        print("="*80)

        for source_name, result in results.items():
            print(f"\n{source_name}:")
            print("-" * 80)

            if result.get("not_relevant"):
                print("ℹ️  Not relevant to this query")
                continue

            if not result["success"]:
                print(f"❌ Error: {result.get('error', 'Unknown error')}")
                continue

            total = result.get("total", 0)
            response_time = result.get("response_time_ms", 0)

            print(f"✅ Found {total} results ({response_time:.0f}ms)")

            if result.get("results"):
                print(f"\nFirst {len(result['results'])} results:")
                for i, item in enumerate(result["results"][:5], 1):
                    # Try to get title
                    title = (
                        item.get("title") or
                        item.get("job_name") or
                        item.get("name") or
                        "Untitled"
                    )
                    print(f"\n  {i}. {title[:100]}")

                    # Try to get URL
                    url = item.get("url") or item.get("job_url") or item.get("uiLink")
                    if url:
                        print(f"     URL: {url}")

                    # Try to get description
                    desc = item.get("description") or item.get("content") or item.get("preview_text")
                    if desc:
                        desc_str = str(desc)[:200]
                        print(f"     {desc_str}...")

        print("\n" + "="*80)


def main():
    parser = argparse.ArgumentParser(
        description="AI-powered research CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 apps/ai_research_cli.py "cyber threat intelligence"
  python3 apps/ai_research_cli.py "military training" --limit 5
  python3 apps/ai_research_cli.py "SIGINT" --sources dvids,discord --json
        """
    )

    parser.add_argument(
        "query",
        help="Research question"
    )

    parser.add_argument(
        "--sources",
        help="Comma-separated list of sources to search (default: all)",
        default=None
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Maximum results per source (default: 10)"
    )

    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON"
    )

    args = parser.parse_args()

    # Parse sources
    source_ids = None
    if args.sources:
        source_ids = [s.strip() for s in args.sources.split(",")]

    # Execute search
    print(f"Searching for: {args.query}", file=sys.stderr)
    if source_ids:
        print(f"Sources: {', '.join(source_ids)}", file=sys.stderr)
    else:
        print(f"Sources: all registered sources", file=sys.stderr)
    print(f"Limit: {args.limit} results per source", file=sys.stderr)
    print("", file=sys.stderr)

    results = asyncio.run(search_all(args.query, source_ids, args.limit))

    # Print results
    print_results(results, args.json)

    # Exit code based on success
    any_success = any(r.get("success") and r.get("total", 0) > 0 for r in results.values())
    sys.exit(0 if any_success else 1)


if __name__ == "__main__":
    main()
