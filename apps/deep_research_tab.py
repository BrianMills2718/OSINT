#!/usr/bin/env python3
"""
Deep Research tab for Streamlit UI.
Integrates v2 RecursiveResearchAgent with live progress display.
"""

import streamlit as st
import asyncio
import logging
import os
import sys
from pathlib import Path
from datetime import datetime
import json

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from research.recursive_agent import RecursiveResearchAgent, Constraints, GoalStatus
from dotenv import load_dotenv

load_dotenv()


# Set up logger for this module
logger = logging.getLogger(__name__)


def render_deep_research_tab(openai_api_key_from_ui):
    """Render the Deep Research tab in Streamlit UI."""

    st.markdown("### 🔬 Deep Investigation (v2)")
    st.caption("Recursive goal-based research with LLM-driven decomposition and synthesis")

    # Get OpenAI API key
    openai_api_key = None
    if openai_api_key_from_ui:
        openai_api_key = openai_api_key_from_ui
    elif hasattr(st, 'secrets') and "OPENAI_API_KEY" in st.secrets:
        try:
            openai_api_key = st.secrets["OPENAI_API_KEY"]
        except Exception as e:
            # Streamlit secrets access error - non-critical, fall back to env
            logger.warning(f"Failed to load OpenAI API key from Streamlit secrets: {e}", exc_info=True)
            pass
    else:
        openai_api_key = os.getenv("OPENAI_API_KEY")

    if not openai_api_key:
        st.error("OpenAI API Key Required")
        with st.expander("How to configure OpenAI API Key", expanded=True):
            st.markdown("""
            **For Local Development:**
            1. Create a `.env` file in the project directory
            2. Add: `OPENAI_API_KEY=your-key-here`
            3. Restart the app

            **For Streamlit Cloud Deployment:**
            1. Go to App Settings -> Secrets
            2. Add: `OPENAI_API_KEY = "your-key-here"`

            **Get your API key:** https://platform.openai.com/api-keys
            """)
        return

    # Set API key
    os.environ["OPENAI_API_KEY"] = openai_api_key

    # Info box explaining the v2 architecture
    st.info("""
    **v2 Recursive Research Agent:**

    - **Recursive goal decomposition**: Complex questions automatically break into sub-goals
    - **LLM-driven decisions**: AI decides when to decompose vs execute directly
    - **Dynamic depth**: Explores as deep as needed (configurable max)
    - **Synthesis at every level**: Results synthesized hierarchically
    - **Cost tracking**: Real-time cost monitoring
    - **Simpler architecture**: ~1,200 lines vs 4,392 in v1

    Use for complex, multi-part research questions.
    """)

    # Research question input
    st.markdown("#### Your Research Question")

    with st.expander("Example Questions for Deep Research", expanded=False):
        st.markdown("""
        **Complex Multi-Part Questions:**
        - "Investigate Palantir government contracts, lobbying activities, and controversies"
        - "What is the relationship between JSOC and CIA Title 50 operations?"
        - "How do federal cybersecurity contracts connect to cleared job opportunities?"

        **Entity-Focused Research:**
        - "Map the relationships between defense contractors working on AI security"
        - "What organizations are involved in signals intelligence collection?"

        **Investigative Questions:**
        - "Trace the evolution of drone warfare programs across military and intelligence agencies"
        - "What are the oversight mechanisms for covert operations?"
        """)

    research_question = st.text_area(
        "What would you like to investigate?",
        placeholder="Example: Investigate Palantir government contracts, lobbying activities, and controversies",
        height=100,
        key="deep_research_question"
    )

    # Configuration options - v2 style
    st.markdown("#### Research Configuration")

    col1, col2, col3 = st.columns(3)

    with col1:
        max_depth = st.number_input(
            "Max Depth",
            min_value=1,
            max_value=20,
            value=8,
            help="Maximum recursion depth for goal decomposition"
        )

    with col2:
        max_time_minutes = st.number_input(
            "Max Time (minutes)",
            min_value=1,
            max_value=120,
            value=15,
            help="Maximum investigation time in minutes"
        )

    with col3:
        max_goals = st.number_input(
            "Max Goals",
            min_value=5,
            max_value=100,
            value=30,
            help="Maximum total goals to pursue"
        )

    # Advanced settings
    with st.expander("Advanced Settings", expanded=False):
        col_a1, col_a2 = st.columns(2)

        with col_a1:
            max_cost = st.number_input(
                "Max Cost ($)",
                min_value=0.1,
                max_value=20.0,
                value=5.0,
                help="Maximum cost in dollars for LLM calls"
            )

        with col_a2:
            max_concurrent = st.number_input(
                "Max Concurrent",
                min_value=1,
                max_value=10,
                value=5,
                help="Maximum concurrent tasks"
            )

    # Research button
    research_btn = st.button("Start Deep Research", type="primary", use_container_width=True, key="deep_research_btn")

    if research_btn and research_question:
        # Create output directory
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        clean_question = "".join(c if c.isalnum() or c == " " else "_" for c in research_question[:50])
        clean_question = "_".join(clean_question.split())
        output_dir = Path("data/research_v2") / f"{timestamp}_{clean_question}"
        output_dir.mkdir(parents=True, exist_ok=True)

        # Create empty placeholders for live updates
        st.markdown("### Research Progress")

        # Live progress indicators
        progress_status = st.empty()
        progress_metrics = st.empty()

        # Final result containers
        synthesis_container = st.container()
        evidence_container = st.container()
        subgoals_container = st.container()
        stats_container = st.container()

        try:
            progress_status.info("Initializing v2 recursive research agent...")

            # Build constraints
            constraints = Constraints(
                max_depth=max_depth,
                max_time_seconds=max_time_minutes * 60,
                max_goals=max_goals,
                max_cost_dollars=max_cost,
                max_concurrent_tasks=max_concurrent
            )

            # Create agent
            agent = RecursiveResearchAgent(
                constraints=constraints,
                output_dir=str(output_dir)
            )

            progress_status.info("Research in progress... (check terminal for detailed logs)")

            # Run research
            result = asyncio.run(agent.research(research_question))

            # Update status based on result
            if result.status == GoalStatus.COMPLETED:
                progress_status.success(f"Research complete! Found {len(result.evidence)} pieces of evidence")
            elif result.status == GoalStatus.PARTIAL:
                progress_status.warning(f"Research partially complete ({len(result.evidence)} evidence pieces)")
            else:
                progress_status.error(f"Research failed: {result.status.value}")

            # Show metrics
            with progress_metrics.container():
                col_m1, col_m2, col_m3, col_m4 = st.columns(4)
                with col_m1:
                    st.metric("Evidence", len(result.evidence))
                with col_m2:
                    st.metric("Sub-goals", len(result.sub_results))
                with col_m3:
                    st.metric("Duration", f"{result.duration_seconds:.1f}s")
                with col_m4:
                    st.metric("Cost", f"${result.cost_dollars:.4f}")

            # Display synthesis
            with synthesis_container:
                st.markdown("---")
                st.markdown("### Research Synthesis")
                if result.synthesis:
                    st.markdown(result.synthesis)
                else:
                    st.info("No synthesis generated")

            # Display evidence by source
            with evidence_container:
                st.markdown("---")
                st.markdown("### Evidence Sources")

                # Group evidence by source
                evidence_by_source = {}
                for e in result.evidence:
                    source = e.source or "Unknown"
                    if source not in evidence_by_source:
                        evidence_by_source[source] = []
                    evidence_by_source[source].append(e)

                if evidence_by_source:
                    for source, evidence_list in evidence_by_source.items():
                        with st.expander(f"{source} ({len(evidence_list)} results)", expanded=False):
                            for e in evidence_list[:15]:  # Limit display
                                st.markdown(f"**{e.title}**")
                                if e.url:
                                    st.markdown(f"[Link]({e.url})")
                                if e.content:
                                    st.caption(e.content[:300] + "..." if len(e.content) > 300 else e.content)
                                st.markdown("---")
                else:
                    st.info("No evidence collected")

            # Display sub-goals
            with subgoals_container:
                st.markdown("---")
                st.markdown("### Sub-Goals Explored")

                if result.sub_results:
                    for i, sub in enumerate(result.sub_results, 1):
                        status_icon = {
                            GoalStatus.COMPLETED: "Done",
                            GoalStatus.PARTIAL: "Partial",
                            GoalStatus.FAILED: "Failed",
                            GoalStatus.SKIPPED: "Skipped"
                        }.get(sub.status, "?")

                        with st.expander(f"Sub-goal {i}: {sub.goal[:80]}... [{status_icon}]", expanded=False):
                            st.write(f"**Goal:** {sub.goal}")
                            st.write(f"**Status:** {sub.status.value}")
                            st.write(f"**Confidence:** {int(sub.confidence * 100)}%")
                            st.write(f"**Evidence:** {len(sub.evidence)} pieces")
                            st.write(f"**Depth:** {sub.depth}")

                            if sub.synthesis:
                                st.markdown("**Synthesis:**")
                                st.caption(sub.synthesis[:500] + "..." if len(sub.synthesis) > 500 else sub.synthesis)
                else:
                    st.info("No sub-goals generated (query may have been directly executable)")

            # Statistics and export
            with stats_container:
                st.markdown("---")
                st.markdown("### Statistics & Export")

                col_s1, col_s2, col_s3, col_s4 = st.columns(4)
                with col_s1:
                    st.metric("Status", result.status.value)
                with col_s2:
                    st.metric("Confidence", f"{int(result.confidence * 100)}%")
                with col_s3:
                    st.metric("Max Depth Reached", result.depth)
                with col_s4:
                    sources_count = len(evidence_by_source) if evidence_by_source else 0
                    st.metric("Sources Used", sources_count)

                st.markdown(f"**Output saved to:** `{output_dir}`")

                # Export buttons
                col_e1, col_e2 = st.columns(2)

                with col_e1:
                    # Export as markdown report
                    report_lines = [
                        "# Research Report",
                        "",
                        f"**Question:** {research_question}",
                        f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                        f"**Status:** {result.status.value}",
                        f"**Confidence:** {int(result.confidence * 100)}%",
                        f"**Evidence:** {len(result.evidence)} pieces",
                        f"**Duration:** {result.duration_seconds:.1f}s",
                        f"**Cost:** ${result.cost_dollars:.4f}",
                        "",
                        "---",
                        "",
                        "## Synthesis",
                        "",
                        result.synthesis or "No synthesis generated",
                        "",
                        "---",
                        "",
                        "## Evidence Summary",
                        ""
                    ]

                    for source, evidence_list in evidence_by_source.items():
                        report_lines.append(f"### {source} ({len(evidence_list)} results)")
                        report_lines.append("")
                        for e in evidence_list[:10]:
                            report_lines.append(f"- **{e.title}**")
                            if e.url:
                                report_lines.append(f"  - {e.url}")
                        report_lines.append("")

                    report_md = "\n".join(report_lines)

                    st.download_button(
                        "Download Report (Markdown)",
                        report_md,
                        f"research_report_{timestamp}.md",
                        "text/markdown",
                        key="download_report_md"
                    )

                with col_e2:
                    # Export as JSON
                    export_data = {
                        "question": research_question,
                        "timestamp": datetime.now().isoformat(),
                        "status": result.status.value,
                        "confidence": result.confidence,
                        "evidence_count": len(result.evidence),
                        "sub_goals_count": len(result.sub_results),
                        "duration_seconds": result.duration_seconds,
                        "cost_dollars": result.cost_dollars,
                        "synthesis": result.synthesis,
                        "configuration": {
                            "max_depth": max_depth,
                            "max_time_minutes": max_time_minutes,
                            "max_goals": max_goals,
                            "max_cost": max_cost,
                            "max_concurrent": max_concurrent
                        },
                        "evidence": [
                            {
                                "title": e.title,
                                "url": e.url,
                                "source": e.source,
                                "content": e.content[:500] if e.content else None
                            }
                            for e in result.evidence
                        ]
                    }

                    st.download_button(
                        "Download Full Data (JSON)",
                        json.dumps(export_data, indent=2),
                        f"research_data_{timestamp}.json",
                        "application/json",
                        key="download_full_json"
                    )

        except Exception as e:
            # Deep research failed
            logger.error(f"Deep research failed: {e}", exc_info=True)
            st.error(f"Deep research failed: {str(e)}")
            st.exception(e)

    elif research_btn and not research_question:
        st.warning("Please enter a research question")
