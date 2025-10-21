"""Debug script to see raw API response structure"""

import sys
import os
import json
sys.path.insert(0, 'twitterexplorer')

import api_client
import toml

# Load API key
secrets_path = r'twitterexplorer\.streamlit\secrets.toml'
secrets = toml.load(secrets_path)
api_key = secrets.get('RAPIDAPI_KEY')

# Create a test search
search_plan = {
    'endpoint': 'search.php',
    'params': {'query': 'AI news', 'count': 10}
}

print("=" * 60)
print("RAW API RESPONSE STRUCTURE")
print("=" * 60)

# Execute API call
result = api_client.execute_api_step(search_plan, [], api_key)

print(f"\nTop-level keys: {result.keys()}")
print(f"Data type: {type(result.get('data'))}")

if 'data' in result:
    data = result['data']
    if isinstance(data, dict):
        print(f"Data keys: {list(data.keys())[:10]}")
        
        # Check each key for lists
        for key in data.keys():
            value = data[key]
            if isinstance(value, list):
                print(f"\n[LIST FOUND] '{key}' has {len(value)} items")
                if value:
                    print(f"  First item type: {type(value[0])}")
                    if isinstance(value[0], dict):
                        print(f"  First item keys: {list(value[0].keys())[:10]}")
                        if 'text' in value[0]:
                            print(f"  Sample text: {value[0]['text'][:100]}...")
            elif isinstance(value, dict):
                print(f"\n[DICT] '{key}' has {len(value)} keys")

# Now test extraction
from investigation_engine import InvestigationEngine

# Create engine
engine = InvestigationEngine(api_key)

# Test extraction
extracted = engine._extract_results_for_evaluation(result)

print("\n" + "=" * 60)
print("EXTRACTION RESULTS")
print("=" * 60)
print(f"Extracted {len(extracted)} items")

if extracted:
    for i, item in enumerate(extracted[:3]):
        print(f"\nItem {i+1}:")
        print(f"  Source: {item.get('source')}")
        print(f"  Text: {item.get('text', '')[:100]}...")
        print(f"  Has metadata: {'metadata' in item}")

print("\n" + "=" * 60)
if len(extracted) > 0:
    print("EXTRACTION SUCCESSFUL - raw results ARE being extracted")
else:
    print("EXTRACTION FAILED - THIS IS THE PROBLEM")
print("=" * 60)