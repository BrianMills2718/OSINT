#!/usr/bin/env python3
"""
Test Gemini 2.5 Flash (full version, not lite) with structured output via LiteLLM

Testing gemini/gemini-2.5-flash model compatibility with the sam_gov codebase
"""
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))))

from dotenv import load_dotenv
load_dotenv()

import litellm
import json
from typing import Dict, List

# Enable verbose logging to see what's happening
litellm.set_verbose = True

def test_simple_completion():
    """Test 1: Simple text completion (no structured output)"""
    print("="*80)
    print("Test 1: Simple Text Completion")
    print("="*80)

    try:
        response = litellm.completion(
            model="gemini/gemini-2.5-flash",
            messages=[
                {"role": "user", "content": "Say 'Hello from Gemini 2.5 Flash!' and nothing else."}
            ]
        )

        print("✓ Response received:")
        print(f"  Content: {response.choices[0].message.content}")
        print(f"  Model: {response.model}")
        print(f"  Usage: {response.usage}")
        return True

    except Exception as e:
        print(f"✗ Error: {type(e).__name__}: {str(e)}")
        return False


def test_json_object():
    """Test 2: JSON object output (type: json_object)"""
    print("\n" + "="*80)
    print("Test 2: JSON Object Output")
    print("="*80)

    try:
        response = litellm.completion(
            model="gemini/gemini-2.5-flash",
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful assistant that outputs JSON."
                },
                {
                    "role": "user",
                    "content": "List 3 programming languages with their year created and primary use case. Return as JSON."
                }
            ],
            response_format={"type": "json_object"}
        )

        print("✓ Response received:")
        result = json.loads(response.choices[0].message.content)
        print(json.dumps(result, indent=2))
        return True

    except Exception as e:
        print(f"✗ Error: {type(e).__name__}: {str(e)}")
        return False


def test_json_schema():
    """Test 3: JSON schema structured output (like sam_gov uses)"""
    print("\n" + "="*80)
    print("Test 3: JSON Schema Structured Output (sam_gov pattern)")
    print("="*80)

    # This is the pattern used in sam_gov codebase
    schema = {
        "type": "object",
        "properties": {
            "databases": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "relevant": {"type": "boolean"},
                        "reason": {"type": "string"}
                    },
                    "required": ["name", "relevant", "reason"],
                    "additionalProperties": False
                },
                "minItems": 3,
                "maxItems": 3
            }
        },
        "required": ["databases"],
        "additionalProperties": False
    }

    try:
        response = litellm.completion(
            model="gemini/gemini-2.5-flash",
            messages=[
                {
                    "role": "user",
                    "content": "Evaluate which databases are relevant for finding 'cybersecurity jobs': SAM.gov (contracts), USAJobs (federal jobs), ClearanceJobs (security cleared jobs)"
                }
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "strict": True,
                    "name": "database_relevance",
                    "schema": schema
                }
            }
        )

        print("✓ Response received:")
        result = json.loads(response.choices[0].message.content)
        print(json.dumps(result, indent=2))

        # Validate structure
        assert "databases" in result, "Missing 'databases' field"
        assert len(result["databases"]) == 3, f"Expected 3 databases, got {len(result['databases'])}"

        print("\n✓ Validation passed:")
        for db in result["databases"]:
            print(f"  - {db['name']}: {'relevant' if db['relevant'] else 'not relevant'} ({db['reason']})")

        return True

    except Exception as e:
        print(f"✗ Error: {type(e).__name__}: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return False


def test_query_generation_pattern():
    """Test 4: Query generation pattern (sam_gov integration pattern)"""
    print("\n" + "="*80)
    print("Test 4: Query Generation Pattern (sam_gov integration)")
    print("="*80)

    # This mimics integrations/government/*_integration.py generate_query() pattern
    schema = {
        "type": "object",
        "properties": {
            "keywords": {
                "type": "string",
                "description": "Search keywords for the query"
            },
            "filters": {
                "type": "object",
                "properties": {
                    "location": {"type": "string"},
                    "job_category": {"type": "string"}
                },
                "additionalProperties": False
            },
            "reasoning": {
                "type": "string",
                "description": "Brief explanation of the query strategy"
            }
        },
        "required": ["keywords", "reasoning"],
        "additionalProperties": False
    }

    try:
        response = litellm.completion(
            model="gemini/gemini-2.5-flash",
            messages=[
                {
                    "role": "user",
                    "content": "Generate a USAJobs query for: 'cybersecurity engineer positions in Washington DC'"
                }
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "strict": True,
                    "name": "usajobs_query",
                    "schema": schema
                }
            }
        )

        print("✓ Response received:")
        result = json.loads(response.choices[0].message.content)
        print(json.dumps(result, indent=2))

        # Validate required fields
        assert "keywords" in result, "Missing 'keywords'"
        assert "reasoning" in result, "Missing 'reasoning'"

        print("\n✓ Query generated:")
        print(f"  Keywords: {result['keywords']}")
        print(f"  Reasoning: {result['reasoning']}")
        if "filters" in result:
            print(f"  Filters: {result['filters']}")

        return True

    except Exception as e:
        print(f"✗ Error: {type(e).__name__}: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return False


def main():
    print("\n" + "🔬"*40)
    print("TESTING GEMINI 2.5 FLASH FOR SAM_GOV COMPATIBILITY")
    print("🔬"*40)

    # Check API key
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        print("\n✗ ERROR: GEMINI_API_KEY not found in environment")
        print("  Please set it in .env file")
        return False

    print(f"\n✓ API Key found: {api_key[:10]}...")
    print(f"✓ Testing model: gemini/gemini-2.5-flash\n")

    # Run all tests
    results = {
        "simple_completion": test_simple_completion(),
        "json_object": test_json_object(),
        "json_schema": test_json_schema(),
        "query_generation": test_query_generation_pattern()
    }

    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)

    passed = sum(results.values())
    total = len(results)

    for test_name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status} - {test_name}")

    print(f"\nResults: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All tests passed! Gemini 2.5 Flash is compatible with sam_gov codebase.")
        print("   Ready to use in config_default.yaml")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Review errors above.")

    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
