#!/usr/bin/env python3
"""
USAJobs Query Syntax Empirical Testing

Tests various query syntax patterns against USAJobs API to determine:
1. Does USAJobs support Boolean operators (AND, OR, NOT)?
2. Does USAJobs support quoted phrases for exact matching?
3. Does USAJobs support parentheses for grouping?
4. What is the actual behavior with complex vs simple queries?

Purpose: Validate existing LLM prompt guidance ("DO NOT use OR operators").
"""

import os
import sys
import requests
from dotenv import load_dotenv
from datetime import datetime

# Load environment
load_dotenv()

# Get USAJobs API key
api_key = os.getenv("USAJOBS_API_KEY")
if not api_key:
    print("ERROR: USAJOBS_API_KEY not found in .env")
    sys.exit(1)

BASE_URL = "https://data.usajobs.gov/api/search"

print("=" * 80)
print("USAJOBS QUERY SYNTAX EMPIRICAL TESTING")
print("=" * 80)
print(f"Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print()

# Test queries with different syntax patterns
test_queries = [
    # Simple keywords (expected to work well per existing prompt)
    ("Simple keyword", "intelligence"),
    ("Two keywords (space)", "intelligence analyst"),
    ("Three keywords (space)", "intelligence analyst senior"),

    # Boolean operators (expected NOT to work per existing prompt)
    ("Boolean AND", "intelligence AND analyst"),
    ("Boolean OR", "intelligence OR security"),
    ("Boolean NOT", "intelligence NOT classified"),

    # Quoted phrases
    ("Quoted phrase", '"intelligence analyst"'),
    ("Quoted phrase with AND", '"intelligence analyst" AND senior'),

    # Parentheses
    ("Parentheses simple", "(intelligence OR security) AND analyst"),

    # Mixed syntax
    ("Mixed: quotes + OR", '"intelligence analyst" OR cybersecurity'),
    ("Complex Boolean", "intelligence OR security OR analyst OR investigator"),
]

def test_query(description, query_string):
    """Test a single query and return results."""
    params = {
        "Keyword": query_string,
        "ResultsPerPage": 10
    }

    headers = {
        "Host": "data.usajobs.gov",
        "User-Agent": "brianmills2718@gmail.com",
        "Authorization-Key": api_key
    }

    print(f"\nTest: {description}")
    print(f"Query: {query_string}")

    try:
        response = requests.get(BASE_URL, params=params, headers=headers, timeout=10)

        if response.status_code == 200:
            data = response.json()
            search_result = data.get("SearchResult", {})
            total = search_result.get("SearchResultCount", 0)
            items = search_result.get("SearchResultItems", [])

            print(f"✅ PASS | Status: 200 | Results: {total} total, {len(items)} returned")

            # Sample first result title for verification
            if items:
                matched_obj = items[0].get("MatchedObjectDescriptor", {})
                title = matched_obj.get("PositionTitle", "")[:60]
                org = matched_obj.get("OrganizationName", "")[:40]
                print(f"  Sample: {title} at {org}")

            return {
                "description": description,
                "query": query_string,
                "status": "PASS",
                "status_code": 200,
                "total_results": total,
                "returned_results": len(items)
            }

        elif response.status_code == 429:
            print(f"⏱️ RATE LIMIT | Status: 429 | (Too many requests)")
            return {
                "description": description,
                "query": query_string,
                "status": "RATE_LIMIT",
                "status_code": 429,
                "total_results": None,
                "returned_results": None
            }
        else:
            print(f"❌ FAIL | Status: {response.status_code}")
            error_text = response.text[:200] if response.text else "No error details"
            print(f"  Error: {error_text}")
            return {
                "description": description,
                "query": query_string,
                "status": "FAIL",
                "status_code": response.status_code,
                "total_results": None,
                "returned_results": None,
                "error": error_text
            }

    except requests.Timeout:
        print(f"⏱️ TIMEOUT | Request exceeded 10 seconds")
        return {
            "description": description,
            "query": query_string,
            "status": "TIMEOUT",
            "status_code": None,
            "total_results": None,
            "returned_results": None
        }
    except Exception as e:
        print(f"❌ ERROR | {str(e)}")
        return {
            "description": description,
            "query": query_string,
            "status": "ERROR",
            "status_code": None,
            "total_results": None,
            "returned_results": None,
            "error": str(e)
        }

# Run all tests
results = []
for description, query in test_queries:
    result = test_query(description, query)
    results.append(result)

    # Brief delay between requests
    import time
    time.sleep(1)

# Summary
print("\n" + "=" * 80)
print("TEST SUMMARY")
print("=" * 80)
print()

passed = sum(1 for r in results if r["status"] == "PASS")
failed = sum(1 for r in results if r["status"] == "FAIL")
rate_limited = sum(1 for r in results if r["status"] == "RATE_LIMIT")
errors = sum(1 for r in results if r["status"] in ["TIMEOUT", "ERROR"])

print(f"Total Tests: {len(results)}")
print(f"✅ Passed: {passed}")
print(f"❌ Failed: {failed}")
print(f"⏱️ Rate Limited: {rate_limited}")
print(f"❌ Errors/Timeouts: {errors}")
print()

# Syntax conclusions
print("=" * 80)
print("QUERY SYNTAX CONCLUSIONS")
print("=" * 80)
print()

# Categorize results
simple_queries = results[:3]  # First 3 are simple
boolean_queries = results[3:6]  # Next 3 are Boolean operators
other_queries = results[6:]  # Rest are mixed

print("Simple Keywords (EXPECTED TO WORK):")
for r in simple_queries:
    if r["status"] == "PASS":
        print(f"  ✅ {r['description']}: {r['total_results']} results")
    else:
        print(f"  ❌ {r['description']}: {r['status']}")
print()

print("Boolean Operators (EXPECTED NOT TO WORK PER PROMPT):")
for r in boolean_queries:
    if r["status"] == "PASS":
        print(f"  ✅ {r['description']}: {r['total_results']} results - **WORKS** (unexpected?)")
    else:
        print(f"  ❌ {r['description']}: {r['status']}")
print()

print("Other Syntax (Quotes, Parentheses, Mixed):")
for r in other_queries:
    if r["status"] == "PASS":
        print(f"  ✅ {r['description']}: {r['total_results']} results")
    else:
        print(f"  ❌ {r['description']}: {r['status']}")
print()

# Specific validation questions
print("=" * 80)
print("VALIDATION QUESTIONS")
print("=" * 80)
print()

# Question 1: Do Boolean operators work at all?
boolean_passed = sum(1 for r in boolean_queries if r["status"] == "PASS")
if boolean_passed > 0:
    print("Q1: Do Boolean operators work?")
    print(f"   YES - {boolean_passed}/3 Boolean queries succeeded")
    print("   NOTE: Existing prompt says 'DO NOT use OR operators' - may need update")
else:
    print("Q1: Do Boolean operators work?")
    print("   NO - All Boolean queries failed")
    print("   VALIDATES existing prompt guidance")
print()

# Question 2: Are simple queries better than Boolean?
simple_avg = sum(r.get("total_results", 0) for r in simple_queries if r["status"] == "PASS") / max(1, sum(1 for r in simple_queries if r["status"] == "PASS"))
boolean_avg = sum(r.get("total_results", 0) for r in boolean_queries if r["status"] == "PASS") / max(1, sum(1 for r in boolean_queries if r["status"] == "PASS"))

if simple_avg > 0 or boolean_avg > 0:
    print("Q2: Are simple queries better than Boolean?")
    print(f"   Simple queries: {simple_avg:.1f} results average")
    print(f"   Boolean queries: {boolean_avg:.1f} results average")
    if simple_avg > boolean_avg:
        print("   CONCLUSION: Simple queries find more results - VALIDATES prompt guidance")
    else:
        print("   CONCLUSION: Boolean queries comparable or better - PROMPT MAY NEED UPDATE")
else:
    print("Q2: Are simple queries better than Boolean?")
    print("   INSUFFICIENT DATA - too many failures to compare")
print()

print("Output saved for documentation: tests/usajobs_query_syntax_results.txt")
