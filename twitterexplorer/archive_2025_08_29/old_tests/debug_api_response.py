"""Debug script to see what the API is actually returning"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import sys
sys.path.insert(0, 'twitterexplorer')
import api_client
import config
import json

def load_api_key():
    """Load API key from secrets.toml"""
    secrets_path = "twitterexplorer/.streamlit/secrets.toml"
    
    if os.path.exists(secrets_path):
        with open(secrets_path, 'r') as f:
            content = f.read()
            for line in content.split('\n'):
                if 'RAPIDAPI_KEY' in line:
                    key = line.split('=')[1].strip().strip('"')
                    return key
    return None

def debug_api_response():
    """Debug what execute_api_step actually returns"""
    
    api_key = load_api_key()
    if not api_key:
        print("Could not load API key")
        return
    
    print("="*60)
    print("DEBUGGING API RESPONSE")
    print("="*60)
    
    # Test 1: timeline.php endpoint
    search_plan = {
        'endpoint': 'timeline.php',
        'params': {'screenname': 'elonmusk'},
        'reason': 'Get Elon Musk tweets'
    }
    
    print("\nTest 1: timeline.php for elonmusk")
    print("-"*40)
    
    result = api_client.execute_api_step(
        search_plan,
        [],  # No previous results
        api_key
    )
    
    print(f"Result keys: {list(result.keys())}")
    
    if 'error' in result:
        print(f"ERROR: {result['error']}")
    else:
        data = result.get('data', {})
        print(f"Data type: {type(data)}")
        
        if isinstance(data, dict):
            print(f"Data keys: {list(data.keys())}")
            
            # Check each key for lists
            for key in data.keys():
                val = data[key]
                if isinstance(val, list):
                    print(f"  '{key}': List with {len(val)} items")
                    if val:
                        print(f"    First item type: {type(val[0])}")
                        if isinstance(val[0], dict):
                            print(f"    First item keys: {list(val[0].keys())[:5]}...")
                elif isinstance(val, dict):
                    print(f"  '{key}': Dict with {len(val)} keys")
                else:
                    print(f"  '{key}': {type(val)}")
        
        # Show a sample of the actual data
        print("\nSample of raw data:")
        data_str = json.dumps(data, indent=2)
        print(data_str[:1000])
    
    # Test 2: search.php endpoint
    search_plan = {
        'endpoint': 'search.php',
        'params': {'query': 'twitter', 'search_type': 'Top'},
        'reason': 'Search for twitter'
    }
    
    print("\n\nTest 2: search.php for 'twitter'")
    print("-"*40)
    
    result = api_client.execute_api_step(
        search_plan,
        [],
        api_key
    )
    
    print(f"Result keys: {list(result.keys())}")
    
    if 'error' in result:
        print(f"ERROR: {result['error']}")
    else:
        data = result.get('data', {})
        print(f"Data type: {type(data)}")
        
        if isinstance(data, dict):
            print(f"Data keys: {list(data.keys())}")
            
            for key in data.keys():
                val = data[key]
                if isinstance(val, list):
                    print(f"  '{key}': List with {len(val)} items")

if __name__ == "__main__":
    debug_api_response()