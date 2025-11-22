#!/usr/bin/env python3
"""Test if DVIDS is rate limiting us."""
import os
import sys
from pathlib import Path
import requests
import time

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

def test():
    load_dotenv()

    print("=" * 60)
    print("DVIDS Rate Limit Test")
    print("=" * 60)

    api_key = os.getenv('DVIDS_API_KEY')
    if not api_key:
        print("❌ No API key")
        return False

    # Wait 5 seconds to let rate limit reset
    print(f"\nWaiting 5 seconds for rate limit to reset...")
    time.sleep(5)

    # Try simple query
    print(f"\nTest 1: Simple query...")
    params1 = {
        "api_key": api_key,
        "page": 1,
        "max_results": 5,
        "q": "training"
    }

    try:
        response = requests.get(
            "https://api.dvidshub.net/search",
            params=params1,
            timeout=15
        )
        print(f"  Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"  ✅ Results: {len(data.get('results', []))}")
        else:
            print(f"  ❌ Failed: {response.text[:200]}")
            return False
    except Exception as e:
        print(f"  ❌ Exception: {e}")
        return False

    # Wait again
    print(f"\nWaiting 3 seconds...")
    time.sleep(3)

    # Try the problematic long query
    print(f"\nTest 2: Long SIGINT query...")
    params2 = {
        "api_key": api_key,
        "page": 1,
        "max_results": 5,
        "q": 'SIGINT OR "signals intelligence"'
    }

    try:
        response = requests.get(
            "https://api.dvidshub.net/search",
            params=params2,
            timeout=15
        )
        print(f"  Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"  ✅ Results: {len(data.get('results', []))}")
            return True
        else:
            print(f"  ❌ HTTP {response.status_code}")
            print(f"  This suggests rate limiting or WAF blocking")
            return False
    except Exception as e:
        print(f"  ❌ Exception: {e}")
        return False

if __name__ == "__main__":
    test()
