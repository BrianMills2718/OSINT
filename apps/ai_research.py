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
    Use AI to generate appropriate search queries for all three databases.
    Returns structured JSON with queries for ClearanceJobs, DVIDS, and SAM.gov.
    """

    # Get today's date and a date 60 days ago for context
    today = datetime.now()
    sixty_days_ago = today - timedelta(days=60)

    today_str = today.strftime("%Y-%m-%d")
    sixty_days_ago_str = sixty_days_ago.strftime("%Y-%m-%d")

    prompt = f"""You are a research assistant helping to search across three databases:
1. ClearanceJobs - Security clearance job postings
2. DVIDS - Military media (photos, videos, news articles)
3. SAM.gov - Government contract opportunities

**IMPORTANT DATE CONTEXT:**
- Today's date is: {today_str}
- 60 days ago was: {sixty_days_ago_str}
- When specifying date ranges, use dates between these two dates (in the PAST)
- For "last couple months", use approximately {sixty_days_ago_str} to {today_str}

Research Question: {research_question}

Generate appropriate search queries for each database. For each database, determine:
- Keywords to search (use SIMPLE keywords - just the most important 1-3 words, NO commas)
- Relevant filters that would help narrow results
- Whether this database is relevant for the research question

**KEYWORD EXAMPLES:**
- Good for DVIDS: "JTTF" or "counterterrorism" (short and simple)
- Good for SAM.gov: "counterterrorism" or "intelligence" (broad terms that appear in contracts)
- Bad: "Joint Terrorism Task Force, JTTF, counterterrorism" (too complex, has commas)
- Bad for SAM.gov: "JTTF" or "Joint Terrorism Task Force" (too specific, unlikely in contracts)

**DATE FORMAT REQUIREMENTS:**
- DVIDS: YYYY-MM-DD format (e.g., "{sixty_days_ago_str}")
- SAM.gov: MM/DD/YYYY format (e.g., "{sixty_days_ago.strftime('%m/%d/%Y')}")
- Use dates between {sixty_days_ago_str} and {today_str} ONLY

