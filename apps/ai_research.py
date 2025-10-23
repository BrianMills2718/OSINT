#!/usr/bin/env python3
"""AI-powered research assistant for unified search across all databases."""

import streamlit as st
import json
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import litellm
import requests
from datetime import datetime, timedelta
import logging

# Configure file logging for query debugging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ai_research_queries.log'),
        logging.StreamHandler()  # Also log to console
    ]
)
logger = logging.getLogger('AIResearch')

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Old imports removed - now using registry-driven approach
# from ClearanceJobs import ClearanceJobs
# from core.api_request_tracker import log_request
# from usajobs_execute import execute_usajobs_search

# Load environment variables from .env file in project directory
# This works for local development. For production (Streamlit Cloud),
# use Streamlit secrets instead (st.secrets["OPENAI_API_KEY"])
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


def generate_search_queries(research_question, comprehensive_mode=False):
    """
    Use AI to generate appropriate search queries using registry for dynamic source discovery.

    Args:
        research_question: The user's research question
        comprehensive_mode: If True, select ALL relevant sources. If False, select 2-3 most relevant.

    Returns structured JSON with selected sources and keywords for each.
    Each integration's generate_query() will add source-specific parameters.
    """
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

    # LLM prompt - dynamic from registry, changes based on mode
    if comprehensive_mode:
        task_instruction = "Select EVERY database that could provide relevant information for this research question."
        selection_guidance = """
IMPORTANT:
- Include EVERY database that might have relevant information
- Only exclude databases that are clearly irrelevant
- Cast a very wide net - when in doubt, include it
- Keep keywords simple and focused
- source_id MUST be one of: {', '.join([s['id'] for s in source_list])}

Example: For "cybersecurity jobs", include:
- clearancejobs (security cleared jobs)
- usajobs (federal cybersecurity positions)
- sam (cybersecurity contracts - related to jobs)
- dvids (might have cyber warfare content)
Exclude only: discord (not about jobs), fbi_vault (not about jobs)
"""
    else:
        task_instruction = "Select ALL databases that are relevant for this research question."
        selection_guidance = """
IMPORTANT:
- Include ALL databases that have relevant information
- Only exclude databases that are clearly NOT relevant
- Use your judgment - include sources that could help answer the question
- Keep keywords simple and focused
- Prioritize free sources (requires_api_key: false) when quality is similar
- source_id MUST be one of: {', '.join([s['id'] for s in source_list])}

Examples:
- For "JTTF activity": Include discord (real-time chatter), fbi_vault (official docs), maybe dvids (operations). Exclude clearancejobs, sam, usajobs (not about jobs/contracts).
- For "cybersecurity jobs": Include clearancejobs, usajobs. Optionally sam (contracts). Exclude discord, fbi_vault, dvids.
"""

    prompt = f"""You are a research assistant with access to multiple databases.

Available Databases:
{json.dumps(source_list, indent=2)}

Research Question: {research_question}

Task: {task_instruction}

Consider:
- Database category and description
- Response time (prefer fast sources for exploratory queries)
- API key requirements (note which require keys)

For each selected database, provide:
- source_id: The database ID (must match an id from Available Databases list)
- keywords: Search keywords (1-3 focused terms, NOT a sentence)
- reasoning: Why this database is relevant (1 sentence)

{selection_guidance}

Return JSON array of selected sources."""

    # Generic schema - works for any number of sources
    schema = {
        "type": "object",
        "properties": {
            "selected_sources": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "source_id": {
                            "type": "string",
                            "description": "Database ID from available list"
                        },
                        "keywords": {
                            "type": "string",
                            "description": "Search keywords (1-3 terms)"
                        },
                        "reasoning": {
                            "type": "string",
                            "description": "Why this database is relevant"
                        }
                    },
                    "required": ["source_id", "keywords", "reasoning"],
                    "additionalProperties": False
                },
                "minItems": 1,
                "maxItems": 10  # Allow up to 10 sources (covers all current + future sources)
            },
            "research_strategy": {
                "type": "string",
                "description": "Overall strategy for answering the research question"
            }
        },
        "required": ["selected_sources", "research_strategy"],
        "additionalProperties": False
    }

    # Call gpt-5-mini with structured output
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

    # Extract and parse the response
    result_text = get_text(response)
    return json.loads(result_text)


