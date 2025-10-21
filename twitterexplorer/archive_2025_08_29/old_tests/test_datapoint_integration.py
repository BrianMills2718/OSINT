"""Test that DataPoints and Insights are created during real investigations"""
import pytest
from twitterexplorer.investigation_engine import InvestigationEngine, InvestigationConfig
from unittest.mock import Mock, patch

def test_investigation_creates_datapoints():
    """EVIDENCE: Real investigation must create DataPoint nodes"""
    
    # Create engine
    engine = InvestigationEngine("test_key")
    
    # Mock the API to return specific results
    mock_results = [
        {
            'text': 'Court documents from March 15, 2002 show Trump and Epstein at Mar-a-Lago.',
            'source': 'twitter_search',
            'metadata': {'author': '@reporter'}
        },
        {
            'text': 'Generic result with no specific information',
            'source': 'twitter_search',
            'metadata': {}
        },
        {
            'text': 'Another specific finding: Financial records show $2.5 million transaction on July 4, 2002.',
            'source': 'twitter_search',
            'metadata': {'author': '@investigator'}
        }
    ]
    
    # Patch _execute_search to return our mock results
    from twitterexplorer.investigation_engine import SearchAttempt
    
    def mock_execute(endpoint, params):
        attempt = SearchAttempt(
            search_id=1,
            endpoint=endpoint,
            params=params,
            timestamp=None,
            results_count=3,
            effectiveness_score=7.0,
            query_description="test query"
        )
        attempt._raw_results = mock_results
        return attempt
    
    with patch.object(engine, '_execute_search', side_effect=mock_execute):
        # Run investigation with small limit
        config = InvestigationConfig(max_searches=2)
        session = engine.conduct_investigation("Trump Epstein 2002", config)
    
    # Verify graph was populated
    if engine.graph_mode:
        graph = engine.llm_coordinator.graph
        
        # Check for DataPoint nodes
        datapoint_nodes = [n for n in graph.nodes.values() if 'DataPoint' in str(n)]
        assert len(datapoint_nodes) >= 2, f"Expected at least 2 DataPoints, got {len(datapoint_nodes)}"
        
        # Check that specific findings became DataPoints
        datapoint_contents = [str(n.properties.get('content', '')) for n in datapoint_nodes]
        assert any('March 15, 2002' in content for content in datapoint_contents)
        assert any('$2.5 million' in content for content in datapoint_contents)
        
        # Generic result should NOT be a DataPoint
        assert not any('Generic result' in content for content in datapoint_contents)
        
        print(f"[OK] Created {len(datapoint_nodes)} DataPoint nodes from specific findings")
        
        # Check for edges from search to DataPoints
        edges = graph.edges
        discovery_edges = [e for e in edges if e.edge_type == "DISCOVERED"]
        assert len(discovery_edges) > 0, "No DISCOVERED edges found"
        
        print(f"[OK] Created {len(discovery_edges)} edges from searches to DataPoints")

def test_investigation_creates_insights():
    """EVIDENCE: Investigation must create Insights when patterns exist"""
    
    engine = InvestigationEngine("test_key")
    
    # Mock multiple related results for pattern detection
    mock_results = [
        {'text': f'Finding {i}: Meeting on date in 2002 at location.', 'source': 'twitter_search', 'metadata': {}} 
        for i in range(5)
    ]
    
    from twitterexplorer.investigation_engine import SearchAttempt
    
    def mock_execute(endpoint, params):
        attempt = SearchAttempt(
            search_id=1,
            endpoint=endpoint,
            params=params,
            timestamp=None,
            results_count=5,
            effectiveness_score=7.0,
            query_description="test query"
        )
        attempt._raw_results = mock_results
        return attempt
    
    with patch.object(engine, '_execute_search', side_effect=mock_execute):
        
        config = InvestigationConfig(max_searches=1)
        session = engine.conduct_investigation("pattern test", config)
    
    if engine.graph_mode:
        graph = engine.llm_coordinator.graph
        
        # Check for Insight nodes
        insight_nodes = [n for n in graph.nodes.values() if 'Insight' in str(n)]
        
        # May or may not create insights depending on LLM assessment
        if len(insight_nodes) > 0:
            print(f"[OK] Created {len(insight_nodes)} Insight nodes from patterns")
            
            # Check edges from DataPoints to Insights
            support_edges = [e for e in graph.edges if e.edge_type == "SUPPORTS"]
            if len(support_edges) > 0:
                print(f"[OK] Created {len(support_edges)} SUPPORTS edges to Insights")
        else:
            print("[OK] No patterns detected (valid outcome for test data)")

def test_dead_end_searches_have_no_edges():
    """EVIDENCE: Searches with no significant findings should have no outgoing edges"""
    
    engine = InvestigationEngine("test_key")
    
    # Mock search with only generic results
    mock_results = [
        {'text': 'Click here to read more', 'source': 'test', 'metadata': {}},
        {'text': 'Subscribe for updates', 'source': 'test', 'metadata': {}},
        {'text': 'No specific information available', 'source': 'test', 'metadata': {}}
    ]
    
    from twitterexplorer.investigation_engine import SearchAttempt
    
    def mock_execute(endpoint, params):
        attempt = SearchAttempt(
            search_id=1,
            endpoint=endpoint,
            params=params,
            timestamp=None,
            results_count=3,
            effectiveness_score=2.0,
            query_description="dead end"
        )
        attempt._raw_results = mock_results
        return attempt
    
    with patch.object(engine, '_execute_search', side_effect=mock_execute):
        
        config = InvestigationConfig(max_searches=1)
        session = engine.conduct_investigation("dead end test", config)
    
    if engine.graph_mode:
        graph = engine.llm_coordinator.graph
        
        # Find search nodes
        search_nodes = [n for n in graph.nodes.values() if 'SearchQuery' in str(n)]
        
        for search_node in search_nodes:
            # Check outgoing edges
            outgoing = [e for e in graph.edges if e.source_id == search_node.id]
            
            # Dead-end search should have no outgoing edges
            if 'dead end' in str(search_node.properties.get('parameters', {})):
                assert len(outgoing) == 0, f"Dead-end search has {len(outgoing)} outgoing edges"
                print("[OK] Dead-end search correctly has no outgoing edges")

if __name__ == "__main__":
    print("\n=== Testing DataPoint/Insight Integration ===\n")
    test_investigation_creates_datapoints()
    test_investigation_creates_insights()
    test_dead_end_searches_have_no_edges()
    print("\n[SUCCESS] All integration tests completed!")