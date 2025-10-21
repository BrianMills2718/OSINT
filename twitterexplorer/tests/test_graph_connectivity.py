import pytest
import networkx as nx
import sys
import os
sys.path.insert(0, 'twitterexplorer')

from investigation_engine import InvestigationEngine, InvestigationConfig
from investigation_graph import InvestigationGraph

def test_root_node_creation():
    """Test AnalyticQuestion root node is created"""
    # Load API key
    import toml
    secrets_path = r'twitterexplorer\.streamlit\secrets.toml'
    secrets = toml.load(secrets_path)
    api_key = secrets.get('RAPIDAPI_KEY')
    
    engine = InvestigationEngine(api_key)
    result = engine.conduct_investigation("Trump health investigation", InvestigationConfig(max_searches=3))
    
    # Must have exactly 1 AnalyticQuestion root
    if engine.graph_mode and hasattr(engine.llm_coordinator, 'graph'):
        graph = engine.llm_coordinator.graph
        root_nodes = [node for node_id, node in graph.nodes.items() if node.node_type == "AnalyticQuestion"]
        assert len(root_nodes) == 1, f"Expected 1 AnalyticQuestion root, found {len(root_nodes)}"
        assert root_nodes[0].properties.get("is_root") == True, "Root node must have is_root=True"
    else:
        pytest.skip("Graph mode not enabled")

def test_single_connected_component():
    """Test graph forms one connected component"""
    # Load API key
    import toml
    secrets_path = r'twitterexplorer\.streamlit\secrets.toml'
    secrets = toml.load(secrets_path)
    api_key = secrets.get('RAPIDAPI_KEY')
    
    engine = InvestigationEngine(api_key)
    result = engine.conduct_investigation("Trump health investigation", InvestigationConfig(max_searches=3))
    
    if engine.graph_mode and hasattr(engine.llm_coordinator, 'graph'):
        # Convert to NetworkX and check connectivity
        graph = engine.llm_coordinator.graph
        G = nx.DiGraph()
        
        for node_id, node in graph.nodes.items():
            G.add_node(node_id, type=node.node_type)
        
        for edge in graph.edges:
            G.add_edge(edge.source_id, edge.target_id, type=edge.edge_type)
        
        # Must be single connected component
        components = list(nx.connected_components(G.to_undirected()))
        assert len(components) == 1, f"Found {len(components)} components, expected 1"
    else:
        pytest.skip("Graph mode not enabled")

def test_datapoint_creation_from_findings():
    """Test DataPoints are created from findings"""
    # Load API key
    import toml
    secrets_path = r'twitterexplorer\.streamlit\secrets.toml'
    secrets = toml.load(secrets_path)
    api_key = secrets.get('RAPIDAPI_KEY')
    
    engine = InvestigationEngine(api_key)
    result = engine.conduct_investigation("Trump health investigation", InvestigationConfig(max_searches=3))
    
    if engine.graph_mode and hasattr(engine.llm_coordinator, 'graph'):
        # Must have DataPoints if findings exist
        graph = engine.llm_coordinator.graph  
        datapoints = [node for node_id, node in graph.nodes.items() if node.node_type == "DataPoint"]
        findings_count = len(result.accumulated_findings)
        
        if findings_count > 0:
            assert len(datapoints) > 0, f"Found {findings_count} findings but 0 DataPoints"
    else:
        pytest.skip("Graph mode not enabled")

def test_search_query_connectivity():
    """Test no SearchQuery nodes are orphaned"""
    # Load API key
    import toml
    secrets_path = r'twitterexplorer\.streamlit\secrets.toml'
    secrets = toml.load(secrets_path)
    api_key = secrets.get('RAPIDAPI_KEY')
    
    engine = InvestigationEngine(api_key)
    result = engine.conduct_investigation("Trump health investigation", InvestigationConfig(max_searches=3))
    
    if engine.graph_mode and hasattr(engine.llm_coordinator, 'graph'):
        graph = engine.llm_coordinator.graph
        G = nx.DiGraph()
        
        for node_id, node in graph.nodes.items():
            G.add_node(node_id, type=node.node_type)
        
        for edge in graph.edges:
            G.add_edge(edge.source_id, edge.target_id, type=edge.edge_type)
        
        # No SearchQuery nodes should be isolated
        search_nodes = [n for n, data in G.nodes(data=True) if data['type'] == 'SearchQuery']
        isolated_searches = [n for n in search_nodes if G.degree(n) == 0]
        
        assert len(isolated_searches) == 0, f"Found {len(isolated_searches)} isolated SearchQuery nodes"
    else:
        pytest.skip("Graph mode not enabled")

if __name__ == "__main__":
    # Run tests individually for debugging
    print("Testing root node creation...")
    test_root_node_creation()
    print("✓ Root node test passed")
    
    print("Testing single connected component...")
    test_single_connected_component()
    print("✓ Connectivity test passed")
    
    print("Testing DataPoint creation...")
    test_datapoint_creation_from_findings()
    print("✓ DataPoint test passed")
    
    print("Testing SearchQuery connectivity...")
    test_search_query_connectivity()
    print("✓ SearchQuery connectivity test passed")
    
    print("All graph connectivity tests passed!")