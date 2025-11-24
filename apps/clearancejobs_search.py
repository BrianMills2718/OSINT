"""ClearanceJobs search interface - Improved UX"""

import streamlit as st
import pandas as pd
import time
import json
import asyncio
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from integrations.government.clearancejobs_http import search_clearancejobs


def render_clearancejobs_tab(results_per_page, enable_rate_limiting):
    """Render ClearanceJobs search tab."""

    st.markdown("### 🏢 Security Clearance Job Search")
    st.caption("Find government and defense contractor jobs requiring security clearances • No login required")

    # Quick Search Box
    st.markdown("#### 🚀 Quick Search")
    col_q1, col_q2 = st.columns([3, 1])

    with col_q1:
        quick_keyword = st.text_input(
            "Search keywords",
            placeholder="Try: cybersecurity analyst, network engineer, software developer...",
            label_visibility="collapsed",
            key="cj_quick_keyword"
        )

    with col_q2:
        quick_search_btn = st.button("🔍 Quick Search", type="primary", use_container_width=True, key="cj_quick_btn")

    # Common Filters (always visible)
    with st.expander("🎯 **Common Filters**", expanded=True):
        col1, col2, col3 = st.columns(3)

        with col1:
            clearance_filter = st.multiselect(
                "Security Clearance",
                options=["Secret", "Top Secret", "Top Secret/SCI"],
                help="Leave empty for all clearances"
            )

        with col2:
            experience = st.selectbox(
                "Minimum Experience",
                options=["Any", "Entry Level", "2+ years", "5+ years", "10+ years"],
            )

        with col3:
            location_state = st.selectbox(
                "State",
                options=["All States", "Maryland", "Virginia", "D.C.", "California", "Colorado", "Texas", "Florida"],
                help="Popular defense industry states"
            )

    # Advanced Filters (collapsed by default)
    with st.expander("⚙️ Advanced Filters"):
        col_a1, col_a2 = st.columns(2)

        with col_a1:
            st.markdown("**Location**")
            city = st.text_input("City", placeholder="e.g., Washington, Alexandria")

            all_states = ["All States"] + [
                "Alabama", "Alaska", "Arizona", "Arkansas", "California", "Colorado",
                "Connecticut", "D.C.", "Delaware", "Florida", "Georgia", "Hawaii",
                "Idaho", "Illinois", "Indiana", "Iowa", "Kansas", "Kentucky",
                "Louisiana", "Maine", "Maryland", "Massachusetts", "Michigan",
                "Minnesota", "Mississippi", "Missouri", "Nebraska", "Nevada",
                "New Hampshire", "New Jersey", "New Mexico", "New York",
                "North Carolina", "North Dakota", "Ohio", "Oklahoma", "Oregon",
                "Pennsylvania", "Rhode Island", "South Carolina", "South Dakota",
                "Tennessee", "Texas", "Utah", "Vermont", "Virginia", "Washington",
                "West Virginia", "Wyoming"
            ]
            state_adv = st.selectbox("State (All)", options=all_states, key="cj_state_adv")

            remote_only = st.checkbox("Remote jobs only")

        with col_a2:
            st.markdown("**Requirements**")
            polygraph = st.multiselect(
                "Polygraph",
                options=["None Required", "Any Polygraph", "CI Polygraph", "Full Scope Polygraph"]
            )

            job_type = st.selectbox(
                "Employment Type",
                options=["All Types", "Employee", "Contractor/Consultant", "Intern/Entry Level"]
            )

            posted_within = st.selectbox(
                "Posted Within",
                options=["Any time", "Last 24 hours", "Last 3 days", "Last week", "Last month"]
            )

        st.markdown("**Other**")
        col_a3, col_a4 = st.columns(2)
        with col_a3:
            company = st.text_input("Company Name", placeholder="e.g., Lockheed Martin, Booz Allen")
        with col_a4:
            page_num = st.number_input("Page", min_value=1, value=1, key="cj_page")

    # Handle quick search or full search
    search_triggered = quick_search_btn or st.button("🔎 Search with Filters", use_container_width=True, key="cj_full_search")

    if search_triggered:
        # Use quick keyword if provided, otherwise empty
        keyword = quick_keyword if quick_keyword else ""

        if not keyword and not any([clearance_filter, city, company]):
            st.warning("⚠️ Please enter search keywords or select at least one filter")
            return

        with st.spinner("Searching ClearanceJobs..."):
            try:
                if enable_rate_limiting:
                    time.sleep(1.0)

                # Note: The Playwright scraper currently only supports basic keyword search
                # Advanced filters would require significant updates to clearancejobs_playwright.py
                # For now, using simple search and filtering client-side

                # Execute Playwright search
                result = asyncio.run(search_clearancejobs(
                    keywords=keyword,
                    limit=results_per_page,
                    headless=True
                ))

                if not result["success"]:
                    raise Exception(result.get("error", "Unknown error"))

                jobs_raw = result.get("jobs", [])
                total_count = result.get("total", len(jobs_raw))

                # Convert Playwright results to expected format
                jobs = []
                for job in jobs_raw:
                    jobs.append({
                        "job_name": job.get("title", ""),
                        "job_url": job.get("url", ""),
                        "company_name": job.get("company", ""),
                        "clearance": job.get("clearance", "N/A"),
                        "locations": [{"location": job.get("location", "")}],
                        "preview_text": job.get("description", ""),
                        "polygraph": "Not Specified",
                        "updated": job.get("updated", "")
                    })

                # Create pagination object
                pagination = {
                    "total": total_count,
                    "current_page": 1,  # Playwright scraper doesn't support pagination yet
                    "total_pages": 1
                }

                if not jobs:
                    st.info("No jobs found. Try broadening your search criteria.")
                else:
                    # Success message
                    st.success(f"✅ Found **{pagination.get('total', 0):,} jobs** (Page {pagination.get('current_page', 1)} of {pagination.get('total_pages', 1):,})")

                    # Display results
                    for idx, job in enumerate(jobs, 1):
                        with st.container():
                            col_j1, col_j2 = st.columns([3, 1])

                            with col_j1:
                                st.markdown(f"### {idx}. [{job.get('job_name', 'Untitled')}]({job.get('job_url', '#')})")
                                st.markdown(f"**{job.get('company_name', 'N/A')}**")

                            with col_j2:
                                st.markdown(f"**{job.get('clearance', 'N/A')}**")
                                if job.get('polygraph') and job.get('polygraph') != 'Not Specified':
                                    st.caption(f"Polygraph: {job['polygraph']}")

                            # Location
                            locations = job.get('locations', [])
                            if locations:
                                loc_str = ' • '.join([loc.get('location', 'N/A') for loc in locations])
                                st.caption(f"📍 {loc_str}")

                            # Preview
                            preview = job.get('preview_text', '')
                            if preview:
                                st.write(preview[:250] + "..." if len(preview) > 250 else preview)

                            st.markdown("---")

                    # Export
                    col_e1, col_e2, col_e3 = st.columns([1, 1, 2])
                    with col_e1:
                        df = pd.DataFrame(jobs)
                        csv = df.to_csv(index=False).encode('utf-8')
                        st.download_button(
                            "📥 Download CSV",
                            csv,
                            f"clearancejobs_{datetime.now().strftime('%Y%m%d')}.csv",
                            "text/csv",
                            use_container_width=True
                        )
                    with col_e2:
                        json_str = json.dumps(data, indent=2)
                        st.download_button(
                            "📥 Download JSON",
                            json_str,
                            f"clearancejobs_{datetime.now().strftime('%Y%m%d')}.json",
                            "application/json",
                            use_container_width=True
                        )

            except Exception as e:
                st.error(f"❌ Search failed: {str(e)}")
                with st.expander("Error Details"):
                    st.exception(e)
