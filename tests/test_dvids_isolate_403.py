#!/usr/bin/env python3
"""
DVIDS 403 Isolation Test - Systematically isolate the exact cause

NO SPECULATION. Test one variable at a time.

What we know:
- Full query with all params: 403
- Simple "q=JSOC": 200
- Simple "q=Delta+Force": 200
- Simple "q=Army+OR+Navy+OR+Marines": 200

What we don't know:
- Which parameter(s) cause the 403?
- Is it URL length?
- Is it specific parameter combinations?
- Is it number of OR clauses?

Tests:
1. Add parameters ONE AT A TIME to find which triggers 403
2. Test different OR clause counts (1, 3, 5, 10, 12)
3. Test URL length by adding dummy parameters
4. Test each parameter individually with simple query
"""

import requests
import os
from dotenv import load_dotenv
import time

load_dotenv()

api_key = os.getenv("DVIDS_API_KEY")

if not api_key:
    print("❌ DVIDS_API_KEY not found")
    exit(1)

BASE_URL = "https://api.dvidshub.net/search"

def test_url(description, params):
    """Test a URL and return result."""
    print(f"\nTEST: {description}")

    # Build full params dict
    full_params = {"api_key": api_key, **params}

    # Show what we're testing
    print(f"Parameters: {params}")

    start = time.time()
    response = requests.get(BASE_URL, params=full_params, timeout=10)
    elapsed = time.time() - start

    # Build actual URL for display
    url = response.url

    print(f"Status: {response.status_code} ({elapsed:.2f}s)")
    print(f"URL length: {len(url)} chars")

    if response.status_code == 200:
        try:
            data = response.json()
            total = data.get('results_total', 0)
            print(f"✅ SUCCESS - {total} results")
            return True, total, url
        except:
            print(f"✅ SUCCESS - but couldn't parse JSON")
            return True, 0, url
    else:
        print(f"❌ FAILED - HTTP {response.status_code}")
        return False, None, url

print("=" * 80)
print("DVIDS 403 ISOLATION TEST")
print("=" * 80)
print("\nBaseline: We know simple queries work")
print()

# BASELINE TEST
print("=" * 80)
print("BASELINE: Confirm simple query works")
print("=" * 80)

baseline_success, _, baseline_url = test_url(
    "Simple query: q=JSOC",
    {"q": "JSOC", "page": "1", "max_results": "5"}
)

if not baseline_success:
    print("\n❌ BASELINE FAILED - Cannot proceed")
    exit(1)

# TEST SET 1: Add parameters ONE AT A TIME
print("\n" + "=" * 80)
print("TEST SET 1: Add Parameters One at a Time")
print("=" * 80)
print("Start with q=JSOC, add one parameter at a time to find trigger")

results_set1 = []

# Test 1.1: Just q parameter (baseline)
success, total, url = test_url(
    "1.1: Just q=JSOC",
    {"q": "JSOC"}
)
results_set1.append(("Just q", success))

# Test 1.2: Add page
success, total, url = test_url(
    "1.2: Add page parameter",
    {"q": "JSOC", "page": "1"}
)
results_set1.append(("+ page", success))

# Test 1.3: Add max_results
success, total, url = test_url(
    "1.3: Add max_results",
    {"q": "JSOC", "page": "1", "max_results": "5"}
)
results_set1.append(("+ max_results", success))

# Test 1.4: Add type[]=image
success, total, url = test_url(
    "1.4: Add type[]=image",
    {"q": "JSOC", "page": "1", "max_results": "5", "type[]": "image"}
)
results_set1.append(("+ type[]=image", success))

# Test 1.5: Add multiple type[] (this uses requests' list handling)
success, total, url = test_url(
    "1.5: Add type[]=image,video,news",
    {"q": "JSOC", "page": "1", "max_results": "5", "type[]": ["image", "video", "news"]}
)
results_set1.append(("+ type[]=[image,video,news]", success))

# Test 1.6: Add branch=Joint
success, total, url = test_url(
    "1.6: Add branch=Joint",
    {"q": "JSOC", "page": "1", "max_results": "5", "type[]": ["image", "video", "news"], "branch": "Joint"}
)
results_set1.append(("+ branch=Joint", success))

# Test 1.7: Add country
success, total, url = test_url(
    "1.7: Add country=United States",
    {"q": "JSOC", "page": "1", "max_results": "5", "type[]": ["image", "video", "news"], "branch": "Joint", "country": "United States"}
)
results_set1.append(("+ country", success))

# TEST SET 2: Number of OR clauses
print("\n" + "=" * 80)
print("TEST SET 2: Test Different Numbers of OR Clauses")
print("=" * 80)
print("Test if 403 is triggered by too many OR terms")

results_set2 = []

# Test 2.1: 2 OR terms
success, total, url = test_url(
    "2.1: 2 OR terms",
    {"q": "JSOC OR Delta", "page": "1", "max_results": "5"}
)
results_set2.append(("2 OR terms", success, url))

