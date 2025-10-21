#!/usr/bin/env python3
"""
Deep Research tab for Streamlit UI.
Integrates SimpleDeepResearch engine with live progress display.
"""

import streamlit as st
import asyncio
import os
import sys
from pathlib import Path
from datetime import datetime
import json

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from research.deep_research import SimpleDeepResearch, ResearchProgress
from dotenv import load_dotenv

load_dotenv()


def render_deep_research_tab(openai_api_key_from_ui):
    """Render the Deep Research tab in Streamlit UI."""

    st.markdown("### 🔬 Deep Research Engine")
    st.caption("Multi-phase investigative research with task decomposition, entity tracking, and automated follow-ups")

    # Get OpenAI API key
    openai_api_key = None
    if openai_api_key_from_ui:
        openai_api_key = openai_api_key_from_ui
    elif hasattr(st, 'secrets') and "OPENAI_API_KEY" in st.secrets:
        try:
            openai_api_key = st.secrets["OPENAI_API_KEY"]
        except:
            pass
    else:
        openai_api_key = os.getenv("OPENAI_API_KEY")

    if not openai_api_key:
        st.error("⚠️ **OpenAI API Key Required**")
        with st.expander("💡 How to configure OpenAI API Key", expanded=True):
            st.markdown("""
            **For Local Development:**
            1. Create a `.env` file in the project directory
            2. Add: `OPENAI_API_KEY=your-key-here`
            3. Restart the app

            **For Streamlit Cloud Deployment:**
            1. Go to App Settings → Secrets
            2. Add: `OPENAI_API_KEY = "your-key-here"`

            **Get your API key:** https://platform.openai.com/api-keys
            """)
        return

    # Set API key
    os.environ["OPENAI_API_KEY"] = openai_api_key

    # Info box explaining the difference
    st.info("""
    **🔬 Deep Research vs 🤖 AI Research:**

    - **AI Research** (Quick): Searches selected databases in parallel, returns results in ~10-30 seconds
    - **Deep Research** (Thorough): Multi-phase investigation with:
      - Task decomposition (breaks complex questions into sub-tasks)
      - Retry logic (reformulates failed queries)
      - Entity tracking (connects entities across results)
      - Follow-up tasks (automatically investigates interesting findings)
      - Can run for minutes to hours

    Use Deep Research for complex, multi-part questions requiring thorough investigation.
    """)

    # Research question input
    st.markdown("#### 🔍 Your Research Question")

    with st.expander("💡 Example Questions for Deep Research", expanded=False):
        st.markdown("""
        **Complex Multi-Part Questions:**
        - "What is the relationship between JSOC and CIA Title 50 operations?"
        - "How do federal cybersecurity contracts connect to cleared job opportunities?"
        - "What are the connections between special operations units and intelligence agencies?"

        **Entity-Focused Research:**
        - "Map the relationships between defense contractors working on AI security"
        - "What organizations are involved in signals intelligence collection?"

        **Investigative Questions:**
        - "Trace the evolution of drone warfare programs across military and intelligence agencies"
        - "What are the oversight mechanisms for covert operations?"
        """)

    research_question = st.text_area(
        "What would you like to investigate?",
        placeholder="Example: What is the relationship between JSOC and CIA Title 50 operations?",
        height=100,
        key="deep_research_question"
    )

    # Configuration options
    st.markdown("#### ⚙️ Research Configuration")

    col1, col2, col3 = st.columns(3)

    with col1:
        max_tasks = st.number_input(
            "Max Tasks",
            min_value=3,
            max_value=50,
            value=10,
            help="Maximum number of research tasks to execute (prevents infinite loops)"
        )

    with col2:
        max_time_minutes = st.number_input(
            "Max Time (minutes)",
            min_value=5,
            max_value=240,
            value=60,
            help="Maximum investigation time in minutes"
        )

    with col3:
        max_retries = st.number_input(
            "Max Retries per Task",
            min_value=0,
            max_value=5,
            value=2,
            help="How many times to retry failed searches with reformulated queries"
        )

    # Advanced settings
    with st.expander("🔧 Advanced Settings", expanded=False):
        min_results_per_task = st.number_input(
            "Minimum Results per Task",
            min_value=1,
            max_value=20,
            value=3,
            help="Minimum results to consider a task successful"
        )

    # Research button
    research_btn = st.button("🚀 Start Deep Research", type="primary", use_container_width=True, key="deep_research_btn")

    if research_btn and research_question:
        # Create placeholders for live updates
        status_container = st.container()
        progress_container = st.container()
        entity_container = st.container()
        report_container = st.container()
        stats_container = st.container()

        # Progress tracking
        progress_data = {
            "events": [],
            "tasks_created": 0,
            "tasks_completed": 0,
            "tasks_failed": 0,
            "entities_discovered": set(),
            "relationships_discovered": []
        }

        def progress_callback(progress: ResearchProgress):
            """Handle progress updates from deep research engine."""
            progress_data["events"].append(progress)

            # Update counters based on event type
            if progress.event == "task_created":
                progress_data["tasks_created"] += 1
            elif progress.event == "task_completed":
                progress_data["tasks_completed"] += 1
            elif progress.event == "task_failed":
                progress_data["tasks_failed"] += 1
            elif progress.event == "entity_discovered":
                if progress.data and "entity" in progress.data:
                    progress_data["entities_discovered"].add(progress.data["entity"])
            elif progress.event == "relationship_discovered":
                progress_data["relationships_discovered"].append(progress.message)

        # Execute deep research
        with status_container:
            st.markdown("### 📊 Research Progress")

        try:
            # Create engine
            engine = SimpleDeepResearch(
                max_tasks=max_tasks,
                max_retries_per_task=max_retries,
                max_time_minutes=max_time_minutes,
                min_results_per_task=min_results_per_task,
                progress_callback=progress_callback
            )

            # Run research (async)
            with st.spinner(f"🔬 Deep research in progress (max {max_time_minutes} minutes)..."):
                result = asyncio.run(engine.research(research_question))

            # Display live progress
            with progress_container:
                st.markdown("#### 📋 Task Execution Log")

                # Show key events
                key_events = []
                for event in progress_data["events"]:
                    if event.event in ["task_created", "task_completed", "task_failed", "task_retry", "follow_ups_created"]:
                        key_events.append(f"**[{event.timestamp}]** {event.event.upper()}: {event.message}")

                if key_events:
                    for event_msg in key_events[-20:]:  # Last 20 events
                        st.caption(event_msg)
                else:
                    st.info("No task events logged")

                # Progress metrics
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Tasks Created", progress_data["tasks_created"])
                with col2:
                    st.metric("Tasks Completed", progress_data["tasks_completed"],
                             delta=f"{progress_data['tasks_completed']} succeeded" if progress_data["tasks_completed"] > 0 else None)
                with col3:
                    st.metric("Tasks Failed", progress_data["tasks_failed"],
                             delta=f"{progress_data['tasks_failed']} failed" if progress_data["tasks_failed"] > 0 else None,
                             delta_color="inverse")

            # Display entity relationships
            with entity_container:
                st.markdown("#### 🕸️ Entity Network")

                if result["entity_relationships"]:
                    # Show top 10 entities with their relationships
                    entity_items = list(result["entity_relationships"].items())[:10]

                    for entity, related in entity_items:
                        with st.expander(f"**{entity}** ({len(related)} connections)", expanded=False):
                            if related:
                                st.markdown("**Connected to:**")
                                for rel in related[:10]:  # Top 10 connections
                                    st.caption(f"• {rel}")
                            else:
                                st.caption("No connections discovered")
                else:
                    st.info("No entity relationships discovered (tasks may have failed or returned no results)")

            # Display final report
            with report_container:
                st.markdown("---")
                st.markdown("### 📄 Final Research Report")
                st.markdown(result["report"])

            # Display statistics
            with stats_container:
                st.markdown("---")
                st.markdown("### 📊 Research Statistics")

                col1, col2, col3, col4 = st.columns(4)

                with col1:
                    st.metric("Tasks Executed", result["tasks_executed"])
                with col2:
                    st.metric("Tasks Failed", result["tasks_failed"])
                with col3:
                    st.metric("Total Results", result["total_results"])
                with col4:
                    st.metric("Elapsed Time", f"{result['elapsed_minutes']:.1f} min")

                # Entities discovered
                st.markdown(f"**Entities Discovered:** {len(result['entities_discovered'])}")
                if result['entities_discovered']:
                    st.caption(", ".join(result['entities_discovered'][:20]))

                # Sources searched
                st.markdown(f"**Sources Searched:** {len(result['sources_searched'])}")
                if result['sources_searched']:
                    st.caption(", ".join(result['sources_searched']))

                # Export results
                st.markdown("---")
                st.markdown("### 📥 Export Results")

                # Export as JSON
                export_data = {
                    "research_question": research_question,
                    "timestamp": datetime.now().isoformat(),
                    "configuration": {
                        "max_tasks": max_tasks,
                        "max_time_minutes": max_time_minutes,
                        "max_retries": max_retries,
                        "min_results_per_task": min_results_per_task
                    },
                    "results": result,
                    "progress_log": [
                        {
                            "timestamp": event.timestamp,
                            "event": event.event,
                            "message": event.message,
                            "task_id": event.task_id
                        }
                        for event in progress_data["events"]
                    ]
                }

                col_e1, col_e2 = st.columns(2)

                with col_e1:
                    # Export report as markdown
                    report_md = f"""# Deep Research Report

**Question:** {research_question}
**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Tasks Executed:** {result['tasks_executed']}
**Total Results:** {result['total_results']}

---

{result['report']}

---

## Statistics

- Tasks Executed: {result['tasks_executed']}
- Tasks Failed: {result['tasks_failed']}
- Total Results: {result['total_results']}
- Entities Discovered: {len(result['entities_discovered'])}
- Elapsed Time: {result['elapsed_minutes']:.1f} minutes

## Entities Discovered

{', '.join(result['entities_discovered']) if result['entities_discovered'] else 'None'}

## Sources Searched

{', '.join(result['sources_searched']) if result['sources_searched'] else 'None'}
"""
                    st.download_button(
                        "📄 Download Report (Markdown)",
                        report_md,
                        f"deep_research_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
                        "text/markdown",
                        key="download_report_md"
                    )

                with col_e2:
                    # Export full data as JSON
                    json_data = json.dumps(export_data, indent=2)
                    st.download_button(
                        "📊 Download Full Data (JSON)",
                        json_data,
                        f"deep_research_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                        "application/json",
                        key="download_full_json"
                    )

        except Exception as e:
            st.error(f"❌ Deep research failed: {str(e)}")
            st.exception(e)

    elif research_btn and not research_question:
        st.warning("⚠️ Please enter a research question")
