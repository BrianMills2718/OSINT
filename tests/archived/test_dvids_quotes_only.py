#!/usr/bin/env python3
"""
DVIDS Quoted Phrase Test - Verify if quotes are really the issue

Simple test: Try queries with and without quotes to confirm hypothesis.
"""

import requests
import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("DVIDS_API_KEY")
BASE_URL = "https://api.dvidshub.net/search"

print("=" * 80)
print("DVIDS QUOTED PHRASE VERIFICATION")
print("=" * 80)
print()

tests = [
    # Test 1: Single word, no quotes
    ("Test 1: Single word 'hello' (no quotes)", "hello"),

    # Test 2: Single word WITH quotes
    ("Test 2: Single word '\"hello\"' (WITH quotes)", '"hello"'),

    # Test 3: Two words, no quotes
    ("Test 3: Two words 'hello world' (no quotes)", "hello world"),

    # Test 4: Two words WITH quotes (phrase)
    ("Test 4: Phrase '\"hello world\"' (WITH quotes)", '"hello world"'),

    # Test 5: Two separate words with OR, no quotes
    ("Test 5: 'hello OR world' (no quotes)", "hello OR world"),

    # Test 6: Two quoted phrases with OR
    ("Test 6: '\"hello world\" OR \"foo bar\"' (WITH quotes)", '"hello world" OR "foo bar"'),

    # Test 7: Mix of quoted and unquoted
    ("Test 7: 'hello OR \"world test\"' (mixed)", 'hello OR "world test"'),
]

for description, query in tests:
    print(f"\n{description}")
    print(f"Query: {query}")

    params = {
        "api_key": api_key,
        "q": query,
        "page": "1",
        "max_results": "5"
    }

    try:
        response = requests.get(BASE_URL, params=params, timeout=10)

        if response.status_code == 200:
            print(f"✅ PASS - Status 200")
        else:
            print(f"❌ FAIL - Status {response.status_code}")

    except Exception as e:
        print(f"❌ ERROR - {str(e)}")

print("\n" + "=" * 80)
print("CONCLUSION")
print("=" * 80)
print()
print("If tests with quotes fail and without quotes pass:")
print("  → Quoted phrases are the cause")
print()
print("If both pass:")
print("  → Quoted phrases are NOT the cause (something else is wrong)")
print()
print("If both fail:")
print("  → API might be down or other issue")
