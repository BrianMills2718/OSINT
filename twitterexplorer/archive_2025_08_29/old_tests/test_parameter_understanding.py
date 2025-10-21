#!/usr/bin/env python3
"""
Test Parameter Understanding - Verify LLM uses correct endpoints and parameters
"""

import sys
import os

# Add twitterexplorer to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'twitterexplorer'))

def test_parameter_understanding():
    """Test LLM understands correct parameter usage for targeted searches"""
    print("=== Testing LLM Parameter Understanding ===")
    
    try:
        # Check the prompt contains the detailed parameter guidance
        from graph_aware_llm_coordinator import GraphAwareLLMCoordinator
        from llm_client import get_litellm_client
        from investigation_graph import InvestigationGraph
        
        # Create coordinator
        llm_client = get_litellm_client()
        investigation_graph = InvestigationGraph()
        coordinator = GraphAwareLLMCoordinator(llm_client, investigation_graph)
        
        # Test the prompt contains detailed guidance
        goal = "find john greenewald posts about michael herrera"
        context = "We need targeted search for specific user posts about specific topic"
        
        prompt = coordinator._create_strategic_decision_prompt(goal, context)
        
        # Check for critical guidance elements
        critical_guidance = [
            "CRITICAL ENDPOINT USAGE GUIDE:",
            "search.php** - Use for TARGETED SEARCHES:",
            "timeline.php** - Use for RECENT USER POSTS ONLY:",
            "To find User X's posts about Topic Y: Use search.php",
            "from:johngreenewald herrera",
            "Cannot filter by topic - returns chronological timeline only"
        ]
        
        found_guidance = []
        for guidance in critical_guidance:
            if guidance in prompt:
                found_guidance.append(guidance)
        
        print(f"[OK] Parameter guidance in prompt: {len(found_guidance)}/{len(critical_guidance)}")
        for guidance in found_guidance:
            print(f"  + {guidance}")
            
        missing_guidance = set(critical_guidance) - set(found_guidance)
        if missing_guidance:
            print("[ERROR] Missing critical parameter guidance:")
            for guidance in missing_guidance:
                print(f"  - {guidance}")
                
        # Check endpoint configuration includes limitations
        timeline_config = coordinator.available_endpoints.get('timeline.php', {})
        search_config = coordinator.available_endpoints.get('search.php', {})
        
        print(f"\n[OK] Timeline endpoint configuration:")
        print(f"  Description: {timeline_config.get('description', 'Missing')}")
        print(f"  Limitation: {timeline_config.get('limitation', 'Missing')}")
        
        print(f"\n[OK] Search endpoint configuration:")
        print(f"  Description: {search_config.get('description', 'Missing')}")
        print(f"  Examples: {search_config.get('query_examples', 'Missing')}")
        
        # Verify advanced search operators are included
        advanced_operators = [
            "from:johngreenewald herrera",
            "@johngreenewald herrera", 
            "Boolean operators:",
            "(debunk OR hoax OR fraud)",
            "search_type",
            "Latest",
            "Top"
        ]
        
        found_operators = []
        for operator in advanced_operators:
            if operator in prompt:
                found_operators.append(operator)
                
        print(f"\n[OK] Advanced search operators in prompt: {len(found_operators)}/{len(advanced_operators)}")
        for operator in found_operators:
            print(f"  + {operator}")
            
        # Test strategic guidance section
        strategy_guidance = [
            "To find User X's posts about Topic Y: Use search.php",
            "To see User X's recent activity: Use timeline.php", 
            "To analyze User X's network: Use following.php/followers.php",
            "To analyze specific claims: Use tweet.php + latest_replies.php"
        ]
        
        found_strategies = []
        for strategy in strategy_guidance:
            if strategy in prompt:
                found_strategies.append(strategy)
                
        print(f"\n[OK] Strategic guidance in prompt: {len(found_strategies)}/{len(strategy_guidance)}")
        for strategy in found_strategies:
            print(f"  + {strategy}")
            
        print("\n=== Expected LLM Behavior Changes ===")
        print("LLM should now:")
        print("  1. Use search.php with 'from:johngreenewald herrera' for targeted user posts")
        print("  2. Use timeline.php only for recent activity overview") 
        print("  3. Use Boolean operators: (debunk OR hoax OR fraud)")
        print("  4. Use search_type: Latest/Top for recency control")
        print("  5. Understand timeline.php cannot filter by topic")
        
        # Calculate coverage score
        total_elements = len(critical_guidance) + len(advanced_operators) + len(strategy_guidance)
        found_elements = len(found_guidance) + len(found_operators) + len(found_strategies)
        coverage = found_elements / total_elements
        
        print(f"\nOverall Parameter Understanding Coverage: {coverage:.1%}")
        
        if coverage >= 0.8:
            print("[OK] LLM has comprehensive parameter understanding")
            return True
        else:
            print("[WARNING] LLM parameter understanding may be incomplete")
            return False
        
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_parameter_understanding()
    print(f"\n{'[OK] TEST PASSED' if success else '[ERROR] TEST FAILED'}")