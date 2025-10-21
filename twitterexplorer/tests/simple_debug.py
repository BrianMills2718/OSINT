#!/usr/bin/env python3
"""
Simple Debug - Test LLM decision generation without Unicode issues
"""

import sys
import os

# Add twitterexplorer to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'twitterexplorer'))

def main():
    print("=== Testing LLM Strategic Decision Generation ===")
    
    try:
        # Import required modules
        from graph_aware_llm_coordinator import GraphAwareLLMCoordinator
        from llm_client import get_litellm_client
        from investigation_graph import InvestigationGraph
        
        # Load environment variables
        from dotenv import load_dotenv
        load_dotenv()
        
        # Create LLM coordinator
        llm_client = get_litellm_client()
        investigation_graph = InvestigationGraph()
        coordinator = GraphAwareLLMCoordinator(llm_client, investigation_graph)
        
        print("LLM coordinator created successfully")
        
        # Initialize investigation
        context = coordinator.start_investigation("find me information debunking ufo whistleblower michael herrer")
        
        print("Investigation context initialized:", context.goal)
        
        # Make strategic decision
        decision = coordinator.make_strategic_decision("find me information debunking ufo whistleblower michael herrer")
        
        print("\n=== LLM Strategic Decision Generated ===")
        print("Decision Type:", decision.decision_type)
        print("Reasoning:", decision.reasoning[:200] + "..." if len(decision.reasoning) > 200 else decision.reasoning)
        print("Number of searches:", len(decision.searches))
        
        for i, search in enumerate(decision.searches):
            print(f"\nSearch {i+1}:")
            print(f"  - Endpoint: {search.get('endpoint', 'MISSING')}")
            print(f"  - Parameters: {search.get('parameters', 'MISSING')}")
            if 'parameters' in search and isinstance(search['parameters'], dict) and 'query' in search['parameters']:
                print(f"  - Query: '{search['parameters']['query']}'")
            else:
                print("  - NO QUERY PARAMETER FOUND!")
        
        # Convert to investigation engine format  
        print("\n=== Testing Conversion to Investigation Engine Format ===")
        
        # This is how investigation_engine.py converts the decision
        searches = []
        for search_spec in decision.searches:
            search_plan = {
                'endpoint': search_spec.get('endpoint', 'search.php'),
                'params': search_spec.get('parameters', {}),
                'reason': search_spec.get('reasoning', search_spec.get('reason', '')),
                'max_pages': search_spec.get('max_pages', 3)
            }
            searches.append(search_plan)
            print(f"Converted search plan: {search_plan}")
        
        return decision
        
    except Exception as e:
        print("LLM Decision Generation Failed:", str(e))
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    main()