Return a JSON object with search parameters for each database according to the schema.
If a database is not relevant to the research question, set "relevant": false for that database."""

    # Define the JSON schema for structured output
    query_schema = {
        "type": "object",
        "properties": {
            "clearancejobs": {
                "type": "object",
                "properties": {
                    "relevant": {"type": "boolean"},
                    "keywords": {"type": "string"},
                    "clearances": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of clearance levels, empty if not relevant"
                    },
                    "posted_days_ago": {
                        "type": "integer",
                        "description": "Number of days ago the job was posted, 0 if not relevant"
                    },
                    "reasoning": {"type": "string"}
                },
                "required": ["relevant", "keywords", "clearances", "posted_days_ago", "reasoning"],
                "additionalProperties": False
            },
            "dvids": {
                "type": "object",
                "properties": {
                    "relevant": {"type": "boolean"},
                    "keywords": {"type": "string"},
                    "media_types": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Leave empty array - not supported by API. Will search all media types."
                    },
                    "date_from": {
                        "type": "string",
                        "description": "Leave empty string - date filtering not reliably supported by DVIDS API"
                    },
                    "date_to": {
                        "type": "string",
                        "description": "Leave empty string - date filtering not reliably supported by DVIDS API"
                    },
                    "reasoning": {"type": "string"}
                },
                "required": ["relevant", "keywords", "media_types", "date_from", "date_to", "reasoning"],
                "additionalProperties": False
            },
            "sam_gov": {
                "type": "object",
                "properties": {
                    "relevant": {"type": "boolean"},
                    "keywords": {"type": "string"},
                    "posted_from": {
                        "type": "string",
                        "description": "Start date in MM/DD/YYYY format, empty string if not relevant"
                    },
                    "posted_to": {
                        "type": "string",
                        "description": "End date in MM/DD/YYYY format, empty string if not relevant"
                    },
                    "naics_codes": {
                        "type": "string",
                        "description": "Comma-separated NAICS codes, empty string if not relevant"
                    },
                    "reasoning": {"type": "string"}
                },
                "required": ["relevant", "keywords", "posted_from", "posted_to", "naics_codes", "reasoning"],
                "additionalProperties": False
            },
            "research_strategy": {
                "type": "string",
                "description": "Overall strategy for how these queries will help answer the research question"
            }
        },
        "required": ["clearancejobs", "dvids", "sam_gov", "research_strategy"],
        "additionalProperties": False
    }

    # Call gpt-5-mini with structured output
    response = litellm.responses(
        model="gpt-5-mini",
        input=prompt,
        text={
            "format": {
                "type": "json_schema",
                "name": "search_queries",
                "schema": query_schema,
                "strict": True
            }
        }
    )

    # Extract and parse the response
    result_text = get_text(response)
    return json.loads(result_text)


def execute_clearancejobs_search(query_params, limit=10):
    """Execute ClearanceJobs search based on AI-generated parameters."""
    start_time = datetime.now()
    endpoint = "https://api.clearancejobs.com/api/v1/jobs/search"

    try:
        cj = ClearanceJobs()

        body = {
            "pagination": {"page": 1, "size": limit},
            "query": query_params.get("keywords", "")
        }

        # Add clearances if specified (non-empty array)
        if query_params.get("clearances") and len(query_params["clearances"]) > 0:
            body["filters"] = body.get("filters", {})
            body["filters"]["clearance"] = query_params["clearances"]

        # Add date filter if specified (non-zero value)
        if query_params.get("posted_days_ago") and query_params["posted_days_ago"] > 0:
            body["filters"] = body.get("filters", {})
            body["filters"]["posted"] = query_params["posted_days_ago"]

        response = cj.post("/jobs/search", body)
        response_time_ms = (datetime.now() - start_time).total_seconds() * 1000

        # Log successful request
        log_request("ClearanceJobs", endpoint, response.status_code, response_time_ms, None, body)

        data = response.json()

        # ClearanceJobs returns "data" array and "meta" object
        jobs = data.get("data", [])
        meta = data.get("meta", {})
        pagination = meta.get("pagination", {})
        total = pagination.get("total", len(jobs))  # Fall back to job count if no pagination info

        return {
            "success": True,
            "total": total,
            "results": jobs[:limit],
            "source": "ClearanceJobs",
            "debug_query": {
                "endpoint": "POST /jobs/search",
                "body": body
            }
        }

    except Exception as e:
        # Log failed request
        response_time_ms = (datetime.now() - start_time).total_seconds() * 1000
        status_code = getattr(e, 'response', None) and e.response.status_code or 0
        log_request("ClearanceJobs", endpoint, status_code, response_time_ms, str(e), body if 'body' in locals() else query_params)

        return {
            "success": False,
            "error": str(e),
            "source": "ClearanceJobs",
            "debug_query": {
                "endpoint": "POST /jobs/search",
                "attempted_body": body if 'body' in locals() else query_params
            }
        }


def execute_dvids_search(query_params, api_key, limit=10):
    """Execute DVIDS search based on AI-generated parameters."""
    start_time = datetime.now()
    url = "https://api.dvidshub.net/search"

    try:
        if not api_key:
            return {
                "success": False,
                "error": "DVIDS API key required",
                "source": "DVIDS"
            }

        # Build params - use correct DVIDS API parameters
        params = {
            "api_key": api_key,
            "q": query_params.get("keywords", ""),
            "max_results": min(limit, 50)  # DVIDS max is 50
        }

        # Note: DVIDS searches all media types and dates by default
        # Date filtering via from_publishdate/to_publishdate can be added but often causes issues

        response = requests.get(url, params=params, timeout=30)
        response_time_ms = (datetime.now() - start_time).total_seconds() * 1000

        # Log request
        log_request("DVIDS", url, response.status_code, response_time_ms, None, params)

        # Capture the actual URL that was requested
        actual_url = response.url

        response.raise_for_status()
        data = response.json()

        results = data.get("results", [])
        # DVIDS uses page_info for metadata
        page_info = data.get("page_info", {})
        total = page_info.get("total_results", 0)

        return {
            "success": True,
            "total": total,
            "results": results[:limit],
            "source": "DVIDS",
            "debug_query": {
                "endpoint": "GET " + url,
                "params": params,
                "actual_url": actual_url
            }
        }

    except Exception as e:
        # Log failed request
        response_time_ms = (datetime.now() - start_time).total_seconds() * 1000
        status_code = getattr(e, 'response', None) and e.response.status_code or 0
        log_request("DVIDS", url, status_code, response_time_ms, str(e), params if 'params' in locals() else query_params)

        return {
            "success": False,
            "error": str(e),
            "source": "DVIDS",
            "debug_query": {
                "endpoint": "GET https://api.dvidshub.net/v1/search",
                "attempted_params": params if 'params' in locals() else query_params,
                "actual_url": response.url if 'response' in locals() else "N/A"
            }
        }


def execute_sam_search(query_params, api_key, limit=10):
    """Execute SAM.gov search based on AI-generated parameters."""
    start_time = datetime.now()
    url = "https://api.sam.gov/opportunities/v2/search"

    try:
        if not api_key:
            return {
                "success": False,
                "error": "SAM.gov API key required",
                "source": "SAM.gov"
            }

        # Default to last 30 days if not specified or empty
        posted_from = query_params.get("posted_from", "")
        if not posted_from or not posted_from.strip():
            posted_from = (datetime.now() - timedelta(days=30)).strftime("%m/%d/%Y")

        posted_to = query_params.get("posted_to", "")
        if not posted_to or not posted_to.strip():
            posted_to = datetime.now().strftime("%m/%d/%Y")

        params = {
            "api_key": api_key,
            "keywords": query_params.get("keywords", ""),
            "postedFrom": posted_from,
            "postedTo": posted_to,
            "limit": min(limit, 100),
            "offset": 0
        }

        # Add NAICS codes if specified (non-empty string)
        if query_params.get("naics_codes") and query_params["naics_codes"].strip():
            params["ncode"] = query_params["naics_codes"]

        response = requests.get(url, params=params, timeout=60)  # Increased timeout - SAM.gov can be slow
        response_time_ms = (datetime.now() - start_time).total_seconds() * 1000

        # Log request (IMPORTANT for rate limit tracking)
        log_request("SAM.gov", url, response.status_code, response_time_ms, None, params)

        # Capture the actual URL that was requested
        actual_url = response.url

        response.raise_for_status()
        data = response.json()

        opportunities = data.get('opportunitiesData', data.get('results', []))
        total = data.get('totalRecords', data.get('total', 0))

        return {
            "success": True,
            "total": total,
            "results": opportunities[:limit],
            "source": "SAM.gov",
            "debug_query": {
                "endpoint": "GET " + url,
                "params": params,
                "actual_url": actual_url
            }
        }

    except Exception as e:
        # Log failed request (including 429 rate limits!)
        response_time_ms = (datetime.now() - start_time).total_seconds() * 1000
        status_code = getattr(e, 'response', None) and e.response.status_code or 0
        log_request("SAM.gov", url, status_code, response_time_ms, str(e), params if 'params' in locals() else query_params)

        return {
            "success": False,
            "error": str(e),
            "source": "SAM.gov",
            "debug_query": {
                "endpoint": "GET https://api.sam.gov/opportunities/v2/search",
                "attempted_params": params if 'params' in locals() else query_params,
                "actual_url": response.url if 'response' in locals() else "N/A"
            }
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

    # TODO: Integrate USAJobs into AI Research (currently only ClearanceJobs, DVIDS, SAM.gov)

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

                    col_s1, col_s2, col_s3 = st.columns(3)

                    with col_s1:
                        st.markdown("**🏢 ClearanceJobs**")
                        if queries['clearancejobs']['relevant']:
                            st.markdown(f"Keywords: `{queries['clearancejobs']['keywords']}`")
                            st.caption(queries['clearancejobs']['reasoning'])
                        else:
                            st.caption("❌ Not relevant for this query")

                    with col_s2:
                        st.markdown("**📸 DVIDS**")
                        if queries['dvids']['relevant']:
                            st.markdown(f"Keywords: `{queries['dvids']['keywords']}`")
                            st.caption(queries['dvids']['reasoning'])
                        else:
                            st.caption("❌ Not relevant for this query")

                    with col_s3:
                        st.markdown("**📋 SAM.gov**")
                        if queries['sam_gov']['relevant']:
                            st.markdown(f"Keywords: `{queries['sam_gov']['keywords']}`")
                            st.caption(queries['sam_gov']['reasoning'])
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
