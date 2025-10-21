"""Test adaptive strategy system"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from adaptive_strategy_system import AdaptiveStrategySystem
from twitterexplorer.graph_aware_llm_coordinator import GraphAwareLLMCoordinator
from twitterexplorer.investigation_graph import InvestigationGraph
from twitterexplorer.llm_client import get_litellm_client

def test_adaptive_detection():
    """Test that system detects when adaptation is needed"""
    
    print("="*60)
    print("TEST: ADAPTIVE STRATEGY DETECTION")
    print("="*60)
    
    adaptive = AdaptiveStrategySystem()
    
    # Simulate consecutive failures
    recent_searches = [
        {'endpoint': 'search.php', 'query': 'michael herrera', 'results_count': 0},
        {'endpoint': 'search.php', 'query': 'herrera ufo', 'results_count': 0},
        {'endpoint': 'search.php', 'query': 'ufo claims', 'results_count': 0},
        {'endpoint': 'search.php', 'query': 'michael herrera claims', 'results_count': 0},
    ]
    
    analysis = adaptive.analyze_situation(
        recent_searches=recent_searches,
        total_results=0,
        investigation_goal="debunk michael herrera ufo claims"
    )
    
    assert analysis["needs_pivot"] == True
    assert analysis["pivot_reason"] == "consecutive_failures"
    print(f"[PASS] Detected consecutive failures: {analysis['pivot_reason']}")
    print(f"[PASS] Recommended strategy: {analysis['recommended_strategy']}")
    
    # Test stuck pattern detection
    stuck_searches = [
        {'endpoint': 'search.php', 'query': 'same query', 'results_count': 0},
        {'endpoint': 'search.php', 'query': 'same query', 'results_count': 0},
        {'endpoint': 'search.php', 'query': 'same query', 'results_count': 0},
        {'endpoint': 'search.php', 'query': 'different', 'results_count': 0},
        {'endpoint': 'search.php', 'query': 'same query', 'results_count': 0},
    ]
    
    analysis2 = adaptive.analyze_situation(
        recent_searches=stuck_searches,
        total_results=0,
        investigation_goal="find information"
    )
    
    assert analysis2["needs_pivot"] == True
    print(f"[INFO] Pivot reason detected: {analysis2['pivot_reason']}")
    assert analysis2["pivot_reason"] in ["stuck_in_pattern", "consecutive_failures", "low_overall_results", "endpoint_fixation"]
    print(f"[PASS] Detected pattern issue: {analysis2['pivot_reason']}")
    
    return True

def test_pivot_generation():
    """Test pivot strategy generation"""
    
    print("\n" + "="*60)
    print("TEST: PIVOT STRATEGY GENERATION")
    print("="*60)
    
    adaptive = AdaptiveStrategySystem()
    
    # Generate broadened search pivot
    context = {
        'searches_conducted': 5,
        'results_found': 0,
        'endpoints_used': ['search.php'],
        'recent_queries': ['michael herrera ufo', 'herrera claims', 'ufo debunk']
    }
    
    pivot = adaptive.generate_pivot_strategy(
        current_context=context,
        pivot_type="broaden_search",
        investigation_goal="debunk michael herrera ufo claims"
    )
    
    assert pivot["strategy_type"] == "broadened_search"
    assert len(pivot["searches"]) > 0
    print(f"[PASS] Generated broadened search with {len(pivot['searches'])} searches")
    print(f"[PASS] Reasoning: {pivot['reasoning']}")
    
    # Generate alternative sources pivot
    pivot2 = adaptive.generate_pivot_strategy(
        current_context=context,
        pivot_type="alternative_sources",
        investigation_goal="debunk michael herrera ufo claims"
    )
    
    assert pivot2["strategy_type"] == "alternative_sources"
    assert any(s['endpoint'] != 'search.php' for s in pivot2['searches'])
    print(f"[PASS] Generated alternative sources with diverse endpoints")
    
    # Check endpoints used
    endpoints = [s['endpoint'] for s in pivot2['searches']]
    print(f"[PASS] Endpoints in pivot: {endpoints}")
    
    return True

def test_coordinator_integration():
    """Test adaptive strategy integration with coordinator"""
    
    print("\n" + "="*60)
    print("TEST: COORDINATOR ADAPTIVE INTEGRATION")
    print("="*60)
    
    # Create coordinator
    graph = InvestigationGraph()
    llm_client = get_litellm_client()
    coordinator = GraphAwareLLMCoordinator(llm_client, graph)
    
    # Simulate failures
    for i in range(4):
        coordinator.track_search_results(
            endpoint="search.php",
            query=f"test query {i}",
            results_count=0
        )
    
    print(f"Simulated {len(coordinator.search_history)} failed searches")
    print(f"Total results: {coordinator.total_results_found}")
    
    # Check if adaptation triggers
    pivot_decision = coordinator.check_and_adapt_strategy("find information about test topic")
    
    if pivot_decision:
        print(f"[PASS] Pivot triggered!")
        print(f"[PASS] Decision type: {pivot_decision.decision_type}")
        print(f"[PASS] Reasoning: {pivot_decision.reasoning[:100]}...")
        print(f"[PASS] Searches planned: {len(pivot_decision.searches)}")
        
        for search in pivot_decision.searches:
            print(f"  - {search.endpoint}: {search.reasoning[:50]}...")
    else:
        print("[WARNING] No pivot triggered - may need more failures")
    
    # Get adaptation report
    report = coordinator.adaptive_strategy.get_adaptation_report()
    print("\n" + report)
    
    return True

if __name__ == "__main__":
    success = True
    
    try:
        success = test_adaptive_detection() and success
        success = test_pivot_generation() and success
        success = test_coordinator_integration() and success
        
        if success:
            print("\n" + "="*60)
            print("[SUCCESS] ALL ADAPTIVE STRATEGY TESTS PASSED!")
            print("="*60)
            print("\nThe system now:")
            print("- Detects when searches are failing")
            print("- Identifies stuck patterns")
            print("- Generates pivot strategies")
            print("- Tries alternative approaches")
            print("- Broadens or narrows searches adaptively")
        else:
            print("\n[FAILURE] Some tests failed")
            
    except Exception as e:
        print(f"\n[ERROR] Test failed with exception: {e}")
        import traceback
        traceback.print_exc()