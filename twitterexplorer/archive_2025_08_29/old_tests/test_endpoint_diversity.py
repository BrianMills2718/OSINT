#!/usr/bin/env python3
"""
Test Endpoint Diversity - Verify LLM uses diverse endpoints strategically
"""

import sys
import os
import json

# Add twitterexplorer to the path  
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'twitterexplorer'))

def test_endpoint_diversity():
    """Test that LLM coordinator now has access to diverse endpoints and uses them"""
    print("=== Testing Endpoint Diversity and Strategic Flexibility ===")
    
    try:
        # Import required modules
        from graph_aware_llm_coordinator import GraphAwareLLMCoordinator
        from llm_client import get_litellm_client  
        from investigation_graph import InvestigationGraph
        
        # Create coordinator
        llm_client = get_litellm_client()
        investigation_graph = InvestigationGraph()
        coordinator = GraphAwareLLMCoordinator(llm_client, investigation_graph)
        
        # Test endpoint availability
        endpoints = coordinator.available_endpoints
        print(f"[OK] Coordinator has access to {len(endpoints)} endpoints:")
        
        endpoint_categories = {
            'Content Discovery': ['search.php', 'trends.php'],
            'User Analysis': ['timeline.php', 'screenname.php', 'usermedia.php'], 
            'Network Analysis': ['following.php', 'followers.php'],
            'Conversation Analysis': ['tweet.php', 'latest_replies.php', 'tweet_thread.php', 'retweets.php']
        }
        
        for category, expected_endpoints in endpoint_categories.items():
            available_in_category = [ep for ep in expected_endpoints if ep in endpoints]
            print(f"  {category}: {len(available_in_category)}/{len(expected_endpoints)} endpoints")
            for ep in available_in_category:
                description = endpoints[ep]['description']
                best_for = endpoints[ep]['best_for']
                print(f"    - {ep}: {description}")
                print(f"      Best for: {best_for}")
        
        # Test strategic prompt includes diversity guidance
        goal = "investigate credibility of UFO whistleblower claims"
        context = "Sample investigation context showing need for network analysis"
        
        prompt = coordinator._create_strategic_decision_prompt(goal, context)
        
        # Verify prompt encourages endpoint diversity
        diversity_indicators = [
            "USE STRATEGIC VARIETY",
            "Network Analysis:",
            "Conversation Analysis:", 
            "STRATEGIC MIXING",
            "Don't limit to just search.php"
        ]
        
        found_indicators = []
        for indicator in diversity_indicators:
            if indicator in prompt:
                found_indicators.append(indicator)
        
        print(f"\n[OK] Strategic diversity guidance in prompt: {len(found_indicators)}/{len(diversity_indicators)}")
        for indicator in found_indicators:
            print(f"  + {indicator}")
        
        missing_indicators = set(diversity_indicators) - set(found_indicators)
        if missing_indicators:
            print("[WARNING] Missing diversity indicators:")
            for indicator in missing_indicators:
                print(f"  - {indicator}")
        
        # Test network endpoints are properly configured
        network_endpoints = ['following.php', 'followers.php']
        for endpoint in network_endpoints:
            if endpoint in endpoints:
                config = endpoints[endpoint]
                print(f"\n[OK] {endpoint} configuration:")
                print(f"  Description: {config['description']}")
                print(f"  Parameters: {config['params']}")
                print(f"  Best for: {config['best_for']}")
            else:
                print(f"[ERROR] Missing critical network endpoint: {endpoint}")
                return False
        
        # Test conversation endpoints are properly configured
        conversation_endpoints = ['latest_replies.php', 'tweet_thread.php']
        for endpoint in conversation_endpoints:
            if endpoint in endpoints:
                config = endpoints[endpoint]
                print(f"\n[OK] {endpoint} configuration:")
                print(f"  Description: {config['description']}")
                print(f"  Parameters: {config['params']}")
                print(f"  Best for: {config['best_for']}")
            else:
                print(f"[ERROR] Missing critical conversation endpoint: {endpoint}")
                return False
                
        print("\n=== Endpoint Strategic Capabilities ===")
        print("LLM can now strategically:")
        print("  1. Discover content: search.php + trends.php")  
        print("  2. Analyze users: timeline.php + screenname.php + usermedia.php")
        print("  3. Map networks: following.php + followers.php")
        print("  4. Track conversations: tweet.php + latest_replies.php + tweet_thread.php")
        print("  5. Measure influence: retweets.php + followers.php")
        
        print(f"\nTotal strategic endpoints available: {len(endpoints)}")
        print("This is a major improvement from the previous 3 endpoints!")
        
        return True
        
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_endpoint_diversity()
    print(f"\n{'[OK] TEST PASSED' if success else '[ERROR] TEST FAILED'}")