#!/usr/bin/env python3
"""
Test API Parameter Fix - Verify LLM generates proper search parameters
"""

import sys
import os
import json

# Add twitterexplorer to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'twitterexplorer'))

def test_llm_parameter_generation():
    """Test that the LLM now generates proper search parameters"""
    print("=== Testing LLM Parameter Generation Fix ===")
    
    try:
        # Import required modules
        from graph_aware_llm_coordinator import GraphAwareLLMCoordinator
        from llm_client import get_litellm_client
        from investigation_graph import InvestigationGraph
        
        # Load environment variables
        from dotenv import load_dotenv
        load_dotenv()
        
        # Get real API key from Streamlit secrets or environment
        api_key = None
        
        # Try to get from Streamlit secrets first (if available)
        try:
            import streamlit as st
            if hasattr(st, 'secrets') and 'GEMINI_API_KEY' in st.secrets:
                api_key = st.secrets['GEMINI_API_KEY']
                print("Using API key from Streamlit secrets")
        except:
            pass
        
        # Fallback to environment variable
        if not api_key:
            api_key = os.getenv("GEMINI_API_KEY")
            if api_key and api_key != "your_gemini_api_key_here":
                print("Using API key from environment")
            else:
                print("No valid API key found - skipping LLM test")
                print("The prompt fix should still work when real API key is available")
                return
        
        # Create LLM coordinator with fixed prompt
        from llm_client import LiteLLMClient
        llm_client = LiteLLMClient(api_key)
        investigation_graph = InvestigationGraph()
        coordinator = GraphAwareLLMCoordinator(llm_client, investigation_graph)
        
        print("LLM coordinator created successfully")
        
        # Initialize investigation to populate graph context
        context = coordinator.start_investigation("find me information debunking ufo whistleblower michael herrer")
        print("Investigation context initialized")
        
        # Make strategic decision with fixed prompt
        decision = coordinator.make_strategic_decision("find me information debunking ufo whistleblower michael herrer")
        
        print("\n=== LLM Response Analysis ===")
        print(f"Decision Type: {decision.decision_type}")
        print(f"Number of searches: {len(decision.searches)}")
        
        # Check each search for proper structure
        for i, search in enumerate(decision.searches):
            print(f"\nSearch {i+1}:")
            print(f"  Raw search object: {search}")
            
            # Check required fields
            has_endpoint = 'endpoint' in search
            has_parameters = 'parameters' in search
            has_query = has_parameters and isinstance(search.get('parameters'), dict) and 'query' in search['parameters']
            
            print(f"  Has endpoint: {has_endpoint}")
            print(f"  Has parameters: {has_parameters}")
            print(f"  Has query parameter: {has_query}")
            
            if has_endpoint:
                print(f"  Endpoint: {search['endpoint']}")
            if has_parameters:
                print(f"  Parameters: {search['parameters']}")
                if has_query:
                    print(f"  Query: '{search['parameters']['query']}'")
            
            # Validation
            if not has_endpoint:
                print("  ERROR: Missing 'endpoint' field")
            if not has_parameters:
                print("  ERROR: Missing 'parameters' field")
            if not has_query and search.get('endpoint') == 'search.php':
                print("  ERROR: Missing 'query' in parameters for search.php endpoint")
        
        # Test the conversion to API format
        print("\n=== Testing API Format Conversion ===")
        
        # This is how investigation_engine.py converts decisions
        api_searches = []
        for search_spec in decision.searches:
            search_plan = {
                'endpoint': search_spec.get('endpoint', 'search.php'),
                'params': search_spec.get('parameters', {}),
                'reason': search_spec.get('reasoning', search_spec.get('reason', '')),
                'max_pages': search_spec.get('max_pages', 3)
            }
            api_searches.append(search_plan)
            
            print(f"API Search: {search_plan}")
            
            # Validate API search
            if search_plan['params']:
                print(f"  API parameters: {search_plan['params']}")
                if 'query' in search_plan['params']:
                    print(f"  API query: '{search_plan['params']['query']}'")
                    print("  SUCCESS: API format has query parameter!")
                else:
                    print("  ERROR: API format missing query parameter")
            else:
                print("  ERROR: API format has empty parameters")
        
        return decision
        
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    test_llm_parameter_generation()