#!/usr/bin/env python3
"""
Test gpt-5-mini structured output compatibility
Tests both native OpenAI client and LiteLLM approaches
"""

import os
import json
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

# Test with native OpenAI client first
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
    print("[OK] Native OpenAI client available")
except ImportError:
    OPENAI_AVAILABLE = False
    print("[ERROR] Native OpenAI client not available")

# Test with LiteLLM
try:
    import litellm
    LITELLM_AVAILABLE = True
    print("[OK] LiteLLM available")
except ImportError:
    LITELLM_AVAILABLE = False
    print("[ERROR] LiteLLM not available")

# Load API key
def get_api_key():
    """Load OpenAI API key from secrets file"""
    secrets_path = "C:\\Users\\Brian\\projects\\twitterexplorer\\twitterexplorer\\.streamlit\\secrets.toml"
    try:
        with open(secrets_path, 'r') as f:
            for line in f:
                if 'OPENAI_API_KEY' in line and '=' in line:
                    key = line.split('=')[1].strip().strip('"\'')
                    return key
    except Exception as e:
        print(f"Failed to load API key: {e}")
    return None

# Define test Pydantic models
class Finding(BaseModel):
    is_significant: bool
    relevance_score: float
    reasoning: str
    key_points: List[str]

class InvestigationDecision(BaseModel):
    decision_type: str
    reasoning: str
    confidence: float
    next_action: str

class EmergentQuestion(BaseModel):
    question_text: str
    priority: float
    emergence_reason: str
    investigation_focus: str

def test_native_openai_structured_output():
    """Test structured outputs with native OpenAI client"""
    print("\n" + "="*60)
    print("TESTING: Native OpenAI Client with gpt-5-mini")
    print("="*60)
    
    if not OPENAI_AVAILABLE:
        print("[ERROR] Skipping - OpenAI client not available")
        return False
    
    api_key = get_api_key()
    if not api_key:
        print("[ERROR] Skipping - No API key available")
        return False
    
    try:
        client = OpenAI(api_key=api_key)
        
        # Test 1: Basic structured output with Finding model
        print("\nTest 1: Basic Finding Assessment")
        print("-" * 30)
        
        response = client.chat.completions.create(
            model="gpt-5-mini",
            messages=[
                {"role": "system", "content": "You are an expert investigation analyst."},
                {"role": "user", "content": "Assess this finding: 'Trump mentioned Venezuela in recent tweet'. Is it significant for investigating military deployment claims?"}
            ],
            response_format=Finding
        )
        
        # Parse response
        if hasattr(response.choices[0].message, 'parsed') and response.choices[0].message.parsed:
            result = response.choices[0].message.parsed
            print(f"[OK] Structured output successful!")
            print(f"   Significant: {result.is_significant}")
            print(f"   Relevance: {result.relevance_score}")
            print(f"   Reasoning: {result.reasoning[:100]}...")
            print(f"   Key Points: {len(result.key_points)} items")
        else:
            print(f"[ERROR] No parsed result. Raw content: {response.choices[0].message.content}")
            return False
        
        # Test 2: Investigation Decision model
        print("\nTest 2: Investigation Decision")
        print("-" * 30)
        
        response = client.chat.completions.create(
            model="gpt-5-mini",
            messages=[
                {"role": "system", "content": "You are a strategic investigation coordinator."},
                {"role": "user", "content": "Current investigation: 'Trump sent military to Venezuela'. Found 312 results but no concrete evidence. What should be the next action?"}
            ],
            response_format=InvestigationDecision
        )
        
        if hasattr(response.choices[0].message, 'parsed') and response.choices[0].message.parsed:
            result = response.choices[0].message.parsed
            print(f"[OK] Structured output successful!")
            print(f"   Decision Type: {result.decision_type}")
            print(f"   Next Action: {result.next_action}")
            print(f"   Confidence: {result.confidence}")
        else:
            print(f"[ERROR] No parsed result. Raw content: {response.choices[0].message.content}")
            return False
        
        # Test 3: Complex nested structure - Emergent Questions
        print("\nTest 3: Emergent Question Generation")
        print("-" * 30)
        
        response = client.chat.completions.create(
            model="gpt-5-mini",
            messages=[
                {"role": "system", "content": "Generate an emergent investigation question based on current findings."},
                {"role": "user", "content": "Investigation into Trump-Venezuela military claims found 312 social media posts but no official confirmations. Generate a strategic follow-up question."}
            ],
            response_format=EmergentQuestion
        )
        
        if hasattr(response.choices[0].message, 'parsed') and response.choices[0].message.parsed:
            result = response.choices[0].message.parsed
            print(f"[OK] Structured output successful!")
            print(f"   Question: {result.question_text}")
            print(f"   Priority: {result.priority}")
            print(f"   Focus: {result.investigation_focus}")
        else:
            print(f"[ERROR] No parsed result. Raw content: {response.choices[0].message.content}")
            return False
        
        print(f"\n[OK] Native OpenAI structured outputs: ALL TESTS PASSED")
        return True
        
    except Exception as e:
        print(f"[ERROR] Native OpenAI test failed: {e}")
        return False

