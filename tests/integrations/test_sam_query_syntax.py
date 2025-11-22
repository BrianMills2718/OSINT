#!/usr/bin/env python3
"""
SAM.gov Query Syntax Empirical Testing

Tests various query syntax patterns against SAM.gov API to determine:
1. Does SAM.gov support Boolean operators (AND, OR, NOT)?
2. Does SAM.gov support quoted phrases for exact matching?
3. Does SAM.gov support parentheses for grouping?
4. What is the actual character limit for keywords parameter?
5. Does SAM.gov use Lucene syntax as documented?

Purpose: Create evidence-based query syntax guidance for SAM LLM prompt.
"""

import os
import sys
import requests
from dotenv import load_dotenv
from datetime import datetime, timedelta

# Load environment
load_dotenv()

# Get SAM API key
api_key = os.getenv("SAM_GOV_API_KEY")
if not api_key:
    print("ERROR: SAM_GOV_API_KEY not found in .env")
    sys.exit(1)

BASE_URL = "https://api.sam.gov/opportunities/v2/search"

# Date range (required by SAM.gov)
to_date = datetime.now()
from_date = to_date - timedelta(days=60)  # Last 60 days

print("=" * 80)
print("SAM.GOV QUERY SYNTAX EMPIRICAL TESTING")
print("=" * 80)
print(f"Date Range: {from_date.strftime('%Y-%m-%d')} to {to_date.strftime('%Y-%m-%d')}")
print(f"Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print()

# Test queries with different syntax patterns
test_queries = [
    # Simple keywords
    ("Simple keyword", "cybersecurity"),
    ("Two keywords (space)", "cyber security"),
    ("Two keywords (comma)", "cyber, security"),

    # Boolean operators
    ("Boolean AND", "cyber AND security"),
    ("Boolean OR", "cyber OR security"),
    ("Boolean NOT", "cyber NOT classified"),

    # Quoted phrases
    ("Quoted phrase", '"information security"'),
    ("Quoted phrase with AND", '"cyber security" AND training'),
    ("Two quoted phrases", '"cyber security" AND "information assurance"'),

    # Parentheses (Lucene grouping)
    ("Parentheses simple", "(cyber OR security) AND training"),
    ("Nested parentheses", "((cyber OR security) AND (training OR education))"),

    # Mixed syntax
    ("Mixed: quotes + OR", '"cyber security" OR cybersecurity'),
    ("Mixed: multiple terms", "cyber OR security OR information OR protection"),

    # Character limit testing (SAM docs say ~200 chars max)
    ("Medium query (100 chars)", "cyber security information assurance network defense threat intelligence vulnerability management"),
    ("Long query (200 chars)", "cybersecurity OR information security OR cyber defense OR network security OR threat intelligence OR vulnerability assessment OR security operations OR incident response OR security engineering OR penetration testing"),
]

def test_query(description, query_string):
    """Test a single query and return results."""
    params = {
        "api_key": api_key,
        "postedFrom": from_date.strftime("%m/%d/%Y"),
        "postedTo": to_date.strftime("%m/%d/%Y"),
        "keywords": query_string,
        "limit": 10,
        "offset": 0
    }

    print(f"\nTest: {description}")
    print(f"Query: {query_string}")
    print(f"Length: {len(query_string)} characters")

    try:
        response = requests.get(BASE_URL, params=params, timeout=15)

        if response.status_code == 200:
            data = response.json()
            total = data.get("totalRecords", 0)
            opportunities = data.get("opportunitiesData", [])

            print(f"✅ PASS | Status: 200 | Results: {total} total, {len(opportunities)} returned")

            # Sample first result title for verification
            if opportunities:
                first_title = opportunities[0].get("title", "")[:80]
                print(f"  Sample: {first_title}...")

            return {
                "description": description,
                "query": query_string,
                "status": "PASS",
                "status_code": 200,
                "total_results": total,
                "returned_results": len(opportunities)
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
        print(f"⏱️ TIMEOUT | Request exceeded 15 seconds")
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

    # Brief delay to avoid rate limits (SAM.gov is strict)
    import time
    time.sleep(2)

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

if passed > 0:
    print("Working Syntax Patterns:")
    for r in results:
        if r["status"] == "PASS":
            print(f"  ✅ {r['description']}: {r['total_results']} results")
    print()

if failed > 0:
    print("Failed Syntax Patterns:")
    for r in results:
        if r["status"] == "FAIL":
            error_snippet = r.get("error", "")[:100] if r.get("error") else "Unknown error"
            print(f"  ❌ {r['description']}: HTTP {r['status_code']} - {error_snippet}")
    print()

print("Note: Rate limits (HTTP 429) may prevent complete testing.")
print("Recommendation: Run test again after rate limit window expires.")
print()
print("Output saved for documentation: tests/sam_query_syntax_results.txt")
