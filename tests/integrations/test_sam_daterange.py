#!/usr/bin/env python3
"""Test SAM.gov with different date ranges to find maximum allowed."""
import os
import sys
from pathlib import Path
import requests
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

def test():
    load_dotenv()

    print("=" * 60)
    print("SAM.gov Date Range Test")
    print("=" * 60)

    api_key = os.getenv('SAM_GOV_API_KEY')
    if not api_key:
        print("❌ No API key")
        return False

    # Test different date ranges
    test_ranges = [
        ("1 year", 365),
        ("364 days", 364),
        ("6 months", 180),
        ("90 days", 90),
        ("60 days", 60),
        ("30 days", 30)
    ]

    for name, days in test_ranges:
        print(f"\n{name} ({days} days):")

        to_date = datetime.now()
        from_date = to_date - timedelta(days=days)

        params = {
            "api_key": api_key,
            "postedFrom": from_date.strftime("%m/%d/%Y"),
            "postedTo": to_date.strftime("%m/%d/%Y"),
            "limit": 10,
            "offset": 0,
            "keywords": "cybersecurity"
        }

        try:
            response = requests.get(
                "https://api.sam.gov/opportunities/v2/search",
                params=params,
                timeout=15
            )

            if response.status_code == 200:
                data = response.json()
                results = data.get("opportunitiesData", [])
                print(f"   ✅ Success: {len(results)} results")
                print(f"   From: {from_date.strftime('%Y-%m-%d')}")
                print(f"   To: {to_date.strftime('%Y-%m-%d')}")
                return True  # Found working range
            else:
                print(f"   ❌ HTTP {response.status_code}: {response.text[:100]}")

        except Exception as e:
            print(f"   ❌ Exception: {e}")

    return False

if __name__ == "__main__":
    success = test()
    sys.exit(0 if success else 1)
