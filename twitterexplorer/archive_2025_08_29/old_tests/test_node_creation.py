"""Test suite for DataPoint and Insight node creation"""
import pytest
import sys
from datetime import datetime
from twitterexplorer.investigation_graph import InvestigationGraph, NodeType


def test_datapoint_node_creation():
    """EVIDENCE: DataPoint nodes must be created and tracked"""
    graph = InvestigationGraph()
    
    # Create a DataPoint node
    datapoint = graph.create_datapoint_node(
        content="User @example tweeted about topic X",
        source="twitter_search",
        timestamp=datetime.now().isoformat()
    )
    
    # Verify node was created
    assert datapoint is not None
    assert datapoint.id in graph.nodes
    assert datapoint.type == NodeType.DATAPOINT
    assert datapoint.attributes['content'] == "User @example tweeted about topic X"
    assert datapoint.attributes['source'] == "twitter_search"
    assert 'timestamp' in datapoint.attributes
    
    print(f"[PASS] DataPoint node created: {datapoint.id}")
    return datapoint


def test_insight_node_creation():
    """EVIDENCE: Insight nodes must be created from DataPoints"""
    graph = InvestigationGraph()
    
    # Create some DataPoints first
    dp1 = graph.create_datapoint_node(
        content="Multiple users discussing topic X",
        source="search_1"
    )
    dp2 = graph.create_datapoint_node(
        content="Topic X trending in region Y",
        source="search_2"
    )
    
    # Create an Insight node
    insight = graph.create_insight_node_enhanced(
        content="Topic X has significant regional interest",
        confidence=0.8,
        supporting_datapoints=[dp1.id, dp2.id]
    )
    
    # Verify node was created
    assert insight is not None
    assert insight.id in graph.nodes
    assert insight.type == NodeType.INSIGHT
    assert insight.attributes['confidence'] == 0.8
    assert len(insight.attributes['supporting_datapoints']) == 2
    
    print(f"[PASS] Insight node created: {insight.id}")
    return insight


def test_datapoint_to_insight_edges():
    """EVIDENCE: Edges must connect DataPoints to Insights"""
    graph = InvestigationGraph()
    
    # Create DataPoints
    dp1 = graph.create_datapoint_node(content="Data 1", source="src1")
    dp2 = graph.create_datapoint_node(content="Data 2", source="src2")
    
    # Create Insight
    insight = graph.create_insight_node_enhanced(
        content="Combined insight",
        confidence=0.75,
        supporting_datapoints=[dp1.id, dp2.id]
    )
    
    # Verify edges were created
    edges_from_dp1 = [e for e in graph.edges if e.source_id == dp1.id and e.target_id == insight.id]
    edges_from_dp2 = [e for e in graph.edges if e.source_id == dp2.id and e.target_id == insight.id]
    
    assert len(edges_from_dp1) > 0, "No edge from DataPoint 1 to Insight"
    assert len(edges_from_dp2) > 0, "No edge from DataPoint 2 to Insight"
    assert edges_from_dp1[0].edge_type == "SUPPORTS"
    
    print(f"[PASS] Edges created from DataPoints to Insight")
    return graph


def test_search_to_datapoint_integration():
    """EVIDENCE: Search results must generate DataPoint nodes"""
    graph = InvestigationGraph()
    
    # Simulate search result
    search_result = {
        'endpoint': 'search.php',
        'query': 'test topic',
        'results': [
            {'text': 'Result 1 text', 'author': 'user1'},
            {'text': 'Result 2 text', 'author': 'user2'}
        ]
    }
    
    # Create DataPoints from search
    datapoints = graph.create_datapoints_from_search(search_result)
    
    # Verify DataPoints were created
    assert len(datapoints) == 2
    assert all(dp.type == NodeType.DATAPOINT for dp in datapoints)
    assert datapoints[0].attributes['content'] == 'Result 1 text'
    assert datapoints[0].attributes['source'] == 'search.php'
    
    print(f"[PASS] Created {len(datapoints)} DataPoints from search")
    return datapoints


def test_insight_generation_from_datapoints():
    """EVIDENCE: System must generate insights from accumulated DataPoints"""
    graph = InvestigationGraph()
    
    # Create multiple related DataPoints
    datapoints = []
    for i in range(5):
        dp = graph.create_datapoint_node(
            content=f"Tweet about controversial topic from user{i}",
            source=f"search_{i}"
        )
        datapoints.append(dp)
    
    # Generate insight from DataPoints
    insight = graph.generate_insight_from_datapoints(
        datapoints,
        insight_text="High engagement on controversial topic indicates public interest"
    )
    
    # Verify insight was created with proper connections
    assert insight is not None
    assert insight.type == NodeType.INSIGHT
    assert len(insight.attributes['supporting_datapoints']) == 5
    
    # Check all edges exist
    for dp in datapoints:
        edges = [e for e in graph.edges if e.source_id == dp.id and e.target_id == insight.id]
        assert len(edges) > 0, f"Missing edge from {dp.id} to insight"
    
    print(f"[PASS] Generated insight from {len(datapoints)} DataPoints")
    return insight


def test_node_type_enum():
    """EVIDENCE: NodeType enum must include DATAPOINT and INSIGHT"""
    # Check that NodeType enum has required values
    assert hasattr(NodeType, 'DATAPOINT'), "NodeType.DATAPOINT missing"
    assert hasattr(NodeType, 'INSIGHT'), "NodeType.INSIGHT missing"
    
    # Verify string values
    assert NodeType.DATAPOINT.value == 'datapoint'
    assert NodeType.INSIGHT.value == 'insight'
    
    print("[PASS] NodeType enum has DATAPOINT and INSIGHT")


if __name__ == "__main__":
    print("\n=== Testing DataPoint and Insight Node Creation ===\n")
    
    try:
        test_node_type_enum()
        dp = test_datapoint_node_creation()
        insight = test_insight_node_creation()
        graph = test_datapoint_to_insight_edges()
        datapoints = test_search_to_datapoint_integration()
        generated_insight = test_insight_generation_from_datapoints()
        
        print("\n[SUCCESS] All node creation tests passed!")
        
    except AssertionError as e:
        print(f"\n[FAILURE] Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)