#!/usr/bin/env python3
"""User Guide Tab - Non-technical documentation for team members."""

import streamlit as st


def render_user_guide_tab():
    """Render the User Guide tab with organized documentation."""

    st.markdown("# 📖 User Guide")
    st.markdown("**Welcome!** This guide will help you get started with the Multi-Source Intelligence Research Platform.")

    st.markdown("---")

    # ========================================================================
    # QUICK START
    # ========================================================================
    st.markdown("## 🚀 Quick Start")

    with st.expander("🎯 What Can This Tool Do?", expanded=True):
        st.markdown("""
        This platform helps you research information across multiple government and job databases **simultaneously**.

        **Key Features:**

        1. **⚡ Quick Search** - Ask questions in plain English, get answers from multiple databases at once
        2. **🔬 Deep Investigation** - Complex multi-part research with autonomous task decomposition
        3. **📊 Monitor Management** - Set up alerts that email you when new information appears

        **What Makes This Different:**
        - Instead of searching multiple websites separately, ask ONE question and get ALL results
        - AI understands your question and automatically creates the right searches
        - Get daily email alerts for ongoing investigations
        """)

        st.info("💡 **Tip:** Most users should start with Quick Search. It's the easiest and most powerful way to find information.")

    # ========================================================================
    # HOW TO USE
    # ========================================================================
    st.markdown("---")
    st.markdown("## 📚 How to Use Each Feature")

    with st.expander("⚡ Quick Search - Ask Questions, Get Answers"):
        st.markdown("""
        **What It Does:**
        - You ask a question in plain English
        - AI automatically searches multiple databases for you
        - You get a summary + detailed results in 10-20 seconds

        **Good Questions to Ask:**
        - "What intelligence analyst jobs require TS/SCI clearance?"
        - "Find contracts related to cyber threat detection in the last 2 months"
        - "What are the latest developments in AI security across government jobs and contracts?"
        - "Show me special operations content from DVIDS in the Middle East"

        **Bad Questions (Too Vague):**
        - "Jobs" (be specific: what kind of jobs?)
        - "Security stuff" (what aspect of security?)

        **How It Works:**
        1. Go to the **⚡ Quick Search** tab
        2. Type your question in the text box
        3. Click **🚀 Research**
        4. Wait 10-20 seconds while AI searches databases in parallel
        5. Review summary and detailed results
        6. Download CSV exports if needed

        **Pro Tips:**
        - ✅ Be specific about what you're looking for
        - ✅ Mention timeframes if relevant ("last 2 months", "recent")
        - ✅ Include key requirements (clearance level, location, skills)
        - ❌ Don't use yes/no questions
        - ❌ Don't ask for analysis the databases can't provide
        """)

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Example: Good Question**")
            st.code("""
What cybersecurity positions requiring
Top Secret clearance are available in
the DC area, and what related government
contracts exist?
            """, language=None)

        with col2:
            st.markdown("**What You'll Get:**")
            st.markdown("""
            - Summary of findings
            - ClearanceJobs postings
            - USAJobs federal positions
            - SAM.gov contract opportunities
            - Related DVIDS media
            """)

    with st.expander("🔬 Deep Investigation - Complex Research"):
        st.markdown("""
        **What It Does:**
        - Autonomous multi-step research for complex questions
        - Breaks questions into subtasks automatically
        - Iterates and refines searches based on findings
        - Tracks entity relationships across results
        - Takes 5-30 minutes depending on complexity

        **When to Use:**
        - Complex, multi-part questions that need thorough investigation
        - When you want to explore connections between entities
        - Research that benefits from iterative refinement
        - When Quick Search isn't thorough enough

        **Examples:**
        - "What is the relationship between JSOC and CIA Title 50 operations?"
        - "How do government surveillance programs use AI, and who are their contractors?"
        - "Analyze the network of defense contractors working on cyber threat detection"

        **How It Works:**
        1. Go to the **🔬 Deep Investigation** tab
        2. Enter your complex research question
        3. Adjust settings (max tasks, time limit, concurrency)
        4. Click **Start Investigation**
        5. Watch real-time progress as tasks execute in parallel
        6. Review comprehensive report with entity network

        **Settings Explained:**
        - **Max Tasks:** How many subtasks to execute (default: 15)
        - **Max Retries:** How many times to retry failed queries (default: 2)
        - **Time Limit:** Maximum investigation duration (default: 120 minutes)
        - **Min Results:** Minimum results per task to succeed (default: 3)

        **What You Get:**
        - Executive summary of findings
        - Detailed analysis with connections between entities
        - Entity relationship network
        - Source attribution
        - Full methodology breakdown
        """)

    with st.expander("📊 Monitor Management - Set Up Alerts"):
        st.markdown("""
        **What It Does:**
        - Automatically searches for keywords on a schedule (daily, every 6 hours, etc.)
        - Emails you when NEW results appear (no duplicate spam)
        - Tracks results over time

        **Use Cases:**
        - Track ongoing investigations
        - Monitor specific contracts or programs
        - Get alerts for new job postings
        - Watch for mentions of organizations or technologies

        **How to Create a Monitor:**

        1. **Go to 📊 Monitor Management tab**
        2. **Click "➕ Create Monitor" sub-tab**
        3. **Fill out the form:**
           - **Name:** "Surveillance Programs Monitor"
           - **Keywords:** (one per line)
             ```
             Section 702
             FISA Court
             NSA surveillance
             ```
           - **Sources:** Select which databases to search
           - **Schedule:** How often to run (e.g., "daily 06:00")
           - **Alert Email:** Where to send results
        4. **Click "Create Monitor"**
        5. **Test it:** Click "▶️ Run Now" in Active Monitors tab

        **What Happens:**
        - Monitor runs automatically on your schedule
        - First run: Sends all results it finds
        - Future runs: Only sends NEW results (no duplicates)
        - You get an email with links to view full content

        **Example Workflow:**
        - **Day 1:** Monitor finds 10 results → Emails you all 10
        - **Day 2:** Monitor finds 12 results → Emails only the 2 new ones
        - **Day 3:** Monitor finds 12 results → No email (all seen before)
        """)

        st.info("💡 **Tip:** Start with a test monitor and click 'Run Now' to see results immediately. Then adjust keywords if needed.")

    with st.expander("⚙️ Advanced Search - Search Individual Sources"):
        st.markdown("""
        **What It Does:**
        - Direct access to each database with all available filters
        - More control than Quick Search
        - Useful when you know exactly what filters you need

        **When to Use:**
        - You need very specific filters (e.g., NAICS codes for contracts)
        - You want to explore one database in depth
        - Quick Search isn't giving you the right results

        **Available Sources:**

        **🏢 ClearanceJobs** - Security clearance job postings
        - Filter by clearance level (TS/SCI, Secret, Top Secret)
        - Filter by when posted (last 7 days, 30 days, etc.)
        - Keywords for job title or description

        **📸 DVIDS** - Military media (photos, videos, news)
        - Search military photos, videos, and news articles
        - Filter by date range
        - Useful for visual intelligence gathering

        **📋 SAM.gov** - Government contract opportunities
        - Search active contracts and RFPs
        - Filter by date posted
        - Filter by NAICS codes (industry categories)

        **💼 USAJobs** - Federal government job postings
        - Search federal civil service positions
        - Filter by pay grade (GS-9, GS-12, etc.)
        - Filter by date posted
        """)

        st.warning("⚠️ **Most users don't need this!** Quick Search is easier and searches everything at once.")

    # ========================================================================
    # UNDERSTANDING THE DATA
    # ========================================================================
    st.markdown("---")
    st.markdown("## 🗂️ Understanding the Data Sources")

    with st.expander("🏢 ClearanceJobs"):
        st.markdown("""
        Job board for security clearance positions (Secret, Top Secret, TS/SCI). Defense contractors and government agencies. Updated daily.

        **Query Parameters:**
        - `keywords`: Job title/description search terms
        """)

    with st.expander("📸 DVIDS"):
        st.markdown("""
        Official military media: photos, videos, news articles. Combat operations, training exercises, deployments. Updated multiple times daily. Use broad keywords (e.g., "special operations" not specific unit names).

        **Query Parameters:**
        - `keywords`: Search terms (use OR for alternatives)
        - `media_types`: image, video, news
        - `branches`: Army, Navy, Air Force, Marines, Coast Guard, Joint
        - `country`: Country name filter
        - `from_date`, `to_date`: Date range (YYYY-MM-DD)
        """)

    with st.expander("📋 SAM.gov"):
        st.markdown("""
        Official government contracting database. Contract opportunities (RFPs, RFQs), grants, active awards. Updated daily. Has strict rate limits—use monitors for ongoing tracking.

        **Query Parameters:**
        - `keywords`: Search terms (max ~200 chars)
        - `procurement_types`: Solicitation, Presolicitation, Combined Synopsis/Solicitation, Sources Sought
        - `set_aside`: Small business types (SBA, 8A, SDVOSBC, WOSB, HZC)
        - `naics_codes`: Industry codes (e.g., 541512=Computer Systems Design)
        - `organization`: Agency name (e.g., "Department of Defense")
        - `date_range_days`: Days back to search (1-364)
        """)

    with st.expander("💼 USAJobs"):
        st.markdown("""
        Official federal civil service jobs (GS scale). All agencies, competitive service, internships. Direct government employment (vs. ClearanceJobs contractors). Strict qualification requirements.

        **Query Parameters:**
        - `keywords`: Job title/description (1-3 simple terms, no OR operators)
        - `location`: Geographic location (e.g., "Washington, DC", "Remote")
        - `organization`: Agency name (e.g., "FBI", "NASA")
        - `pay_grade_low`, `pay_grade_high`: GS pay grade range (1-15)
        """)

    with st.expander("🗄️ FBI Vault"):
        st.markdown("""
        FBI's Freedom of Information Act (FOIA) library. Declassified documents, investigations, and records. Historical cases, notable individuals, and FBI operations. Updated as documents are declassified.

        **Query Parameters:**
        - `keywords`: Search terms for document titles and content
        - `limit`: Number of results to return
        """)

    with st.expander("💬 Discord"):
        st.markdown("""
        OSINT Discord servers: The OWL, Bellingcat. Messages archived and searchable. Track specific users across servers. More servers will be added.

        **Query Parameters:**
        - `keywords`: Message content search
        - `user`: Specific user tracking
        - `channel`: Channel filter
        - `server`: Server filter
        - `date_range`: Time period
        """)

    with st.expander("🐦 Twitter & Social Media"):
        st.markdown("""
        User tracking and monitoring. Important accounts identified and stored. Search by user, keyword, or topic. Additional platforms will be added.

        **Query Parameters:**
        - `keywords`: Tweet/post content search
        - `user`: Specific account tracking
        - `hashtag`: Hashtag filter
        - `date_range`: Time period
        - `media_type`: text, image, video
        """)
