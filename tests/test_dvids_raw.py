#!/usr/bin/env python3
"""Test DVIDS with raw HTTP request."""
import os
import sys
from pathlib import Path
import requests

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

def test():
    load_dotenv()

    print("=" * 60)
    print("DVIDS Raw HTTP Test")
    print("=" * 60)

    api_key = os.getenv('DVIDS_API_KEY')
    print(f"\n1. API Key: {api_key[:15]}...") if api_key else print("❌ Missing")

    if not api_key:
        print("❌ No API key")
        return False

    # Test 1: Simple search
    print(f"\n2. Test 1: Simple search (training)...")
    params = {
        "api_key": api_key,
        "page": 1,
        "max_results": 10,
        "q": "training"
    }

    try:
        response = requests.get(
            "https://api.dvidshub.net/search",
            params=params,
            timeout=15
        )
        print(f"   Status: {response.status_code}")
        print(f"   URL: {response.url[:150]}...")

        if response.status_code == 200:
            data = response.json()
            results = data.get("results", [])
            print(f"   ✅ Success: {len(results)} results")
            if results:
                print(f"   First result: {results[0].get('title', 'No title')[:80]}")
            return len(results) > 0
        else:
            print(f"   ❌ HTTP {response.status_code}")
            print(f"   Response: {response.text[:500]}")
            return False

    except Exception as e:
        print(f"   ❌ Exception: {type(e).__name__}: {e}")
        return False

if __name__ == "__main__":
    success = test()
    sys.exit(0 if success else 1)
