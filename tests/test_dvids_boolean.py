#!/usr/bin/env python3
"""Test if DVIDS supports Boolean operators."""
import os
import sys
from pathlib import Path
import requests

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

def test():
    load_dotenv()

    print("=" * 60)
    print("DVIDS Boolean Operator Test")
    print("=" * 60)

    api_key = os.getenv('DVIDS_API_KEY')
    if not api_key:
        print("❌ No API key")
        return False

    tests = [
        ("Simple: training", "training"),
        ("With OR: training OR exercise", "training OR exercise"),
        ("Space-separated: training exercise", "training exercise"),
        ("Just exercise", "exercise")
    ]

    for name, query in tests:
        print(f"\n{name}:")
        print(f"  Query: {query}")

        params = {
            "api_key": api_key,
            "page": 1,
            "max_results": 5,
            "q": query
        }

        try:
            response = requests.get(
                "https://api.dvidshub.net/search",
                params=params,
                timeout=15
            )

            if response.status_code == 200:
                data = response.json()
                results = data.get("results", [])
                print(f"  ✅ {len(results)} results")
                if len(results) > 0:
                    print(f"     First: {results[0].get('title', 'No title')[:60]}...")
            else:
                print(f"  ❌ HTTP {response.status_code}")

        except Exception as e:
            print(f"  ❌ Exception: {e}")

    return True

if __name__ == "__main__":
    test()
