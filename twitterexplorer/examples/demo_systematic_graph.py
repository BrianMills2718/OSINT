"""Demonstration of systematic graph generation for realistic investigations"""
import json
from datetime import datetime, timedelta
import random
from twitterexplorer.graph_visualizer import InvestigationGraphVisualizer
from twitterexplorer.investigation_engine import (
    InvestigationEngine, 
    InvestigationSession,
    InvestigationRound,
    InvestigationConfig,
    SearchAttempt
)

def generate_realistic_investigation():
    """Generate a realistic investigation with many searches"""
    print("\n" + "="*80)
    print(" SYSTEMATIC GRAPH VISUALIZATION - REALISTIC INVESTIGATION")
    print("="*80)
    
    # Create visualizer
    visualizer = InvestigationGraphVisualizer()
    
    # Investigation parameters
    query = "Trump Epstein connections 2002 Mar-a-Lago parties"
    print(f"\nInvestigation Query: {query}")
    print("-"*80)
    
    # Add initial query node (ROOT OF THE GRAPH)
    query_id = visualizer.add_query_node(query)
    print(f"\n[OK] Added root query node: {query_id}")
    
    # Simulate realistic search progression
    search_strategies = [
        # Round 1: Broad searches
        ("Trump Epstein 2002", "search.php", 127),
        ("Mar-a-Lago parties 2002", "search.php", 89),
        ("Epstein flight logs Trump", "search.php", 156),
        
        # Round 2: Timeline searches
        ("realDonaldTrump", "timeline.php", 45),
        ("jeffreyepstein", "timeline.php", 0),  # Dead end - account suspended
        
        # Round 3: Specific date searches
        ("Trump March 15 2002", "search.php", 34),
        ("Epstein Palm Beach 2002", "search.php", 78),
        ("calendar girl party Mar-a-Lago", "search.php", 12),
        
        # Round 4: Follow-up searches
        ("Trump denies knowing Epstein", "search.php", 234),
        ("court documents Trump Epstein", "search.php", 67),
        ("witness testimony Mar-a-Lago", "search.php", 23),
        
        # Round 5: Financial searches
        ("Trump Organization Epstein payment", "search.php", 8),
        ("3.5 million transaction 2002", "search.php", 2),
        
        # Round 6: More timelines
        ("VirginiaGiuffre", "timeline.php", 156),
        ("AlanDershowitz", "timeline.php", 89),
        
        # Round 7: Verification searches
        ("fact check Trump Epstein friendship", "search.php", 145),
        ("NBC footage Trump Epstein 1992", "search.php", 67),
        ("Katie Johnson lawsuit", "search.php", 45),
        
        # Round 8: Dead ends
        ("Epstein Trump business deals", "search.php", 0),
        ("Trump Tower Epstein apartment", "search.php", 0),
        ("find different angle", "search.php", 0),  # Generic dead end
    ]
    
    print(f"\nExecuting {len(search_strategies)} searches...")
    print("-"*40)
    
    # Track all nodes for pattern detection
    all_search_ids = []
    all_datapoint_ids = []
    
    # Execute searches and create nodes
    for i, (search_query, endpoint, result_count) in enumerate(search_strategies, 1):
        # Create search parameters
        if endpoint == "timeline.php":
            params = {"screenname": search_query}
        else:
            params = {"query": search_query}
        
        # Add search node
        search_id = visualizer.add_search_node(params, endpoint, i, parent_id=query_id)
        all_search_ids.append(search_id)
        
        # Progress indicator
        status = "[OK]" if result_count > 0 else "[--]"
        print(f"{status} Search #{i:2d}: {search_query[:40]:<40} | Results: {result_count:3d}")
        
        # Add datapoints for searches with results
        if result_count > 0:
            # Simulate finding significant results (30% chance per result)
            significant_findings = []
            
            if "court documents" in search_query.lower():
                finding = "Court filings from March 2002 show Trump and Epstein as co-defendants in assault case"
                dp_id = visualizer.add_datapoint_node(finding, endpoint, search_id, relevance=0.9)
                all_datapoint_ids.append(dp_id)
                significant_findings.append(finding)
            
            if "flight logs" in search_query.lower():
                finding = "FAA logs confirm Trump flew on Epstein's plane from Palm Beach to Newark on Feb 28, 2002"
                dp_id = visualizer.add_datapoint_node(finding, endpoint, search_id, relevance=0.85)
                all_datapoint_ids.append(dp_id)
                significant_findings.append(finding)
            
            if "witness testimony" in search_query.lower():
                finding = "Former Mar-a-Lago employee: 'Trump and Epstein recruited girls at calendar auditions'"
                dp_id = visualizer.add_datapoint_node(finding, endpoint, search_id, relevance=0.8)
                all_datapoint_ids.append(dp_id)
                significant_findings.append(finding)
            
            if "3.5 million" in search_query.lower():
                finding = "Bank records show $3.5M transfer from Trump Org to shell company linked to Epstein"
                dp_id = visualizer.add_datapoint_node(finding, endpoint, search_id, relevance=0.75)
                all_datapoint_ids.append(dp_id)
                significant_findings.append(finding)
            
            if "NBC footage" in search_query.lower():
                finding = "1992 NBC video shows Trump saying about Epstein: 'He likes them young'"
                dp_id = visualizer.add_datapoint_node(finding, endpoint, search_id, relevance=0.95)
                all_datapoint_ids.append(dp_id)
                significant_findings.append(finding)
            
            # Random additional findings based on result count
            if result_count > 50 and random.random() > 0.5:
                finding = f"Multiple sources confirm meetings between Trump and Epstein in {random.choice(['January', 'February', 'March'])} 2002"
                dp_id = visualizer.add_datapoint_node(finding, endpoint, search_id, relevance=0.6)
                all_datapoint_ids.append(dp_id)
                significant_findings.append(finding)
            
            if significant_findings:
                print(f"    -> Found {len(significant_findings)} significant finding(s)")
    
    # Generate insights from patterns
    print(f"\n[PATTERN DETECTION]")
    print("-"*40)
    
    insights_data = [
        ("Multiple independent sources confirm Trump-Epstein meetings at Mar-a-Lago in 2002", 0.85, all_datapoint_ids[:3]),
        ("Financial records and flight logs establish ongoing relationship despite denials", 0.9, all_datapoint_ids[1:4]),
        ("Witness testimonies corroborate recruitment activities at private parties", 0.75, all_datapoint_ids[2:5]),
        ("Timeline contradictions between public statements and documented evidence", 0.95, all_datapoint_ids[:6]),
        ("Pattern of shell company transactions matches known money laundering schemes", 0.7, all_datapoint_ids[3:5])
    ]
    
    for i, (synthesis, confidence, supporting) in enumerate(insights_data, 1):
        if len(supporting) > 0:  # Only add insights with supporting evidence
            insight_id = visualizer.add_insight_node(synthesis, confidence, supporting[:3])
            print(f"[OK] Insight #{i}: {synthesis[:60]}... (confidence: {confidence:.0%})")
    
    # Get statistics
    print(f"\n[GRAPH STATISTICS]")
    print("-"*40)
    stats = visualizer.get_statistics()
    
    print(f"Total Nodes: {stats['total_nodes']}")
    print(f"  - Initial Query: {stats['node_counts']['query']}")
    print(f"  - Search Queries: {stats['node_counts']['search']}")
    print(f"  - Findings (DataPoints): {stats['node_counts']['datapoint']}")
    print(f"  - Insights (Patterns): {stats['node_counts']['insight']}")
    print(f"\nTotal Connections: {stats['total_edges']}")
    
    for edge_type, count in stats['edge_counts'].items():
        print(f"  - {edge_type}: {count}")
    
    if stats['metrics'].get('dead_end_searches'):
        print(f"\nDead-end Searches (no findings): {len(stats['metrics']['dead_end_searches'])}")
        for dead_end in stats['metrics']['dead_end_searches'][:5]:
            print(f"  - {dead_end}")
    
    print(f"\nGraph Density: {stats['metrics'].get('density', 0):.3f}")
    print(f"Average Connections per Node: {stats['metrics'].get('avg_degree', 0):.1f}")
    
    # Save visualization
    print(f"\n[SAVING VISUALIZATION]")
    print("-"*40)
    
    # Save HTML file
    filepath = visualizer.save_visualization("investigation_realistic.html")
    print(f"[OK] HTML visualization saved to: {filepath}")
    
    # Export data for Streamlit
    vis_data = visualizer.export_vis_data()
    with open('investigation_data.json', 'w') as f:
        json.dump(vis_data, f, indent=2)
    print(f"[OK] Graph data exported to: investigation_data.json")
    
    # Get Streamlit component
    streamlit_data, streamlit_html = visualizer.get_streamlit_component()
    print(f"[OK] Streamlit component ready ({len(streamlit_html)} chars of HTML)")
    
    print("\n" + "="*80)
    print(" DEMONSTRATION COMPLETE")
    print("="*80)
    print("\nThis systematic approach can be integrated into the InvestigationEngine")
    print("to automatically generate graphs from any investigation session.")
    print("\nKey improvements over ad-hoc approach:")
    print("  1. Initial query node included as graph root")
    print("  2. Handles realistic investigation sizes (20+ searches)")
    print("  3. Systematic Python-based generation (InvestigationGraphVisualizer class)")
    print("  4. Ready for Streamlit integration (get_streamlit_component method)")
    print("  5. Identifies dead-end searches automatically")
    print("  6. Calculates graph metrics and statistics")
    
    return visualizer


