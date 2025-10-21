"""Test ACTUAL DataPoint creation during a real investigation flow"""
import sys
import json
from twitterexplorer.investigation_engine import InvestigationEngine, InvestigationConfig, SearchAttempt
from unittest.mock import patch

def mock_api_call(endpoint, params):
    """Mock API to return realistic results"""
    # Return different results based on endpoint
    if endpoint == 'search.php':
        return {
            'results': [
                {'text': 'Breaking: Court filing from July 15, 2019 reveals new details about Trump-Epstein relationship dating back to 2002.'},
                {'text': 'Financial documents show $3.5 million property deal between Trump Organization and Epstein associate in March 2002.'},
                {'text': 'Click here for more news updates'},  # Generic - should be filtered
                {'text': 'Witness testimony from December 2019 describes parties at Mar-a-Lago in 2002 attended by both Trump and Epstein.'},
            ]
        }
    return {'results': []}

def test_real_datapoint_creation():
    """Test that DataPoints are actually created during investigation"""
    print("=== TESTING REAL DATAPOINT CREATION ===\n")
    
    # Create engine
    engine = InvestigationEngine("test_key")
    print(f"Engine created. Graph mode: {engine.graph_mode}")
    
    if not engine.graph_mode:
        print("[SKIP] Graph mode not enabled - cannot test DataPoint creation")
        return False
    
    # Check initial graph state
    initial_nodes = len(engine.llm_coordinator.graph.nodes) if hasattr(engine.llm_coordinator, 'graph') else 0
    print(f"Initial graph nodes: {initial_nodes}")
    
    # Mock the API client to return controlled results
    with patch.object(engine.api_client, 'execute_search', side_effect=mock_api_call):
        # Also need to mock the LLM decision making
        def mock_llm_decision(*args, **kwargs):
            # Return a simple search strategy
            return {
                'type': 'gap_filling',
                'description': 'Test search',
                'searches': [
                    {
                        'endpoint': 'search.php',
                        'params': {'query': 'Trump Epstein 2002'},
                        'reasoning': 'Test search'
                    }
                ],
                'reasoning': 'Test investigation'
            }
        
        with patch.object(engine.llm_coordinator, 'decide_next_action', side_effect=mock_llm_decision):
            # Mock the batch evaluation to return reasonable scores
            def mock_evaluate(*args, **kwargs):
                return {
                    'overall_quality': 7.0,
                    'information_density': 0.7,
                    'source_credibility': 0.8,
                    'insights': ['Found relevant information'],
                    'gaps_remaining': []
                }
            
            with patch.object(engine.llm_coordinator, 'evaluate_batch_results', side_effect=mock_evaluate):
                # Run a minimal investigation
                config = InvestigationConfig(max_searches=1)
                
                try:
                    print("\nRunning investigation...")
                    session = engine.conduct_investigation("Trump Epstein 2002 test", config)
                    print(f"Investigation completed. Session ID: {session.session_id}")
                except Exception as e:
                    print(f"Investigation failed: {e}")
                    import traceback
                    traceback.print_exc()
                    return False
    
    # Check final graph state
    if hasattr(engine.llm_coordinator, 'graph'):
        graph = engine.llm_coordinator.graph
        final_nodes = len(graph.nodes)
        print(f"\nFinal graph nodes: {final_nodes}")
        print(f"Nodes created: {final_nodes - initial_nodes}")
        
        # Count node types
        node_types = {}
        for node in graph.nodes.values():
            node_type = type(node).__name__
            node_types[node_type] = node_types.get(node_type, 0) + 1
        
        print("\nNode types created:")
        for node_type, count in node_types.items():
            print(f"  {node_type}: {count}")
        
        # Check for DataPoint nodes specifically
        datapoint_count = sum(1 for n in graph.nodes.values() if 'DataPoint' in str(type(n)))
        print(f"\nDataPoint nodes created: {datapoint_count}")
        
        # Check edges
        edge_count = len(graph.edges)
        print(f"Edges created: {edge_count}")
        
        # Look for DISCOVERED edges
        discovered_edges = [e for e in graph.edges if e.edge_type == "DISCOVERED"]
        print(f"DISCOVERED edges: {len(discovered_edges)}")
        
        return datapoint_count > 0
    else:
        print("Graph not accessible")
        return False

if __name__ == "__main__":
    success = test_real_datapoint_creation()
    print("\n" + "="*50)
    if success:
        print("VERIFICATION: DataPoints ARE created during investigations")
    else:
        print("WARNING: Could not verify DataPoint creation")
    print("="*50)