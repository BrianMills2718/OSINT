#!/usr/bin/env python3
"""Test that api_keys dict includes brave_search key."""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

def test():
    load_dotenv()

    print("=" * 60)
    print("Testing API Keys Dict Construction")
    print("=" * 60)

    # Simulate what ai_research.py does
    dvids_api_key = os.getenv('DVIDS_API_KEY')
    sam_api_key = os.getenv('SAM_GOV_API_KEY')
    usajobs_api_key = os.getenv('USAJOBS_API_KEY')
    rapidapi_key = os.getenv('RAPIDAPI_KEY')

    api_keys = {
        "dvids": dvids_api_key,
        "sam": sam_api_key,
        "usajobs": usajobs_api_key,
        "twitter": rapidapi_key,
        "brave_search": os.getenv("BRAVE_SEARCH_API_KEY"),
    }

    print("\n1. API Keys Dict Contents:")
    for source_id, key in api_keys.items():
        status = "✅ Found" if key else "❌ Missing"
        print(f"   {source_id}: {status}")

    print("\n2. brave_search Key Check:")
    if "brave_search" in api_keys:
        print(f"   ✅ 'brave_search' is in dict")
        if api_keys["brave_search"]:
            print(f"   ✅ Value is not None: {api_keys['brave_search'][:10]}...")
        else:
            print(f"   ❌ Value is None")
    else:
        print(f"   ❌ 'brave_search' NOT in dict")

    print("\n3. Simulating integration lookup:")
    brave_key = api_keys.get("brave_search")
    if brave_key:
        print(f"   ✅ api_keys.get('brave_search') returns: {brave_key[:10]}...")
        print(f"\n✅ TEST PASSED: brave_search key is in dict and has value")
        return True
    else:
        print(f"   ❌ api_keys.get('brave_search') returns: {brave_key}")
        print(f"\n❌ TEST FAILED: brave_search key missing or None")
        return False

if __name__ == "__main__":
    success = test()
    sys.exit(0 if success else 1)
