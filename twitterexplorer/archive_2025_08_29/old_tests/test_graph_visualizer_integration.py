"""Test integration of graph visualizer with InvestigationEngine"""
from twitterexplorer.graph_visualizer import InvestigationGraphVisualizer, create_graph_from_investigation
from twitterexplorer.investigation_engine import (
    InvestigationEngine,
    InvestigationSession,
    InvestigationConfig,
    InvestigationRound,
    SearchAttempt
)
from unittest.mock import Mock, patch
import json


def test_visualizer_basic_functionality():
    """Test basic graph visualizer functionality"""
    print("\n[TEST 1: Basic Functionality]")
    print("-"*40)
    
    viz = InvestigationGraphVisualizer()
    
    # Add query node (root)
    query_id = viz.add_query_node("Test investigation query")
    assert query_id in viz.nodes
    print(f"[OK] Query node added: {query_id}")
    
    # Add search nodes
    search1_id = viz.add_search_node(
        {"query": "test search 1"}, 
        "search.php", 
        1, 
        parent_id=query_id
    )
    assert search1_id in viz.nodes
    print(f"[OK] Search node added: {search1_id}")
    
    # Add datapoint
    dp_id = viz.add_datapoint_node(
        "Significant finding about the topic",
        "twitter",
        search_id=search1_id,
        relevance=0.8
    )
    assert dp_id in viz.nodes
    print(f"[OK] DataPoint node added: {dp_id}")
    
    # Add insight
    insight_id = viz.add_insight_node(
        "Pattern detected in findings",
        0.75,
        [dp_id]
    )
    assert insight_id in viz.nodes
    print(f"[OK] Insight node added: {insight_id}")
    
    # Check statistics
    stats = viz.get_statistics()
    assert stats['total_nodes'] == 4
    assert stats['total_edges'] == 3  # query->search, search->dp, dp->insight
    assert stats['node_counts']['query'] == 1
    assert stats['node_counts']['search'] == 1
    assert stats['node_counts']['datapoint'] == 1
    assert stats['node_counts']['insight'] == 1
    print(f"[OK] Statistics correct: {stats['total_nodes']} nodes, {stats['total_edges']} edges")
    
    # Export vis data
    vis_data = viz.export_vis_data()
    assert len(vis_data['nodes']) == 4
    assert len(vis_data['edges']) == 3
    print("[OK] Export to vis.js format works")
    
    # Generate HTML
    html = viz.generate_html()
    assert "Investigation Knowledge Graph" in html
    assert "vis.Network" in html
    assert query_id in html
    print(f"[OK] HTML generation works ({len(html)} chars)")
    
    print("\n[TEST 1 PASSED]")


def test_dead_end_detection():
    """Test that dead-end searches are properly identified"""
    print("\n[TEST 2: Dead-End Detection]")
    print("-"*40)
    
    viz = InvestigationGraphVisualizer()
    
    # Add query
    query_id = viz.add_query_node("Test query")
    
    # Add successful search with findings
    search1_id = viz.add_search_node(
        {"query": "successful search"},
        "search.php",
        1,
        parent_id=query_id
    )
    dp_id = viz.add_datapoint_node(
        "Found something",
        "twitter",
        search_id=search1_id
    )
    
    # Add dead-end searches (no findings)
    search2_id = viz.add_search_node(
        {"query": "dead end search"},
        "search.php",
        2,
        parent_id=query_id
    )
    
    search3_id = viz.add_search_node(
        {"screenname": "suspended_account"},
        "timeline.php",
        3,
        parent_id=query_id
    )
    
    # Check dead-end detection
    stats = viz.get_statistics()
    dead_ends = stats['metrics'].get('dead_end_searches', [])
    
    assert len(dead_ends) == 2
    assert any("dead end" in de for de in dead_ends)
    assert any("suspended" in de for de in dead_ends)
    print(f"[OK] Detected {len(dead_ends)} dead-end searches")
    
    print("\n[TEST 2 PASSED]")


