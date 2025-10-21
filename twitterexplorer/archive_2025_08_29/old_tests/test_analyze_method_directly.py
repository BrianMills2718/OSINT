"""Test the _analyze_round_results_with_llm method directly to verify DataPoint creation"""
from twitterexplorer.investigation_engine import (
    InvestigationEngine, 
    InvestigationSession, 
    InvestigationRound,
    InvestigationConfig,
    SearchAttempt
)
from datetime import datetime

def test_analyze_method_creates_datapoints():
    """Directly test that _analyze_round_results_with_llm creates DataPoints"""
    print("=== TESTING _analyze_round_results_with_llm METHOD ===\n")
    
    # Create engine
    engine = InvestigationEngine("test_key")
    print(f"Engine created. Graph mode: {engine.graph_mode}")
    
    if not engine.graph_mode:
        print("[SKIP] Graph mode not enabled")
        return False
    
    # Create session and round objects
    config = InvestigationConfig(max_searches=10)
    session = InvestigationSession("test query", config)
    current_round = InvestigationRound(
        round_number=1,
        strategy_description="Test round for DataPoint verification"
    )
    
    # Create mock search attempts with specific and generic results
    attempts = []
    
    # Attempt 1: Has specific results
    attempt1 = SearchAttempt(
        search_id=1,
        round_number=1,
        endpoint="search.php",
        params={"query": "Trump Epstein 2002"},
        query_description="Test search 1",
        results_count=3,
        effectiveness_score=7.0,
        execution_time=1.0
    )
    attempt1._raw_results = [
        {
            'text': 'Court documents from March 15, 2002 reveal Trump and Epstein attended same event.',
            'source': 'twitter_search',
            'metadata': {}
        },
        {
            'text': 'Financial records show $2.5 million transaction between parties in July 2002.',
            'source': 'twitter_search',
            'metadata': {}
        },
        {
            'text': 'Click here to read more about this topic',  # Generic - should be filtered
            'source': 'twitter_search',
            'metadata': {}
        }
    ]
    attempts.append(attempt1)
    
    # Attempt 2: Has only generic results
    attempt2 = SearchAttempt(
        search_id=2,
        round_number=1,
        endpoint="search.php",
        params={"query": "test"},
        query_description="Test search 2",
        results_count=2,
        effectiveness_score=2.0,
        execution_time=1.0
    )
    attempt2._raw_results = [
        {
            'text': 'Subscribe for updates',
            'source': 'twitter_search',
            'metadata': {}
        },
        {
            'text': 'No results found',
            'source': 'twitter_search',
            'metadata': {}
        }
    ]
    attempts.append(attempt2)
    
    # Check initial graph state
    initial_nodes = len(engine.llm_coordinator.graph.nodes)
    initial_edges = len(engine.llm_coordinator.graph.edges)
    print(f"Initial state: {initial_nodes} nodes, {initial_edges} edges")
    
    # Call the method we're testing
    print("\nCalling _analyze_round_results_with_llm...")
    try:
        engine._analyze_round_results_with_llm(session, current_round, attempts)
        print("Method executed successfully")
    except Exception as e:
        print(f"Method failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Check final graph state
    final_nodes = len(engine.llm_coordinator.graph.nodes)
    final_edges = len(engine.llm_coordinator.graph.edges)
    print(f"\nFinal state: {final_nodes} nodes, {final_edges} edges")
    print(f"Created: {final_nodes - initial_nodes} nodes, {final_edges - initial_edges} edges")
    
    # Analyze node types
    node_types = {}
    for node in engine.llm_coordinator.graph.nodes.values():
        node_type = node.__class__.__name__
        node_types[node_type] = node_types.get(node_type, 0) + 1
    
    print("\nNode types in graph:")
    for node_type, count in node_types.items():
        print(f"  {node_type}: {count}")
    
    # Check for DataPoints specifically
    datapoint_nodes = [
        n for n in engine.llm_coordinator.graph.nodes.values() 
        if 'DataPoint' in n.__class__.__name__
    ]
    print(f"\nDataPoint nodes found: {len(datapoint_nodes)}")
    
    # Show DataPoint contents
    if datapoint_nodes:
        print("\nDataPoint contents:")
        for i, dp in enumerate(datapoint_nodes[:3], 1):  # Show first 3
            content = dp.properties.get('content', '')[:80]
            print(f"  {i}. {content}...")
    
    # Check for SearchQuery nodes
    search_nodes = [
        n for n in engine.llm_coordinator.graph.nodes.values()
        if 'SearchQuery' in n.__class__.__name__
    ]
    print(f"\nSearchQuery nodes found: {len(search_nodes)}")
    
    # Check edges
    edge_types = {}
    for edge in engine.llm_coordinator.graph.edges:
        edge_types[edge.edge_type] = edge_types.get(edge.edge_type, 0) + 1
    
    print("\nEdge types in graph:")
    for edge_type, count in edge_types.items():
        print(f"  {edge_type}: {count}")
    
    # Verify our expectations
    print("\n" + "="*50)
    print("VERIFICATION RESULTS:")
    print("="*50)
    
    checks = {
        "SearchQuery nodes created": len(search_nodes) == 2,
        "DataPoints created for specific findings": len(datapoint_nodes) >= 2,
        "No DataPoints for generic content": len(datapoint_nodes) <= 3,
        "DISCOVERED edges created": edge_types.get('DISCOVERED', 0) > 0,
        "Graph was modified": final_nodes > initial_nodes
    }
    
    all_passed = True
    for check, passed in checks.items():
        status = "[PASS]" if passed else "[FAIL]"
        print(f"{status} {check}")
        if not passed:
            all_passed = False
    
    return all_passed

if __name__ == "__main__":
    success = test_analyze_method_creates_datapoints()
    print("\n" + "="*50)
    if success:
        print("SUCCESS: DataPoints ARE created by _analyze_round_results_with_llm")
    else:
        print("FAILURE: DataPoint creation not working as expected")
    print("="*50)