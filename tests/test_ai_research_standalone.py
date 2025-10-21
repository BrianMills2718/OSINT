#!/usr/bin/env python3
"""
Standalone AI Research test without Streamlit dependencies.
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import litellm
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ai_research_test.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('AIResearchTest')

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

load_dotenv()

def get_text(resp):
    """Extract text from litellm responses() API response"""
    texts = []
    if hasattr(resp, 'output') and resp.output:
        for item in resp.output:
            if hasattr(item, "content") and item.content is not None:
                for c in item.content:
                    if hasattr(c, "text") and c.text is not None:
                        texts.append(c.text)

    if not texts:
        return str(resp)

    return "\n".join(texts)


def generate_search_queries_standalone(research_question, comprehensive_mode=True):
    """Generate search queries using registry."""
    from integrations.registry import registry

    # Get all available sources from registry
    all_sources = registry.get_all()

    # Build source list with metadata for LLM
    source_list = []
    for source_id, source_class in all_sources.items():
        temp_instance = source_class()
        meta = temp_instance.metadata

        source_list.append({
            "id": source_id,
            "name": meta.name,
            "category": meta.category.value,
            "description": meta.description,
            "requires_api_key": meta.requires_api_key,
            "typical_response_time": meta.typical_response_time
        })

    logger.info(f"Registry loaded: {len(source_list)} sources available")
    logger.info(f"Sources: {[s['id'] for s in source_list]}")

    # LLM prompt
    if comprehensive_mode:
        task_instruction = "Select EVERY database that could provide relevant information for this research question."
        selection_guidance = """
IMPORTANT:
- Include EVERY database that might have relevant information
- Only exclude databases that are clearly irrelevant
- Cast a very wide net - when in doubt, include it
- Keep keywords simple and focused
"""
    else:
        task_instruction = "Select ALL databases that are relevant for this research question."
        selection_guidance = """
IMPORTANT:
- Include ALL databases that have relevant information
- Only exclude databases that are clearly NOT relevant
"""

    prompt = f"""You are a research assistant with access to multiple databases.

Available Databases:
{json.dumps(source_list, indent=2)}

Research Question: {research_question}

Task: {task_instruction}

{selection_guidance}

For each selected database, provide:
- source_id: The database ID (must match an id from Available Databases list)
- keywords: Search keywords (1-3 focused terms, NOT a sentence)
- reasoning: Why this database is relevant (1 sentence)

