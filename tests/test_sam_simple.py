#!/usr/bin/env python3
"""Test SAM.gov with simple keywords (no OR operators)."""
import asyncio
import os
import sys
from pathlib import Path
import requests

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

def test():
    load_dotenv()

    print("=" * 60)
    print("SAM.gov Simple Keywords Test")
    print("=" * 60)

    api_key = os.getenv('SAM_GOV_API_KEY')
    print(f"\n1. API Key: {api_key[:15]}...") if api_key else print("❌ Missing")

    if not api_key:
        print("❌ No API key")
        return False

    # Test 1: Simple keywords (what user wants)
    print(f"\n2. Test with simple keywords (SIGINT)...")
    params1 = {
        "api_key": api_key,
        "postedFrom": "10/22/2024",
        "postedTo": "10/22/2025",
        "limit": 10,
        "offset": 0,
        "keywords": "SIGINT"
    }

    try:
        response = requests.get(
            "https://api.sam.gov/opportunities/v2/search",
            params=params1,
            timeout=15
        )
        print(f"   Status: {response.status_code}")
        print(f"   URL: {response.url[:200]}...")

        if response.status_code == 200:
            data = response.json()
            results = data.get("opportunitiesData", [])
            print(f"   ✅ Success: {len(results)} results")
            return True
        else:
            print(f"   ❌ Failed: HTTP {response.status_code}")
            print(f"   Response: {response.text[:500]}")
            return False

    except Exception as e:
        print(f"   ❌ Exception: {type(e).__name__}: {e}")
        return False

if __name__ == "__main__":
    success = test()
    sys.exit(0 if success else 1)
