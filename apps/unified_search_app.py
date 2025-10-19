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
    page_title="Unified Search - ClearanceJobs, DVIDS & SAM.gov",
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
st.markdown('<div class="main-header">🔍 Unified Multi-Source Search</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Search across ClearanceJobs, DVIDS, and SAM.gov from a single interface</div>', unsafe_allow_html=True)

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

    with st.expander("⚙️ Search Settings", expanded=False):
        results_per_page = st.slider("Results per page", 10, 100, 25, 5)
        enable_rate_limiting = st.checkbox("Rate limiting", value=True,
                                          help="Adds 1s delay between searches")

    st.markdown("---")
    st.markdown("### 📊 Available Sources")
    st.markdown("✅ **ClearanceJobs** - No auth required")
    st.markdown(f"{'✅' if dvids_api_key else '⚠️'} **DVIDS** - API key {'configured' if dvids_api_key else 'needed'}")
    st.markdown(f"{'✅' if sam_api_key else '⚠️'} **SAM.gov** - API key {'configured' if sam_api_key else 'needed'}")

    # Rate limit tracking stats
    with st.expander("📈 API Usage Stats", expanded=False):
        try:
            from api_request_tracker import get_request_stats
            from pathlib import Path

            log_file = Path("api_requests.jsonl")

            if log_file.exists():
                stats = get_request_stats(hours=24)

                st.caption("Last 24 hours")

                if stats.get("total_requests", 0) > 0:
                    st.metric("Total Requests", stats["total_requests"])
                    st.metric("Rate Limit Hits", stats["rate_limit_hits"],
                             delta=None if stats["rate_limit_hits"] == 0 else "⚠️",
                             delta_color="off" if stats["rate_limit_hits"] == 0 else "inverse")

                    for api, api_stats in stats.get("apis", {}).items():
                        st.markdown(f"**{api}**")
                        cols = st.columns(3)
                        with cols[0]:
                            st.caption(f"Requests: {api_stats['total_requests']}")
                        with cols[1]:
                            st.caption(f"429 Errors: {api_stats['rate_limit_hits']}")
                        with cols[2]:
                            success_pct = f"{api_stats['success_rate']*100:.0f}%"
                            st.caption(f"Success: {success_pct}")

                        if api_stats['rate_limit_timestamps']:
                            st.warning(f"⚠️ Rate limited at: {api_stats['rate_limit_timestamps'][-1]}")
                else:
                    st.info("No API requests logged yet")
            else:
                st.info("No API requests logged yet. Use the app and stats will appear here.")
        except Exception as e:
            st.caption(f"Stats unavailable: {str(e)}")

# Create tabs
tab1, tab2, tab3, tab4 = st.tabs([
    "🏢 ClearanceJobs (Jobs)",
    "📸 DVIDS (Media)",
    "📋 SAM.gov (Contracts)",
    "🤖 AI Research"
])

# ============================================================================
# TAB 1: CLEARANCEJOBS
# ============================================================================
with tab1:
    from clearancejobs_search import render_clearancejobs_tab
    render_clearancejobs_tab(results_per_page, enable_rate_limiting)

# ============================================================================
# TAB 2: DVIDS
# ============================================================================
with tab2:
    from dvids_search import render_dvids_tab
    render_dvids_tab(dvids_api_key, results_per_page, enable_rate_limiting)

# ============================================================================
# TAB 3: SAM.GOV
# ============================================================================
with tab3:
    from sam_search import render_sam_tab
    render_sam_tab(sam_api_key, results_per_page, enable_rate_limiting)

# ============================================================================
# TAB 4: AI RESEARCH
# ============================================================================
with tab4:
    from ai_research import render_ai_research_tab
    render_ai_research_tab(openai_api_key, dvids_api_key, sam_api_key)

# Footer
st.markdown("---")
col_f1, col_f2, col_f3 = st.columns(3)
with col_f1:
    st.caption("📖 [User Guide](README_UNIFIED_APP.md)")
with col_f2:
    st.caption("🔧 [Technical Docs](INTEGRATION_ANALYSIS.md)")
with col_f3:
    st.caption("⚠️ Respect API limits and terms of service")
