#!/usr/bin/env python3
"""Test if branch parameter is filtering out all results."""
import os
import sys
from pathlib import Path
import requests

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

def test():
    load_dotenv()

    print("=" * 60)
    print("DVIDS Branch Filter Test")
    print("=" * 60)

    api_key = os.getenv('DVIDS_API_KEY')
    if not api_key:
        print("❌ No API key")
        return False

    query = "training exercise OR training exercises OR field training OR joint exercise OR live-fire OR drill OR maneuver OR war games"

    tests = [
        ("No branch filter", None),
        ("Army", "Army"),
        ("Navy", "Navy"),
        ("Air Force", "Air Force")
    ]

    for name, branch in tests:
        print(f"\n{name}:")

        params = {
            "api_key": api_key,
            "page": 1,
            "max_results": 10,
            "q": query
        }

        if branch:
            params["branch"] = branch

        try:
            response = requests.get(
                "https://api.dvidshub.net/search",
                params=params,
                timeout=15
            )

            if response.status_code == 200:
                data = response.json()
                results = data.get("results", [])
                print(f"  Results: {len(results)}")
                if len(results) > 0:
                    print(f"  First: {results[0].get('title', 'No title')[:60]}")
            else:
                print(f"  ❌ HTTP {response.status_code}")

        except Exception as e:
            print(f"  ❌ Exception: {e}")

    return True

if __name__ == "__main__":
    test()
