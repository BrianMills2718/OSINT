"""DVIDS search interface - Improved UX"""

import streamlit as st
import pandas as pd
import requests
import time
import json
from datetime import datetime, timedelta
from PIL import Image
from io import BytesIO


def render_dvids_tab(api_key, results_per_page, enable_rate_limiting):
    """Render DVIDS search tab."""

    st.markdown("### 📸 Military Media Search")
    st.caption("Search DoD photos, videos, news and media from DVIDS • API key required")

    if not api_key:
        st.warning("⚠️ **API Key Required** - Please add your DVIDS API key in the sidebar")
        st.info("🔑 Get your free API key at: https://www.dvidshub.net/")
        return

    # Quick Search
    st.markdown("#### 🚀 Quick Search")
    col_q1, col_q2 = st.columns([3, 1])

    with col_q1:
        quick_query = st.text_input(
            "Search military media",
            placeholder="Try: F-35, training, deployment, humanitarian... (leave empty to browse all)",
            label_visibility="collapsed",
            key="dvids_quick_query"
        )

    with col_q2:
        quick_search_btn = st.button("🔍 Quick Search", type="primary", use_container_width=True, key="dvids_quick_btn")

    # Common Filters
    with st.expander("🎯 **Common Filters**", expanded=True):
        col1, col2, col3 = st.columns(3)

        with col1:
            media_types = st.multiselect(
                "Media Type",
                options=["image", "video", "news"],
                default=["image"],
                help="Select one or more types"
            )

        with col2:
            branch = st.selectbox(
                "Military Branch",
                options=["All Branches", "Army", "Navy", "Air Force", "Marines", "Coast Guard", "Joint"]
            )

        with col3:
            country = st.selectbox(
                "Country",
                options=["All Countries", "United States", "Germany", "Japan", "South Korea", "Italy", "United Kingdom"]
            )

    # Date Range
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        from_date = st.date_input("From Date (optional)", value=None, key="dvids_from")
    with col_d2:
        to_date = st.date_input("To Date (optional)", value=None, key="dvids_to")

    # Advanced Filters
    with st.expander("⚙️ Advanced Filters"):
        col_a1, col_a2 = st.columns(2)

        with col_a1:
            st.markdown("**Location & Organization**")
            state = st.text_input("State", placeholder="e.g., California, Texas")
            city = st.text_input("City", placeholder="e.g., San Diego, Fort Hood")
            cocom = st.text_input("Combatant Command", placeholder="e.g., USCENTCOM, USPACOM")

        with col_a2:
            st.markdown("**Media Options**")
            aspect_ratio = st.selectbox("Aspect Ratio (Images)", options=["Any", "landscape", "portrait", "16:9", "4:3"])
            col_opt1, col_opt2 = st.columns(2)
            with col_opt1:
                hd_only = st.checkbox("HD Video Only")
            with col_opt2:
                has_captions = st.checkbox("Has Captions")

        page_num = st.number_input("Page", min_value=1, value=1, key="dvids_page", help="Max 20 pages (1000 results)")

    # Search
    search_triggered = quick_search_btn or st.button("🔎 Search with Filters", use_container_width=True, key="dvids_full_search")

    if search_triggered:
        with st.spinner("Searching DVIDS..."):
            try:
                if enable_rate_limiting:
                    time.sleep(0.5)

                params = {
                    "api_key": api_key,
                    "page": page_num,
                    "max_results": min(results_per_page, 50)
                }

                if quick_query:
                    params["q"] = quick_query

                if media_types:
                    params["type[]"] = media_types

                if branch != "All Branches":
                    params["branch"] = branch

                if country != "All Countries":
                    params["country"] = country

                if state:
                    params["state"] = state

                if city:
                    params["city"] = city

                if cocom:
                    params["cocom"] = cocom

                if from_date:
                    params["from_publishdate"] = datetime.combine(from_date, datetime.min.time()).isoformat() + "Z"

                if to_date:
                    params["to_publishdate"] = datetime.combine(to_date, datetime.min.time()).isoformat() + "Z"

                if aspect_ratio != "Any":
                    params["aspect_ratio"] = aspect_ratio

                if hd_only:
                    params["hd"] = 1

                if has_captions:
                    params["has_captions"] = 1

                params["has_image"] = 1  # Always include this for better results

                # Request
                response = requests.get("https://api.dvidshub.net/search", params=params, timeout=20)
                response.raise_for_status()
                data = response.json()

                results = data.get('results', [])
                page_info = data.get('page_info', {})

                if not results:
                    st.info("No results found. Try different search terms or broaden your filters.")
                else:
                    total = page_info.get('total_results', 0)
                    st.success(f"✅ Found **{total:,} results** (Page {page_num}, showing {len(results)} items)")

                    if total > 1000:
                        st.warning("⚠️ DVIDS limits results to 1000 total. Refine your search for more specific results.")

                    # Display in grid
                    cols = st.columns(3)
                    for idx, item in enumerate(results):
                        col = cols[idx % 3]
                        with col:
                            with st.container():
                                # Title and link
                                title = item.get('title', 'Untitled')
                                url = item.get('url', '#')
                                st.markdown(f"**[{title[:60]}...]({url})**" if len(title) > 60 else f"**[{title}]({url})**")

                                # Thumbnail
                                thumb = item.get('thumbnail')
                                if thumb:
                                    try:
                                        st.image(thumb, use_container_width=True)
                                    except:
                                        st.caption("🖼️ [Image unavailable]")

                                # Metadata badges
                                item_type = item.get('type', 'N/A')
                                st.markdown(f"<span style='background:#e1f5fe;padding:2px 8px;border-radius:3px;font-size:0.8em'>{item_type}</span>", unsafe_allow_html=True)

                                date_pub = item.get('date_published') or item.get('publishdate')
                                if date_pub:
                                    st.caption(f"📅 {date_pub[:10]}")

                                credit = item.get('credit', '')
                                if credit:
                                    st.caption(f"👤 {credit[:30]}")

                                st.markdown("")  # Spacing

                    # Export
                    st.markdown("---")
                    col_e1, col_e2 = st.columns(2)
                    with col_e1:
                        df = pd.DataFrame(results)
                        csv = df.to_csv(index=False).encode('utf-8')
                        st.download_button(
                            "📥 Download CSV",
                            csv,
                            f"dvids_{datetime.now().strftime('%Y%m%d')}.csv",
                            "text/csv",
                            use_container_width=True
                        )
                    with col_e2:
                        json_str = json.dumps(data, indent=2)
                        st.download_button(
                            "📥 Download JSON",
                            json_str,
                            f"dvids_{datetime.now().strftime('%Y%m%d')}.json",
                            "application/json",
                            use_container_width=True
                        )

            except requests.HTTPError as e:
                st.error(f"❌ HTTP Error {e.response.status_code}")
                if e.response.status_code == 403:
                    st.error("Invalid API key. Please check your key in the sidebar.")
                else:
                    st.code(e.response.text[:500])
            except Exception as e:
                st.error(f"❌ Search failed: {str(e)}")
                with st.expander("Error Details"):
                    st.exception(e)
