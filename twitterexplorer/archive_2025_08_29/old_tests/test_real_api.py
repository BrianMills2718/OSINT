"""Test real Twitter API with proper authentication"""
import requests
import json
import os
import sys

# Load secrets properly
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def load_api_key():
    """Load API key from secrets.toml"""
    secrets_path = "twitterexplorer/.streamlit/secrets.toml"
    
    if os.path.exists(secrets_path):
        with open(secrets_path, 'r') as f:
            content = f.read()
            for line in content.split('\n'):
                if 'RAPIDAPI_KEY' in line:
                    # Extract the key
                    key = line.split('=')[1].strip().strip('"')
                    return key
    return None

def test_twitter_api():
    """Test the actual Twitter API with real authentication"""
    
    print("="*60)
    print("TESTING REAL TWITTER API")
    print("="*60)
    
    # Get API key
    api_key = load_api_key()
    if not api_key:
        print("[ERROR] Could not load API key from secrets.toml")
        return False
    
    print(f"[INFO] API Key loaded: {api_key[:10]}...")
    
    # Test search endpoint
    url = "https://twitter-api45.p.rapidapi.com/search.php"
    
    headers = {
        "X-RapidAPI-Key": api_key,
        "X-RapidAPI-Host": "twitter-api45.p.rapidapi.com"
    }
    
    # Try a simple search that should return results
    params = {
        "query": "twitter",  # Very common term
        "search_type": "Top"
    }
    
    print("\n### TEST 1: Search Endpoint ###")
    print(f"URL: {url}")
    print(f"Headers: X-RapidAPI-Key: {api_key[:10]}...")
    print(f"Params: {params}")
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        print(f"\nResponse Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Response Type: {type(data)}")
            
            if isinstance(data, dict):
                print(f"Response Keys: {list(data.keys())}")
                
                # Check for results
                if 'timeline' in data:
                    results = data['timeline']
                    print(f"Found {len(results)} results in 'timeline' key")
                    if results:
                        print("\nFirst result sample:")
                        first = results[0]
                        print(f"  User: {first.get('screen_name', 'N/A')}")
                        print(f"  Text: {first.get('text', 'N/A')[:100]}...")
                        return True
                elif 'results' in data:
                    results = data['results']
                    print(f"Found {len(results)} results in 'results' key")
                    if results:
                        print("\nFirst result sample:")
                        print(json.dumps(results[0], indent=2)[:500])
                        return True
                else:
                    print("No obvious results key found")
                    print("\nFull response:")
                    print(json.dumps(data, indent=2)[:1000])
            else:
                print(f"Unexpected response type: {type(data)}")
                print(f"Response: {str(data)[:500]}")
                
        elif response.status_code == 403:
            print("[ERROR] 403 Forbidden - API key may be invalid or expired")
            print(f"Response: {response.text[:500]}")
        elif response.status_code == 429:
            print("[ERROR] 429 Too Many Requests - Rate limit exceeded")
        else:
            print(f"[ERROR] Unexpected status code: {response.status_code}")
            print(f"Response: {response.text[:500]}")
            
    except requests.exceptions.Timeout:
        print("[ERROR] Request timed out")
    except Exception as e:
        print(f"[ERROR] Request failed: {e}")
    
    # Test trends endpoint
    print("\n### TEST 2: Trends Endpoint ###")
    url = "https://twitter-api45.p.rapidapi.com/trends.php"
    params = {"country": "UnitedStates"}
    
    print(f"URL: {url}")
    print(f"Params: {params}")
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        print(f"\nResponse Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list):
                print(f"Found {len(data)} trends")
                if data:
                    print("\nFirst trend:")
                    print(json.dumps(data[0], indent=2)[:300])
            elif isinstance(data, dict):
                print(f"Response Keys: {list(data.keys())}")
                if 'trends' in data:
                    trends = data['trends']
                    print(f"Found {len(trends)} trends")
                    if trends:
                        print("\nFirst trend:")
                        print(json.dumps(trends[0], indent=2)[:300])
            else:
                print(f"Unexpected response: {str(data)[:500]}")
                
    except Exception as e:
        print(f"[ERROR] Trends request failed: {e}")
    
    # Test timeline endpoint
    print("\n### TEST 3: Timeline Endpoint ###")
    url = "https://twitter-api45.p.rapidapi.com/timeline.php"
    params = {"screenname": "elonmusk"}  # Popular account
    
    print(f"URL: {url}")
    print(f"Params: {params}")
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        print(f"\nResponse Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, dict):
                print(f"Response Keys: {list(data.keys())}")
                if 'timeline' in data:
                    timeline = data['timeline']
                    print(f"Found {len(timeline)} tweets")
                    if timeline:
                        print("\nFirst tweet:")
                        first = timeline[0]
                        print(f"  Text: {first.get('text', 'N/A')[:100]}...")
                        print(f"  Created: {first.get('created_at', 'N/A')}")
            else:
                print(f"Unexpected response: {str(data)[:500]}")
                
    except Exception as e:
        print(f"[ERROR] Timeline request failed: {e}")
    
    print("\n" + "="*60)
    print("API TEST COMPLETE")
    print("="*60)
    
    return False

if __name__ == "__main__":
    success = test_twitter_api()
    if success:
        print("\n[SUCCESS] API is working and returning data!")
    else:
        print("\n[WARNING] API may not be returning expected data")