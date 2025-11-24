#!/usr/bin/env python3
"""
SigInt Research Platform - Minimal Clean UI
Simplified 2-tab interface focusing on core functionality.
"""

import streamlit as st
import sys
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add ClearanceJobs to path (legacy requirement)
sys.path.insert(0, 'ClearanceJobs')

# Page configuration
st.set_page_config(
    page_title="SigInt Research Platform",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Simple, clean CSS
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
</style>
""", unsafe_allow_html=True)

# Header
st.markdown('<div class="main-header">🔍 SigInt Research Platform</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">AI-powered investigative research across government, military, and social sources</div>', unsafe_allow_html=True)

# Sidebar - API Configuration
with st.sidebar:
    st.header("⚙️ Configuration")

    # OpenAI API Key
    with st.expander("🔑 API Keys", expanded=False):
        st.caption("Configure API keys for research")

        # Try secrets first, then env, then allow UI override
        openai_default = ""
        try:
            if hasattr(st, 'secrets') and "OPENAI_API_KEY" in st.secrets:
                openai_default = st.secrets["OPENAI_API_KEY"]
        except:
            pass
        if not openai_default:
            openai_default = os.getenv("OPENAI_API_KEY", "")

        openai_api_key = st.text_input(
            "OpenAI API Key",
            value=openai_default if openai_default else "",
            type="password",
            help="Required for deep research. Get at platform.openai.com/api-keys"
        )

        # Anthropic API Key
        anthropic_default = ""
        try:
            if hasattr(st, 'secrets') and "ANTHROPIC_API_KEY" in st.secrets:
                anthropic_default = st.secrets["ANTHROPIC_API_KEY"]
        except:
            pass
        if not anthropic_default:
            anthropic_default = os.getenv("ANTHROPIC_API_KEY", "")

        anthropic_api_key = st.text_input(
            "Anthropic API Key (Optional)",
            value=anthropic_default if anthropic_default else "",
            type="password",
            help="Alternative to OpenAI. Get at console.anthropic.com"
        )

        # Google API Key
        google_default = ""
        try:
            if hasattr(st, 'secrets') and "GOOGLE_API_KEY" in st.secrets:
                google_default = st.secrets["GOOGLE_API_KEY"]
        except:
            pass
        if not google_default:
            google_default = os.getenv("GOOGLE_API_KEY", "")

        google_api_key = st.text_input(
            "Google API Key (Optional)",
            value=google_default if google_default else "",
            type="password",
            help="For Gemini models. Get at ai.google.dev"
        )

    # Source status
    st.header("📊 Available Sources")

    # Check which sources are configured
    sources_status = []

    # Government sources
    if os.getenv("SAM_API_KEY"):
        sources_status.append("✅ SAM.gov - Contracts")
    if os.getenv("DVIDS_API_KEY"):
        sources_status.append("✅ DVIDS - Military Media")
    if os.getenv("USAJOBS_API_KEY"):
        sources_status.append("✅ USAJobs - Federal Jobs")

    # Social sources
    if os.getenv("DISCORD_TOKEN"):
        sources_status.append("✅ Discord - OSINT Communities")
    if os.getenv("REDDIT_CLIENT_ID"):
        sources_status.append("✅ Reddit - Defense Discussions")
    if os.getenv("TWITTER_BEARER_TOKEN"):
        sources_status.append("✅ Twitter - Breaking News")

    # Web sources
    if os.getenv("BRAVE_API_KEY"):
        sources_status.append("✅ Brave Search - Web")

    # Always available
    sources_status.append("✅ ClearanceJobs - Security Jobs")

    for source in sources_status:
        st.caption(source)

    if len(sources_status) < 3:
        st.warning("⚠️ Limited sources configured. Add API keys in .env for better coverage.")

# Main interface - 2 tabs
tab1, tab2 = st.tabs([
    "📖 User Guide",
    "🔬 Deep Research"
])

# Tab 1: User Guide
with tab1:
    from user_guide import render_user_guide_tab
    render_user_guide_tab()

# Tab 2: Deep Research
with tab2:
    # Determine which API key to use
    api_key_to_use = openai_api_key or anthropic_api_key or google_api_key

    if not api_key_to_use:
        st.error("⚠️ **No LLM API key configured**")
        st.info("""
        Deep Research requires an LLM API key. Configure one of:
        - OpenAI (GPT-4, GPT-4o, GPT-4o-mini)
        - Anthropic (Claude 3.5 Sonnet)
        - Google (Gemini 1.5 Pro/Flash)

        Add your key in the sidebar or in your .env file.
        """)
    else:
        # Render deep research interface
        from deep_research_tab import render_deep_research_tab
        render_deep_research_tab(api_key_to_use)

# Footer
st.markdown("---")
st.caption("🔍 SigInt Research Platform | Built for investigative journalism")
