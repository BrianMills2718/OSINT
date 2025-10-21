#!/usr/bin/env python3
"""
End-to-End Test: Twitter Integration via Agentic Research

Tests Twitter integration through the full research pipeline:
1. LLM analyzes research question
2. LLM selects relevant sources (should include Twitter)
3. TwitterIntegration generates search parameters
4. Search executes via api_client
5. Results display with proper formatting
"""

import asyncio
import sys
from dotenv import load_dotenv
import os

# Add parent directory to path
sys.path.insert(0, '/home/brian/sam_gov')

from integrations.registry import registry
from core.parallel_executor import ParallelExecutor
from llm_utils import acompletion
import json

load_dotenv()

async def test_twitter_via_research_flow():
    """Test Twitter integration through full agentic research flow."""

    research_question = "Recent Twitter discussions about JTTF"

    print("=" * 80)
    print("END-TO-END TEST: Twitter Integration via Research Flow")
    print("=" * 80)
    print(f"\nResearch Question: {research_question}")
    print()

    # Step 1: Get all available sources
    print("[STEP 1] Loading available sources from registry")
    print("-" * 80)

    all_sources = registry.get_all()
    source_list = []

    for source_id, source_class in all_sources.items():
        temp_instance = source_class()
        meta = temp_instance.metadata
        source_list.append({
            "id": source_id,
            "name": meta.name,
            "category": meta.category.value,
            "description": meta.description,
            "requires_api_key": meta.requires_api_key
        })

    print(f"✅ Loaded {len(source_list)} sources from registry")
    print(f"   Sources: {[s['id'] for s in source_list]}")
    print()

    # Step 2: LLM selects relevant sources
    print("[STEP 2] LLM Source Selection")
    print("-" * 80)

    prompt = f"""You are a research assistant selecting the most relevant data sources.

Research Question: {research_question}

Available Sources:
{json.dumps(source_list, indent=2)}

Select 2-3 MOST relevant sources for this research question.

For each selected source, provide:
- source_id: The ID from available sources
- keywords: 1-3 focused keywords for this source
- reasoning: Why this source is relevant

Return JSON with this structure:
{{
  "selected_sources": [
    {{"source_id": "...", "keywords": "...", "reasoning": "..."}}
  ]
}}
"""

    schema = {
        "type": "object",
        "properties": {
            "selected_sources": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "source_id": {"type": "string"},
                        "keywords": {"type": "string"},
                        "reasoning": {"type": "string"}
                    },
                    "required": ["source_id", "keywords", "reasoning"],
                    "additionalProperties": False
                }
            }
        },
        "required": ["selected_sources"],
        "additionalProperties": False
    }

    response = await acompletion(
        model="gpt-4o-mini",  # Use reliable model
        messages=[{"role": "user", "content": prompt}],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "strict": True,
                "name": "source_selection",
                "schema": schema
            }
        }
    )

    result = json.loads(response.choices[0].message.content)
    selected_sources = result["selected_sources"]

    print(f"✅ LLM selected {len(selected_sources)} sources:")
    for i, source in enumerate(selected_sources, 1):
        print(f"\n{i}. {source['source_id']}")
        print(f"   Keywords: {source['keywords']}")
        print(f"   Reasoning: {source['reasoning']}")

    # Check if Twitter was selected
    twitter_selected = any(s['source_id'] == 'twitter' for s in selected_sources)
    print()
    if twitter_selected:
        print("✅ TWITTER WAS SELECTED by LLM")
    else:
        print("⚠️  WARNING: Twitter was NOT selected by LLM")
        print("   This may indicate LLM source selection bias")
    print()

    # Step 3: Execute searches for selected sources
    print("[STEP 3] Executing Searches via Selected Integrations")
    print("-" * 80)

    api_keys = {
        'twitter': os.getenv('RAPIDAPI_KEY'),
        'sam': os.getenv('SAM_GOV_API_KEY'),
        'dvids': os.getenv('DVIDS_API_KEY'),
        'usajobs': os.getenv('USAJOBS_API_KEY')
    }

    results_by_source = {}

    for selected in selected_sources:
        source_id = selected['source_id']
        print(f"\nSearching {source_id}...")

        # Get integration
        integration_class = registry.get(source_id)
        integration = integration_class()

        # Get API key if needed
        api_key = None
        if integration.metadata.requires_api_key:
            api_key = api_keys.get(source_id)
            if not api_key:
                print(f"  ⚠️  No API key for {source_id}, skipping")
                continue

        # Generate query
        query_params = await integration.generate_query(research_question=research_question)

        if query_params is None:
            print(f"  ⚠️  Integration determined not relevant, skipping")
            continue

        print(f"  Query params: {query_params}")

        # Execute search
        result = await integration.execute_search(query_params, api_key, limit=5)

        if result.success:
            print(f"  ✅ Success: {result.total} total, {len(result.results)} returned, {result.response_time_ms:.0f}ms")
            results_by_source[source_id] = result.results
        else:
            print(f"  ❌ Error: {result.error}")

    # Step 4: Display results
    print()
    print("[STEP 4] Results Summary")
    print("=" * 80)

    total_results = sum(len(results) for results in results_by_source.values())
    print(f"\nTotal results across all sources: {total_results}")
    print(f"Sources with results: {len(results_by_source)}")

    for source_id, results in results_by_source.items():
        print(f"\n{source_id.upper()}: {len(results)} results")
        print("-" * 80)

        for i, item in enumerate(results[:3], 1):  # Show first 3 from each source
            title = item.get('title', 'Untitled')
            url = item.get('url', '')
            date = item.get('date', '')

            print(f"\n{i}. {title}")
            if url:
                print(f"   URL: {url}")
            if date:
                print(f"   Date: {date}")

            # Show Twitter-specific metadata if available
            if source_id == 'twitter':
                author = item.get('author', '')
                favorites = item.get('favorites', 0)
                retweets = item.get('retweets', 0)
                if author:
                    print(f"   Author: @{author}")
                if favorites or retweets:
                    print(f"   Engagement: {favorites} likes, {retweets} RTs")

    # Final verdict
    print()
    print("=" * 80)
    if twitter_selected and 'twitter' in results_by_source:
        print("✅ END-TO-END TEST: PASS")
        print("   - Twitter was selected by LLM")
        print("   - Twitter search executed successfully")
        print("   - Results returned and displayed")
    elif twitter_selected and 'twitter' not in results_by_source:
        print("⚠️  END-TO-END TEST: PARTIAL PASS")
        print("   - Twitter was selected by LLM")
        print("   - But search failed or returned no results")
    else:
        print("⚠️  END-TO-END TEST: LLM SELECTION ISSUE")
        print("   - Twitter was NOT selected by LLM")
        print("   - This indicates potential source selection bias")
        print("   - Integration itself may still be working")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(test_twitter_via_research_flow())
