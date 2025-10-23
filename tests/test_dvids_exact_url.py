#!/usr/bin/env python3
"""Test the exact DVIDS URL that's failing."""
import os
import sys
from pathlib import Path
import requests

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

def test():
    load_dotenv()

    print("=" * 60)
    print("DVIDS Exact URL Test")
    print("=" * 60)

    api_key = os.getenv('DVIDS_API_KEY')
    if not api_key:
        print("❌ No API key")
        return False

    # Exact params from failing E2E test
    params = {
        "api_key": api_key,
        "page": 1,
        "max_results": 5,
        "q": 'SIGINT OR "signals intelligence" OR "signals-intelligence" OR "signals-intel" OR "electronic warfare" OR "signals intelligence unit" OR "signals intelligence training" OR "signals intelligence operations" OR "signals intelligence exercise"',
        "type[]": ['image', 'video', 'news']
    }

    print(f"\nQuery: {params['q'][:80]}...")
    print(f"Media types: {params['type[]']}")

    try:
        response = requests.get(
            "https://api.dvidshub.net/search",
            params=params,
            timeout=15
        )

        print(f"\nStatus: {response.status_code}")
        print(f"URL: {response.url[:200]}...")

        if response.status_code == 200:
            data = response.json()
            results = data.get("results", [])
            print(f"\n✅ Results: {len(results)}")
            return True
        else:
            print(f"\n❌ HTTP {response.status_code}")
            print(f"Response: {response.text[:500]}")
            return False

    except Exception as e:
        print(f"\n❌ Exception: {e}")
        return False

if __name__ == "__main__":
    test()
