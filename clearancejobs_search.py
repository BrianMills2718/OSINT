"""ClearanceJobs search interface - Improved UX"""

import streamlit as st
import pandas as pd
import time
import json
from datetime import datetime
from ClearanceJobs import ClearanceJobs


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

                # Build search
                body = {
                    "keywords": keyword,
                    "limit": results_per_page,
                    "page": page_num
                }

                # Map UI values to API values
                clearance_map = {
                    "Secret": 2,
                    "Top Secret": 3,
                    "Top Secret/SCI": 4
                }
                if clearance_filter:
                    body["clearance"] = [clearance_map[c] for c in clearance_filter]

                exp_map = {
                    "Entry Level": "b",
                    "2+ years": "c",
                    "5+ years": "d",
                    "10+ years": "e"
                }
                if experience != "Any" and experience in exp_map:
                    body["career_level"] = [exp_map[experience]]

                # State handling
                state_to_use = state_adv if state_adv != "All States" else (location_state if location_state != "All States" else None)
                state_id_map = {
                    "Alabama": 1, "Alaska": 2, "Arizona": 3, "Arkansas": 4, "California": 5,
                    "Colorado": 6, "Connecticut": 7, "D.C.": 53, "Delaware": 8, "Florida": 9,
                    "Georgia": 10, "Hawaii": 11, "Idaho": 12, "Illinois": 13, "Indiana": 14,
                    "Maryland": 20, "Massachusetts": 21, "Michigan": 22, "Minnesota": 23,
                    "Mississippi": 24, "Missouri": 25, "Nebraska": 27, "Nevada": 28,
                    "New Hampshire": 29, "New Jersey": 30, "New Mexico": 31, "New York": 32,
                    "North Carolina": 33, "North Dakota": 34, "Ohio": 35, "Oklahoma": 36,
                    "Oregon": 37, "Pennsylvania": 38, "Rhode Island": 40, "South Carolina": 41,
                    "South Dakota": 42, "Tennessee": 43, "Texas": 44, "Utah": 45,
                    "Vermont": 46, "Virginia": 48, "Washington": 49, "West Virginia": 50,
                    "Wyoming": 52
                }
                if state_to_use and state_to_use in state_id_map:
                    body["loc"] = state_id_map[state_to_use]

                if city:
                    body["city"] = city

                poly_map = {
                    "None Required": "n",
                    "Any Polygraph": "p",
                    "CI Polygraph": "i",
                    "Full Scope Polygraph": "l"
                }
                if polygraph:
                    body["polygraph"] = [poly_map[p] for p in polygraph]

                type_map = {
                    "Employee": "e",
                    "Contractor/Consultant": "c",
                    "Intern/Entry Level": "i"
                }
                if job_type != "All Types" and job_type in type_map:
                    body["type"] = type_map[job_type]

                posted_map = {
                    "Last 24 hours": 1,
                    "Last 3 days": 3,
                    "Last week": 7,
                    "Last month": 31
                }
                if posted_within != "Any time" and posted_within in posted_map:
                    body["received"] = posted_map[posted_within]

                if remote_only:
                    body["remote"] = 1

                if company:
                    body["co_name"] = company

                # Search
                cj = ClearanceJobs()
                response = cj.post('/jobs/search', body)
                data = response.json()

                jobs = data.get('data', [])
                pagination = data.get('meta', {}).get('pagination', {})

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
