#!/usr/bin/env python3
"""
Test the fixed LLM client structured output support
"""

import sys
import os

# Add the twitterexplorer directory to path
sys.path.insert(0, 'twitterexplorer')

from llm_client import get_litellm_client
from pydantic import BaseModel
from typing import List

class TestFinding(BaseModel):
    is_significant: bool
    relevance_score: float
    reasoning: str
    key_points: List[str]

def test_fixed_llm_client():
    """Test the fixed LLM client with structured outputs"""
    print("Testing Fixed LLM Client with Structured Output")
    print("="*50)
    
    try:
        # Get the LiteLLM client
        client = get_litellm_client()
        print("[OK] LiteLLM client initialized")
        
        # Test structured output with the TestFinding model
        response = client.completion(
            model="gpt-5-mini",
            messages=[
                {"role": "system", "content": "You are an expert investigation analyst."},
                {"role": "user", "content": "Assess this finding: 'Trump mentioned Venezuela in social media post'. Is it significant for investigating military deployment claims?"}
            ],
            response_format=TestFinding
        )
        
        print(f"[OK] Response received")
        print(f"   Response type: {type(response)}")
        print(f"   Has choices: {hasattr(response, 'choices')}")
        
        if hasattr(response, 'choices') and response.choices:
            message = response.choices[0].message
            print(f"   Message content length: {len(message.content) if message.content else 0}")
            print(f"   Has parsed attribute: {hasattr(message, 'parsed')}")
            
            if hasattr(message, 'parsed') and message.parsed:
                parsed = message.parsed
                print(f"[SUCCESS] Structured output parsed correctly!")
                print(f"   Parsed type: {type(parsed)}")
                print(f"   Is significant: {parsed.is_significant}")
                print(f"   Relevance score: {parsed.relevance_score}")
                print(f"   Reasoning length: {len(parsed.reasoning)} chars")
                print(f"   Key points: {len(parsed.key_points)} items")
                return True
            else:
                print(f"[ERROR] No parsed attribute or None")
                print(f"   Raw content: {message.content[:200] if message.content else 'None'}")
                return False
        else:
            print(f"[ERROR] No response choices")
            return False
            
    except Exception as e:
        print(f"[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_fixed_llm_client()
    print(f"\nTest Result: {'PASSED' if success else 'FAILED'}")