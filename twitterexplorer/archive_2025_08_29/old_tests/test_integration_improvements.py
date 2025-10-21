"""Integration test to demonstrate backend improvements"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from twitterexplorer.investigation_engine import InvestigationEngine, InvestigationConfig
from unittest.mock import Mock

def test_investigation_improvements():
    """Test that shows improvements over baseline"""
    
    print("="*60)
    print("BACKEND IMPROVEMENTS INTEGRATION TEST")
    print("="*60)
    
    # Create mock API client to avoid real API calls
    mock_api_client = Mock()
    mock_api_client.search.return_value = {
        "results": [{"text": "test result", "user": "testuser"}],
        "meta": {"count": 1}
    }
    
    # Create engine
    engine = InvestigationEngine("test_key")
    engine.api_client = mock_api_client
    
    # Create config for quick test
    config = InvestigationConfig(
        max_searches=10,
        pages_per_search=1,
        satisfaction_enabled=False  # Run all searches
    )
    
    print("\n### TEST 1: ENDPOINT DIVERSITY ###")
    
    # Run investigation
    try:
        result = engine.conduct_investigation(
            "find different takes on Trump Epstein drama",
            config=config
        )
        
        # Check endpoint diversity
        endpoints_used = set()
        for i, search in enumerate(result.search_history[:10], 1):
            endpoints_used.add(search.endpoint)
            print(f"Search {i}: {search.endpoint} - {search.query[:50] if hasattr(search, 'query') else 'N/A'}")
        
        print(f"\nUnique endpoints used: {len(endpoints_used)}")
        print(f"Endpoints: {list(endpoints_used)}")
        
        if len(endpoints_used) >= 3:
            print("[PASS] Good endpoint diversity!")
        elif len(endpoints_used) == 2:
            print("[WARNING] Limited endpoint diversity")
        else:
            print("[FAIL] Poor endpoint diversity - only using", list(endpoints_used))
            
    except Exception as e:
        print(f"[ERROR] Investigation failed: {e}")
    
    print("\n### TEST 2: GRAPH CONNECTIVITY ###")
    
    # Check graph connectivity
    nodes = len(engine.llm_coordinator.graph.nodes)
    edges = len(engine.llm_coordinator.graph.edges)
    
    print(f"Graph nodes created: {nodes}")
    print(f"Graph edges created: {edges}")
    
    if edges > 0:
        print("[PASS] Graph has edges - knowledge is connected!")
        
        # Show edge types
        edge_types = set()
        for edge in engine.llm_coordinator.graph.edges:
            edge_types.add(edge.edge_type)
        print(f"Edge types: {list(edge_types)}")
    else:
        print("[FAIL] No edges created - isolated nodes!")
    
    print("\n### TEST 3: QUERY RELEVANCE ###")
    
    # Check if queries are relevant to the investigation goal
    relevant_count = 0
    for search in result.search_history[:10]:
        query = str(search.query) if hasattr(search, 'query') else str(search)
        if any(term in query.lower() for term in ['trump', 'epstein', 'drama', 'scandal']):
            relevant_count += 1
    
    relevance_percentage = (relevant_count / min(10, len(result.search_history))) * 100
    print(f"Query relevance: {relevance_percentage:.0f}% ({relevant_count}/10 relevant)")
    
    if relevance_percentage >= 50:
        print("[PASS] Queries are relevant to investigation goal")
    else:
        print("[FAIL] Queries drift from investigation goal")
    
    print("\n### TEST 4: NO REPETITIVE LOOPS ###")
    
    # Check for repetitive queries
    queries_seen = []
    repetitions = 0
    
    for search in result.search_history[:10]:
        query = str(search.query) if hasattr(search, 'query') else str(search)
        if query in queries_seen:
            repetitions += 1
            print(f"[WARNING] Repeated query: {query[:50]}")
        queries_seen.append(query)
    
    if repetitions == 0:
        print("[PASS] No repetitive queries detected")
    elif repetitions <= 2:
        print(f"[WARNING] {repetitions} query repetitions detected")
    else:
        print(f"[FAIL] {repetitions} query repetitions - stuck in loop!")
    
    print("\n### SUMMARY ###")
    print(f"- Endpoint diversity: {len(endpoints_used)} different endpoints")
    print(f"- Graph connectivity: {edges} edges connecting {nodes} nodes")
    print(f"- Query relevance: {relevance_percentage:.0f}%")
    print(f"- Query repetitions: {repetitions}")
    
    # Overall assessment
    score = 0
    if len(endpoints_used) >= 3: score += 25
    if edges > 0: score += 25
    if relevance_percentage >= 50: score += 25
    if repetitions <= 2: score += 25
    
    print(f"\nOVERALL SCORE: {score}/100")
    
    if score >= 75:
        print("[SUCCESS] Backend significantly improved!")
    elif score >= 50:
        print("[PARTIAL] Some improvements, but more work needed")
    else:
        print("[NEEDS WORK] Backend still has major issues")

if __name__ == "__main__":
    test_investigation_improvements()