#!/usr/bin/env python3
"""Test Brave Search with raw HTTP response to see actual errors."""
import os
import sys
from pathlib import Path
import requests

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

def test():
    load_dotenv()

    print("=" * 60)
    print("Brave Search Raw HTTP Response Test")
    print("=" * 60)

    api_key = os.getenv('BRAVE_SEARCH_API_KEY')
    print(f"\n1. API Key: {api_key[:10]}..." if api_key else "❌ Missing")

    if not api_key:
        print("❌ No API key")
        return False

    # Make raw HTTP request
    print(f"\n2. Making raw HTTP request...")
    print(f"   Query: 'test'")

    try:
        response = requests.get(
            "https://api.search.brave.com/res/v1/web/search",
            params={"q": "test", "count": 1},
            headers={
                "Accept": "application/json",
                "X-Subscription-Token": api_key
            },
            timeout=15
        )

        print(f"\n3. Response:")
        print(f"   Status Code: {response.status_code}")
        print(f"   Headers: {dict(response.headers)}")
        print(f"\n4. Body:")
        print(response.text[:500])  # First 500 chars

        if response.status_code == 200:
            data = response.json()
            results = data.get('web', {}).get('results', [])
            print(f"\n5. Results: {len(results)} items")
            return len(results) > 0
        else:
            print(f"\n❌ HTTP {response.status_code}")
            return False

    except Exception as e:
        print(f"\n❌ Exception: {type(e).__name__}: {e}")
        return False

if __name__ == "__main__":
    success = test()
    sys.exit(0 if success else 1)
