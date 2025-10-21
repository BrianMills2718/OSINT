"""Test that the LLM-based evaluator is properly integrated and working"""
from twitterexplorer.investigation_engine import (
    InvestigationEngine, 
    InvestigationSession, 
    InvestigationRound,
    InvestigationConfig,
    SearchAttempt
)
from unittest.mock import Mock, patch, MagicMock
import json

def test_llm_evaluator_integration():
    """Test that LLM evaluator is being used, not regex"""
    print("=== TESTING LLM EVALUATOR INTEGRATION ===\n")
    
    # Create engine
    engine = InvestigationEngine("test_key")
    print(f"1. Engine created. Graph mode: {engine.graph_mode}")
    
    if not engine.graph_mode:
        print("[SKIP] Graph mode not enabled")
        return False
    
    # Check that LLM coordinator has the llm client
    if hasattr(engine.llm_coordinator, 'llm'):
        print(f"2. LLM client found: {type(engine.llm_coordinator.llm).__name__}")
    else:
        print("2. WARNING: No LLM client found on coordinator")
    
    # Create test data
    config = InvestigationConfig(max_searches=10)
    session = InvestigationSession("Trump Epstein investigation", config)
    current_round = InvestigationRound(
        round_number=1,
        strategy_description="Test LLM evaluation"
    )
    
    # Create a search attempt with results
    attempt = SearchAttempt(
        search_id=1,
        round_number=1,
        endpoint="search.php",
        params={"query": "Trump Epstein 2002"},
        query_description="Test search",
        results_count=3,
        effectiveness_score=7.0,
        execution_time=1.0
    )
    
    attempt._raw_results = [
        {
            'text': 'Court documents from March 15, 2002 reveal Trump and Epstein connection.',
            'source': 'twitter_search',
            'metadata': {}
        },
        {
            'text': 'Click here for more updates',  # Should be rejected
            'source': 'twitter_search',
            'metadata': {}
        },
        {
            'text': 'Financial records show $5 million transaction in 2002.',
            'source': 'twitter_search',
            'metadata': {}
        }
    ]
    
    print("\n3. Testing _analyze_round_results_with_llm method...")
    
    # Mock the LLM's batch evaluation response
    mock_llm_response = {
        'evaluations': [
            {
                'is_significant': True,
                'relevance_score': 0.9,
                'specificity_score': 0.85,
                'entities': {'people': ['Trump', 'Epstein'], 'dates': ['March 15, 2002']},
                'key_claims': ['Court documents reveal connection'],
                'reasoning': 'Specific date and names with legal documentation'
            },
            {
                'is_significant': False,
                'relevance_score': 0.0,
                'specificity_score': 0.0,
                'entities': {},
                'key_claims': [],
                'reasoning': 'Generic content with no specific information'
            },
            {
                'is_significant': True,
                'relevance_score': 0.8,
                'specificity_score': 0.9,
                'entities': {'money': ['$5 million'], 'dates': ['2002']},
                'key_claims': ['Financial transaction of $5 million'],
                'reasoning': 'Specific financial information relevant to investigation'
            }
        ]
    }
    
    # Mock the LLM completion call
    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message.content = json.dumps(mock_llm_response)
    
    # Track if LLM was actually called
    llm_called = False
    original_completion = None
    
    if hasattr(engine.llm_coordinator, 'llm'):
        original_completion = engine.llm_coordinator.llm.completion
        
        def mock_completion(*args, **kwargs):
            nonlocal llm_called
            llm_called = True
            # Check that it's asking about finding evaluation
            messages = kwargs.get('messages', [])
            if messages and any('evaluating' in str(m) for m in messages):
                print("   [OK] LLM called for finding evaluation")
                return mock_response
            # Otherwise call original
            return original_completion(*args, **kwargs)
        
        engine.llm_coordinator.llm.completion = mock_completion
    
    # Run the analysis
    initial_nodes = len(engine.llm_coordinator.graph.nodes)
    
    try:
        engine._analyze_round_results_with_llm(session, current_round, [attempt])
        print("   [OK] Analysis completed without errors")
    except Exception as e:
        print(f"   [FAIL] Analysis failed: {e}")
        return False
    
    # Check results
    final_nodes = len(engine.llm_coordinator.graph.nodes)
    nodes_created = final_nodes - initial_nodes
    
    print(f"\n4. Results:")
    print(f"   - Nodes created: {nodes_created}")
    print(f"   - LLM was called: {llm_called}")
    
    # Count DataPoints
    datapoint_count = 0
    for node in engine.llm_coordinator.graph.nodes.values():
        if 'DataPoint' in node.__class__.__name__:
            datapoint_count += 1
            content = node.properties.get('content', '')[:50]
            print(f"   - DataPoint: {content}...")
    
    print(f"\n5. Verification:")
    if llm_called:
        print("   [OK] LLM evaluator was used (not regex)")
    else:
        print("   [FAIL] LLM was NOT called - might be using regex")
    
    if datapoint_count == 2:  # Should create 2 DataPoints (not the generic one)
        print(f"   [OK] Correct number of DataPoints created: {datapoint_count}")
    else:
        print(f"   [WARNING] Unexpected DataPoint count: {datapoint_count} (expected 2)")
    
    # Restore original completion if we mocked it
    if original_completion:
        engine.llm_coordinator.llm.completion = original_completion
    
    return llm_called and nodes_created > 0

if __name__ == "__main__":
    success = test_llm_evaluator_integration()
    print("\n" + "="*50)
    if success:
        print("SUCCESS: LLM evaluator is properly integrated")
    else:
        print("ISSUE: Check the results above")
    print("="*50)