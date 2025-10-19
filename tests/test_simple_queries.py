#!/usr/bin/env python3
"""Test each API with VERY simple, broad queries that should definitely return results."""

import requests
import json
import sys
from datetime import datetime, timedelta

# Add ClearanceJobs to path
sys.path.insert(0, 'ClearanceJobs')
from ClearanceJobs import ClearanceJobs

print("=" * 80)
print("TESTING SIMPLE QUERIES THAT SHOULD RETURN RESULTS")
print("=" * 80)
print()

# Test 1: ClearanceJobs - Very broad search
print("TEST 1: ClearanceJobs - Search for 'engineer' (very common)")
print("-" * 80)

try:
    cj = ClearanceJobs()

    body = {
        "pagination": {"page": 1, "size": 5},
        "query": "engineer"
    }

    print(f"Body: {json.dumps(body, indent=2)}")
    response = cj.post("/jobs/search", body)

    print(f"Status: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        results = data.get("data", [])
        meta = data.get("meta", {})
        pagination = meta.get("pagination", {})
        total = pagination.get("total", len(results))
        print(f"✅ Found {total} total results, returned {len(results)}")
        if results:
            print(f"First job: {results[0].get('title', 'N/A')}")
    else:
        print(f"❌ Error: {response.text[:200]}")

except Exception as e:
    print(f"❌ Exception: {str(e)}")

print()

# Test 2: ClearanceJobs with filters
print("TEST 2: ClearanceJobs - 'engineer' with Secret clearance filter")
print("-" * 80)

try:
    cj = ClearanceJobs()

    body = {
        "pagination": {"page": 1, "size": 5},
        "query": "engineer",
        "filters": {
            "clearance": ["Secret"]
        }
    }

    print(f"Body: {json.dumps(body, indent=2)}")
    response = cj.post("/jobs/search", body)

    print(f"Status: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        total = data.get("total", 0)
        results = data.get("results", [])
        print(f"✅ Found {total} total results with Secret clearance, returned {len(results)}")
        if results:
            print(f"First job: {results[0].get('title', 'N/A')}")
    else:
        print(f"❌ Error: {response.text[:200]}")

except Exception as e:
    print(f"❌ Exception: {str(e)}")

print()

# Test 3: ClearanceJobs - Try 'counterterrorism'
print("TEST 3: ClearanceJobs - 'counterterrorism' (specific term)")
print("-" * 80)

try:
    cj = ClearanceJobs()

    body = {
        "pagination": {"page": 1, "size": 5},
        "query": "counterterrorism"
    }

    print(f"Body: {json.dumps(body, indent=2)}")
    response = cj.post("/jobs/search", body)

    print(f"Status: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        total = data.get("total", 0)
        results = data.get("results", [])
        print(f"Result: {total} total jobs with 'counterterrorism'")
        if total == 0:
            print("⚠️ No results - this is likely legitimate (specific term)")
        else:
            print(f"✅ Found {len(results)} jobs")
            if results:
                print(f"First job: {results[0].get('title', 'N/A')}")
    else:
        print(f"❌ Error: {response.text[:200]}")

except Exception as e:
    print(f"❌ Exception: {str(e)}")

print()

# Test 4: SAM.gov - Very broad search with longer timeout
print("TEST 4: SAM.gov - 'software' (very common, 60s timeout)")
print("-" * 80)

today = datetime.now()
thirty_days_ago = today - timedelta(days=30)

params = {
    "api_key": "SAM-db0e8074-ef7f-41b2-8456-b0f79a0a2112",
    "keywords": "software",
    "postedFrom": thirty_days_ago.strftime("%m/%d/%Y"),
    "postedTo": today.strftime("%m/%d/%Y"),
    "limit": 5
}

print(f"Params: {json.dumps(params, indent=2)}")
print(f"Timeout: 60 seconds")

try:
    start = datetime.now()
    response = requests.get(
        "https://api.sam.gov/opportunities/v2/search",
        params=params,
        timeout=60  # Longer timeout
    )
    elapsed = (datetime.now() - start).total_seconds()

    print(f"Status: {response.status_code} (took {elapsed:.1f}s)")
    print(f"URL: {response.url}")

    if response.status_code == 200:
        data = response.json()
        total = data.get('totalRecords', data.get('total', 0))
        results = data.get('opportunitiesData', data.get('results', []))
        print(f"✅ Found {total} total results, returned {len(results)}")
        if results:
            print(f"First result: {results[0].get('title', 'N/A')[:60]}...")
    else:
        print(f"❌ Error: {response.text[:200]}")

except requests.Timeout:
    print(f"❌ Timeout after 60 seconds - SAM.gov API is very slow or down")
except Exception as e:
    print(f"❌ Exception: {str(e)}")

print()

# Test 5: SAM.gov - Smaller date range
print("TEST 5: SAM.gov - 'software' last 7 days (60s timeout)")
print("-" * 80)

today = datetime.now()
seven_days_ago = today - timedelta(days=7)

params = {
    "api_key": "SAM-db0e8074-ef7f-41b2-8456-b0f79a0a2112",
    "keywords": "software",
    "postedFrom": seven_days_ago.strftime("%m/%d/%Y"),
    "postedTo": today.strftime("%m/%d/%Y"),
    "limit": 5
}

print(f"Date range: {seven_days_ago.strftime('%m/%d/%Y')} to {today.strftime('%m/%d/%Y')}")

try:
    start = datetime.now()
    response = requests.get(
        "https://api.sam.gov/opportunities/v2/search",
        params=params,
        timeout=60
    )
    elapsed = (datetime.now() - start).total_seconds()

    print(f"Status: {response.status_code} (took {elapsed:.1f}s)")

    if response.status_code == 200:
        data = response.json()
        total = data.get('totalRecords', data.get('total', 0))
        results = data.get('opportunitiesData', data.get('results', []))
        print(f"✅ Found {total} total results, returned {len(results)}")
        if results:
            print(f"First result: {results[0].get('title', 'N/A')[:60]}...")
    else:
        print(f"❌ Error: {response.text[:200]}")

except requests.Timeout:
    print(f"❌ Timeout after 60 seconds - SAM.gov API is very slow or down")
except Exception as e:
    print(f"❌ Exception: {str(e)}")

print()
print("=" * 80)
print("SUMMARY")
print("=" * 80)
print("If ClearanceJobs 'engineer' works but 'counterterrorism' returns 0:")
print("  → Legitimate - no jobs with that keyword")
print()
print("If SAM.gov times out even with 60s timeout:")
print("  → API is slow/down, need to increase timeout in ai_research.py")
print("=" * 80)