def test_litellm_structured_output():
    """Test structured outputs with LiteLLM"""
    print("\n" + "="*60)
    print("TESTING: LiteLLM with gpt-5-mini")
    print("="*60)
    
    if not LITELLM_AVAILABLE:
        print("[ERROR] Skipping - LiteLLM not available")
        return False
    
    api_key = get_api_key()
    if not api_key:
        print("[ERROR] Skipping - No API key available")
        return False
    
    # Set API key for LiteLLM
    os.environ['OPENAI_API_KEY'] = api_key
    
    try:
        # Test 1: LiteLLM with response_format parameter
        print("\nTest 1: LiteLLM with response_format (Pydantic)")
        print("-" * 40)
        
        response = litellm.completion(
            model="gpt-5-mini",
            messages=[
                {"role": "system", "content": "You are an expert investigation analyst."},
                {"role": "user", "content": "Assess this finding: 'Venezuela military deployment mentioned on social media'. Rate significance."}
            ],
            response_format=Finding
        )
        
        print(f"Response type: {type(response)}")
        print(f"Response choices: {len(response.choices) if hasattr(response, 'choices') else 'No choices'}")
        
        if hasattr(response, 'choices') and response.choices:
            message = response.choices[0].message
            print(f"Message type: {type(message)}")
            print(f"Message content: {message.content if hasattr(message, 'content') else 'No content'}")
            if hasattr(message, 'parsed'):
                print(f"Parsed available: {message.parsed}")
            else:
                print("No parsed attribute")
        
        # Test 2: LiteLLM with JSON schema approach
        print("\nTest 2: LiteLLM with JSON Schema")
        print("-" * 40)
        
        finding_schema = {
            "type": "object",
            "properties": {
                "is_significant": {"type": "boolean"},
                "relevance_score": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                "reasoning": {"type": "string"},
                "key_points": {"type": "array", "items": {"type": "string"}}
            },
            "required": ["is_significant", "relevance_score", "reasoning", "key_points"],
            "additionalProperties": False
        }
        
        response = litellm.completion(
            model="gpt-5-mini",
            messages=[
                {"role": "system", "content": "You are an expert investigation analyst. Respond with valid JSON."},
                {"role": "user", "content": "Assess this finding: 'Venezuela military deployment mentioned on social media'. Rate significance. Respond in JSON format."}
            ],
            response_format={"type": "json_object"}
        )
        
        if hasattr(response, 'choices') and response.choices:
            content = response.choices[0].message.content
            print(f"[OK] JSON response received")
            print(f"   Content type: {type(content)}")
            print(f"   Content length: {len(content) if content else 0}")
            
            try:
                parsed_json = json.loads(content)
                print(f"   Valid JSON: [OK]")
                print(f"   Keys: {list(parsed_json.keys())}")
            except json.JSONDecodeError as e:
                print(f"   Invalid JSON: [ERROR] {e}")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] LiteLLM test failed: {e}")
        print(f"   Error type: {type(e)}")
        import traceback
        print(f"   Traceback: {traceback.format_exc()}")
        return False

