#!/usr/bin/env python3
"""
Debug API Integration - Test the complete flow from LLM decision to Twitter API call

This will help identify where the search parameters are being lost between 
the LLM generating intelligent strategies and the API receiving empty queries.
"""

import sys
import os

# Add twitterexplorer to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'twitterexplorer'))

def test_llm_decision_generation():
    """Test that LLM generates proper strategic decisions with search parameters"""
    print("=== Testing LLM Strategic Decision Generation ===")
    
    try:
        # Import required modules
        from graph_aware_llm_coordinator import GraphAwareLLMCoordinator
        from llm_client import get_litellm_client
        from investigation_graph import InvestigationGraph
        
        # Create LLM coordinator
        llm_client = get_litellm_client()
        investigation_graph = InvestigationGraph()
        coordinator = GraphAwareLLMCoordinator(llm_client, investigation_graph)
        
        # Initialize investigation
        context = coordinator.start_investigation("find me information debunking ufo whistleblower michael herrer")
        
        print(f"✅ Investigation context initialized: {context.goal}")
        
        # Make strategic decision
        decision = coordinator.make_strategic_decision("find me information debunking ufo whistleblower michael herrer")
        
        print(f"✅ LLM Strategic Decision Generated:")
        print(f"   Decision Type: {decision.decision_type}")
        print(f"   Reasoning: {decision.reasoning[:100]}...")
        print(f"   Number of searches: {len(decision.searches)}")
        
        for i, search in enumerate(decision.searches):
            print(f"   Search {i+1}:")
            print(f"     - Endpoint: {search.get('endpoint', 'MISSING')}")
            print(f"     - Parameters: {search.get('parameters', 'MISSING')}")
            if 'parameters' in search and 'query' in search['parameters']:
                print(f"     - Query: '{search['parameters']['query']}'")
            else:
                print(f"     - ❌ NO QUERY PARAMETER FOUND!")
        
        return decision
        
    except Exception as e:
        print(f"❌ LLM Decision Generation Failed: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_api_call_execution(decision):
    """Test that the search decision gets properly converted to API calls"""
    print("\n=== Testing API Call Execution ===")
    
    if not decision or not decision.searches:
        print("❌ No decision or searches to test")
        return
    
    try:
        # Import API client
        import api_client
        
        # Test with first search from decision
        search_spec = decision.searches[0]
        
        print(f"Testing search spec: {search_spec}")
        
        # Convert to API client format
        search_plan = {
            'endpoint': search_spec.get('endpoint', 'search.php'),
            'params': search_spec.get('parameters', {}),
            'reason': search_spec.get('reasoning', 'Test search'),
            'max_pages': 1  # Just test 1 page
        }
        
        print(f"Converted search plan: {search_plan}")
        
        # Check if we have a RapidAPI key
        rapidapi_key = os.getenv("RAPIDAPI_KEY")
        if not rapidapi_key:
            print("❌ RAPIDAPI_KEY not found in environment - cannot test actual API call")
            print("   But search plan conversion looks correct")
            return
        
        print(f"✅ RapidAPI key found: {rapidapi_key[:10]}...")
        
        # Execute the API call
        print("🔄 Executing Twitter API call...")
        result = api_client.execute_api_step(
            search_plan,
            [],  # No previous results
            rapidapi_key
        )
        
        print(f"✅ API Call Result:")
        print(f"   - Endpoint: {result.get('endpoint')}")
        print(f"   - Executed params: {result.get('executed_params', {})}")
        print(f"   - Has data: {'data' in result}")
        print(f"   - Has error: {'error' in result}")
        
        if 'error' in result:
            print(f"   - Error: {result['error']}")
        elif 'data' in result:
            data = result['data']
            if isinstance(data, dict):
                print(f"   - Data keys: {list(data.keys())}")
                # Count results
                total_results = 0
                for key, value in data.items():
                    if isinstance(value, list):
                        total_results += len(value)
                        print(f"   - {key}: {len(value)} items")
                print(f"   - Total results: {total_results}")
            else:
                print(f"   - Data type: {type(data)}")
        
        return result
        
    except Exception as e:
        print(f"❌ API Call Execution Failed: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_investigation_engine_flow():
    """Test the complete investigation engine flow"""
    print("\n=== Testing Complete Investigation Engine Flow ===")
    
    try:
        from investigation_engine import InvestigationEngine, InvestigationConfig
        
        # Check if we have RapidAPI key
        rapidapi_key = os.getenv("RAPIDAPI_KEY") 
        if not rapidapi_key:
            print("❌ RAPIDAPI_KEY not found - cannot test complete flow")
            return
        
        # Create investigation engine
        engine = InvestigationEngine(rapidapi_key)
        print(f"✅ Investigation engine created (Graph mode: {engine.graph_mode})")
        
        # Create minimal config for testing
        config = InvestigationConfig(
            max_searches=3,  # Just 3 searches for testing
            max_time_minutes=2,  # 2 minute limit
            show_search_details=False,  # Reduce output
            show_strategy_reasoning=True
        )
        
        print("🔄 Running investigation with minimal config...")
        
        # This would normally be run in Streamlit, but we'll simulate it
        import unittest.mock
        
        # Mock Streamlit functions
        with unittest.mock.patch('streamlit.container'), \
             unittest.mock.patch('streamlit.empty'), \
             unittest.mock.patch('streamlit.info'), \
             unittest.mock.patch('streamlit.success'), \
             unittest.mock.patch('streamlit.error'):
            
            session = engine.conduct_investigation(
                "find me information debunking ufo whistleblower michael herrer",
                config
            )
        
        print(f"✅ Investigation completed:")
        print(f"   - Search count: {session.search_count}")
        print(f"   - Total results: {session.total_results_found}")
        print(f"   - Round count: {session.round_count}")
        print(f"   - Completion reason: {session.completion_reason}")
        
        # Check search history for actual parameters
        print(f"\n   Search History:")
        for attempt in session.search_history:
            print(f"   - Search {attempt.search_id}: {attempt.endpoint}")
            print(f"     Params: {attempt.params}")
            print(f"     Results: {attempt.results_count}")
            if attempt.error:
                print(f"     Error: {attempt.error}")
        
        return session
        
    except Exception as e:
        print(f"❌ Investigation Engine Flow Failed: {e}")
        import traceback
        traceback.print_exc()
        return None

def main():
    """Main test function"""
    print("Twitter Explorer API Integration Debug Tool")
    print("=" * 50)
    
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    # Test 1: LLM Decision Generation
    decision = test_llm_decision_generation()
    
    # Test 2: API Call Execution
    test_api_call_execution(decision)
    
    # Test 3: Complete Investigation Engine Flow
    # test_investigation_engine_flow()  # Comment out for now to avoid Streamlit issues
    
    print("\n=== Debug Summary ===")
    if decision and decision.searches:
        print("✅ LLM generates strategic decisions with search parameters")
        search = decision.searches[0]
        if 'parameters' in search and search['parameters']:
            print("✅ Search parameters are properly structured")
        else:
            print("❌ Search parameters are missing or empty")
    else:
        print("❌ LLM decision generation failed")
    
    print("\nNext steps:")
    print("1. If LLM works but API fails: Fix API integration")
    print("2. If LLM generates empty params: Fix prompt/response parsing")
    print("3. If everything works individually: Fix investigation engine integration")

if __name__ == "__main__":
    main()