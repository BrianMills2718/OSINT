#!/usr/bin/env python3
"""
DVIDS Final Isolation - Test the 3 remaining hypotheses

We know:
- All params individually work
- 12 OR terms with dummy keywords work (187 chars)
- Exact failing query fails (341 chars)

Differences between working and failing:
1. Quoted phrases ("Joint Special Operations Command")
2. URL length (341 vs 187 chars)
3. Specific keywords (JSOC, Delta Force, etc)

Test each hypothesis independently.
"""

import requests
import os
from dotenv import load_dotenv
import time

load_dotenv()

api_key = os.getenv("DVIDS_API_KEY")
BASE_URL = "https://api.dvidshub.net/search"

def test_query(description, q_value):
    """Test a query and return detailed results."""
    print(f"\nTEST: {description}")
    print(f"Query: {q_value[:100]}{'...' if len(q_value) > 100 else ''}")

    params = {"api_key": api_key, "q": q_value, "page": "1", "max_results": "5"}

    start = time.time()
    response = requests.get(BASE_URL, params=params, timeout=10)
    elapsed = time.time() - start

    url_length = len(response.url)
    print(f"Status: {response.status_code} ({elapsed:.2f}s)")
    print(f"URL length: {url_length} chars")

    if response.status_code == 200:
        print("✅ PASS")
        return True, url_length
    else:
        print("❌ FAIL")
        return False, url_length

print("=" * 80)
print("DVIDS FINAL ISOLATION TEST")
print("=" * 80)

results = {}

# HYPOTHESIS 1: URL Length
print("\n" + "=" * 80)
print("HYPOTHESIS 1: URL Length Limit")
print("=" * 80)
print("Test if URLs >340 chars trigger 403")

# Test 1.1: Long URL with dummy terms (match failing query length)
long_dummy = " OR ".join([f"dummyterm{i}" for i in range(25)])
success, length = test_query(
    "1.1: Long URL with 25 dummy terms (~340 chars)",
    long_dummy
)
results['long_dummy'] = (success, length)

# Test 1.2: Very long URL (>400 chars)
very_long_dummy = " OR ".join([f"verylongdummyterm{i}" for i in range(30)])
success, length = test_query(
    "1.2: Very long URL with 30 terms (>400 chars)",
    very_long_dummy
)
results['very_long_dummy'] = (success, length)

# HYPOTHESIS 2: Quoted Phrases
print("\n" + "=" * 80)
print("HYPOTHESIS 2: Quoted Phrases")
print("=" * 80)
print("Test if quoted phrases trigger 403")

# Test 2.1: Simple quoted phrases (non-sensitive)
success, length = test_query(
    "2.1: Quoted phrases with innocent terms",
    '"military training" OR "naval exercises" OR "air force operations"'
)
results['quoted_innocent'] = (success, length)

# Test 2.2: Many quoted phrases
success, length = test_query(
    "2.2: Multiple quoted phrases",
    '"term one" OR "term two" OR "term three" OR "term four" OR "term five" OR "term six"'
)
results['quoted_multiple'] = (success, length)

# Test 2.3: Exact number of quoted phrases from failing query (7 quoted phrases)
success, length = test_query(
    "2.3: 7 quoted phrases (same count as failing query)",
    '"dummy one" OR "dummy two" OR "dummy three" OR "dummy four" OR "dummy five" OR "dummy six" OR "dummy seven" OR plain1 OR plain2 OR plain3 OR plain4 OR plain5'
)
results['quoted_seven'] = (success, length)

# HYPOTHESIS 3: Specific Keywords
print("\n" + "=" * 80)
print("HYPOTHESIS 3: Specific Keywords (Content)")
print("=" * 80)
print("Test if specific military terms trigger 403")

# Test 3.1: Exact keywords but fewer of them
success, length = test_query(
    "3.1: Just sensitive keywords (JSOC, Delta Force, DEVGRU)",
    'JSOC OR "Delta Force" OR DEVGRU'
)
results['keywords_few'] = (success, length)

# Test 3.2: All 12 keywords from failing query but shorter phrases
success, length = test_query(
    "3.2: All failing keywords in short form",
    'JSOC OR SOF OR counterterrorism OR "Delta Force" OR DEVGRU OR "SEAL Team 6"'
)
results['keywords_short'] = (success, length)

# Test 3.3: Exact failing keywords with quoted phrases
success, length = test_query(
    "3.3: Exact failing keywords (6 quoted phrases)",
    'JSOC OR "Joint Special Operations Command" OR "special operations" OR "special operations forces" OR SOF OR counterterrorism'
)
results['keywords_exact_half'] = (success, length)

