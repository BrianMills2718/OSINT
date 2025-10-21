"""Test endpoint diversity enforcement"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from twitterexplorer.graph_aware_llm_coordinator import GraphAwareLLMCoordinator, EndpointDiversityTracker
from twitterexplorer.investigation_graph import InvestigationGraph
from twitterexplorer.investigation_engine import InvestigationEngine, InvestigationConfig
from unittest.mock import Mock
import json

def test_endpoint_diversity_tracker():
    """EVIDENCE: System must track and enforce endpoint diversity"""
    
    print("="*60)
    print("TEST: ENDPOINT DIVERSITY TRACKER")
    print("="*60)
    
    # Create tracker
    tracker = EndpointDiversityTracker()
    
    # Test enforcement thresholds
    tracker.record_usage("search.php")
    tracker.record_usage("search.php")
    tracker.record_usage("search.php")
    
    # Should suggest alternatives after 3 uses
    overused = tracker.get_overused_endpoints(threshold=3)
    assert "search.php" in overused
    print("[PASS] Detects overused endpoints")
    
    # Should suggest unused endpoints
    unused = tracker.get_unused_endpoints()
    assert "timeline.php" in unused
    assert "mentions.php" in unused
    assert len(unused) >= 10
    print(f"[PASS] Identifies {len(unused)} unused endpoints")
    
    # Test diversity score
    diversity_score = tracker.calculate_diversity_score()
    assert diversity_score < 0.3  # Low diversity with only 1 endpoint
    print(f"[PASS] Diversity score: {diversity_score:.2f} (low as expected)")
    
    # Add variety
    tracker.record_usage("timeline.php")
    tracker.record_usage("mentions.php")
    tracker.record_usage("screenname.php")
    
    new_diversity = tracker.calculate_diversity_score()
    assert new_diversity > diversity_score
    print(f"[PASS] Improved diversity: {new_diversity:.2f}")
    
    return True

def test_endpoint_selection_with_diversity():
    """EVIDENCE: Coordinator must consider diversity when selecting endpoints"""
    
    print("\n" + "="*60)
    print("TEST: DIVERSITY-AWARE ENDPOINT SELECTION")
    print("="*60)
    
    # Create coordinator with diversity tracking
    graph = InvestigationGraph()
    mock_llm = Mock()
    coordinator = GraphAwareLLMCoordinator(mock_llm, graph)
    
    # Simulate overuse of search.php
    coordinator.diversity_tracker.record_usage("search.php")
    coordinator.diversity_tracker.record_usage("search.php")
    coordinator.diversity_tracker.record_usage("search.php")
    coordinator.diversity_tracker.record_usage("search.php")
    
    # Mock LLM response
    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message.content = json.dumps({
        "endpoint": "search.php",  # LLM still suggests search.php
        "reasoning": "General search"
    })
    mock_llm.simple_completion.return_value = mock_response
    
    # Select endpoint with diversity enforcement
    endpoint, reasoning = coordinator._select_endpoint_with_diversity(
        "find information about Michael Herrera",
        {"search.php": 4}  # Already used 4 times
    )
    
    # Should override to use a different endpoint
    assert endpoint != "search.php", f"Should not use overused search.php, got {endpoint}"
    assert endpoint in ["timeline.php", "mentions.php", "screenname.php"]
    print(f"[PASS] Diverted from search.php to {endpoint}")
    print(f"[PASS] Reasoning: {reasoning}")
    
    return True

def test_investigation_with_enforced_diversity():
    """EVIDENCE: Full investigation must show endpoint diversity"""
    
    print("\n" + "="*60)
    print("TEST: INVESTIGATION WITH ENFORCED DIVERSITY")
    print("="*60)
    
    # Create engine with diversity enforcement
    engine = InvestigationEngine("test_key")
    
    # Mock API to avoid real calls
    mock_api = Mock()
    mock_api.search.return_value = {"results": [], "meta": {"count": 0}}
    mock_api.timeline.return_value = {"results": [], "meta": {"count": 0}}
    mock_api.mentions.return_value = {"results": [], "meta": {"count": 0}}
    engine.api_client = mock_api
    
    # Configure for quick test with diversity
    config = InvestigationConfig(
        max_searches=10,
        pages_per_search=1,
        satisfaction_enabled=False,
        enforce_endpoint_diversity=True,  # NEW: Enable diversity enforcement
        max_endpoint_repeats=2  # NEW: Max 2 uses per endpoint
    )
    
    # Run investigation
    result = engine.conduct_investigation(
        "debunk Michael Herrera UFO claims",
        config=config
    )
    
    # Analyze endpoint usage
    endpoint_counts = {}
    for search in result.search_history:
        endpoint = search.endpoint
        endpoint_counts[endpoint] = endpoint_counts.get(endpoint, 0) + 1
    
    print(f"\nEndpoint usage distribution:")
    for endpoint, count in endpoint_counts.items():
        print(f"  {endpoint}: {count} times")
    
    # Verify diversity
    unique_endpoints = len(endpoint_counts)
    max_usage = max(endpoint_counts.values())
    
    assert unique_endpoints >= 3, f"Should use at least 3 endpoints, got {unique_endpoints}"
    assert max_usage <= 4, f"No endpoint should be used >4 times, max was {max_usage}"
    
    diversity_score = unique_endpoints / len(result.search_history)
    print(f"\n[PASS] Endpoint diversity achieved!")
    print(f"[PASS] Used {unique_endpoints} different endpoints")
    print(f"[PASS] Diversity score: {diversity_score:.2f}")
    print(f"[PASS] Max single endpoint usage: {max_usage}")
    
    return True

def test_strategic_endpoint_mapping():
    """EVIDENCE: System must map investigation needs to appropriate endpoints"""
    
    print("\n" + "="*60)
    print("TEST: STRATEGIC ENDPOINT MAPPING")
    print("="*60)
    
    coordinator = GraphAwareLLMCoordinator(Mock(), InvestigationGraph())
    
    # Test mappings for different investigation needs
    test_cases = [
        {
            "need": "Find what a specific user said",
            "expected": ["timeline.php", "screenname.php"],
            "query": "What did @elonmusk say about Herrera?"
        },
        {
            "need": "Find conversations about topic",
            "expected": ["mentions.php", "replies.php"],
            "query": "Who is discussing Herrera's claims?"
        },
        {
            "need": "Find trending discussions",
            "expected": ["trends.php", "search.php"],
            "query": "Is Herrera trending?"
        },
        {
            "need": "Find user connections",
            "expected": ["follows.php", "follower.php"],
            "query": "Who follows Herrera supporters?"
        }
    ]
    
    for test in test_cases:
        suggested = coordinator._suggest_endpoint_for_need(test["query"])
        assert suggested in test["expected"], \
            f"For '{test['need']}', expected {test['expected']}, got {suggested}"
        print(f"[PASS] {test['need']}: -> {suggested}")
    
    return True

if __name__ == "__main__":
    success = True
    
    try:
        # Run all tests
        success = test_endpoint_diversity_tracker() and success
        success = test_endpoint_selection_with_diversity() and success
        success = test_investigation_with_enforced_diversity() and success
        success = test_strategic_endpoint_mapping() and success
        
        if success:
            print("\n" + "="*60)
            print("[SUCCESS] ALL ENDPOINT DIVERSITY TESTS PASSED!")
            print("="*60)
        else:
            print("\n[FAILURE] Some tests failed")
            
    except Exception as e:
        print(f"\n[ERROR] Test failed with exception: {e}")
        import traceback
        traceback.print_exc()