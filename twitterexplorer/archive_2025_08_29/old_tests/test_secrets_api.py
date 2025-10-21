"""Test API with keys from secrets.toml"""
import os
import sys
import toml
import requests

# Load secrets
secrets_path = "twitterexplorer/.streamlit/secrets.toml"
print(f"Loading secrets from: {secrets_path}")

with open(secrets_path, 'r') as f:
    secrets = toml.load(f)

rapidapi_key = secrets.get('RAPIDAPI_KEY')
print(f"RapidAPI Key: {rapidapi_key[:20]}...")

# Test the API directly
print("\n[TESTING TWITTER API]")
print("-" * 40)

url = "https://twitter-api45.p.rapidapi.com/search.php"
headers = {
    "X-RapidAPI-Key": rapidapi_key,
    "X-RapidAPI-Host": "twitter-api45.p.rapidapi.com"
}
params = {
    "query": "Elon Musk",
    "search_type": "Top"
}

print(f"URL: {url}")
print(f"Headers: X-RapidAPI-Key: {rapidapi_key[:20]}...")
print(f"Params: {params}")

try:
    response = requests.get(url, headers=headers, params=params, timeout=10)
    print(f"\nResponse Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print("[SUCCESS] API call succeeded!")
        
        # Check what's in the response
        if isinstance(data, dict):
            print(f"Response keys: {list(data.keys())}")
            
            # Look for timeline or results
            if 'timeline' in data:
                timeline = data['timeline']
                if isinstance(timeline, list) and len(timeline) > 0:
                    print(f"Found {len(timeline)} items in timeline")
                    print("\nFirst item sample:")
                    first = timeline[0]
                    if isinstance(first, dict):
                        for key in ['text', 'screen_name', 'created_at', 'user_info']:
                            if key in first:
                                value = str(first[key])[:100]
                                # Encode to avoid unicode issues
                                value = value.encode('ascii', 'ignore').decode('ascii')
                                print(f"  {key}: {value}")
                else:
                    print(f"Timeline is: {timeline}")
            else:
                print(f"No 'timeline' key. Data sample: {str(data)[:200]}")
    else:
        print(f"[ERROR] Status {response.status_code}")
        print(f"Response: {response.text}")
        
except Exception as e:
    print(f"[ERROR] Exception: {e}")

print("\n" + "=" * 60)
print("CONCLUSION:")
if response.status_code == 200:
    print("[OK] API key from secrets.toml is WORKING!")
    print("[OK] Twitter API is accessible!")
elif response.status_code == 403:
    print("[ERROR] API key is valid but not subscribed to Twitter API")
    print("        You need to subscribe to the Twitter API on RapidAPI")
else:
    print(f"[ERROR] Unexpected error: {response.status_code}")
print("=" * 60)