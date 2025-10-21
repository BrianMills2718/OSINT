"""Test suite to identify what schemas work with Gemini API"""

import os
import pytest
from pydantic import BaseModel, Field
from typing import Dict, List, Any, Optional
from litellm import completion
import json

# Load API key
import toml
secrets_path = r'C:\Users\Brian\projects\twitterexplorer\twitterexplorer\.streamlit\secrets.toml'
try:
    secrets = toml.load(secrets_path)
    os.environ['GEMINI_API_KEY'] = secrets.get('GEMINI_API_KEY', '')
except:
    pass

def test_simple_schema():
    """Test that Gemini accepts simple schemas"""
    class SimpleOutput(BaseModel):
        text: str
        score: float
    
    try:
        response = completion(
            model="gemini/gemini-2.0-flash-exp",
            messages=[{"role": "user", "content": "Generate a simple test response with text='hello' and score=0.5"}],
            response_format=SimpleOutput  # Test if this works
        )
        print(f"[PASS] Simple schema works: {response.choices[0].message.content}")
        return True
    except Exception as e:
        print(f"[FAIL] Simple schema failed: {e}")
        return False

def test_nested_dict_any_schema():
    """Test the problematic Dict[str, Any] case"""
    class ProblematicOutput(BaseModel):
        params: Dict[str, Any]  # This causes the error
    
    try:
        response = completion(
            model="gemini/gemini-2.0-flash-exp",
            messages=[{"role": "user", "content": "Generate test params"}],
            response_format=ProblematicOutput
        )
        print(f"[PASS] Dict[str, Any] works: {response.choices[0].message.content}")
        return True
    except Exception as e:
        print(f"[FAIL] Dict[str, Any] failed (expected): {e}")
        return False

def test_dict_str_str_schema():
    """Test Dict[str, str] as alternative"""
    class FixedOutput(BaseModel):
        params: Dict[str, str] = Field(
            default_factory=dict,
            description="String key-value pairs only"
        )
    
    try:
        response = completion(
            model="gemini/gemini-2.0-flash-exp",
            messages=[{"role": "user", "content": "Generate test params with string values"}],
            response_format=FixedOutput
        )
        print(f"[PASS] Dict[str, str] works: {response.choices[0].message.content}")
        return True
    except Exception as e:
        print(f"[FAIL] Dict[str, str] failed: {e}")
        return False

def test_flattened_schema():
    """Test flattened structure avoiding nested dicts"""
    class FlatOutput(BaseModel):
        endpoint: str
        query_param: str = ""
        filter_param: str = ""
        expected_value: str
    
    try:
        response = completion(
            model="gemini/gemini-2.0-flash-exp",
            messages=[{"role": "user", "content": "Generate test endpoint plan with endpoint='search.php' and query_param='test'"}],
            response_format=FlatOutput
        )
        print(f"[PASS] Flattened schema works: {response.choices[0].message.content}")
        return True
    except Exception as e:
        print(f"[FAIL] Flattened schema failed: {e}")
        return False

def test_json_mode_fallback():
    """Test JSON mode as fallback"""
    class AnyOutput(BaseModel):
        params: Dict[str, Any]
    
    try:
        response = completion(
            model="gemini/gemini-2.0-flash-exp",
            messages=[{"role": "user", "content": "Generate test params. Return JSON: {\"params\": {\"key\": \"value\"}}"}],
            response_format={"type": "json_object"}
        )
        content = response.choices[0].message.content
        data = json.loads(content) if isinstance(content, str) else content
        print(f"[PASS] JSON mode works: {data}")
        return True
    except Exception as e:
        print(f"[FAIL] JSON mode failed: {e}")
        return False

def test_complex_nested_schema():
    """Test our actual StrategyOutput schema"""
    from v2.models import StrategyOutput, EndpointPlan, EvaluationCriteria
    
    try:
        response = completion(
            model="gemini/gemini-2.0-flash-exp",
            messages=[{"role": "user", "content": "Generate a strategy with one endpoint"}],
            response_format=StrategyOutput
        )
        print(f"[PASS] StrategyOutput schema works: {response.choices[0].message.content}")
        return True
    except Exception as e:
        print(f"[FAIL] StrategyOutput schema failed: {e}")
        return False

def run_all_tests():
    """Run all schema tests and report results"""
    print("=" * 60)
    print("GEMINI SCHEMA COMPATIBILITY TESTS")
    print("=" * 60)
    
    results = {
        "Simple Schema": test_simple_schema(),
        "Dict[str, Any]": test_nested_dict_any_schema(),
        "Dict[str, str]": test_dict_str_str_schema(),
        "Flattened Schema": test_flattened_schema(),
        "JSON Mode": test_json_mode_fallback(),
        "Complex Nested": test_complex_nested_schema()
    }
    
    print("\n" + "=" * 60)
    print("RESULTS SUMMARY:")
    print("=" * 60)
    for test_name, passed in results.items():
        status = "[PASS]" if passed else "[FAIL]"
        print(f"{test_name:20} {status}")
    
    print("\n" + "=" * 60)
    print("RECOMMENDATION:")
    if results["Dict[str, str]"]:
        print("-> Use Dict[str, str] instead of Dict[str, Any]")
    elif results["Flattened Schema"]:
        print("-> Use flattened schemas to avoid nested dicts")
    else:
        print("-> Fall back to JSON mode with proper parsing")
    print("=" * 60)
    
    return results

if __name__ == "__main__":
    run_all_tests()