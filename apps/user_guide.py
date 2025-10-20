#!/usr/bin/env python3
"""User Guide Tab - Non-technical documentation and FAQ for team members."""

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

        1. **🤖 AI Research** - Ask questions in plain English, get answers from 4 databases at once
        2. **📊 Automated Monitoring** - Set up alerts that email you when new information appears
        3. **⚙️ Advanced Search** - Search individual databases with specific filters

        **What Makes This Different:**
        - Instead of searching 4 websites separately, ask ONE question and get ALL results
        - AI understands your question and automatically creates the right searches
        - Get daily email alerts for ongoing investigations
        """)

        st.info("💡 **Tip:** Most users should start with the AI Research tab. It's the easiest and most powerful way to find information.")

    with st.expander("🔑 Setting Up Your API Keys"):
        st.markdown("""
        Some data sources require free API keys. Here's how to get them:

        **Required for AI Research:**
        - **OpenAI** - Powers the AI assistant
          - Get it at: https://platform.openai.com/api-keys
          - Cost: ~$0.01-0.05 per search (very cheap)
          - Add to sidebar under "API Keys"

        **Required for Data Sources:**
        - **DVIDS** (Military Media) - Free
          - Get it at: https://www.dvidshub.net/
          - No cost, unlimited use

        - **SAM.gov** (Government Contracts) - Free
          - Get it at: https://sam.gov/content/home (Account Details → API Key)
          - No cost, but has rate limits

        - **USAJobs** (Federal Jobs) - Free
          - Get it at: https://developer.usajobs.gov/APIRequest/Index
          - No cost, unlimited use

        **Not Required:**
        - **ClearanceJobs** - No API key needed (works automatically)
        """)

        st.success("✅ Enter your API keys in the sidebar under '🔑 API Keys'")

    with st.expander("⚡ 5-Minute Tutorial"):
        st.markdown("""
        **Let's find cybersecurity jobs and contracts in one search:**

        1. **Get your OpenAI API key** (see section above)
        2. **Go to the 🤖 AI Research tab**
        3. **Type this question:**
           ```
           What cybersecurity jobs and government contracts are available
           for cleared professionals working on threat intelligence?
           ```
        4. **Click "🚀 Research"**
        5. **Wait 10-20 seconds** while the AI:
           - Analyzes your question
           - Searches 4 databases in parallel
           - Summarizes all findings

        **You'll get:**
        - A written summary answering your question
        - Job postings from ClearanceJobs and USAJobs
        - Contract opportunities from SAM.gov
        - Related military media from DVIDS
        - Download buttons for CSV exports
        """)

        st.warning("⏱️ **Be Patient:** The first search takes 15-30 seconds. This is normal - we're searching 4 databases and running AI analysis!")

    # ========================================================================
    # HOW TO USE
    # ========================================================================
    st.markdown("---")
    st.markdown("## 📚 How to Use Each Feature")

    with st.expander("🤖 AI Research - Ask Questions, Get Answers"):
        st.markdown("""
        **What It Does:**
        - You ask a question in plain English
        - AI automatically searches 4 databases for you
        - You get a summary + detailed results

        **Good Questions to Ask:**
        - "What intelligence analyst jobs require TS/SCI clearance?"
        - "Find contracts related to cyber threat detection in the last 2 months"
        - "What are the latest developments in AI security across government jobs and contracts?"
        - "Show me special operations content from DVIDS in the Middle East"

        **Bad Questions (Too Vague):**
        - "Jobs" (be specific: what kind of jobs?)
        - "Security stuff" (what aspect of security?)

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
        """)

        st.info("💡 **Tip:** Start with a test monitor and click 'Run Now' to see results immediately. Then adjust keywords if needed.")

    with st.expander("⚙️ Advanced Search - Search Individual Sources"):
        st.markdown("""
        **What It Does:**
        - Direct access to each database with all available filters
        - More control than AI Research
        - Useful when you know exactly what filters you need

        **When to Use:**
        - You need very specific filters (e.g., NAICS codes for contracts)
        - You want to explore one database in depth
        - AI Research isn't giving you the right results

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

        st.warning("⚠️ **Most users don't need this!** The AI Research tab is easier and searches everything at once.")

    # ========================================================================
    # UNDERSTANDING THE DATA
    # ========================================================================
    st.markdown("---")
    st.markdown("## 🗂️ Understanding the Data Sources")

    with st.expander("🏢 ClearanceJobs - What is it?"):
        st.markdown("""
        **What:** Job board for positions requiring security clearances

        **Who uses it:** Defense contractors, intelligence agencies, cleared professionals

        **What you'll find:**
        - Jobs requiring Secret, Top Secret, TS/SCI clearances
        - Cybersecurity, intelligence analysis, engineering positions
        - Defense contractor and government agency roles

        **Data quality:** ⭐⭐⭐⭐⭐ (5/5)
        - Very comprehensive for cleared positions
        - Updated daily
        - Includes salary ranges and detailed requirements

        **Example results:**
        - "Senior Cyber Threat Analyst - TS/SCI required"
        - "Intelligence Operations Specialist - DC Metro Area"
        - "Systems Engineer - Active Top Secret Clearance"
        """)

    with st.expander("📸 DVIDS - What is it?"):
        st.markdown("""
        **What:** Defense Visual Information Distribution Service - Official military media

        **Who uses it:** Military public affairs, journalists, researchers

        **What you'll find:**
        - Official military photos, videos, news articles
        - Combat operations, training exercises, deployments
        - Press releases from DoD and military branches

        **Data quality:** ⭐⭐⭐⭐ (4/5)
        - Official, verified content only
        - Updated multiple times daily
        - Sometimes limited by operational security (can't show everything)

        **Example results:**
        - Photos from special operations training
        - Videos of Navy ship deployments
        - News articles about military exercises

        **Pro Tip:** Use broad keywords like "special operations" instead of specific unit names (which may be classified)
        """)

    with st.expander("📋 SAM.gov - What is it?"):
        st.markdown("""
        **What:** System for Award Management - Official U.S. government contracting database

        **Who uses it:** Government contractors, grant seekers, procurement officers

        **What you'll find:**
        - Contract opportunities (RFPs, RFQs, sources sought)
        - Grant opportunities
        - Active contracts and awards

        **Data quality:** ⭐⭐⭐⭐⭐ (5/5)
        - Official government source
        - Comprehensive and legally required postings
        - Updated daily

        **Limitations:**
        - Rate limits (too many searches = temporary block)
        - Sometimes slow to respond

        **Example results:**
        - "Cybersecurity Services for DHS - $5M contract"
        - "Intelligence Analysis Support - DoD RFP"
        - "Threat Detection Software - Sources Sought Notice"

        **Pro Tip:** Use the monitor feature for ongoing contract tracking - SAM.gov has strict rate limits for frequent searches
        """)

    with st.expander("💼 USAJobs - What is it?"):
        st.markdown("""
        **What:** Official job site for U.S. federal government civil service positions

        **Who uses it:** Anyone seeking federal employment (GS scale jobs)

        **What you'll find:**
        - Federal civil service positions across all agencies
        - Competitive service jobs (open to public)
        - Some excepted service positions
        - Internships and entry-level programs

        **Data quality:** ⭐⭐⭐⭐⭐ (5/5)
        - Official source for all federal jobs
        - Comprehensive job descriptions
        - Shows pay grades, locations, requirements

        **Different from ClearanceJobs:**
        - ClearanceJobs = mostly contractors
        - USAJobs = direct federal employment
        - Both can require clearances

        **Example results:**
        - "Intelligence Analyst (GS-12) - FBI"
        - "Cybersecurity Specialist (GS-13) - DHS"
        - "Foreign Affairs Officer (GS-9/11) - State Department"

        **Pro Tip:** Federal jobs have strict qualification requirements - read the "Qualifications" section carefully
        """)

    # ========================================================================
    # FAQ
    # ========================================================================
    st.markdown("---")
    st.markdown("## ❓ Frequently Asked Questions")

    with st.expander("How do I write a good research question?"):
        st.markdown("""
        **Good questions are:**
        - ✅ Specific and detailed
        - ✅ Action-oriented (finding, analyzing, tracking)
        - ✅ Focused on what these databases contain

        **Examples:**

        **Good:**
        - "What intelligence analyst positions requiring TS/SCI are available in Virginia?"
        - "Find government contracts related to artificial intelligence security from the last 60 days"
        - "Show me DVIDS content about cyber warfare exercises"

        **Bad:**
        - "Jobs" (too vague)
        - "Tell me about cybersecurity" (databases contain jobs/contracts, not articles)
        - "Is AI security important?" (yes/no question)

        **Template:**
        ```
        [Action] + [Topic] + [Filters/Requirements]

        Find + cybersecurity contracts + from last 2 months in DC area
        ```
        """)

    with st.expander("What's the difference between AI Research and Advanced Search?"):
        st.markdown("""
        **AI Research (🤖):**
        - Ask questions in plain English
        - Searches ALL 4 databases automatically
        - AI decides which databases to use and what filters to apply
        - Best for: Exploratory research, broad questions, multiple sources
        - Example: "What jobs and contracts exist for cyber threat analysts?"

        **Advanced Search (⚙️):**
        - Search ONE database at a time
        - You manually set all filters
        - More control, but more work
        - Best for: When you know exactly what you want from one specific source
        - Example: Searching only SAM.gov for contracts with NAICS code 541512

        **Which should I use?**
        - 90% of the time → Use AI Research
        - Only use Advanced Search if AI Research isn't giving you what you need
        """)

    with st.expander("How do monitors work?"):
        st.markdown("""
        **Monitors automatically search for you on a schedule.**

        **How it works:**

        1. **You create a monitor** with keywords and sources
        2. **Scheduler runs it** (e.g., every day at 6 AM)
        3. **Monitor searches** all selected databases
        4. **Deduplication** - Compares results to previous runs
        5. **Email alert** - Only sends NEW results (no spam)

        **Example:**

        **Day 1:** Monitor finds 10 results → Emails you all 10

        **Day 2:** Monitor finds 12 results:
        - 10 are the same as Day 1 (ignored)
        - 2 are new → Emails you the 2 new ones

        **Day 3:** Monitor finds 12 results:
        - All 12 seen before → No email sent

        **This prevents spam while ensuring you never miss new information.**
        """)

        st.info("💡 **Tip:** Use 'Run Now' button to test your monitor before scheduling it")

    with st.expander("Why am I getting rate limit errors?"):
        st.markdown("""
        **What are rate limits?**
        - APIs restrict how many searches you can do per minute/hour
        - Prevents abuse and server overload

        **Which sources have limits:**
        - 🟡 **SAM.gov** - Strictest limits (~10 searches/minute)
        - 🟢 **DVIDS, USAJobs, ClearanceJobs** - Very generous limits

        **Solutions:**

        1. **Wait 60 seconds** between searches
        2. **Use monitors** instead of manual searches (spreads searches over time)
        3. **Check API Usage Stats** in sidebar to see your request history
        4. **Avoid rapid repeated searches** of SAM.gov

        **If you see "429 Rate Limit" error:**
        - This is temporary
        - Wait 5-10 minutes
        - Try again
        - API will reset automatically
        """)

        st.warning("⚠️ **SAM.gov is the most restrictive** - use monitors for ongoing SAM.gov tracking instead of manual searches")

    with st.expander("Can I export results?"):
        st.markdown("""
        **Yes! Multiple ways to export:**

        **1. CSV Download (Best for spreadsheets)**
        - After any search, expand the database results
        - Click "📥 Download [Database] Results (CSV)"
        - Opens in Excel/Google Sheets

        **2. Copy-Paste**
        - Results are formatted text
        - Select and copy from the browser
        - Paste into documents

        **3. Email Alerts (For monitors)**
        - Monitor results are automatically emailed
        - Includes links to full content

        **What's included in CSV:**
        - All fields returned by the database
        - Job titles, companies, dates, links, etc.
        - Can be messy (contains technical fields)

        **Pro Tip:** Use CSV for bulk analysis, copy-paste for quick notes
        """)

    with st.expander("How much does this cost? (API usage)"):
        st.markdown("""
        **Most APIs are FREE:**
        - ✅ ClearanceJobs - Free, unlimited
        - ✅ DVIDS - Free, unlimited
        - ✅ SAM.gov - Free (but rate limited)
        - ✅ USAJobs - Free, unlimited

        **OpenAI costs money (but very little):**
        - Used for AI Research tab only
        - Cost per search: **$0.01 - $0.05** (1-5 cents)
        - Monthly cost for 100 searches: **~$3-5**

        **Cost breakdown:**
        - Query generation: ~$0.01
        - Result summarization: ~$0.02-0.04
        - Total: **~$0.03 per AI Research search**

        **How to minimize costs:**
        1. Use Advanced Search (free) when you don't need AI
        2. Set up monitors instead of repeated manual searches
        3. Use gpt-5-mini model (already configured - cheapest option)

        **Check your usage:**
        - Go to: https://platform.openai.com/usage
        - See exact costs in real-time
        """)

        st.success("💰 **Bottom line:** Even heavy usage costs less than $10/month")

    with st.expander("What if I find a bug or have suggestions?"):
        st.markdown("""
        **Report Issues:**

        Please share:
        1. What you were trying to do
        2. What happened (error message, unexpected behavior)
        3. Which tab you were using
        4. (Optional) Screenshot

        **Common "bugs" that aren't bugs:**
        - ⏱️ "Search is slow" → Normal for AI Research (15-30 seconds)
        - 🚫 "SAM.gov error" → Usually rate limits (wait and retry)
        - 📭 "No results" → Try broader keywords or different databases

        **Suggestions Welcome:**
        - New data sources you'd like added
        - UI improvements
        - New features
        - Better documentation
        """)

    # ========================================================================
    # TROUBLESHOOTING
    # ========================================================================
    st.markdown("---")
    st.markdown("## 🔧 Troubleshooting")

    with st.expander("API Key Issues"):
        st.markdown("""
        **"API key required" error:**

        1. Check sidebar "🔑 API Keys" section
        2. Make sure key is entered (not blank)
        3. Make sure key doesn't have extra spaces
        4. Try regenerating key from source website

        **"Invalid API key" error:**

        - Key might be expired or revoked
        - Regenerate from source website
        - For OpenAI: Check if you have billing set up

        **Which keys do I really need?**

        **Minimum to get started:**
        - OpenAI (for AI Research)

        **For full functionality:**
        - OpenAI + DVIDS + SAM.gov + USAJobs

        **Testing without keys:**
        - Use Advanced Search → ClearanceJobs (no key needed)
        """)

    with st.expander("No Results Found"):
        st.markdown("""
        **If you're getting zero results:**

        **1. Try broader keywords**
        - ❌ "JTTF counterterrorism analyst" (too specific)
        - ✅ "counterterrorism" or "analyst" (broader)

        **2. Remove date filters**
        - Old or very specific dates might exclude everything
        - Try "last 60 days" or no date filter

        **3. Try a different database**
        - Some topics only appear in certain sources
        - ClearanceJobs: Jobs only
        - SAM.gov: Contracts only
        - DVIDS: Military media only
        - USAJobs: Federal jobs only

        **4. Check if database is actually relevant**
        - Looking for contracts? Won't find them in ClearanceJobs
        - Looking for jobs? Won't find them in DVIDS

        **5. Use AI Research instead**
        - AI understands which databases to search
        - Better at handling vague queries
        """)

    with st.expander("Error Messages"):
        st.markdown("""
        **Common errors and fixes:**

        **"429 Rate Limit Exceeded" (SAM.gov)**
        - Wait 5-10 minutes
        - Avoid rapid repeated searches
        - Use monitors for ongoing tracking

        **"Connection timeout"**
        - Database server might be slow or down
        - Wait 30 seconds and retry
        - Try a different database

        **"No module named..."**
        - Technical error - report to admin
        - Usually fixed by restarting the app

        **"Failed to generate queries"**
        - OpenAI API issue
        - Check your API key
        - Check OpenAI status: https://status.openai.com

        **"JSON parse error"**
        - Temporary AI hiccup
        - Just retry the search
        - If persistent, try rewording your question
        """)

    with st.expander("Performance Issues"):
        st.markdown("""
        **"Why is this so slow?"**

        **Expected speeds:**
        - AI Research: **15-30 seconds** (searching 4 databases + AI analysis)
        - Advanced Search: **2-10 seconds** per database
        - Monitor creation: **Instant**
        - Monitor execution: **20-60 seconds**

        **What affects speed:**
        - Number of databases searched
        - SAM.gov is slowest (often 5-10 seconds)
        - AI analysis takes time
        - Network conditions

        **How to speed things up:**
        - Use Advanced Search for single databases (faster)
        - Reduce "Results per database" setting
        - Search fewer databases in AI Research

        **When to worry:**
        - Search takes >2 minutes → Something's wrong, refresh page
        - Page is frozen → Refresh browser
        - Consistent errors → Report to admin

        **Not worried:**
        - 15-30 seconds for AI Research → Normal
        - 5-10 seconds for SAM.gov → Normal (they're slow)
        """)

    # ========================================================================
    # FOOTER
    # ========================================================================
    st.markdown("---")
    st.markdown("### 📞 Need More Help?")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("""
        **🎓 Learning Resources**
        - Reread this guide
        - Try the 5-minute tutorial
        - Experiment with AI Research
        """)

    with col2:
        st.markdown("""
        **🐛 Found a Bug?**
        - Note what you were doing
        - Take a screenshot
        - Report to team lead
        """)

    with col3:
        st.markdown("""
        **💡 Feature Ideas?**
        - Share your suggestions
        - Describe your use case
        - Explain what would help
        """)

    st.info("💡 **Remember:** This tool is designed to save you time. If something seems too complicated, you're probably overthinking it. Start with AI Research and explore from there!")
