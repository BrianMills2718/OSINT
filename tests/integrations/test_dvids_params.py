#!/usr/bin/env python3
"""Test DVIDS with integration-generated params via raw HTTP."""
import os
import sys
from pathlib import Path
import requests

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

def test():
    load_dotenv()

    print("=" * 60)
    print("DVIDS Params Test")
    print("=" * 60)

    api_key = os.getenv('DVIDS_API_KEY')
    if not api_key:
        print("❌ No API key")
        return False

    # Params from integration test output
    query_params = {
        'keywords': 'training exercise OR training exercises OR field training OR joint exercise OR live-fire OR drill OR maneuver OR war games',
        'media_types': ['image', 'video', 'news'],
        'branches': ['Army', 'Navy', 'Air Force', 'Marines', 'Coast Guard', 'Joint']
    }

    print(f"\nQuery params from integration:")
    print(f"  Keywords: {query_params['keywords'][:80]}...")
    print(f"  Media types: {query_params['media_types']}")
    print(f"  Branches: {query_params['branches']}")

    # Test 1: With all params as integration builds them
    print(f"\n1. Test with type[] array...")
    params1 = {
        "api_key": api_key,
        "page": 1,
        "max_results": 10,
        "q": query_params['keywords'],
        "type[]": query_params['media_types'],  # As integration does it
        "branch": query_params['branches'][0]   # First branch only
    }

    try:
        response = requests.get(
            "https://api.dvidshub.net/search",
            params=params1,
            timeout=15
        )
        print(f"   Status: {response.status_code}")
        print(f"   URL: {response.url[:200]}...")

        if response.status_code == 200:
            data = response.json()
            results = data.get("results", [])
            print(f"   Results: {len(results)}")
        else:
            print(f"   ❌ HTTP {response.status_code}: {response.text[:200]}")

    except Exception as e:
        print(f"   ❌ Exception: {e}")

    # Test 2: Without type[] to see if that's the issue
    print(f"\n2. Test WITHOUT type[] parameter...")
    params2 = {
        "api_key": api_key,
        "page": 1,
        "max_results": 10,
        "q": query_params['keywords'],
        "branch": query_params['branches'][0]
    }

    try:
        response = requests.get(
            "https://api.dvidshub.net/search",
            params=params2,
            timeout=15
        )
        print(f"   Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            results = data.get("results", [])
            print(f"   Results: {len(results)}")
            if results:
                print(f"   ✅ First result: {results[0].get('title', 'No title')[:80]}")
                return True
        else:
            print(f"   ❌ HTTP {response.status_code}")

    except Exception as e:
        print(f"   ❌ Exception: {e}")

    return False

if __name__ == "__main__":
    success = test()
    sys.exit(0 if success else 1)