def test_integration_with_investigation_session():
    """Test integration with actual InvestigationSession"""
    print("\n[TEST 3: InvestigationSession Integration]")
    print("-"*40)
    
    # Create mock investigation session
    session = InvestigationSession("Test Trump Epstein query", InvestigationConfig())
    round1 = InvestigationRound(1, "Initial round")
    
    # Add mock searches
    search1 = SearchAttempt(
        1, 1, "search.php", 
        {"query": "Trump Epstein 2002"},
        "General search", 
        5, 8.0, 1.0
    )
    search1._raw_results = [
        {"text": "Court documents from 2002...", "source": "twitter"}
    ]
    round1.searches.append(search1)
    
    search2 = SearchAttempt(
        2, 1, "timeline.php",
        {"screenname": "realDonaldTrump"},
        "Timeline",
        0, 0.0, 1.0
    )
    round1.searches.append(search2)
    
    session.rounds.append(round1)
    
    # Create visualization from session
    viz = create_graph_from_investigation(session)
    
    # Verify structure
    stats = viz.get_statistics()
    assert stats['node_counts']['query'] == 1  # Initial query
    assert stats['node_counts']['search'] == 2  # Two searches
    print(f"[OK] Created graph from session: {stats['total_nodes']} nodes")
    
    # Check dead-end detection
    dead_ends = stats['metrics'].get('dead_end_searches', [])
    assert len(dead_ends) == 2  # Both searches have no datapoints
    print(f"[OK] Dead-end searches identified: {len(dead_ends)}")
    
    print("\n[TEST 3 PASSED]")


def test_streamlit_component():
    """Test Streamlit component generation"""
    print("\n[TEST 4: Streamlit Component]")
    print("-"*40)
    
    viz = InvestigationGraphVisualizer()
    viz.add_query_node("Test query")
    
    # Get Streamlit component
    data, html = viz.get_streamlit_component()
    
    assert "investigation-network" in html
    assert "vis.Network" in html
    assert isinstance(data, dict)
    assert 'nodes' in data
    assert 'edges' in data
    assert 'statistics' in data
    
    print(f"[OK] Streamlit component generated ({len(html)} chars of HTML)")
    print(f"[OK] Data structure includes {len(data['nodes'])} nodes")
    
    print("\n[TEST 4 PASSED]")


def test_large_graph_handling():
    """Test handling of large investigations"""
    print("\n[TEST 5: Large Graph Handling]")
    print("-"*40)
    
    viz = InvestigationGraphVisualizer()
    
    # Add query
    query_id = viz.add_query_node("Large investigation")
    
    # Add many searches
    search_ids = []
    for i in range(50):
        search_id = viz.add_search_node(
            {"query": f"search query {i}"},
            "search.php",
            i+1,
            parent_id=query_id
        )
        search_ids.append(search_id)
        
        # Add findings for some searches
        if i % 3 == 0:  # 33% have findings
            for j in range(2):
                viz.add_datapoint_node(
                    f"Finding {i}-{j}",
                    "twitter",
                    search_id=search_id
                )
    
    # Add insights
    for i in range(5):
        viz.add_insight_node(
            f"Pattern {i}",
            0.7 + i*0.05,
            []  # No specific supporting nodes for simplicity
        )
    
    # Check stats
    stats = viz.get_statistics()
    assert stats['total_nodes'] == 1 + 50 + 34 + 5  # query + searches + datapoints + insights
    assert stats['node_counts']['search'] == 50
    
    # Check dead-ends
    dead_ends = stats['metrics'].get('dead_end_searches', [])
    assert len(dead_ends) == 33  # 67% have no findings
    
    print(f"[OK] Handled large graph: {stats['total_nodes']} nodes")
    print(f"[OK] Dead-end ratio: {len(dead_ends)}/{stats['node_counts']['search']}")
    
    # Test HTML generation for large graph
    html = viz.generate_html()
    assert len(html) > 10000  # Should be substantial
    print(f"[OK] Generated HTML for large graph ({len(html)} chars)")
    
    print("\n[TEST 5 PASSED]")


if __name__ == "__main__":
    print("="*60)
    print(" GRAPH VISUALIZER INTEGRATION TESTS")
    print("="*60)
    
    test_visualizer_basic_functionality()
    test_dead_end_detection()
    test_integration_with_investigation_session()
    test_streamlit_component()
    test_large_graph_handling()
    
    print("\n" + "="*60)
    print(" ALL TESTS PASSED!")
    print("="*60)
    print("\nThe InvestigationGraphVisualizer is ready for integration:")
    print("  1. Systematic Python-based graph generation")
    print("  2. Includes initial query as root node")
    print("  3. Handles realistic investigation sizes (50+ searches)")
    print("  4. Streamlit-ready component generation")
    print("  5. Automatic dead-end detection")
    print("  6. Complete statistics and metrics")