#!/usr/bin/env python3
"""
Test if specific keywords trigger 403, regardless of quotes
"""

import requests
import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("DVIDS_API_KEY")
BASE_URL = "https://api.dvidshub.net/search"

print("=" * 80)
print("DVIDS KEYWORD CONTENT TEST")
print("=" * 80)
print()

tests = [
    # Non-military terms
    ("Innocent: hello", "hello"),
    ("Innocent: training", "training"),
    ("Innocent: military", "military"),
    ("Innocent: operations", "operations"),

    # Military terms individually
    ("Military: JSOC", "JSOC"),
    ("Military: Delta Force (no quotes)", "Delta Force"),
    ("Military: Delta Force (quoted)", '"Delta Force"'),
    ("Military: DEVGRU", "DEVGRU"),
    ("Military: SEAL Team 6", "SEAL Team 6"),
    ("Military: special operations", "special operations"),

    # Combinations
    ("Combo: military OR training", "military OR training"),
    ("Combo: JSOC OR training", "JSOC OR training"),
    ("Combo: JSOC OR Delta", "JSOC OR Delta"),
]

for description, query in tests:
    print(f"\nQuery: {query}")

    params = {
        "api_key": api_key,
        "q": query,
        "page": "1",
        "max_results": "5"
    }

    response = requests.get(BASE_URL, params=params, timeout=10)

    if response.status_code == 200:
        data = response.json()
        total = data.get('results_total', 0)
        print(f"  ✅ 200 - {total} results")
    else:
        print(f"  ❌ {response.status_code}")

print("\n" + "=" * 80)
