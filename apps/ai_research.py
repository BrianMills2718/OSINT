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

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from ClearanceJobs import ClearanceJobs
from core.api_request_tracker import log_request
from usajobs_execute import execute_usajobs_search

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


def generate_search_queries(research_question):
    """
    Use AI to generate appropriate search queries using registry for dynamic source discovery.

    Returns structured JSON with selected sources and keywords for each.
    LLM selects 2-3 MOST relevant sources (not all sources).
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

    # LLM prompt - dynamic from registry
    prompt = f"""You are a research assistant with access to multiple databases.

Available Databases:
{json.dumps(source_list, indent=2)}

Research Question: {research_question}

Task: Select the 2-3 MOST relevant databases for this research question.

Consider:
- Database category and description
- Response time (prefer fast sources for exploratory queries)
- API key requirements (note which require keys)

For each selected database, provide:
- source_id: The database ID (must match an id from Available Databases list)
- keywords: Search keywords (1-3 focused terms, NOT a sentence)
- reasoning: Why this database is relevant (1 sentence)

IMPORTANT:
- Select ONLY 2-3 most relevant databases (not all of them!)
- Keep keywords simple and focused
- Prioritize free sources (requires_api_key: false) when quality is similar
- source_id MUST be one of: {', '.join([s['id'] for s in source_list])}

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
                "maxItems": 4
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
        query_params = await integration.generate_query(research_question=research_question)

        if not query_params:
            return {
                "success": False,
                "total": 0,
                "results": [],
                "source": integration.metadata.name,
                "error": "Query generation returned no parameters (source deemed not relevant)"
            }

        # Execute search
        result = await integration.execute_search(query_params, api_key, limit)

        response_time_ms = (datetime.now() - start_time).total_seconds() * 1000

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
        return {
            "success": False,
            "total": 0,
            "results": [],
            "source": source_id,
            "error": str(e),
            "response_time_ms": response_time_ms
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


def render_ai_research_tab(openai_api_key_from_ui, dvids_api_key, sam_api_key, usajobs_api_key=None):
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

    # Number of results per database
    col1, col2 = st.columns([3, 1])
    with col2:
        results_per_db = st.number_input(
            "Results per database",
            min_value=5,
            max_value=50,
            value=10,
            key="ai_results_limit"
        )

    # Search button
    search_btn = st.button("🚀 Research", type="primary", use_container_width=True, key="ai_search_btn")

    if search_btn and research_question:
        # Step 1: Generate queries
        with st.spinner("🧠 Analyzing your question and generating search queries..."):
            try:
                queries = generate_search_queries(research_question)

                st.success("✅ Generated search strategy")

                # Display search strategy
                with st.expander("📋 Search Strategy", expanded=True):
                    st.markdown(f"**Overall Strategy:** {queries['research_strategy']}")
                    st.markdown("---")

                    col_s1, col_s2 = st.columns(2)

                    with col_s1:
                        st.markdown("**🏢 ClearanceJobs**")
                        if queries['clearancejobs']['relevant']:
                            st.markdown(f"Keywords: `{queries['clearancejobs']['keywords']}`")
                            st.caption(queries['clearancejobs']['reasoning'])
                        else:
                            st.caption("❌ Not relevant for this query")

                        st.markdown("**📸 DVIDS**")
                        if queries['dvids']['relevant']:
                            st.markdown(f"Keywords: `{queries['dvids']['keywords']}`")
                            st.caption(queries['dvids']['reasoning'])
                        else:
                            st.caption("❌ Not relevant for this query")

                    with col_s2:
                        st.markdown("**📋 SAM.gov**")
                        if queries['sam_gov']['relevant']:
                            st.markdown(f"Keywords: `{queries['sam_gov']['keywords']}`")
                            st.caption(queries['sam_gov']['reasoning'])
                        else:
                            st.caption("❌ Not relevant for this query")

                        st.markdown("**💼 USAJobs**")
                        if queries['usajobs']['relevant']:
                            st.markdown(f"Keywords: `{queries['usajobs']['keywords']}`")
                            st.caption(queries['usajobs']['reasoning'])
                        else:
                            st.caption("❌ Not relevant for this query")

            except Exception as e:
                st.error(f"❌ Failed to generate queries: {str(e)}")
                return

        # Step 2: Execute searches
        with st.spinner("🔎 Searching across all databases..."):
            all_results = {}

            # Show debug info
            with st.expander("🔍 Debug: Actual API Queries", expanded=False):
                st.markdown("### Query Parameters Sent to Each API")
                st.json(queries)

            # ClearanceJobs
            if queries['clearancejobs']['relevant']:
                with st.status("Searching ClearanceJobs..."):
                    result = execute_clearancejobs_search(queries['clearancejobs'], results_per_db)
                    all_results['ClearanceJobs'] = result

                    # Show actual query sent
                    if result.get('debug_query'):
                        st.write("**Query sent:**")
                        st.json(result['debug_query'])

                    if result['success']:
                        st.write(f"✅ Found {result['total']} results")
                    else:
                        st.write(f"❌ Error: {result.get('error')}")
            else:
                all_results['ClearanceJobs'] = {"success": True, "total": 0, "results": [], "skipped": True}

            # DVIDS
            if queries['dvids']['relevant']:
                with st.status("Searching DVIDS..."):
                    result = execute_dvids_search(queries['dvids'], dvids_api_key, results_per_db)
                    all_results['DVIDS'] = result

                    # Show actual query sent
                    if result.get('debug_query'):
                        st.write("**Query sent:**")
                        st.json(result['debug_query'])

                    if result['success']:
                        st.write(f"✅ Found {result['total']} results")
                    else:
                        st.write(f"❌ Error: {result.get('error')}")
            else:
                all_results['DVIDS'] = {"success": True, "total": 0, "results": [], "skipped": True}

            # SAM.gov
            if queries['sam_gov']['relevant']:
                with st.status("Searching SAM.gov..."):
                    result = execute_sam_search(queries['sam_gov'], sam_api_key, results_per_db)
                    all_results['SAM.gov'] = result

                    # Show actual query sent
                    if result.get('debug_query'):
                        st.write("**Query sent:**")
                        st.json(result['debug_query'])

                    if result['success']:
                        st.write(f"✅ Found {result['total']} results")
                    else:
                        st.write(f"❌ Error: {result.get('error')}")
            else:
                all_results['SAM.gov'] = {"success": True, "total": 0, "results": [], "skipped": True}

            # USAJobs
            if queries['usajobs']['relevant']:
                with st.status("Searching USAJobs..."):
                    result = execute_usajobs_search(queries['usajobs'], usajobs_api_key, results_per_db)
                    all_results['USAJobs'] = result

                    # Show actual query sent
                    if result.get('debug_query'):
                        st.write("**Query sent:**")
                        st.json(result['debug_query'])

                    if result['success']:
                        st.write(f"✅ Found {result['total']} results")
                    else:
                        st.write(f"❌ Error: {result.get('error')}")
            else:
                all_results['USAJobs'] = {"success": True, "total": 0, "results": [], "skipped": True}

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
                if result.get('skipped'):
                    st.info("Skipped - not relevant to research question")
                elif not result['success']:
                    st.error(f"Error: {result.get('error')}")
                elif not result['results']:
                    st.info("No results found")
                else:
                    # Display results based on database type
                    if db_name == "ClearanceJobs":
                        for idx, job in enumerate(result['results'], 1):
                            st.markdown(f"**{idx}. {job.get('title', 'Untitled')}**")
                            st.caption(f"Company: {job.get('company', 'N/A')} | Location: {job.get('location', 'N/A')}")
                            if job.get('url'):
                                st.markdown(f"[View Job]({job['url']})")
                            st.markdown("---")

                    elif db_name == "DVIDS":
                        for idx, item in enumerate(result['results'], 1):
                            st.markdown(f"**{idx}. {item.get('title', 'Untitled')}**")
                            st.caption(f"Type: {item.get('type', 'N/A')} | Date: {item.get('date', 'N/A')}")
                            if item.get('url'):
                                st.markdown(f"[View]({item['url']})")
                            st.markdown("---")

                    elif db_name == "SAM.gov":
                        for idx, opp in enumerate(result['results'], 1):
                            st.markdown(f"**{idx}. {opp.get('title', 'Untitled')}**")
                            st.caption(f"Type: {opp.get('type', 'N/A')} | Posted: {opp.get('postedDate', 'N/A')[:10]}")
                            if opp.get('uiLink'):
                                st.markdown(f"[View Opportunity]({opp['uiLink']})")
                            st.markdown("---")

                    elif db_name == "USAJobs":
                        for idx, item in enumerate(result['results'], 1):
                            job_data = item.get('MatchedObjectDescriptor', {})
                            st.markdown(f"**{idx}. {job_data.get('PositionTitle', 'Untitled')}**")

                            # Agency and location
                            org = job_data.get('OrganizationName', 'N/A')
                            location_list = job_data.get('PositionLocationDisplay', 'N/A')

                            # Pay range
                            pay_info = job_data.get('PositionRemuneration', [])
                            if pay_info and len(pay_info) > 0:
                                min_pay = pay_info[0].get('MinimumRange', 'N/A')
                                max_pay = pay_info[0].get('MaximumRange', 'N/A')
                                pay_display = f"${min_pay} - ${max_pay}"
                            else:
                                pay_display = 'N/A'

                            st.caption(f"Agency: {org} | Location: {location_list}")
                            st.caption(f"Pay: {pay_display}")

                            if job_data.get('PositionURI'):
                                st.markdown(f"[View Job]({job_data['PositionURI']})")
                            st.markdown("---")

                    # Export button for each database
                    import pandas as pd
                    df = pd.DataFrame(result['results'])
                    csv = df.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        f"📥 Download {db_name} Results (CSV)",
                        csv,
                        f"{db_name.lower()}_{datetime.now().strftime('%Y%m%d')}.csv",
                        "text/csv",
                        key=f"download_{db_name}"
                    )

    elif search_btn and not research_question:
        st.warning("⚠️ Please enter a research question")