# Test 2.2: 5 OR terms
success, total, url = test_url(
    "2.2: 5 OR terms",
    {"q": "JSOC OR Delta OR DEVGRU OR SEAL OR SOF", "page": "1", "max_results": "5"}
)
results_set2.append(("5 OR terms", success, url))

# Test 2.3: 10 OR terms
ten_terms = " OR ".join([f"term{i}" for i in range(10)])
success, total, url = test_url(
    "2.3: 10 OR terms",
    {"q": ten_terms, "page": "1", "max_results": "5"}
)
results_set2.append(("10 OR terms", success, url))

# Test 2.4: 12 OR terms (same as failing query)
twelve_terms = " OR ".join([f"term{i}" for i in range(12)])
success, total, url = test_url(
    "2.4: 12 OR terms",
    {"q": twelve_terms, "page": "1", "max_results": "5"}
)
results_set2.append(("12 OR terms", success, url))

# TEST SET 3: Full failing query recreated step-by-step
print("\n" + "=" * 80)
print("TEST SET 3: Recreate Failing Query Step by Step")
print("=" * 80)
print("Build up to exact failing query, parameter by parameter")

results_set3 = []

# The actual failing q parameter from the retry test
failing_q = 'JSOC OR "Joint Special Operations Command" OR "special operations" OR "special operations forces" OR SOF OR counterterrorism OR "direct action" OR "special mission unit" OR "Delta Force" OR DEVGRU OR "SEAL Team 6" OR mission OR role'

# Test 3.1: Failing q value with minimal params
success, total, url = test_url(
    "3.1: Exact failing q value, minimal params",
    {"q": failing_q, "page": "1", "max_results": "5"}
)
results_set3.append(("Failing q + minimal params", success, url))

# Test 3.2: Add type[] params
success, total, url = test_url(
    "3.2: Failing q + type[] params",
    {"q": failing_q, "page": "1", "max_results": "5", "type[]": ["image", "video", "news"]}
)
results_set3.append(("+ type[]", success, url))

# Test 3.3: Add branch
success, total, url = test_url(
    "3.3: Failing q + type[] + branch",
    {"q": failing_q, "page": "1", "max_results": "5", "type[]": ["image", "video", "news"], "branch": "Joint"}
)
results_set3.append(("+ branch", success, url))

# Test 3.4: Add country (full failing query)
success, total, url = test_url(
    "3.4: Full failing query (all params)",
    {"q": failing_q, "page": "1", "max_results": "5", "type[]": ["image", "video", "news"], "branch": "Joint", "country": "United States"}
)
results_set3.append(("+ country (FULL)", success, url))

# ANALYSIS
print("\n" + "=" * 80)
print("ANALYSIS")
print("=" * 80)

print("\nSet 1 - Parameter Addition Results:")
for desc, success in results_set1:
    status = "✅ PASS" if success else "❌ FAIL"
    print(f"  {status}: {desc}")

print("\nSet 2 - OR Clause Count Results:")
for desc, success, url in results_set2:
    status = "✅ PASS" if success else "❌ FAIL"
    print(f"  {status}: {desc} (URL: {len(url)} chars)")

print("\nSet 3 - Failing Query Recreation Results:")
for desc, success, url in results_set3:
    status = "✅ PASS" if success else "❌ FAIL"
    print(f"  {status}: {desc} (URL: {len(url)} chars)")

# Determine exact trigger
print("\n" + "=" * 80)
print("CONCLUSIONS")
print("=" * 80)
print()

# Find where Set 1 first fails
first_fail_set1 = None
for i, (desc, success) in enumerate(results_set1):
    if not success:
        first_fail_set1 = desc
        break

if first_fail_set1:
    print(f"Set 1: First failure at: {first_fail_set1}")
    print(f"       → Adding this parameter triggers 403")
else:
    print("Set 1: All parameters passed individually")

# Find where Set 2 first fails
first_fail_set2 = None
for desc, success, url in results_set2:
    if not success:
        first_fail_set2 = (desc, len(url))
        break

if first_fail_set2:
    print(f"\nSet 2: First failure at: {first_fail_set2[0]} ({first_fail_set2[1]} char URL)")
    print(f"       → This many OR clauses triggers 403")
else:
    print("\nSet 2: All OR clause counts passed")

# Find where Set 3 first fails
first_fail_set3 = None
for desc, success, url in results_set3:
    if not success:
        first_fail_set3 = (desc, len(url))
        break

if first_fail_set3:
    print(f"\nSet 3: First failure at: {first_fail_set3[0]} ({first_fail_set3[1]} char URL)")
    print(f"       → This is the exact trigger point")
else:
    print("\nSet 3: All steps passed (403 not reproduced)")

print("\n" + "=" * 80)
print("EVIDENCE-BASED CONCLUSION")
print("=" * 80)
print()
print("Based on which test first failed, we can definitively state:")
print("(See results above)")
