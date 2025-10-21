"""Direct test of _execute_search to verify the fix"""

import sys
import os
import importlib

# Force reload to avoid caching issues
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, 'twitterexplorer')

# Import the module properly
from twitterexplorer.investigation_engine import InvestigationEngine
from twitterexplorer import investigation_engine
importlib.reload(investigation_engine)

def test_execute_search():
    """Test _execute_search directly"""
    
    print("="*60)
    print("DIRECT TEST OF _execute_search METHOD")
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
        return
    
    print(f"[INFO] API Key loaded: {api_key[:10]}...")
    
    # Create engine
    engine = InvestigationEngine(api_key)
    
    # Test search plan
    search_plan = {
        'endpoint': 'timeline.php',
        'params': {'screenname': 'elonmusk'},
        'reason': 'Get latest tweets',
        'max_pages': 1  # Add this to avoid config issues
    }
    
    print("\nExecuting search:")
    print(f"- Endpoint: {search_plan['endpoint']}")
    print(f"- Params: {search_plan['params']}")
    
    # Execute search
    result = engine._execute_search(search_plan, 1, 1)
    
    print("\nSearch result:")
    print(f"- Results count: {result.results_count}")
    print(f"- Effectiveness score: {result.effectiveness_score}")
    print(f"- Error: {result.error if result.error else 'None'}")
    print(f"- Execution time: {result.execution_time:.2f}s")
    
    if result.results_count > 0:
        print(f"\n[SUCCESS] The fix is working! Found {result.results_count} results")
        
        # Check if raw results were extracted
        if hasattr(result, '_raw_results'):
            print(f"[INFO] Also extracted {len(result._raw_results)} items for evaluation")
    else:
        print(f"\n[FAILURE] Still getting 0 results")
        
        # Let's debug the API call directly
        print("\nDEBUG: Calling API directly...")
        import api_client
        
        api_result = api_client.execute_api_step(search_plan, [], api_key)
        
        if 'error' in api_result:
            print(f"  API Error: {api_result['error']}")
        else:
            data = api_result.get('data', {})
            print(f"  API returned data type: {type(data)}")
            if isinstance(data, dict):
                print(f"  Data keys: {list(data.keys())}")
                for key in data.keys():
                    if isinstance(data[key], list):
                        print(f"    '{key}': List with {len(data[key])} items")

if __name__ == "__main__":
    test_execute_search()