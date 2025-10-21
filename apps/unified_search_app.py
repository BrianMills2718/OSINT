#!/usr/bin/env python3
"""
Unified Multi-Source Search Application - Improved UX Version
Integrates ClearanceJobs, DVIDS, and SAM.gov APIs
"""

import streamlit as st
import sys
import os
from dotenv import load_dotenv

# Load environment variables from .env file (for local development)
load_dotenv()

# Add ClearanceJobs to path
sys.path.insert(0, 'ClearanceJobs')

# Page config
st.set_page_config(
    page_title="Multi-Source Intelligence Research Platform",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better UX
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.1rem;
        color: #666;
        margin-bottom: 2rem;
    }
    .quick-search {
        background: #f0f8ff;
        padding: 1.5rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
        margin-bottom: 2rem;
    }
    .info-box {
        background: #fff3cd;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #ffc107;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown('<div class="main-header">🔍 Multi-Source Intelligence Research</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">AI-powered search across government databases, contracts, jobs, and military media</div>', unsafe_allow_html=True)

# Sidebar configuration
with st.sidebar:
    st.header("⚙️ Configuration")

    with st.expander("🔑 API Keys", expanded=False):
        st.caption("Optional: Enter API keys here or configure in Streamlit secrets")

        # OpenAI API Key - check secrets first, then env, then allow UI override
        openai_default = ""
        try:
            if hasattr(st, 'secrets') and "OPENAI_API_KEY" in st.secrets:
                openai_default = st.secrets["OPENAI_API_KEY"]
        except:
            pass
        if not openai_default:
            openai_default = os.getenv("OPENAI_API_KEY", "")

        openai_api_key = st.text_input(
            "OpenAI API Key (for AI Research)",
            value=openai_default if openai_default else "",
            type="password",
            help="Required for AI Research tab. Get at platform.openai.com/api-keys"
        )

        # DVIDS API Key - check secrets first, then env, then default to demo key
        dvids_default = "key-68f319e8dc377"  # Public demo key
        try:
            if hasattr(st, 'secrets') and "DVIDS_API_KEY" in st.secrets:
                dvids_default = st.secrets["DVIDS_API_KEY"]
        except:
            pass
        if dvids_default == "key-68f319e8dc377":  # Still using demo key
            env_key = os.getenv("DVIDS_API_KEY", "")
            if env_key:
                dvids_default = env_key

        dvids_api_key = st.text_input(
            "DVIDS API Key",
            value=dvids_default,
            type="password",
            help="Get your key at dvidshub.net"
        )

        # SAM.gov API Key - check secrets first, then env, then allow UI override
        sam_default = ""
        try:
            if hasattr(st, 'secrets') and "SAM_GOV_API_KEY" in st.secrets:
                sam_default = st.secrets["SAM_GOV_API_KEY"]
        except:
            pass
        if not sam_default:
            sam_default = os.getenv("SAM_GOV_API_KEY", "")

        sam_api_key = st.text_input(
            "SAM.gov API Key",
            value=sam_default if sam_default else "",
            type="password",
            help="Get your key at sam.gov → Account Details"
        )

        # RapidAPI Key (for Twitter) - check secrets first, then env
        rapidapi_default = ""
        try:
            if hasattr(st, 'secrets') and "RAPIDAPI_KEY" in st.secrets:
                rapidapi_default = st.secrets["RAPIDAPI_KEY"]
        except:
            pass
        if not rapidapi_default:
            rapidapi_default = os.getenv("RAPIDAPI_KEY", "")

        rapidapi_key = st.text_input(
            "RapidAPI Key (for Twitter)",
            value=rapidapi_default if rapidapi_default else "",
            type="password",
            help="Get your key at rapidapi.com (used for Twitter search)"
        )

    with st.expander("⚙️ Search Settings", expanded=False):
        results_per_page = st.slider("Results per page", 10, 100, 25, 5)
        enable_rate_limiting = st.checkbox("Rate limiting", value=True,
                                          help="Adds 1s delay between searches")

    # USAJobs API Key - check secrets first, then env
    usajobs_default = ""
    try:
        if hasattr(st, 'secrets') and "USAJOBS_API_KEY" in st.secrets:
            usajobs_default = st.secrets["USAJOBS_API_KEY"]
    except:
        pass
    if not usajobs_default:
        usajobs_default = os.getenv("USAJOBS_API_KEY", "")

    usajobs_api_key = st.text_input(
        "USAJobs API Key",
        value=usajobs_default if usajobs_default else "",
        type="password",
        help="Get your key at developer.usajobs.gov"
    )

    st.markdown("---")
    st.markdown("### 📊 Available Sources")
    st.markdown("✅ **ClearanceJobs** - No auth required")
    st.markdown(f"{'✅' if dvids_api_key else '⚠️'} **DVIDS** - API key {'configured' if dvids_api_key else 'needed'}")
    st.markdown(f"{'✅' if sam_api_key else '⚠️'} **SAM.gov** - API key {'configured' if sam_api_key else 'needed'}")
    st.markdown(f"{'✅' if usajobs_api_key else '⚠️'} **USAJobs** - API key {'configured' if usajobs_api_key else 'needed'}")
    st.markdown(f"{'✅' if rapidapi_key else '⚠️'} **Twitter** - API key {'configured' if rapidapi_key else 'needed'}")

    # Rate limit tracking stats
    with st.expander("📈 API Usage Stats", expanded=False):
        try:
            from core.api_request_tracker import get_request_stats
            from pathlib import Path

            log_file = Path("api_requests.jsonl")

            if log_file.exists():
                stats = get_request_stats(hours=24)

                st.caption("Last 24 hours")

                if stats.get("total_requests", 0) > 0:
                    col_m1, col_m2, col_m3 = st.columns(3)
                    with col_m1:
                        st.metric("Total Requests", stats["total_requests"])
                    with col_m2:
                        st.metric("Successful", stats.get("successful_requests", 0))
                    with col_m3:
                        st.metric("Failed", stats.get("failed_requests", 0),
                                 delta=None if stats.get("failed_requests", 0) == 0 else "⚠️",
                                 delta_color="off" if stats.get("failed_requests", 0) == 0 else "inverse")

                    for api, api_stats in stats.get("apis", {}).items():
                        st.markdown(f"**{api}**")
                        cols = st.columns(4)
                        with cols[0]:
                            st.caption(f"Total: {api_stats['total_requests']}")
                        with cols[1]:
                            st.caption(f"✅ Success: {api_stats.get('successful_requests', 0)}")
                        with cols[2]:
                            st.caption(f"❌ Failed: {api_stats.get('failed_requests', 0)}")
                        with cols[3]:
                            success_pct = f"{api_stats['success_rate']*100:.0f}%"
                            st.caption(f"Rate: {success_pct}")

                        # Show specific error types
                        if api_stats['rate_limit_hits'] > 0:
                            st.warning(f"⚠️ Rate limits (429): {api_stats['rate_limit_hits']} - Last: {api_stats['rate_limit_timestamps'][-1]}")

                        if api_stats.get('status_0_errors', 0) > 0:
                            st.error(f"❌ Status 0 errors: {api_stats['status_0_errors']} (timeouts/connection errors) - Last: {api_stats.get('status_0_timestamps', ['N/A'])[-1]}")
                else:
                    st.info("No API requests logged yet")
            else:
                st.info("No API requests logged yet. Use the app and stats will appear here.")
        except Exception as e:
            st.caption(f"Stats unavailable: {str(e)}")

# Create main tabs - New UX with User Guide first, then primary features
tab1, tab2, tab3, tab4 = st.tabs([
    "📖 User Guide",
    "🤖 AI Research",
    "📊 Monitor Management",
    "⚙️ Advanced Search"
])

# ============================================================================
# TAB 1: USER GUIDE
# ============================================================================
with tab1:
    from user_guide import render_user_guide_tab
    render_user_guide_tab()

# ============================================================================
# TAB 2: AI RESEARCH (PRIMARY INTERFACE)
# ============================================================================
with tab2:
    from ai_research import render_ai_research_tab
    render_ai_research_tab(openai_api_key, dvids_api_key, sam_api_key, usajobs_api_key, rapidapi_key)

# ============================================================================
# TAB 3: MONITOR MANAGEMENT
# ============================================================================
with tab3:
    from monitor_management import render_monitor_management_tab
    render_monitor_management_tab()

# ============================================================================
# TAB 4: ADVANCED SEARCH (NESTED TABS FOR INDIVIDUAL SOURCES)
# ============================================================================
with tab4:
    st.markdown("### ⚙️ Advanced Search - Individual Data Sources")
    st.caption("Search individual sources directly with custom filters (for advanced users)")

    st.info("💡 **New to this tool?** Most users should use the **🤖 AI Research** tab instead - it searches all sources automatically and is much easier!")

    st.markdown("---")

    # Nested tabs for individual sources
    subtab1, subtab2, subtab3, subtab4 = st.tabs([
        "🏢 ClearanceJobs",
        "📸 DVIDS",
        "📋 SAM.gov",
        "💼 USAJobs"
    ])

    with subtab1:
        from clearancejobs_search import render_clearancejobs_tab
        render_clearancejobs_tab(results_per_page, enable_rate_limiting)

    with subtab2:
        from dvids_search import render_dvids_tab
        render_dvids_tab(dvids_api_key, results_per_page, enable_rate_limiting)

    with subtab3:
        from sam_search import render_sam_tab
        render_sam_tab(sam_api_key, results_per_page, enable_rate_limiting)

    with subtab4:
        st.markdown("### 💼 Federal Job Opportunities")
        st.caption("Search federal government jobs on USAJobs.gov • API key required")

        if not usajobs_api_key:
            st.warning("⚠️ **API Key Required** - Please add your USAJobs API key in the sidebar")
            st.info("🔑 Get your free API key at: https://developer.usajobs.gov/APIRequest/Index")
        else:
            st.info("🚧 **USAJobs individual search UI coming soon!** For now, use the AI Research tab which includes USAJobs in multi-source search.")
            st.markdown("""
            **USAJobs is already integrated** in the backend and works through:
            - The **🤖 AI Research tab** (multi-source intelligent search) - RECOMMENDED
            - Direct API calls via Python

            A dedicated USAJobs search interface is planned for a future update.
            """)

# Footer
st.markdown("---")
col_f1, col_f2, col_f3 = st.columns(3)
with col_f1:
    st.caption("💡 **New?** Check the User Guide tab for tutorials and FAQs")
with col_f2:
    st.caption("🤖 **Recommended:** Start with AI Research for best results")
with col_f3:
    st.caption("⚠️ Respect API limits and terms of service")
