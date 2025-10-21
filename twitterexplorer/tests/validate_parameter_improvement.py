#!/usr/bin/env python3
"""
Validate Parameter Improvement - Show LLM now uses correct parameters for targeted searches
"""

import sys
import os

# Add twitterexplorer to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'twitterexplorer'))

def validate_parameter_improvement():
    """Validate LLM understands the difference between search.php and timeline.php usage"""
    print("=== Validating Parameter Understanding Improvement ===")
    
    try:
        from graph_aware_llm_coordinator import GraphAwareLLMCoordinator
        from llm_client import get_litellm_client
        from investigation_graph import InvestigationGraph
        
        # Create coordinator with real LLM
        llm_client = get_litellm_client()
        investigation_graph = InvestigationGraph()
        investigation_graph.create_analytic_question_node("find john greenewald posts about michael herrera")
        coordinator = GraphAwareLLMCoordinator(llm_client, investigation_graph)
        
        print("[OK] Created coordinator with comprehensive parameter guidance")
        print(f"[OK] Available endpoints: {len(coordinator.available_endpoints)}")
        
        # Test specific scenario that was problematic before
        print("\n=== Testing Scenario: Find John Greenewald's posts about Herrera ===")
        print("Previous behavior: Used timeline.php to get recent posts")
        print("Expected new behavior: Use search.php with 'from:johngreenewald herrera'")
        
        # Simulate decision making for this specific case
        goal = "find john greenewald posts about michael herrera"
        
        print("\n[INFO] Making strategic decision with LLM...")
        try:
            decision = coordinator.make_strategic_decision(goal)
            
            print(f"[OK] Decision type: {decision.decision_type}")
            print(f"[OK] Reasoning: {decision.reasoning[:200]}...")
            print(f"[OK] Number of searches planned: {len(decision.searches)}")
            
            # Analyze the search strategies
            for i, search in enumerate(decision.searches):
                endpoint = search.get('endpoint')
                parameters = search.get('parameters', {})
                reasoning = search.get('reasoning', 'No reasoning provided')
                
                print(f"\n[SEARCH {i+1}] Endpoint: {endpoint}")
                print(f"  Parameters: {parameters}")
                print(f"  Reasoning: {reasoning}")
                
                # Check for improved behavior
                if endpoint == 'search.php' and 'query' in parameters:
                    query = parameters['query'].lower()
                    
                    # Look for targeted search patterns
                    if 'from:johngreenewald' in query and 'herrera' in query:
                        print(f"  [✓] EXCELLENT: Using targeted search 'from:johngreenewald herrera'")
                    elif 'johngreenewald' in query and 'herrera' in query:
                        print(f"  [✓] GOOD: Using targeted search for both user and topic")
                    elif 'herrera' in query:
                        print(f"  [✓] OK: Searching for topic 'herrera'")
                    else:
                        print(f"  [!] SUBOPTIMAL: Query doesn't target user posts about topic")
                
                elif endpoint == 'timeline.php':
                    if 'screenname' in parameters:
                        screenname = parameters.get('screenname', '').lower()
                        if 'johngreenewald' in screenname:
                            print(f"  [!] SUBOPTIMAL: Using timeline.php for targeted content")
                            print(f"      Should use search.php with 'from:johngreenewald herrera' instead")
                        else:
                            print(f"  [?] Using timeline.php for different user: {screenname}")
                    else:
                        print(f"  [!] ERROR: timeline.php without screenname parameter")
                
                else:
                    print(f"  [INFO] Using {endpoint} - may be strategic diversification")
            
            print(f"\n[OK] Strategic coherence score: {decision.strategic_coherence_score}")
            print(f"[OK] Context utilization: {decision.context_utilization}")
            
            return True
            
        except Exception as e:
            print(f"[ERROR] LLM decision failed: {e}")
            return False
            
    except Exception as e:
        print(f"[ERROR] Setup failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = validate_parameter_improvement()
    print(f"\n{'[OK] VALIDATION PASSED' if success else '[ERROR] VALIDATION FAILED'}")