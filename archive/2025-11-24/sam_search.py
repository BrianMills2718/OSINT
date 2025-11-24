"""SAM.gov search interface - Improved UX"""

import streamlit as st
import pandas as pd
import requests
import time
import json
from datetime import datetime, timedelta


def render_sam_tab(api_key, results_per_page, enable_rate_limiting):
    """Render SAM.gov search tab."""

    st.markdown("### 📋 Government Contract Opportunities")
    st.caption("Search federal contracting opportunities on SAM.gov • API key required")

    if not api_key:
        st.warning("⚠️ **API Key Required** - Please add your SAM.gov API key in the sidebar")
        st.info("🔑 Get your API key at: https://sam.gov → Account Details page")
        return

    # Important notice about date requirement
    st.markdown("""
    <div style='background:#fff3cd;padding:1rem;border-radius:0.5rem;border-left:4px solid #ffc107;margin-bottom:1.5rem'>
        <strong>⚠️ Important:</strong> Date range is <strong>required</strong> and must not exceed 1 year.
    </div>
    """, unsafe_allow_html=True)

    # REQUIRED: Date Range (prominent)
    st.markdown("#### 📅 Posted Date Range (Required)")
    col_d1, col_d2 = st.columns(2)

    with col_d1:
        posted_from = st.date_input(
            "From Date",
            value=datetime.now() - timedelta(days=30),
            help="Required: Start of search period"
        )

    with col_d2:
        posted_to = st.date_input(
            "To Date",
            value=datetime.now(),
            help="Required: End of search period"
        )

    # Validate date range
    if posted_from and posted_to:
        date_diff = (posted_to - posted_from).days
        if date_diff > 365:
            st.error("❌ Date range cannot exceed 1 year! Please adjust your dates.")
            return
        elif date_diff < 0:
            st.error("❌ 'From Date' must be before 'To Date'!")
            return
        else:
            st.success(f"✅ Valid date range: {date_diff} days")

    # Quick Search
    st.markdown("#### 🚀 Quick Search")
    col_q1, col_q2 = st.columns([3, 1])

    with col_q1:
        quick_keyword = st.text_input(
            "Search keywords",
            placeholder="Try: cybersecurity, IT services, construction, consulting...",
            label_visibility="collapsed",
            key="sam_quick_keyword"
        )

    with col_q2:
        quick_search_btn = st.button("🔍 Quick Search", type="primary", use_container_width=True, key="sam_quick_btn")

    # Common Filters
    with st.expander("🎯 **Common Filters**", expanded=True):
        col1, col2 = st.columns(2)

        with col1:
            proc_type = st.multiselect(
                "Procurement Type",
                options=[
                    "Solicitation",
                    "Presolicitation",
                    "Combined Synopsis/Solicitation",
                    "Sources Sought"
                ],
                help="Select one or more types"
            )

        with col2:
            set_aside = st.selectbox(
                "Set-Aside Type",
                options=[
                    "All",
                    "Total Small Business",
                    "8(a) Set-Aside",
                    "SDVOSB (Service-Disabled Veteran)",
                    "Women-Owned Small Business",
                    "HUBZone Set-Aside"
                ],
                help="Only ONE set-aside type allowed per API"
            )

    # Advanced Filters
    with st.expander("⚙️ Advanced Filters"):
        col_a1, col_a2 = st.columns(2)

        with col_a1:
            st.markdown("**Organization & Location**")
            org_name = st.text_input("Organization", placeholder="e.g., Department of Defense, FBI")
            state = st.text_input("State", placeholder="2-letter code: VA, CA, TX, etc.")
            naics = st.text_input("NAICS Code(s)", placeholder="e.g., 541512,541519 (comma-separated)")

        with col_a2:
            st.markdown("**Other Filters**")
            solnum = st.text_input("Solicitation Number", placeholder="e.g., W912DY24R0005")
            ccode = st.text_input("PSC Code", placeholder="Product/Service Classification")
            page_num = st.number_input("Page", min_value=1, value=1, key="sam_page")

    # Search
    search_triggered = quick_search_btn or st.button("🔎 Search with Filters", use_container_width=True, key="sam_full_search")

    if search_triggered:
        with st.spinner("Searching SAM.gov..."):
            try:
                if enable_rate_limiting:
                    time.sleep(1.0)

                offset = (page_num - 1) * results_per_page

                params = {
                    "api_key": api_key,
                    "postedFrom": posted_from.strftime("%m/%d/%Y"),
                    "postedTo": posted_to.strftime("%m/%d/%Y"),
                    "limit": min(results_per_page, 1000),
                    "offset": offset
                }

                if quick_keyword:
                    params["keywords"] = quick_keyword

                # Procurement type mapping
                ptype_map = {
                    "Solicitation": "o",
                    "Presolicitation": "p",
                    "Combined Synopsis/Solicitation": "k",
                    "Sources Sought": "r"
                }
                if proc_type:
                    params["ptype"] = ",".join([ptype_map[p] for p in proc_type])

                # Set-aside mapping
                setaside_map = {
                    "Total Small Business": "SBA",
                    "8(a) Set-Aside": "8A",
                    "SDVOSB (Service-Disabled Veteran)": "SDVOSBC",
                    "Women-Owned Small Business": "WOSB",
                    "HUBZone Set-Aside": "HZC"
                }
                if set_aside != "All" and set_aside in setaside_map:
                    params["typeOfSetAside"] = setaside_map[set_aside]

                if org_name:
                    params["organizationName"] = org_name

                if state:
                    params["state"] = state.upper()

                if naics:
                    params["ncode"] = naics

                if solnum:
                    params["solnum"] = solnum

                if ccode:
                    params["ccode"] = ccode

                # Request
                response = requests.get(
                    "https://api.sam.gov/opportunities/v2/search",
                    params=params,
                    timeout=30
                )
                response.raise_for_status()
                data = response.json()

                opportunities = data.get('opportunitiesData', data.get('results', []))
                total = data.get('totalRecords', data.get('total', 0))

                if not opportunities:
                    st.info("No opportunities found. Try different keywords or broaden your filters.")
                else:
                    total_pages = (total + results_per_page - 1) // results_per_page
                    st.success(f"✅ Found **{total:,} opportunities** (Page {page_num} of {total_pages:,})")

                    # Display results
                    for idx, opp in enumerate(opportunities, 1 + offset):
                        with st.container():
                            # Title
                            title = opp.get('title', 'Untitled')
                            ui_link = opp.get('uiLink', '')

                            if ui_link:
                                st.markdown(f"### {idx}. [{title}]({ui_link})")
                            else:
                                st.markdown(f"### {idx}. {title}")

                            col_o1, col_o2 = st.columns([2, 1])

                            with col_o1:
                                org = opp.get('fullParentPathName', opp.get('organizationName', 'N/A'))
                                st.markdown(f"**Organization:** {org}")
                                solnum_display = opp.get('solicitationNumber', 'N/A')
                                st.caption(f"Sol #: {solnum_display}")

                            with col_o2:
                                opp_type = opp.get('type', 'N/A')
                                st.markdown(f"**Type:** {opp_type}")
                                posted = opp.get('postedDate', '')
                                if posted:
                                    st.caption(f"Posted: {posted[:10]}")

                            # Deadline
                            deadline = opp.get('responseDeadLine', '')
                            if deadline:
                                deadline_date = datetime.fromisoformat(deadline.replace('Z', '+00:00'))
                                days_left = (deadline_date - datetime.now(deadline_date.tzinfo)).days

                                if days_left < 0:
                                    st.caption(f"⚠️ Deadline passed: {deadline[:10]}")
                                elif days_left < 7:
                                    st.warning(f"🚨 Deadline: {deadline[:10]} ({days_left} days left!)")
                                else:
                                    st.info(f"📅 Deadline: {deadline[:10]} ({days_left} days left)")

                            # Additional info
                            naics_code = opp.get('naicsCode', '')
                            class_code = opp.get('classificationCode', '')
                            set_aside_desc = opp.get('setAside', '')

                            info_parts = []
                            if naics_code:
                                info_parts.append(f"NAICS: {naics_code}")
                            if class_code:
                                info_parts.append(f"PSC: {class_code}")
                            if set_aside_desc:
                                info_parts.append(f"Set-Aside: {set_aside_desc}")

                            if info_parts:
                                st.caption(" | ".join(info_parts))

                            st.markdown("---")

                    # Export
                    col_e1, col_e2 = st.columns(2)
                    with col_e1:
                        df = pd.DataFrame(opportunities)
                        csv = df.to_csv(index=False).encode('utf-8')
                        st.download_button(
                            "📥 Download CSV",
                            csv,
                            f"sam_{datetime.now().strftime('%Y%m%d')}.csv",
                            "text/csv",
                            use_container_width=True
                        )
                    with col_e2:
                        json_str = json.dumps(data, indent=2)
                        st.download_button(
                            "📥 Download JSON",
                            json_str,
                            f"sam_{datetime.now().strftime('%Y%m%d')}.json",
                            "application/json",
                            use_container_width=True
                        )

            except requests.HTTPError as e:
                st.error(f"❌ HTTP Error {e.response.status_code}")
                st.code(e.response.text[:500])
            except Exception as e:
                st.error(f"❌ Search failed: {str(e)}")
                with st.expander("Error Details"):
                    st.exception(e)
