"""Verify what actual content the Twitter API is returning"""
import requests
import json
import toml

# Load API key
secrets_path = "twitterexplorer/.streamlit/secrets.toml"
with open(secrets_path, 'r') as f:
    secrets = toml.load(f)
    api_key = secrets['RAPIDAPI_KEY']

# Make a direct API call
url = "https://twitter-api45.p.rapidapi.com/timeline.php"
headers = {
    "X-RapidAPI-Key": api_key,
    "X-RapidAPI-Host": "twitter-api45.p.rapidapi.com"
}
params = {"screenname": "elonmusk"}

print("Making API call to timeline.php for @elonmusk...")
response = requests.get(url, headers=headers, params=params, timeout=10)

print(f"Status: {response.status_code}")

if response.status_code == 200:
    data = response.json()
    
    # Save raw response for inspection
    with open('raw_api_response.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"\nRaw response saved to raw_api_response.json")
    
    # Inspect the actual content
    if 'timeline' in data and isinstance(data['timeline'], list):
        print(f"\nFound {len(data['timeline'])} items in timeline")
        
        if len(data['timeline']) > 0:
            first_item = data['timeline'][0]
            print("\n=== FIRST TWEET CONTENT ===")
            
            # Check what fields exist
            for key in ['text', 'created_at', 'user_info', 'tweet_id', 'screen_name']:
                if key in first_item:
                    value = first_item[key]
                    if isinstance(value, str):
                        print(f"{key}: {value[:200]}...")
                    elif isinstance(value, dict):
                        print(f"{key}: [dict with {len(value)} keys]")
                    else:
                        print(f"{key}: {value}")
            
            # Show the full structure of first item
            print("\n=== FULL STRUCTURE OF FIRST ITEM ===")
            print(json.dumps(first_item, indent=2, ensure_ascii=False)[:1000])
            
            # Check if this is real Twitter data
            has_tweet_text = 'text' in first_item and len(first_item.get('text', '')) > 0
            has_user_info = 'user_info' in first_item or 'screen_name' in first_item
            has_timestamp = 'created_at' in first_item
            
            print("\n=== DATA VERIFICATION ===")
            print(f"Has tweet text: {has_tweet_text}")
            print(f"Has user info: {has_user_info}")
            print(f"Has timestamp: {has_timestamp}")
            
            if has_tweet_text:
                print(f"\nACTUAL TWEET TEXT: {first_item['text'][:500]}")
                print("\n✅ THIS IS REAL TWITTER DATA!")
            else:
                print("\n❌ No tweet text found - may not be real data")
    else:
        print(f"\nNo timeline data found. Response keys: {list(data.keys())}")
else:
    print(f"API Error: {response.status_code}")
    print(response.text)