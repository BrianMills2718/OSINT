#!/usr/bin/env python3
"""Monitor Management Tab - Control Boolean monitoring system from UI."""

import streamlit as st
import sys
from pathlib import Path
import json
import yaml
from datetime import datetime
import asyncio
import pandas as pd

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def render_monitor_management_tab():
    """Render the Monitor Management tab."""

    st.markdown("### 📊 Boolean Monitor Management")
    st.caption("Manage automated keyword monitoring with email alerts")

    # Get monitor configs directory
    config_dir = Path("data/monitors/configs")

    if not config_dir.exists():
        st.warning("⚠️ Monitor config directory not found. Creating it now...")
        config_dir.mkdir(parents=True, exist_ok=True)

    # Load all monitor configs
    monitor_configs = list(config_dir.glob("*.yaml"))

    if not monitor_configs:
        st.info("ℹ️ No monitors configured yet. Create your first monitor below!")

    # Tabs for different management views
    tab1, tab2, tab3 = st.tabs(["📋 Active Monitors", "➕ Create Monitor", "📈 Results & Alerts"])

    # TAB 1: Active Monitors
    with tab1:
        render_active_monitors(monitor_configs)

    # TAB 2: Create Monitor
    with tab2:
        render_create_monitor()

    # TAB 3: Results & Alerts
    with tab3:
        render_results_viewer()


def render_active_monitors(monitor_configs):
    """Display list of active monitors with controls."""

    if not monitor_configs:
        st.info("No monitors configured. Use the 'Create Monitor' tab to add one.")
        return

    st.markdown(f"**{len(monitor_configs)} monitors configured**")
    st.markdown("---")

    for config_file in sorted(monitor_configs):
        try:
            with open(config_file, 'r') as f:
                config_data = yaml.safe_load(f)

            # Display monitor card
            with st.expander(f"📌 {config_data['name']}", expanded=False):
                col1, col2 = st.columns([2, 1])

                with col1:
                    st.markdown(f"**Keywords**: {len(config_data['keywords'])} configured")
                    with st.expander("View keywords", expanded=False):
                        for kw in config_data['keywords']:
                            st.caption(f"• {kw}")

                    st.markdown(f"**Sources**: {', '.join(config_data['sources'])}")
                    st.markdown(f"**Schedule**: {config_data.get('schedule', 'daily 06:00')}")
                    st.markdown(f"**Alert Email**: {config_data['alert_email']}")
                    st.markdown(f"**Status**: {'✅ Enabled' if config_data.get('enabled', True) else '❌ Disabled'}")

                with col2:
                    # Control buttons
                    if st.button("▶️ Run Now", key=f"run_{config_file.stem}"):
                        run_monitor_now(config_file)

                    if st.button("📝 Edit", key=f"edit_{config_file.stem}"):
                        st.session_state[f'editing_{config_file.stem}'] = True

                    if st.button("🗑️ Delete", key=f"delete_{config_file.stem}"):
                        if st.session_state.get(f'confirm_delete_{config_file.stem}'):
                            config_file.unlink()
                            st.success(f"Deleted monitor: {config_data['name']}")
                            st.rerun()
                        else:
                            st.session_state[f'confirm_delete_{config_file.stem}'] = True
                            st.warning("Click again to confirm deletion")

                # Check for recent results
                results_file = Path(f"data/monitors/{config_data['name'].replace(' ', '_')}_results.json")
                if results_file.exists():
                    with open(results_file, 'r') as f:
                        results_data = json.load(f)

                    last_run = results_data.get('last_run', 'Never')
                    result_count = results_data.get('result_count', 0)

                    st.caption(f"Last run: {last_run}")
                    st.caption(f"Total results: {result_count}")

        except Exception as e:
            st.error(f"Error loading monitor {config_file.name}: {str(e)}")


def run_monitor_now(config_file):
    """Run a monitor immediately."""

    with st.spinner(f"Running monitor {config_file.stem}..."):
        try:
            from monitoring.boolean_monitor import BooleanMonitor

            # Create and run monitor
            monitor = BooleanMonitor(str(config_file))

            # Run in asyncio loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(monitor.run())
            loop.close()

            st.success("✅ Monitor run complete! Check your email for alerts.")

        except Exception as e:
            st.error(f"❌ Monitor run failed: {str(e)}")
            with st.expander("Error details"):
                st.exception(e)


