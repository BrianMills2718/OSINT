#!/usr/bin/env python3
"""Test each API directly to understand what works and what doesn't."""

import requests
import json
from datetime import datetime, timedelta
from ClearanceJobs import ClearanceJobs

print("=" * 80)
print("TESTING APIS DIRECTLY")
print("=" * 80)
print()

# Test 1: DVIDS - Simplest possible query
print("TEST 1: DVIDS - Simplest query")
print("-" * 80)
dvids_url = "https://api.dvidshub.net/v1/search"
dvids_params = {
    "api_key": "key-68f319e8dc377",
    "q": "military",
    "limit": 5
}
print(f"URL: {dvids_url}")
print(f"Params: {json.dumps(dvids_params, indent=2)}")

try:
    response = requests.get(dvids_url, params=dvids_params, timeout=10)
    print(f"Status Code: {response.status_code}")
    print(f"Actual URL: {response.url}")

    if response.status_code == 200:
        data = response.json()
        total = data.get("total", 0)
        results = data.get("results", [])
        print(f"✅ SUCCESS: Found {total} results, showing {len(results)}")
        if results:
            print(f"First result: {results[0].get('title', 'N/A')}")
    else:
        print(f"❌ FAILED: {response.text[:500]}")
except Exception as e:
    print(f"❌ ERROR: {str(e)}")

print()
print()

# Test 2: SAM.gov - Known good search
print("TEST 2: SAM.gov - Simple search with good dates")
print("-" * 80)

# Use dates we KNOW are in the past
today = datetime.now()
thirty_days_ago = today - timedelta(days=30)

sam_url = "https://api.sam.gov/opportunities/v2/search"
sam_params = {
    "api_key": "SAM-db0e8074-ef7f-41b2-8456-b0f79a0a2112",
    "keywords": "software",
    "postedFrom": thirty_days_ago.strftime("%m/%d/%Y"),
    "postedTo": today.strftime("%m/%d/%Y"),
    "limit": 5
}
print(f"URL: {sam_url}")
print(f"Params: {json.dumps(sam_params, indent=2)}")
print(f"Date range: {thirty_days_ago.strftime('%m/%d/%Y')} to {today.strftime('%m/%d/%Y')}")

try:
    response = requests.get(sam_url, params=sam_params, timeout=10)
    print(f"Status Code: {response.status_code}")
    print(f"Actual URL: {response.url}")

    if response.status_code == 200:
        data = response.json()
        total = data.get('totalRecords', data.get('total', 0))
        results = data.get('opportunitiesData', data.get('results', []))
        print(f"✅ SUCCESS: Found {total} results, showing {len(results)}")
        if results:
            print(f"First result: {results[0].get('title', 'N/A')}")
    else:
        print(f"❌ FAILED: {response.text[:500]}")
except Exception as e:
    print(f"❌ ERROR: {str(e)}")

print()
print()

# Test 3: ClearanceJobs - Simple search
print("TEST 3: ClearanceJobs - Simple search")
print("-" * 80)

body = {
    "pagination": {"page": 1, "size": 5},
    "query": "engineer"
}
print(f"Endpoint: POST /jobs/search")
print(f"Body: {json.dumps(body, indent=2)}")

try:
    cj = ClearanceJobs()
    response = cj.post("/jobs/search", body)
    print(f"Status Code: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        total = data.get("total", 0)
        results = data.get("results", [])
        print(f"✅ SUCCESS: Found {total} results, showing {len(results)}")
        if results:
            print(f"First result: {results[0].get('title', 'N/A')}")
    else:
        print(f"❌ FAILED: {response.text[:500]}")
except Exception as e:
    print(f"❌ ERROR: {str(e)}")

print()
print()

# Test 4: What's today's date in Python?
print("TEST 4: Date verification")
print("-" * 80)
print(f"Today's date: {datetime.now().strftime('%Y-%m-%d')}")
print(f"60 days ago: {(datetime.now() - timedelta(days=60)).strftime('%Y-%m-%d')}")
print(f"SAM.gov format today: {datetime.now().strftime('%m/%d/%Y')}")
print(f"SAM.gov format 60 days ago: {(datetime.now() - timedelta(days=60)).strftime('%m/%d/%Y')}")

print()
print("=" * 80)
print("DONE")
print("=" * 80)
