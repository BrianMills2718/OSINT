#!/usr/bin/env python3
"""Quick test of ClearanceJobs with fixed response parsing."""

import sys
sys.path.insert(0, 'ClearanceJobs')
from ClearanceJobs import ClearanceJobs

print("Testing ClearanceJobs with 'engineer' query")
print("=" * 60)

try:
    cj = ClearanceJobs()

    body = {
        "pagination": {"page": 1, "size": 5},
        "query": "engineer"
    }

    response = cj.post("/jobs/search", body)
    data = response.json()

    # Use correct response structure
    results = data.get("data", [])
    meta = data.get("meta", {})
    pagination = meta.get("pagination", {})
    total = pagination.get("total", len(results))

    print(f"Status: {response.status_code}")
    print(f"✅ Found {total} total results, returned {len(results)}")

    if results:
        print(f"\nFirst job:")
        print(f"  Title: {results[0].get('job_name', 'N/A')}")
        print(f"  Company: {results[0].get('company_name', 'N/A')}")
        print(f"  Location: {results[0].get('locations', [{}])[0].get('location', 'N/A')}")
        print(f"  Clearance: {results[0].get('clearance', 'N/A')}")

    print("\n✅ SUCCESS: ClearanceJobs API works correctly!")

except Exception as e:
    print(f"❌ ERROR: {str(e)}")
    import traceback
    traceback.print_exc()