def test_manual_json_schema():
    """Test manual JSON schema approach with native OpenAI"""
    print("\n" + "="*60)
    print("TESTING: Native OpenAI with Manual JSON Schema")
    print("="*60)
    
    if not OPENAI_AVAILABLE:
        print("[ERROR] Skipping - OpenAI client not available")
        return False
    
    api_key = get_api_key()
    if not api_key:
        print("[ERROR] Skipping - No API key available")
        return False
    
    try:
        client = OpenAI(api_key=api_key)
        
        # Define JSON Schema manually (as shown in guide)
        finding_schema = {
            "type": "object",
            "properties": {
                "is_significant": {
                    "type": "boolean",
                    "description": "Whether this finding is significant for the investigation"
                },
                "relevance_score": {
                    "type": "number",
                    "minimum": 0.0,
                    "maximum": 1.0,
                    "description": "Relevance score from 0.0 to 1.0"
                },
                "reasoning": {
                    "type": "string",
                    "description": "Explanation of the assessment"
                },
                "key_points": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Key points extracted from the finding"
                }
            },
            "required": ["is_significant", "relevance_score", "reasoning", "key_points"],
            "additionalProperties": False
        }
        
        print("Testing manual JSON schema format...")
        
        response = client.chat.completions.create(
            model="gpt-5-mini",
            messages=[
                {"role": "system", "content": "You are an expert investigation analyst. Always respond with valid JSON that matches the provided schema."},
                {"role": "user", "content": "Assess this finding: 'Multiple unverified claims about military deployment to Venezuela on Twitter'. Rate significance for investigation."}
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "finding_assessment",
                    "strict": True,
                    "schema": finding_schema
                }
            }
        )
        
        content = response.choices[0].message.content
        print(f"[OK] Response received")
        print(f"   Content type: {type(content)}")
        print(f"   Content length: {len(content) if content else 0}")
        
        if content:
            try:
                parsed = json.loads(content)
                print(f"   Valid JSON: [OK]")
                print(f"   Required fields present:")
                for field in ["is_significant", "relevance_score", "reasoning", "key_points"]:
                    present = field in parsed
                    print(f"     {field}: {'[OK]' if present else '[ERROR]'}")
                    if present and field == "relevance_score":
                        score = parsed[field]
                        valid_range = 0.0 <= score <= 1.0
                        print(f"       Value: {score} ({'[OK]' if valid_range else '[ERROR] out of range'})")
                
                return True
            except json.JSONDecodeError as e:
                print(f"   Invalid JSON: [ERROR] {e}")
                print(f"   Raw content: {content}")
                return False
        else:
            print(f"   No content received: [ERROR]")
            return False
        
    except Exception as e:
        print(f"[ERROR] Manual JSON Schema test failed: {e}")
        import traceback
        print(f"   Traceback: {traceback.format_exc()}")
        return False

def main():
    """Run all structured output tests"""
    print("TEST: gpt-5-mini Structured Output Compatibility Test")
    print(f"TIME: Test started at: {datetime.now()}")
    
    results = {
        "native_openai": False,
        "litellm": False,
        "manual_schema": False
    }
    
    # Run tests
    results["native_openai"] = test_native_openai_structured_output()
    results["litellm"] = test_litellm_structured_output()  
    results["manual_schema"] = test_manual_json_schema()
    
    # Summary
    print("\n" + "="*60)
    print("FINAL RESULTS SUMMARY")
    print("="*60)
    
    for test_name, passed in results.items():
        status = "[OK] PASSED" if passed else "[ERROR] FAILED"
        print(f"{test_name.upper()}: {status}")
    
    total_passed = sum(results.values())
    print(f"\nOverall: {total_passed}/3 tests passed")
    
    if results["native_openai"]:
        print("\n[SUCCESS] CONCLUSION: gpt-5-mini DOES support structured outputs with native OpenAI client")
        print("   TwitterExplorer should use native OpenAI client for structured outputs")
    elif results["manual_schema"]:
        print("\n[WARNING] CONCLUSION: gpt-5-mini supports manual JSON schema but not Pydantic integration")
        print("   TwitterExplorer needs to migrate to manual JSON schema format")
    elif results["litellm"]:
        print("\n[INFO] CONCLUSION: gpt-5-mini works with LiteLLM but may need different approach")
        print("   TwitterExplorer LiteLLM integration needs adjustment")
    else:
        print("\n[ERROR] CONCLUSION: gpt-5-mini structured outputs not working with any approach")
        print("   TwitterExplorer should fallback to supported model or JSON mode")
    
    print(f"\nTIME: Test completed at: {datetime.now()}")

if __name__ == "__main__":
    main()