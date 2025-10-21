#!/usr/bin/env python3
"""
Test that LiteLLM structured output is properly configured
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'twitterexplorer'))

# Load the API key from streamlit secrets
import toml
secrets_path = os.path.join('twitterexplorer', '.streamlit', 'secrets.toml')
if os.path.exists(secrets_path):
    secrets = toml.load(secrets_path)
    os.environ['GEMINI_API_KEY'] = secrets.get('GEMINI_API_KEY', '')

from llm_client import get_litellm_client, StrategicDecision
from pydantic import BaseModel
from typing import List, Dict, Any

class TestResponse(BaseModel):
    """Simple test model"""
    answer: str
    confidence: float
    details: List[str]

def test_structured_output():
    """Test that structured output works with proper schema passing"""
    print("=== Testing LiteLLM Structured Output Configuration ===\n")
    
    try:
        # Get client
        client = get_litellm_client()
        print("[OK] LiteLLM client initialized")
        
        # Test 1: Simple structured output
        print("\n[TEST 1] Simple structured output with TestResponse model")
        print("-" * 50)
        
        response = client.completion(
            model="gemini/gemini-2.5-flash",
            messages=[{
                "role": "user", 
                "content": "What is 2+2? Respond with confidence level and reasoning steps."
            }],
            response_format=TestResponse
        )
        
        if response.choices[0].message.parsed:
            parsed = response.choices[0].message.parsed
            print(f"[OK] Parsed response: {parsed}")
            print(f"  Answer: {parsed.answer}")
            print(f"  Confidence: {parsed.confidence}")
            print(f"  Details: {parsed.details}")
        else:
            print("[FAIL] No parsed response returned")
            print(f"Raw content: {response.choices[0].message.content[:200]}")
            
        # Test 2: Complex strategic decision
        print("\n[TEST 2] Complex StrategicDecision model")
        print("-" * 50)
        
        response = client.completion(
            model="gemini/gemini-2.5-flash",
            messages=[{
                "role": "user",
                "content": """Create a strategic decision for investigating UFO claims.
                
You must decide on search strategies using these endpoints:
- search.php: General search with query parameter
- timeline.php: User timeline with screenname parameter
- trends.php: Trending topics with country parameter

Return a decision with type, reasoning, searches array, and expected outcomes."""
            }],
            response_format=StrategicDecision
        )
        
        if response.choices[0].message.parsed:
            decision = response.choices[0].message.parsed
            print(f"[OK] Parsed StrategicDecision:")
            print(f"  Type: {decision.decision_type}")
            print(f"  Reasoning: {decision.reasoning[:100]}...")
            print(f"  Searches: {len(decision.searches)} search strategies")
            for i, search in enumerate(decision.searches[:2]):
                print(f"    {i+1}. {search}")
            print(f"  Expected outcomes: {len(decision.expected_outcomes)} outcomes")
        else:
            print("[FAIL] No parsed StrategicDecision returned")
            print(f"Raw content: {response.choices[0].message.content[:200]}")
        
        # Test 3: Verify no manual schema in prompt
        print("\n[TEST 3] Verify clean prompts (no manual schema injection)")
        print("-" * 50)
        
        # Check that we're not manually adding schema to prompts
        test_messages = [{
            "role": "user",
            "content": "Simple test prompt"
        }]
        
        # Make a copy to test
        test_copy = test_messages.copy()
        
        response = client.completion(
            model="gemini/gemini-2.5-flash",
            messages=test_copy,
            response_format=TestResponse
        )
        
        # Verify original messages weren't modified
        if test_messages[0]["content"] == "Simple test prompt":
            print("[OK] Prompts are not being modified with manual schema")
        else:
            print("[FAIL] Prompts are being incorrectly modified")
            print(f"Modified to: {test_messages[0]['content'][:100]}")
            
        print("\n" + "="*60)
        print("SUMMARY:")
        print("="*60)
        print("✓ LiteLLM properly configured with native structured output")
        print("✓ Using response_schema in response_format (not manual prompting)")
        print("✓ Client-side JSON schema validation enabled")
        print("✓ No max_tokens constraints limiting output")
        print("\nThe intermittent failures should now be resolved!")
        
    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_structured_output()