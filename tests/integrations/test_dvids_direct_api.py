#!/usr/bin/env python3
"""
DVIDS Direct API Test - Test exact URLs that failed

Bypasses all our code and LLM generation.
Tests the EXACT URL that returned 403 to see if it's really content filtering.
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

print("=" * 80)
print("DVIDS DIRECT API TEST - Test exact failed URLs")
print("=" * 80)
print()

# Test 1: The exact URL that failed 5/5 times
print("TEST 1: Exact URL from failed retry test")
print("Keywords: JSOC, Delta Force, DEVGRU, SEAL Team 6")
print()

test_url_1 = f"https://api.dvidshub.net/search?api_key={api_key}&page=1&max_results=5&type[]=image&type[]=video&type[]=news&branch=Joint&country=United+States&q=JSOC+OR+%22Joint+Special+Operations+Command%22+OR+%22special+operations%22+OR+%22special+operations+forces%22+OR+SOF+OR+counterterrorism+OR+%22direct+action%22+OR+%22special+mission+unit%22+OR+%22Delta+Force%22+OR+DEVGRU+OR+%22SEAL+Team+6%22+OR+mission+OR+role"

print(f"URL: {test_url_1[:100]}...")
start = time.time()
response = requests.get(test_url_1, timeout=10)
elapsed = time.time() - start

print(f"Status: {response.status_code}")
print(f"Time: {elapsed:.2f}s")
if response.status_code == 200:
    data = response.json()
    print(f"Results: {data.get('results_total', 0)} total")
    print("✅ SUCCESS - Content filtering hypothesis WRONG")
else:
    print(f"Error: {response.text[:200]}")
    print("❌ FAILED - Supports content filtering hypothesis")
print()

# Test 2: Simple generic query (should work)
print("TEST 2: Simple generic query")
print("Keywords: military training")
print()

test_url_2 = f"https://api.dvidshub.net/search?api_key={api_key}&page=1&max_results=5&q=military+training"

print(f"URL: {test_url_2}")
start = time.time()
response = requests.get(test_url_2, timeout=10)
elapsed = time.time() - start

print(f"Status: {response.status_code}")
print(f"Time: {elapsed:.2f}s")
if response.status_code == 200:
    data = response.json()
    print(f"Results: {data.get('results_total', 0)} total")
    print("✅ SUCCESS")
else:
    print(f"Error: {response.text[:200]}")
    print("❌ FAILED")
print()

# Test 3: Just "JSOC" alone
print("TEST 3: Just JSOC keyword alone")
print()

test_url_3 = f"https://api.dvidshub.net/search?api_key={api_key}&page=1&max_results=5&q=JSOC"

print(f"URL: {test_url_3}")
start = time.time()
response = requests.get(test_url_3, timeout=10)
elapsed = time.time() - start

print(f"Status: {response.status_code}")
print(f"Time: {elapsed:.2f}s")
if response.status_code == 200:
    data = response.json()
    print(f"Results: {data.get('results_total', 0)} total")
    print("✅ SUCCESS - JSOC alone works")
else:
    print(f"Error: {response.text[:200]}")
    print("❌ FAILED - JSOC alone fails")
print()

# Test 4: Just "Delta Force" alone
print("TEST 4: Just 'Delta Force' keyword")
print()

test_url_4 = f"https://api.dvidshub.net/search?api_key={api_key}&page=1&max_results=5&q=Delta+Force"

print(f"URL: {test_url_4}")
start = time.time()
response = requests.get(test_url_4, timeout=10)
elapsed = time.time() - start

print(f"Status: {response.status_code}")
print(f"Time: {elapsed:.2f}s")
if response.status_code == 200:
    data = response.json()
    print(f"Results: {data.get('results_total', 0)} total")
    print("✅ SUCCESS - Delta Force alone works")
else:
    print(f"Error: {response.text[:200]}")
    print("❌ FAILED - Delta Force alone fails")
print()

# Test 5: Multiple terms with OR (maybe it's the OR operator?)
print("TEST 5: Simple terms with OR operator")
print("Keywords: Army OR Navy OR Marines")
print()

test_url_5 = f"https://api.dvidshub.net/search?api_key={api_key}&page=1&max_results=5&q=Army+OR+Navy+OR+Marines"

print(f"URL: {test_url_5}")
start = time.time()
response = requests.get(test_url_5, timeout=10)
elapsed = time.time() - start

print(f"Status: {response.status_code}")
print(f"Time: {elapsed:.2f}s")
if response.status_code == 200:
    data = response.json()
    print(f"Results: {data.get('results_total', 0)} total")
    print("✅ SUCCESS - OR operator works")
else:
    print(f"Error: {response.text[:200]}")
    print("❌ FAILED - OR operator fails")
print()

print("=" * 80)
print("SUMMARY")
print("=" * 80)
print()
print("If Test 1 PASSES → Content filtering hypothesis WRONG")
print("If Test 1 FAILS but Tests 3/4 PASS → It's the combination/OR query")
print("If Tests 3/4 FAIL → It IS content filtering on specific keywords")
print("If Test 5 FAILS → It's the OR operator itself")
