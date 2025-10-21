"""Test staged prompt approach for better LLM decision making"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from twitterexplorer.graph_aware_llm_coordinator import GraphAwareLLMCoordinator
from twitterexplorer.investigation_graph import InvestigationGraph
from twitterexplorer.llm_client import get_litellm_client
import json

# Available endpoints for validation
AVAILABLE_ENDPOINTS = [
    'search.php', 'trends.php', 'timeline.php', 'screenname.php',
    'usermedia.php', 'following.php', 'followers.php', 'affilates.php',
    'checkfollow.php', 'screennames.php', 'tweet.php', 'latest_replies.php',
    'tweet_thread.php', 'retweets.php', 'checkretweet.php', 'listtimeline.php'
]

def test_endpoint_selection_prompt():
    """EVIDENCE: Endpoint selection must be separate, focused decision"""
    coordinator = GraphAwareLLMCoordinator(get_litellm_client(), InvestigationGraph())
    
    # Check if staged method exists
    if not hasattr(coordinator, '_select_endpoint'):
        print("[WARNING] _select_endpoint method not yet implemented")
        print("Testing with existing make_strategic_decision instead")
        
        # Test with existing method to see endpoint selection
        decision = coordinator.make_strategic_decision("Find Trump's tweets about Epstein")
        
        # Check that we're using appropriate endpoints
        endpoints_used = [search.endpoint for search in decision.searches]
        print(f"Endpoints selected: {endpoints_used}")
        
        # Should include timeline.php for direct user tweets
        if 'timeline.php' in endpoints_used:
            print("[PASS] Selected timeline.php for user tweets")
        else:
            print("[WARNING] Did not select timeline.php for user-specific query")
            
        # Should not ONLY use search.php
        if len(set(endpoints_used)) > 1:
            print(f"[PASS] Using {len(set(endpoints_used))} different endpoints")
        else:
            print(f"[FAIL] Only using {set(endpoints_used)} endpoint(s)")
            
        return
    
    # Test new staged approach if method exists
    endpoint_decision = coordinator._select_endpoint(
        goal="Find Trump's tweets about Epstein",
        context="Need direct source access to Trump's statements"
    )
    
    print(f"Endpoint decision returned: {endpoint_decision}")
    
    # Must return specific endpoint with reasoning
    assert endpoint_decision['endpoint'] in AVAILABLE_ENDPOINTS
    assert len(endpoint_decision['reasoning']) > 20
    
    # Should suggest timeline.php for user-specific tweets
    if endpoint_decision['endpoint'] == 'timeline.php':
        print(f"[PASS] Correctly selected timeline.php for user tweets")
    elif endpoint_decision['endpoint'] == 'search.php':
        print(f"[WARNING] Selected generic search.php instead of timeline.php")
    else:
        print(f"[INFO] Selected {endpoint_decision['endpoint']}")
    
    print(f"ENDPOINT DECISION: {json.dumps(endpoint_decision, indent=2)}")

def test_query_formulation_prompt():
    """EVIDENCE: Query formulation must be endpoint-specific"""
    coordinator = GraphAwareLLMCoordinator(get_litellm_client(), InvestigationGraph())
    
    # Check if staged method exists
    if not hasattr(coordinator, '_formulate_query'):
        print("[WARNING] _formulate_query method not yet implemented")
        print("Testing query formulation in existing decisions")
        
        # Test with existing method
        decision = coordinator.make_strategic_decision("Get recent NASA announcements")
        
        for search in decision.searches:
            if search.endpoint == 'timeline.php':
                # Check if screenname is properly set
                if hasattr(search.parameters, 'screenname') and search.parameters.screenname:
                    print(f"[PASS] Properly formatted timeline.php query: screenname={search.parameters.screenname}")
                else:
                    print(f"[FAIL] timeline.php missing screenname parameter")
            elif search.endpoint == 'search.php':
                # Check if query is properly set
                if hasattr(search.parameters, 'query') and search.parameters.query:
                    print(f"[PASS] Properly formatted search.php query: query={search.parameters.query}")
                else:
                    print(f"[FAIL] search.php missing query parameter")
        return
    
    # Test query formulation for specific endpoint
    query = coordinator._formulate_query(
        endpoint="timeline.php",
        goal="Get Trump's recent statements",
        endpoint_params={'required': ['screenname'], 'optional': ['cursor']}
    )
    
    # Must return properly formatted parameters
    assert 'screenname' in query
    assert query['screenname'] == 'realDonaldTrump'
    
    print(f"[PASS] FORMULATED QUERY: {json.dumps(query, indent=2)}")

def test_prompt_size_reduction():
    """EVIDENCE: Staged prompts should be smaller than monolithic prompt"""
    coordinator = GraphAwareLLMCoordinator(get_litellm_client(), InvestigationGraph())
    
    # Get the current monolithic prompt size
    import logging
    log_capture = []
    
    class LogCapture(logging.Handler):
        def emit(self, record):
            log_capture.append(record.getMessage())
    
    handler = LogCapture()
    coordinator.logger.addHandler(handler)
    coordinator.logger.setLevel(logging.INFO)
    
    # Make a decision to capture prompt size
    decision = coordinator.make_strategic_decision("test investigation")
    
    # Find prompt size log
    prompt_size_log = None
    for log in log_capture:
        if "DIAGNOSTIC: Prompt size" in log:
            prompt_size_log = log
            break
    
    if prompt_size_log:
        # Extract size
        import re
        match = re.search(r'(\d+) chars.*?(\d+) words.*?(\d+) lines', prompt_size_log)
        if match:
            chars = int(match.group(1))
            words = int(match.group(2))
            lines = int(match.group(3))
            
            print(f"Current monolithic prompt: {chars} chars, {words} words, {lines} lines")
            
            # Check if it's too large (>500 lines is definitely too much)
            if lines > 500:
                print(f"[FAIL] Prompt is too large: {lines} lines (should be <200 for simple decisions)")
            elif lines > 200:
                print(f"[WARNING] Prompt is large: {lines} lines (consider splitting for better performance)")
            else:
                print(f"[PASS] Prompt size is reasonable: {lines} lines")
    else:
        print("[WARNING] Could not capture prompt size")

def test_endpoint_diversity_in_decisions():
    """EVIDENCE: System should select diverse endpoints for comprehensive investigation"""
    coordinator = GraphAwareLLMCoordinator(get_litellm_client(), InvestigationGraph())
    
    # Test with investigation that should use multiple endpoints
    decision = coordinator.make_strategic_decision("Comprehensive analysis of Elon Musk's Twitter network")
    
    endpoints_used = [search.endpoint for search in decision.searches]
    unique_endpoints = set(endpoints_used)
    
    print(f"Total searches: {len(decision.searches)}")
    print(f"Unique endpoints: {len(unique_endpoints)}")
    print(f"Endpoints used: {list(unique_endpoints)}")
    
    # Should use at least 3 different endpoints for comprehensive analysis
    if len(unique_endpoints) >= 3:
        print(f"[PASS] Good endpoint diversity: {len(unique_endpoints)} different endpoints")
    elif len(unique_endpoints) == 2:
        print(f"[WARNING] Limited endpoint diversity: only {len(unique_endpoints)} endpoints")
    else:
        print(f"[FAIL] Poor endpoint diversity: only using {list(unique_endpoints)}")
    
    # Check for key endpoints that should be used
    expected_for_network = ['screenname.php', 'following.php', 'followers.php', 'timeline.php']
    used_expected = [ep for ep in expected_for_network if ep in unique_endpoints]
    
    if len(used_expected) >= 2:
        print(f"[PASS] Using appropriate network analysis endpoints: {used_expected}")
    else:
        print(f"[WARNING] Missing key network endpoints. Used: {used_expected}, Expected some of: {expected_for_network}")

if __name__ == "__main__":
    print("="*60)
    print("STAGED PROMPT TESTS")
    print("="*60)
    
    test_endpoint_selection_prompt()
    print("\n" + "-"*60 + "\n")
    
    test_query_formulation_prompt()
    print("\n" + "-"*60 + "\n")
    
    test_prompt_size_reduction()
    print("\n" + "-"*60 + "\n")
    
    test_endpoint_diversity_in_decisions()
    
    print("\n" + "="*60)
    print("STAGED PROMPT TESTS COMPLETE")
    print("="*60)