# Test 3.4: Add one more quoted phrase
success, length = test_query(
    "3.4: Add 'direct action' (7th quoted phrase)",
    'JSOC OR "Joint Special Operations Command" OR "special operations" OR "special operations forces" OR SOF OR counterterrorism OR "direct action"'
)
results['keywords_seven_quoted'] = (success, length)

# Test 3.5: Add more terms to approach failing query
success, length = test_query(
    "3.5: Add more terms (8 quoted phrases)",
    'JSOC OR "Joint Special Operations Command" OR "special operations" OR "special operations forces" OR SOF OR counterterrorism OR "direct action" OR "special mission unit"'
)
results['keywords_eight_quoted'] = (success, length)

# Test 3.6: Almost complete failing query (10 quoted/12 total terms)
success, length = test_query(
    "3.6: Almost complete (10 of 12 terms)",
    'JSOC OR "Joint Special Operations Command" OR "special operations" OR "special operations forces" OR SOF OR counterterrorism OR "direct action" OR "special mission unit" OR "Delta Force" OR DEVGRU'
)
results['keywords_ten'] = (success, length)

# Test 3.7: Add SEAL Team 6 (11th term)
success, length = test_query(
    "3.7: Add SEAL Team 6 (11 of 12 terms)",
    'JSOC OR "Joint Special Operations Command" OR "special operations" OR "special operations forces" OR SOF OR counterterrorism OR "direct action" OR "special mission unit" OR "Delta Force" OR DEVGRU OR "SEAL Team 6"'
)
results['keywords_eleven'] = (success, length)

# Test 3.8: EXACT failing query
success, length = test_query(
    "3.8: EXACT failing query (all 12 terms)",
    'JSOC OR "Joint Special Operations Command" OR "special operations" OR "special operations forces" OR SOF OR counterterrorism OR "direct action" OR "special mission unit" OR "Delta Force" OR DEVGRU OR "SEAL Team 6" OR mission OR role'
)
results['keywords_exact_full'] = (success, length)

# ANALYSIS
print("\n" + "=" * 80)
print("ANALYSIS")
print("=" * 80)

print("\nHypothesis 1 - URL Length:")
for key in ['long_dummy', 'very_long_dummy']:
    if key in results:
        success, length = results[key]
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"  {status}: {key} ({length} chars)")

print("\nHypothesis 2 - Quoted Phrases:")
for key in ['quoted_innocent', 'quoted_multiple', 'quoted_seven']:
    if key in results:
        success, length = results[key]
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"  {status}: {key} ({length} chars)")

print("\nHypothesis 3 - Specific Keywords (Progressive):")
keyword_tests = [
    'keywords_few', 'keywords_short', 'keywords_exact_half',
    'keywords_seven_quoted', 'keywords_eight_quoted',
    'keywords_ten', 'keywords_eleven', 'keywords_exact_full'
]
for key in keyword_tests:
    if key in results:
        success, length = results[key]
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"  {status}: {key} ({length} chars)")

# Find first failure in keyword progression
print("\n" + "=" * 80)
print("CONCLUSION")
print("=" * 80)
print()

# Check if URL length hypothesis
long_urls_pass = all(results.get(k, (False, 0))[0] for k in ['long_dummy', 'very_long_dummy'])
if long_urls_pass:
    print("❌ URL length is NOT the cause (long URLs with dummy terms work)")
else:
    print("✅ URL length IS the cause (long URLs fail even with dummy terms)")

# Check if quoted phrases hypothesis
quoted_pass = all(results.get(k, (False, 0))[0] for k in ['quoted_innocent', 'quoted_multiple', 'quoted_seven'])
if quoted_pass:
    print("❌ Quoted phrases are NOT the cause (quoted phrases work)")
else:
    print("✅ Quoted phrases ARE the cause (quoted phrases trigger 403)")

# Find exact failure point in keyword progression
first_fail = None
for key in keyword_tests:
    if key in results:
        success, length = results[key]
        if not success:
            first_fail = (key, length)
            break

if first_fail:
    print(f"\n✅ EXACT TRIGGER FOUND: {first_fail[0]}")
    print(f"   URL length: {first_fail[1]} chars")
    print(f"   This is the minimum query that triggers 403")

    # Show what changed from last passing test
    last_pass = None
    for key in keyword_tests:
        if key in results and results[key][0]:
            last_pass = (key, results[key][1])
        elif key == first_fail[0]:
            break

    if last_pass:
        print(f"\n   Last PASS: {last_pass[0]} ({last_pass[1]} chars)")
        print(f"   First FAIL: {first_fail[0]} ({first_fail[1]} chars)")
        print(f"   → Adding the next term/phrase triggered the 403")
else:
    print("\n⚠️ Could not reproduce 403 - all tests passed")

print("\n" + "=" * 80)