def render_create_monitor():
    """Form to create a new monitor."""

    st.markdown("#### Create New Monitor")

    with st.form("create_monitor_form"):
        name = st.text_input("Monitor Name", placeholder="e.g., Surveillance Programs Monitor")

        keywords_text = st.text_area(
            "Keywords (one per line)",
            placeholder="Section 702\nFISA Court\nNSA surveillance",
            help="Enter each keyword on a new line. Supports Boolean operators in quotes."
        )

        sources = st.multiselect(
            "Data Sources",
            options=["dvids", "sam", "usajobs", "federal_register", "clearancejobs"],
            default=["federal_register", "dvids"],
            help="Select which sources to search"
        )

        schedule = st.selectbox(
            "Schedule",
            options=["daily 06:00", "daily 12:00", "daily 18:00", "every 6 hours"],
            help="When to run automated searches"
        )

        alert_email = st.text_input(
            "Alert Email",
            placeholder="your@email.com",
            help="Where to send new result alerts"
        )

        enabled = st.checkbox("Enable monitor", value=True)

        submitted = st.form_submit_button("Create Monitor")

        if submitted:
            if not name or not keywords_text or not alert_email or not sources:
                st.error("❌ Please fill in all required fields")
            else:
                # Parse keywords
                keywords = [kw.strip() for kw in keywords_text.split('\n') if kw.strip()]

                # Create config
                config = {
                    'name': name,
                    'keywords': keywords,
                    'sources': sources,
                    'schedule': schedule,
                    'alert_email': alert_email,
                    'enabled': enabled
                }

                # Save config
                config_dir = Path("data/monitors/configs")
                config_dir.mkdir(parents=True, exist_ok=True)

                config_file = config_dir / f"{name.replace(' ', '_').lower()}.yaml"

                with open(config_file, 'w') as f:
                    yaml.dump(config, f, default_flow_style=False)

                st.success(f"✅ Monitor created: {name}")
                st.info("💡 Tip: Use the 'Run Now' button in Active Monitors to test it")
                st.rerun()


def render_results_viewer():
    """View recent monitor results and alerts."""

    st.markdown("#### Recent Results & Alerts")

    results_dir = Path("data/monitors")
    result_files = list(results_dir.glob("*_results.json"))

    if not result_files:
        st.info("No results yet. Run a monitor to see results here.")
        return

    # Let user select which monitor's results to view
    monitor_names = [f.stem.replace('_results', '').replace('_', ' ').title() for f in result_files]
    selected_monitor = st.selectbox("Select Monitor", monitor_names)

    # Find corresponding file
    selected_file = None
    for f in result_files:
        if f.stem.replace('_results', '').replace('_', ' ').title() == selected_monitor:
            selected_file = f
            break

    if selected_file and selected_file.exists():
        with open(selected_file, 'r') as f:
            results_data = json.load(f)

        st.markdown(f"**Last run**: {results_data.get('last_run', 'Unknown')}")
        st.markdown(f"**Total results tracked**: {results_data.get('result_count', 0)}")

        st.markdown("---")
        st.caption("ℹ️ Results are stored as hashes for deduplication. Full results are sent via email alerts.")

        # Show result hashes
        if results_data.get('result_hashes'):
            st.markdown(f"**Unique results**: {len(results_data['result_hashes'])}")

            if st.checkbox("Show result hashes (for debugging)"):
                for i, hash_val in enumerate(results_data['result_hashes'][:20], 1):
                    st.code(f"{i}. {hash_val}", language=None)

                if len(results_data['result_hashes']) > 20:
                    st.caption(f"... and {len(results_data['result_hashes']) - 20} more")

    # Service status
    st.markdown("---")
    st.markdown("#### 🔧 Service Status")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("🔄 Check Service Status"):
            check_service_status()

    with col2:
        if st.button("📋 View Logs"):
            view_service_logs()


def check_service_status():
    """Check systemd service status."""
    import subprocess

    try:
        result = subprocess.run(
            ['systemctl', '--user', 'status', 'osint-monitor'],
            capture_output=True,
            text=True,
            timeout=5
        )

        if 'active (running)' in result.stdout.lower():
            st.success("✅ Monitoring service is running")
        elif 'inactive' in result.stdout.lower():
            st.warning("⚠️ Monitoring service is stopped")
            if st.button("Start Service"):
                subprocess.run(['systemctl', '--user', 'start', 'osint-monitor'])
                st.rerun()
        else:
            st.error("❌ Service status unknown")

        with st.expander("Service details"):
            st.code(result.stdout)

    except subprocess.TimeoutExpired:
        st.error("❌ Command timed out")
    except Exception as e:
        st.error(f"❌ Cannot check service: {str(e)}")
        st.caption("💡 Tip: Service control requires systemd and proper permissions")


def view_service_logs():
    """View recent service logs."""
    import subprocess

    try:
        result = subprocess.run(
            ['journalctl', '--user', '-u', 'osint-monitor', '-n', '50', '--no-pager'],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0:
            st.code(result.stdout, language='log')
        else:
            st.error("❌ Cannot read logs")
            st.caption("💡 Tip: Run manually instead: `.venv/bin/python3 monitoring/scheduler.py`")

    except Exception as e:
        st.error(f"❌ Cannot view logs: {str(e)}")