async def execute_search_via_registry(source_id: str, research_question: str, api_keys: dict, limit: int = 10) -> dict:
    """
    Execute search via registry for any source.

    Args:
        source_id: Database ID (e.g., "dvids", "sam", "clearancejobs")
        research_question: Research question to generate query from
        api_keys: Dict mapping source_id to API key
        limit: Max results

    Returns:
        Dict with {success, total, results, source, error}
    """
    from integrations.registry import registry

    start_time = datetime.now()

    logger.info(f"=" * 80)
    logger.info(f"Starting search for source: {source_id}")
    logger.info(f"Research question: {research_question}")
    logger.info(f"Result limit: {limit}")

    try:
        # Get integration class from registry
        integration_class = registry.get(source_id)
        if not integration_class:
            return {
                "success": False,
                "total": 0,
                "results": [],
                "source": source_id,
                "error": f"Unknown source: {source_id}"
            }

        # Instantiate integration
        integration = integration_class()

        # Get API key if needed
        api_key = None
        if integration.metadata.requires_api_key:
            api_key = api_keys.get(source_id)
            if not api_key:
                return {
                    "success": False,
                    "total": 0,
                    "results": [],
                    "source": integration.metadata.name,
                    "error": f"API key required for {integration.metadata.name}"
                }

        # Generate source-specific query params via integration's LLM
        logger.info(f"Generating query parameters for {integration.metadata.name}...")
        query_params = await integration.generate_query(research_question=research_question)

        # RELEVANCE FILTER DISABLED - Always search all sources
        # Even if LLM says "not relevant", we still execute the search
        # This ensures we don't miss results due to overly conservative LLM filtering
        if not query_params:
            logger.warning(f"{integration.metadata.name}: LLM returned no query params (not relevant), but searching anyway...")
            # Create a simple fallback query with just the research question
            query_params = {"keywords": research_question}
            logger.info(f"{integration.metadata.name}: Using fallback query params: {query_params}")

        logger.info(f"{integration.metadata.name}: Generated query parameters:")
        logger.info(f"  {json.dumps(query_params, indent=2)}")

        # Execute search
        logger.info(f"Executing search for {integration.metadata.name}...")
        result = await integration.execute_search(query_params, api_key, limit)

        response_time_ms = (datetime.now() - start_time).total_seconds() * 1000

        logger.info(f"{integration.metadata.name}: Search completed")
        logger.info(f"  Success: {result.success}")
        logger.info(f"  Total results: {result.total}")
        logger.info(f"  Returned results: {len(result.results)}")
        logger.info(f"  Response time: {response_time_ms:.0f}ms")
        if result.error:
            logger.error(f"  Error: {result.error}")

        # Convert QueryResult to dict format
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
            "query_params": None  # Include even when None for consistency
        }


def summarize_results(research_question, queries, all_results):
    """
    Use AI to summarize all search results in context of the original research question.
    """

    # Prepare results summary for AI
    results_summary = []

    for db_name, result in all_results.items():
        if result["success"]:
            results_summary.append({
                "database": db_name,
                "total_found": result["total"],
                "sample_results": result["results"][:5]  # First 5 results
            })
        else:
            results_summary.append({
                "database": db_name,
                "error": result.get("error", "Unknown error")
            })

    prompt = f"""You are a research assistant analyzing search results across multiple databases.

Original Research Question: {research_question}

Search Strategy: {queries.get('research_strategy', 'N/A')}

Search Results:
{json.dumps(results_summary, indent=2)}

Provide a comprehensive summary that:
1. Directly answers the research question based on the results found
2. Highlights the most relevant findings from each database
3. Notes any patterns or connections across databases
4. Identifies any gaps or areas needing further investigation
5. Provides specific examples from the results to support your analysis

Be concise but thorough. Focus on insights that directly relate to the research question."""

    # Call AI for summary (free-form text, no structured output)
    response = litellm.responses(
        model="gpt-5-mini",
        input=prompt
        # No text parameter needed for free-form text output
    )

    return get_text(response)


