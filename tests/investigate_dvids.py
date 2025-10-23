#!/usr/bin/env python3
"""
Investigate why DVIDS returns 0 results for SIGINT.
Test with progressively simpler queries to find what works.
"""
import os
import sys
from pathlib import Path
import requests
import time

sys.path.insert(0, str(Path(__file__).parent.parent))
from dotenv import load_dotenv

def test_dvids_query(query, description):
    """Test a single DVIDS query and print results."""
    load_dotenv()
    api_key = os.getenv('DVIDS_API_KEY')

    params = {
        "api_key": api_key,
        "page": 1,
        "max_results": 10,
        "q": query
    }

    print(f"\n{description}")
    print(f"Query: {query}")

    try:
        response = requests.get(
            "https://api.dvidshub.net/search",
            params=params,
            timeout=15
        )

        if response.status_code == 200:
            data = response.json()
            results = data.get("results", [])
            print(f"✅ Status 200 - {len(results)} results")
            if results:
                print(f"   First result: {results[0].get('title', 'No title')[:80]}")
            return len(results)
        else:
            print(f"❌ Status {response.status_code}")
            return 0

    except Exception as e:
        print(f"❌ Exception: {e}")
        return 0

def main():
    print("="*60)
    print("DVIDS INVESTIGATION - Finding what queries work")
    print("="*60)

    # Test 1: Single word that definitely exists
    test_dvids_query("training", "Test 1: Simple single word")
    time.sleep(2)

    # Test 2: Two words with OR
    test_dvids_query("training OR exercise", "Test 2: Two words with OR")
    time.sleep(2)

    # Test 3: SIGINT alone
    test_dvids_query("SIGINT", "Test 3: SIGINT alone")
    time.sleep(2)

    # Test 4: signals intelligence with quotes
    test_dvids_query('"signals intelligence"', 'Test 4: "signals intelligence" quoted')
    time.sleep(2)

    # Test 5: intelligence (broader term)
    test_dvids_query("intelligence", "Test 5: intelligence (broad)")
    time.sleep(2)

    # Test 6: surveillance
    test_dvids_query("surveillance", "Test 6: surveillance")
    time.sleep(2)

    # Test 7: cryptologic (technical term)
    test_dvids_query("cryptologic", "Test 7: cryptologic")
    time.sleep(2)

    # Test 8: NSA (organization)
    test_dvids_query("NSA", "Test 8: NSA")
    time.sleep(2)

    # Test 9: electronic warfare (related concept)
    test_dvids_query("electronic warfare", "Test 9: electronic warfare")
    time.sleep(2)

    # Test 10: radio (equipment)
    test_dvids_query("radio", "Test 10: radio")

if __name__ == "__main__":
    main()
