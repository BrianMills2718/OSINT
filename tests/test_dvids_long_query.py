#!/usr/bin/env python3
"""Test if DVIDS handles long queries with multiple OR clauses."""
import os
import sys
from pathlib import Path
import requests

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

def test():
    load_dotenv()

    print("=" * 60)
    print("DVIDS Long Query Test")
    print("=" * 60)

    api_key = os.getenv('DVIDS_API_KEY')
    if not api_key:
        print("❌ No API key")
        return False

    # Exact query from LLM output
    long_query = "training exercise OR training exercises OR field training OR joint exercise OR live-fire OR drill OR maneuver OR war games"

    print(f"\nLong query ({len(long_query)} chars):")
    print(f"  {long_query}")

    params = {
        "api_key": api_key,
        "page": 1,
        "max_results": 10,
        "q": long_query
    }

    print(f"\n\nTesting...")
    try:
        response = requests.get(
            "https://api.dvidshub.net/search",
            params=params,
            timeout=15
        )

        print(f"Status: {response.status_code}")
        print(f"URL: {response.url[:150]}...")

        if response.status_code == 200:
            data = response.json()
            results = data.get("results", [])
            print(f"\n✅ Results: {len(results)}")
            if len(results) > 0:
                for i, r in enumerate(results[:3]):
                    print(f"  {i+1}. {r.get('title', 'No title')[:70]}")
                return True
            else:
                print(f"⚠️ 0 results - query might be too specific or DVIDS has no matches")
                return False
        else:
            print(f"❌ HTTP {response.status_code}")
            print(f"Response: {response.text[:500]}")
            return False

    except Exception as e:
        print(f"❌ Exception: {e}")
        return False

if __name__ == "__main__":
    test()