Return JSON array of selected sources."""

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
                },
                "minItems": 1,
                "maxItems": 10
            },
            "research_strategy": {"type": "string"}
        },
        "required": ["selected_sources", "research_strategy"],
        "additionalProperties": False
    }

    logger.info("Calling LLM for source selection...")
    response = litellm.responses(
        model="gpt-5-mini",
        input=prompt,
        text={
            "format": {
                "type": "json_schema",
                "name": "source_selection",
                "schema": schema,
                "strict": True
            }
        }
    )

    result_text = get_text(response)
    result = json.loads(result_text)
    logger.info(f"LLM selected {len(result['selected_sources'])} sources")
    return result


async def execute_search_standalone(source_id, research_question, api_keys, limit=10):
    """Execute search for a single source."""
    from integrations.registry import registry

    start_time = datetime.now()

    logger.info(f"=" * 80)
    logger.info(f"Starting search for source: {source_id}")
    logger.info(f"Research question: {research_question}")

    try:
        # Get integration
        integration_class = registry.get(source_id)
        if not integration_class:
            logger.error(f"Unknown source: {source_id}")
            return {
                "success": False,
                "total": 0,
                "results": [],
                "source": source_id,
                "error": f"Unknown source: {source_id}"
            }

        integration = integration_class()
        logger.info(f"Integration: {integration.metadata.name}")

        # Get API key
        api_key = None
        if integration.metadata.requires_api_key:
            api_key = api_keys.get(source_id)
            if not api_key:
                logger.warning(f"No API key for {source_id}")
                return {
                    "success": False,
                    "total": 0,
                    "results": [],
                    "source": integration.metadata.name,
                    "error": f"API key required for {integration.metadata.name}"
                }
            logger.info(f"API key found: {api_key[:10]}...")

        # Generate query
        logger.info("Generating query parameters...")
        query_params = await integration.generate_query(research_question=research_question)

        if not query_params:
            logger.warning("Query generation returned None (source deemed not relevant)")
            return {
                "success": False,
                "total": 0,
                "results": [],
                "source": integration.metadata.name,
                "error": "Query generation returned no parameters (source deemed not relevant)",
                "query_params": None
            }

        logger.info(f"Generated query parameters:")
        logger.info(json.dumps(query_params, indent=2))

        # Execute search
        logger.info("Executing search...")
        result = await integration.execute_search(query_params, api_key, limit)

        response_time_ms = (datetime.now() - start_time).total_seconds() * 1000

        logger.info(f"Search completed:")
        logger.info(f"  Success: {result.success}")
        logger.info(f"  Total: {result.total}")
        logger.info(f"  Returned: {len(result.results)}")
        logger.info(f"  Time: {response_time_ms:.0f}ms")

        if result.error:
            logger.error(f"  Error: {result.error}")

        return {
            "success": result.success,
            "total": result.total,
            "results": result.results,
            "source": result.source,
            "error": result.error,
            "response_time_ms": response_time_ms,
            "query_params": query_params
        }

    except Exception as e:
        response_time_ms = (datetime.now() - start_time).total_seconds() * 1000
        logger.exception(f"Exception during search for {source_id}:")
        return {
            "success": False,
            "total": 0,
            "results": [],
            "source": source_id,
            "error": str(e),
            "response_time_ms": response_time_ms,
            "query_params": None
        }


async def main():
    """Run comprehensive search test."""

    research_question = "i am looking for all recent activity and conversation related to domestic counterterrorism and JTTF etc"

    print("=" * 80)
    print("AI RESEARCH - COMPREHENSIVE SEARCH TEST")
    print("=" * 80)
    print(f"\nResearch Question: {research_question}\n")

    # Step 1: Generate strategy
    print("[STEP 1] Generating search strategy...")
    queries = generate_search_queries_standalone(research_question, comprehensive_mode=True)

    print(f"\n✅ Strategy: {queries['research_strategy'][:100]}...")
    print(f"\n✅ Selected {len(queries['selected_sources'])} sources:")
    for source in queries['selected_sources']:
        print(f"   - {source['source_id']}: {source['keywords']}")

    # Step 2: Execute searches
    print("\n[STEP 2] Executing searches...")

    api_keys = {
        "dvids": os.getenv('DVIDS_API_KEY'),
        "sam": os.getenv('SAM_GOV_API_KEY'),
        "usajobs": os.getenv('USAJOBS_API_KEY'),
        "twitter": os.getenv('RAPIDAPI_KEY'),
    }

    tasks = []
    for selected in queries['selected_sources']:
        task = execute_search_standalone(selected['source_id'], research_question, api_keys, limit=10)
        tasks.append(task)

    results_list = await asyncio.gather(*tasks)

    # Step 3: Summary
    print("\n" + "=" * 80)
    print("[STEP 3] RESULTS SUMMARY")
    print("=" * 80)

    for result in results_list:
        status = "✅" if result['success'] else "❌"
        print(f"\n{status} {result['source']}: {result['total']} results ({result.get('response_time_ms', 0):.0f}ms)")
        if result.get('error'):
            print(f"   Error: {result['error'][:100]}...")
        if result.get('query_params'):
            print(f"   Params: {json.dumps(result['query_params'], indent=11)[:200]}...")

    print("\n" + "=" * 80)
    print("✅ TEST COMPLETE - Check ai_research_test.log for full details")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
