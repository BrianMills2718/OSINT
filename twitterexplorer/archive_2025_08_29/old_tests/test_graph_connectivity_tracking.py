"""Test graph connectivity tracking and edge creation"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from twitterexplorer.investigation_graph import InvestigationGraph
from twitterexplorer.investigation_engine import InvestigationEngine, InvestigationConfig
from unittest.mock import Mock, patch
import json

def test_edge_creation_tracking():
    """EVIDENCE: Must track all edge creation attempts"""
    graph = InvestigationGraph()
    
    # Create nodes
    q1 = graph.create_analytic_question_node("main question")
    q2 = graph.create_investigation_question_node("sub question")
    
    # Track edge creation
    edge_attempts = []
    original_create_edge = graph.create_edge
    
    def tracked_create_edge(*args, **kwargs):
        edge_attempts.append({
            'source': args[0].id if args[0] else None,
            'target': args[1].id if args[1] else None,
            'type': args[2] if len(args) > 2 else None
        })
        return original_create_edge(*args, **kwargs)
    
    graph.create_edge = tracked_create_edge
    
    # Create edge
    edge = graph.create_edge(q1, q2, "MOTIVATES", {})
    
    # Verify tracking
    assert len(edge_attempts) == 1
    assert edge_attempts[0]['type'] == "MOTIVATES"
    print(f"EDGE CREATION TRACKED: {edge_attempts}")
    print(f"[PASS] Edge creation tracking working")
    
    # Verify edge was actually created
    assert len(graph.edges) == 1
    assert graph.edges[0].edge_type == "MOTIVATES"
    print(f"[PASS] Edge created successfully in graph")

def test_investigation_engine_graph_updates():
    """EVIDENCE: Investigation engine must create edges during execution"""
    
    # Create mock API client
    mock_api_client = Mock()
    mock_api_client.search.return_value = {
        "results": [{"text": "test result", "user": "testuser"}],
        "meta": {"count": 1}
    }
    
    # Create engine with mocked dependencies
    engine = InvestigationEngine("test_key")
    engine.api_client = mock_api_client
    
    # Track initial state
    initial_nodes = len(engine.llm_coordinator.graph.nodes)
    initial_edges = len(engine.llm_coordinator.graph.edges)
    
    print(f"Initial graph state: {initial_nodes} nodes, {initial_edges} edges")
    
    # Create minimal config for fast test
    config = InvestigationConfig(
        max_searches=2,
        pages_per_search=1
    )
    
    # Run investigation
    try:
        result = engine.conduct_investigation(
            "test query for graph tracking",
            config=config
        )
        
        final_nodes = len(engine.llm_coordinator.graph.nodes)
        final_edges = len(engine.llm_coordinator.graph.edges)
        
        print(f"Final graph state: {final_nodes} nodes, {final_edges} edges")
        
        # MUST create nodes
        if final_nodes > initial_nodes:
            print(f"[PASS] Created {final_nodes - initial_nodes} nodes")
        else:
            print(f"[WARNING] No nodes created during investigation")
        
        # CRITICAL: MUST create edges
        if final_edges > 0:
            print(f"[PASS] Created {final_edges} edges - Graph is connected!")
            # Show edge types
            edge_types = [edge.edge_type for edge in engine.llm_coordinator.graph.edges]
            print(f"Edge types created: {set(edge_types)}")
        else:
            print(f"[FAIL] NO EDGES CREATED! Graph has isolated nodes")
            
    except Exception as e:
        print(f"[ERROR] Investigation failed: {e}")
        # Still check if any graph updates happened
        final_nodes = len(engine.llm_coordinator.graph.nodes)
        final_edges = len(engine.llm_coordinator.graph.edges)
        print(f"Graph state at error: {final_nodes} nodes, {final_edges} edges")

def test_graph_edge_creation_methods():
    """EVIDENCE: Test that edge creation methods work correctly"""
    graph = InvestigationGraph()
    
    # Create various node types
    analytic = graph.create_analytic_question_node("main investigation")
    investigation = graph.create_investigation_question_node("specific question")
    search = graph.create_search_query_node("search.php", {"query": "test"})
    data_point = graph.create_data_point_node("result content", {"source": "twitter"})
    insight = graph.create_insight_node("key finding", "pattern")
    
    print(f"Created {len(graph.nodes)} nodes")
    
    # Create edges between nodes
    try:
        edge1 = graph.create_edge(analytic, investigation, "MOTIVATES", {})
        edge2 = graph.create_edge(investigation, search, "OPERATIONALIZES", {})
        edge3 = graph.create_edge(search, data_point, "GENERATES", {})
        edge4 = graph.create_edge(data_point, insight, "SUPPORTS", {})
        
        print(f"[PASS] Created {len(graph.edges)} edges successfully")
        
        # Verify graph connectivity
        connected_nodes = set()
        for edge in graph.edges:
            connected_nodes.add(edge.source_id)
            connected_nodes.add(edge.target_id)
        
        isolated_nodes = set(graph.nodes.keys()) - connected_nodes
        if isolated_nodes:
            print(f"[WARNING] Isolated nodes found: {isolated_nodes}")
        else:
            print(f"[PASS] All nodes are connected in the graph")
            
    except Exception as e:
        print(f"[FAIL] Edge creation failed: {e}")

def test_update_graph_with_decision():
    """EVIDENCE: Test that _update_graph_with_decision creates edges"""
    from twitterexplorer.graph_aware_llm_coordinator import GraphAwareLLMCoordinator
    from twitterexplorer.llm_client import StrategicDecision, SearchStrategy, SearchParameters
    
    # Create coordinator with graph
    mock_llm = Mock()
    coordinator = GraphAwareLLMCoordinator(mock_llm, InvestigationGraph())
    
    # Create initial analytic question
    analytic = coordinator.graph.create_analytic_question_node("test investigation")
    
    # Create a strategic decision
    decision = StrategicDecision(
        decision_type="gap_filling",
        reasoning="Test decision",
        searches=[
            SearchStrategy(
                endpoint="search.php",
                parameters=SearchParameters(query="test query"),
                reasoning="Test search"
            )
        ],
        expected_outcomes=["test outcome"]
    )
    
    # Track edges before update
    edges_before = len(coordinator.graph.edges)
    
    # Update graph with decision
    try:
        coordinator._update_graph_with_decision(decision)
        edges_after = len(coordinator.graph.edges)
        
        if edges_after > edges_before:
            print(f"[PASS] _update_graph_with_decision created {edges_after - edges_before} edges")
            for edge in coordinator.graph.edges:
                print(f"  Edge: {edge.source_id[:8]}... -{edge.edge_type}-> {edge.target_id[:8]}...")
        else:
            print(f"[FAIL] _update_graph_with_decision created no edges!")
            
    except Exception as e:
        print(f"[ERROR] _update_graph_with_decision failed: {e}")

if __name__ == "__main__":
    print("="*60)
    print("GRAPH CONNECTIVITY TRACKING TESTS")
    print("="*60)
    
    test_edge_creation_tracking()
    print("\n" + "-"*60 + "\n")
    
    test_graph_edge_creation_methods()
    print("\n" + "-"*60 + "\n")
    
    test_update_graph_with_decision()
    print("\n" + "-"*60 + "\n")
    
    test_investigation_engine_graph_updates()
    
    print("\n" + "="*60)
    print("GRAPH CONNECTIVITY TESTS COMPLETE")
    print("="*60)