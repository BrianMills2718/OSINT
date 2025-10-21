"""Test that the result counting fix works properly"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from twitterexplorer.investigation_engine import InvestigationEngine, InvestigationConfig
import json

def test_result_counting():
    """Test that results are properly counted after the fix"""
    
    print("="*60)
    print("TESTING RESULT COUNTING FIX")
    print("="*60)
    
    # Load API key
    secrets_path = "twitterexplorer/.streamlit/secrets.toml"
    api_key = None
    
    if os.path.exists(secrets_path):
        with open(secrets_path, 'r') as f:
            content = f.read()
            for line in content.split('\n'):
                if 'RAPIDAPI_KEY' in line:
                    api_key = line.split('=')[1].strip().strip('"')
                    break
    
    if not api_key:
        print("[ERROR] Could not load API key")
        return False
    
    print(f"[INFO] API Key loaded: {api_key[:10]}...")
    
    # Create engine
    engine = InvestigationEngine(api_key)
    
    # Configure for minimal test
    config = InvestigationConfig(
        max_searches=3,  # Just 3 searches
        pages_per_search=1,  # Single page
        satisfaction_enabled=False,  # No early termination
        enforce_endpoint_diversity=True
    )
    
    print("\nConfiguration:")
    print(f"- Max searches: {config.max_searches}")
    print(f"- Pages per search: {config.pages_per_search}")
    
    print("\n" + "-"*60)
    print("Starting investigation...")
    print("-"*60)
    
    # Run investigation
    try:
        result = engine.conduct_investigation(
            "Latest tweets from Elon Musk",
            config=config
        )
        
        print(f"\n[COMPLETED] Investigation finished")
        print(f"Searches conducted: {result.search_count}")
        print(f"Total results found: {result.total_results_found}")
        
        # Check each search
        print("\n### DETAILED SEARCH RESULTS ###")
        for i, search in enumerate(result.search_history, 1):
            endpoint = search.endpoint if hasattr(search, 'endpoint') else 'unknown'
            results = search.results_count if hasattr(search, 'results_count') else 0
            
            # Get query details
            if hasattr(search, 'params'):
                params = search.params if isinstance(search.params, dict) else {}
                query = params.get('query', params.get('screenname', 'N/A'))
            else:
                query = 'N/A'
            
            print(f"{i}. {endpoint}: {query}")
            print(f"   Results: {results}")
            
            if results > 0:
                print(f"   [SUCCESS] Got {results} results!")
            else:
                print(f"   [WARNING] No results")
        
        # Final verdict
        print("\n" + "="*60)
        print("TEST RESULTS")
        print("="*60)
        
        if result.total_results_found > 0:
            print(f"[SUCCESS] Fix is working! Found {result.total_results_found} total results")
            print("The investigation engine is now properly counting results from all API response formats")
            return True
        else:
            print("[FAILURE] Still getting 0 results despite the fix")
            print("Need to investigate further why results aren't being counted")
            
            # Debug: Check if _execute_search is using the updated code
            print("\nDEBUG: Checking if the fix was applied correctly...")
            
            # Try a direct API call to verify the API works
            print("\nDirect API test:")
            import sys
            sys.path.insert(0, 'twitterexplorer')
            import api_client
            
            search_plan = {
                'endpoint': 'timeline.php',
                'params': {'screenname': 'elonmusk'},
                'reason': 'Test'
            }
            
            api_result = api_client.execute_api_step(search_plan, [], api_key)
            
            if 'data' in api_result:
                data = api_result['data']
                if 'timeline' in data:
                    print(f"  API returned {len(data['timeline'])} results")
                else:
                    print(f"  API data keys: {list(data.keys())}")
            
            return False
            
    except Exception as e:
        print(f"\n[ERROR] Investigation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_result_counting()
    
    if success:
        print("\n" + "="*60)
        print("FIX VERIFIED - SYSTEM IS NOW WORKING")
        print("="*60)
    else:
        print("\n" + "="*60) 
        print("FIX NOT WORKING - FURTHER DEBUGGING NEEDED")
        print("="*60)