def render_ai_research_tab(openai_api_key_from_ui, dvids_api_key, sam_api_key, usajobs_api_key=None, rapidapi_key=None):
    """Render the AI Research tab in the Streamlit app."""

    st.markdown("### 🤖 AI-Powered Research Assistant")
    st.caption("Ask a research question and AI will search across all databases and summarize results")

    # Get OpenAI API key from multiple sources (priority order):
    # 1. User input in sidebar (highest priority - allows override)
    # 2. Streamlit secrets (for Streamlit Cloud deployment)
    # 3. Environment variable (for local .env or server deployment)
    openai_api_key = None

    # Check UI input first (allows users to override)
    if openai_api_key_from_ui:
        openai_api_key = openai_api_key_from_ui
    # Check Streamlit secrets (production deployment)
    elif hasattr(st, 'secrets') and "OPENAI_API_KEY" in st.secrets:
        try:
            openai_api_key = st.secrets["OPENAI_API_KEY"]
        except:
            pass
    # Fall back to environment variable (local development)
    else:
        openai_api_key = os.getenv("OPENAI_API_KEY")

    # If still no key, show error and allow UI input
    if not openai_api_key:
        st.error("⚠️ **OpenAI API Key Required**")

        with st.expander("💡 How to configure OpenAI API Key", expanded=True):
            st.markdown("""
            **For Local Development:**
            1. Create a `.env` file in the project directory
            2. Add: `OPENAI_API_KEY=your-key-here`
            3. Restart the app

            **For Streamlit Cloud Deployment:**
            1. Go to App Settings → Secrets
            2. Add: `OPENAI_API_KEY = "your-key-here"`

            **Get your API key:** https://platform.openai.com/api-keys
            """)

        return

    # Set the API key for litellm to use
    os.environ["OPENAI_API_KEY"] = openai_api_key

    # Research question input
    st.markdown("#### 🔍 Your Research Question")

    # Example queries
    with st.expander("💡 Example Queries", expanded=False):
        st.markdown("""
        **Government Contracts:**
        - "What contracts are available for cybersecurity threat intelligence?"
        - "Find intelligence community contracting opportunities"

        **Jobs:**
        - "TS/SCI cleared positions in counterterrorism"
        - "Cybersecurity jobs requiring polygraph"

        **Military & Media:**
        - "Recent DVIDS content about special operations in the Middle East"
        - "Military exercises related to cyber warfare"

        **Multi-Source:**
        - "What are the latest developments in AI security across government contracts, jobs, and military media?"
        - "Find information about SIGINT (signals intelligence) jobs, contracts, and recent operations"
        """)

    research_question = st.text_area(
        "What would you like to research?",
        placeholder="Example: What cybersecurity job opportunities and government contracts are available for cleared professionals working on AI security?",
        height=100,
        key="ai_research_question"
    )

    # Search options
    col1, col2 = st.columns([3, 1])

    with col1:
        comprehensive_mode = st.checkbox(
            "🔍 Comprehensive Search (maximum coverage)",
            value=False,
            help="Enable to cast the widest possible net - includes every database that could potentially have relevant info. Disable for more selective, focused results."
        )

    with col2:
        results_per_db = st.number_input(
            "Results per database",
            min_value=5,
            max_value=50,
            value=10,
            key="ai_results_limit"
        )

    # Info about search mode
    if comprehensive_mode:
        st.info("💡 **Comprehensive mode**: Searches EVERY database that might have relevant info. Slower and more expensive, but ensures exhaustive coverage.")
    else:
        st.info("💡 **Intelligent mode** (default): AI selects all relevant databases while excluding clearly irrelevant sources. Balances coverage with efficiency.")

    # Search button
    search_btn = st.button("🚀 Research", type="primary", use_container_width=True, key="ai_search_btn")

    if search_btn and research_question:
        # Step 1: Generate queries
        with st.spinner("🧠 Analyzing your question and generating search queries..."):
            try:
                queries = generate_search_queries(research_question, comprehensive_mode=comprehensive_mode)

                st.success("✅ Generated search strategy")

                # Display search strategy
                with st.expander("📋 Search Strategy", expanded=True):
                    st.markdown(f"**Overall Strategy:** {queries['research_strategy']}")
                    st.markdown("---")

                    # Dynamic columns based on number of sources
                    selected_sources = queries['selected_sources']
                    cols = st.columns(len(selected_sources))

                    for idx, selected in enumerate(selected_sources):
                        with cols[idx]:
                            st.markdown(f"**{selected.get('source_id', 'Unknown')}**")
                            st.markdown(f"Keywords: `{selected.get('keywords', 'N/A')}`")
                            st.caption(selected.get('reasoning', 'No reasoning provided'))

            except Exception as e:
                st.error(f"❌ Failed to generate queries: {str(e)}")
                return

        # Step 2: Execute searches
        with st.spinner("🔎 Searching across selected databases..."):
            all_results = {}

            # Build API key dict
            api_keys = {
                "dvids": dvids_api_key,
                "sam": sam_api_key,
                "usajobs": usajobs_api_key,
                "twitter": rapidapi_key,  # Twitter uses RAPIDAPI_KEY
                "brave_search": os.getenv("BRAVE_SEARCH_API_KEY"),
                # Add others as needed - registry will handle any source
            }

            # Execute searches in parallel
            import asyncio

            async def search_all_sources():
                tasks = []
                for selected in queries['selected_sources']:
                    source_id = selected['source_id']
                    # Pass full research question, not just keywords
                    # Each integration's generate_query() will see the full context
                    task = execute_search_via_registry(source_id, research_question, api_keys, results_per_db)
                    tasks.append(task)

                return await asyncio.gather(*tasks)

            # Run async searches
            results_list = asyncio.run(search_all_sources())

            # Convert to dict keyed by source
            for result in results_list:
                source_name = result.get('source', 'Unknown')
                all_results[source_name] = result

                # Show status (query params logged to file)
                if result.get('not_relevant'):
                    st.info(f"ℹ️ {source_name}: Not relevant to this query")
                elif result['success']:
                    st.success(f"✅ {source_name}: Found {result['total']} results")
                else:
                    st.error(f"❌ {source_name}: {result.get('error', 'Unknown error')}")

        # Step 3: Summarize results
        with st.spinner("📝 Analyzing and summarizing results..."):
            try:
                summary = summarize_results(research_question, queries, all_results)

                st.markdown("---")
                st.markdown("### 📊 Research Summary")
                st.markdown(summary)

            except Exception as e:
                st.error(f"❌ Failed to generate summary: {str(e)}")

        # Step 4: Display detailed results
        st.markdown("---")
        st.markdown("### 📁 Detailed Results")

        for db_name, result in all_results.items():
            with st.expander(f"{db_name} ({result.get('total', 0)} results)", expanded=False):
                if not result['success']:
                    st.error(f"Error: {result.get('error')}")
                elif not result['results']:
                    st.info("No results found")
                else:
                    # GENERIC display - works for all sources
                    for idx, item in enumerate(result['results'], 1):
                        # Try common title fields
                        title = (item.get('title') or
                                item.get('job_name') or
                                item.get('name') or
                                item.get('MatchedObjectDescriptor', {}).get('PositionTitle') or
                                'Untitled')

                        st.markdown(f"**{idx}. {title}**")

                        # Show URL if available
                        url = (item.get('url') or
                              item.get('job_url') or
                              item.get('uiLink') or
                              item.get('MatchedObjectDescriptor', {}).get('PositionURI'))
                        if url:
                            st.markdown(f"[View]({url})")

                        # Show common metadata fields if available
                        metadata_parts = []

                        # Date fields
                        date_val = (item.get('date') or
                                   item.get('date_published') or
                                   item.get('postedDate') or
                                   item.get('updated'))
                        if date_val:
                            metadata_parts.append(f"Date: {str(date_val)[:10]}")

                        # Type/Category
                        type_val = (item.get('type') or
                                   item.get('category'))
                        if type_val:
                            metadata_parts.append(f"Type: {type_val}")

                        # Company/Organization
                        org_val = (item.get('company') or
                                  item.get('company_name') or
                                  item.get('organization') or
                                  item.get('MatchedObjectDescriptor', {}).get('OrganizationName'))
                        if org_val:
                            metadata_parts.append(f"Org: {org_val}")

                        # Location
                        loc_val = (item.get('location') or
                                  item.get('PositionLocationDisplay'))
                        if loc_val:
                            metadata_parts.append(f"Location: {loc_val}")

                        if metadata_parts:
                            st.caption(" | ".join(metadata_parts))

                        # Show description/content if available
                        desc = (item.get('description') or
                               item.get('preview_text') or
                               item.get('content'))
                        if desc:
                            st.caption(desc[:200] + "..." if len(str(desc)) > 200 else desc)

                        st.markdown("---")

                    # Export button for each database
                    import pandas as pd
                    df = pd.DataFrame(result['results'])
                    csv = df.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        f"📥 Download {db_name} Results (CSV)",
                        csv,
                        f"{db_name.lower().replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.csv",
                        "text/csv",
                        key=f"download_{db_name.replace(' ', '_')}"
                    )

    elif search_btn and not research_question:
        st.warning("⚠️ Please enter a research question")
