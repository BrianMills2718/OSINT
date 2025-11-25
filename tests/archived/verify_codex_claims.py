#!/usr/bin/env python3
"""
Verify Codex's claims about DVIDS boolean query behavior.
Test the exact combinations Codex claims return 0.
"""
import os
import sys
from pathlib import Path
import requests
import time

sys.path.insert(0, str(Path(__file__).parent.parent))
from dotenv import load_dotenv

def test_dvids(query, description):
    """Test DVIDS query and return result count."""
    load_dotenv()
    api_key = os.getenv('DVIDS_API_KEY')

    params = {
        "api_key": api_key,
        "page": 1,
        "max_results": 10,
        "q": query
    }

    print(f"\n{description}")
    print(f"Query: '{query}'")

    try:
        response = requests.get(
            "https://api.dvidshub.net/search",
            params=params,
            timeout=15
        )

        if response.status_code == 200:
            data = response.json()
            results = data.get("results", [])
            page_info = data.get("page_info", {})
            total = page_info.get("total_results", len(results))
            print(f"✅ Status 200")
            print(f"   Results returned: {len(results)}")
            print(f"   Total available: {total}")
            return total
        else:
            print(f"❌ Status {response.status_code}")
            return None

    except Exception as e:
        print(f"❌ Exception: {e}")
        return None

def main():
    print("="*70)
    print("VERIFYING CODEX'S CLAIMS ABOUT DVIDS BOOLEAN QUERIES")
    print("="*70)

    # Codex's Claim 1: Individual terms work
    print("\n" + "="*70)
    print("CLAIM 1: Individual terms return results")
    print("="*70)

    test_dvids("SIGINT", "Test 1a: SIGINT alone")
    time.sleep(2)

    test_dvids("ELINT", "Test 1b: ELINT alone")
    time.sleep(2)

    test_dvids("COMINT", "Test 1c: COMINT alone")
    time.sleep(2)

    test_dvids("signals intelligence", "Test 1d: signals intelligence")
    time.sleep(2)

    # Codex's Claim 2: Some OR combos return 0
    print("\n" + "="*70)
    print("CLAIM 2: Certain OR combinations collapse to 0")
    print("="*70)

    test_dvids("SIGINT OR signals intelligence", "Test 2a: SIGINT OR signals intelligence")
    time.sleep(2)

    test_dvids("SIGINT OR ELINT", "Test 2b: SIGINT OR ELINT (Codex claims this returns 0)")
    time.sleep(2)

    test_dvids("SIGINT OR COMINT", "Test 2c: SIGINT OR COMINT")
    time.sleep(2)

    test_dvids("ELINT OR COMINT", "Test 2d: ELINT OR COMINT")
    time.sleep(2)

    # Codex's Claim 3: Big OR chain returns 0
    print("\n" + "="*70)
    print("CLAIM 3: Large OR chain returns 0")
    print("="*70)

    test_dvids("SIGINT OR signals intelligence OR COMINT OR ELINT OR electronic warfare",
               "Test 3: Full OR chain (Codex claims 0)")
    time.sleep(2)

    # Test with media type filter
    print("\n" + "="*70)
    print("CLAIM 4: Media type filter affects results")
    print("="*70)

    load_dotenv()
    api_key = os.getenv('DVIDS_API_KEY')

    # Test without type filter
    params1 = {
        "api_key": api_key,
        "page": 1,
        "max_results": 10,
        "q": "SIGINT"
    }
    print("\nTest 4a: SIGINT without type[] filter")
    response1 = requests.get("https://api.dvidshub.net/search", params=params1, timeout=15)
    if response1.status_code == 200:
        data1 = response1.json()
        total1 = data1.get("page_info", {}).get("total_results", 0)
        print(f"   Total: {total1}")

    time.sleep(2)

    # Test with type filter
    params2 = {
        "api_key": api_key,
        "page": 1,
        "max_results": 10,
        "q": "SIGINT",
        "type[]": ["image", "video", "news"]
    }
    print("\nTest 4b: SIGINT with type[]=['image','video','news']")
    response2 = requests.get("https://api.dvidshub.net/search", params=params2, timeout=15)
    if response2.status_code == 200:
        data2 = response2.json()
        total2 = data2.get("page_info", {}).get("total_results", 0)
        results2 = data2.get("results", [])
        print(f"   Total: {total2}")
        if results2:
            print(f"   First result type: {results2[0].get('type', 'unknown')}")

    print("\n" + "="*70)
    print("VERIFICATION COMPLETE")
    print("="*70)

if __name__ == "__main__":
    main()