def demonstrate_integration_with_engine():
    """Show how to integrate with the actual InvestigationEngine"""
    print("\n" + "="*80)
    print(" INTEGRATION WITH INVESTIGATION ENGINE")
    print("="*80)
    
    code_example = """
# In investigation_engine.py, after investigation completes:

from twitterexplorer.graph_visualizer import create_graph_from_investigation

class InvestigationEngine:
    def conduct_investigation(self, query, config):
        # ... existing investigation code ...
        
        # After investigation completes
        if self.graph_mode and self.llm_coordinator.graph:
            # Create visualization from session and LLM graph
            visualizer = create_graph_from_investigation(
                session, 
                self.llm_coordinator.graph
            )
            
            # Save visualization
            visualizer.save_visualization(f"investigation_{session.session_id}.html")
            
            # For Streamlit integration
            if self.progress_container:
                data, html = visualizer.get_streamlit_component()
                self.progress_container.markdown(html, unsafe_allow_html=True)
        
        return session
"""
    
    print(code_example)
    
    print("\n" + "="*80)
    print(" STREAMLIT INTEGRATION EXAMPLE")
    print("="*80)
    
    streamlit_code = """
# In app.py:

import streamlit as st
from twitterexplorer.graph_visualizer import create_graph_from_investigation

# After investigation completes
if st.session_state.get('investigation_complete'):
    session = st.session_state['investigation_session']
    
    # Create graph visualization
    visualizer = create_graph_from_investigation(session)
    
    # Display statistics
    stats = visualizer.get_statistics()
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Searches", stats['node_counts']['search'])
    with col2:
        st.metric("Findings", stats['node_counts']['datapoint'])
    with col3:
        st.metric("Insights", stats['node_counts']['insight'])
    with col4:
        st.metric("Dead Ends", len(stats['metrics'].get('dead_end_searches', [])))
    
    # Display interactive graph
    data, html = visualizer.get_streamlit_component()
    st.components.v1.html(html, height=600)
    
    # Option to download
    if st.button("Download Graph"):
        filepath = visualizer.save_visualization()
        with open(filepath, 'r') as f:
            st.download_button(
                "Download HTML", 
                f.read(), 
                file_name="investigation_graph.html",
                mime="text/html"
            )
"""
    
    print(streamlit_code)


if __name__ == "__main__":
    # Run realistic demonstration
    visualizer = generate_realistic_investigation()
    
    # Show integration examples
    demonstrate_integration_with_engine()