#!/usr/bin/env python3
"""
Working unified API test - demonstrating the approach that will be implemented
"""

import os
import json
from dotenv import load_dotenv
import litellm
from typing import List, Dict, Any, Optional

# Load environment variables
load_dotenv()

class UnifiedLLMWrapper:
    """
    Simplified wrapper showing exactly what we need to implement
    """
    
    @staticmethod
    def is_responses_api_model(model: str) -> bool:
        """Check if model needs responses() API"""
        return 'gpt-5' in model.lower()
    
    @staticmethod
    def convert_messages_to_input(messages: List[Dict[str, str]]) -> str:
        """Convert messages array to input string"""
        parts = []
        for msg in messages:
            role = msg.get('role', 'user')
            content = msg.get('content', '')
            if role == 'system':
                parts.append(f"System: {content}")
            elif role == 'assistant':
                parts.append(f"Assistant: {content}")
            else:
                parts.append(f"User: {content}")
        return "\n\n".join(parts)
    
    @staticmethod
    def extract_responses_content(response) -> str:
        """Extract text from responses() API response"""
        texts = []
        if hasattr(response, 'output'):
            for item in response.output:
                if hasattr(item, 'content'):
                    for c in item.content:
                        if hasattr(c, 'text'):
                            texts.append(c.text)
                elif hasattr(item, 'type') and item.type == 'message':
                    # Alternative structure
                    for c in item.content:
                        if hasattr(c, 'text'):
                            texts.append(c.text)
        return "\n".join(texts) if texts else str(response)
    
    @classmethod
    def generate(cls, model: str, messages: List[Dict[str, str]], **kwargs) -> str:
        """Main generation method"""
        try:
            if cls.is_responses_api_model(model):
                # Use responses() API for gpt-5-mini
                print(f"📡 Using responses() API for {model}")
                input_text = cls.convert_messages_to_input(messages)
                
                # Handle JSON format if needed
                text_format = kwargs.pop('text_format', {"format": {"type": "text"}})
                
                response = litellm.responses(
                    model=model,
                    input=input_text,
                    text=text_format,
                    **kwargs
                )
                
                return cls.extract_responses_content(response)
            else:
                # Use completion() API for other models
                print(f"📝 Using completion() API for {model}")
                response = litellm.completion(
                    model=model,
                    messages=messages,
                    **kwargs
                )
                
                if hasattr(response, 'choices'):
                    return response.choices[0].message.content
                return str(response)
                
        except Exception as e:
            print(f"❌ Error: {e}")
            raise


def test_both_apis():
    """Test that both APIs work with our wrapper"""
    print("="*60)
    print("Testing Unified API Wrapper")
    print("="*60)
    
    # Test messages
    messages = [
        {"role": "system", "content": "You are a helpful coding assistant."},
        {"role": "user", "content": "Write a Python function to reverse a string. Just the function, no explanation."}
    ]
    
    # Test gpt-5-mini with responses() API
    print("\n1️⃣ Testing gpt-5-mini...")
    try:
        result = UnifiedLLMWrapper.generate(
            "gpt-5-mini-2025-08-07",
            messages,
            max_output_tokens=100
        )
        print(f"✅ Success! Response:\n{result}\n")
    except Exception as e:
        print(f"❌ Failed: {e}\n")
    
    # Test gpt-4 with completion() API
    print("2️⃣ Testing gpt-4...")
    try:
        result = UnifiedLLMWrapper.generate(
            "gpt-4",
            messages,
            max_tokens=100
        )
        print(f"✅ Success! Response:\n{result}\n")
    except Exception as e:
        print(f"❌ Failed: {e}\n")
    
    # Test Claude if API key available
    if os.getenv("ANTHROPIC_API_KEY"):
        print("3️⃣ Testing Claude...")
        try:
            result = UnifiedLLMWrapper.generate(
                "claude-3-sonnet-20240229",
                messages,
                max_tokens=100
            )
            print(f"✅ Success! Response:\n{result}\n")
        except Exception as e:
            print(f"❌ Failed: {e}\n")


def test_json_generation():
    """Test JSON generation with both APIs"""
    print("="*60)
    print("Testing JSON Generation")
    print("="*60)
    
    messages = [
        {"role": "user", "content": "Generate a JSON object with fields: name (string), age (number), active (boolean). Use example values."}
    ]
    
    # For gpt-5-mini with JSON schema
    print("\n1️⃣ Testing JSON with gpt-5-mini...")
    try:
        text_format = {
            "format": {
                "type": "json_schema",
                "name": "person",
                "schema": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "age": {"type": "number"},
                        "active": {"type": "boolean"}
                    },
                    "required": ["name", "age", "active"],
                    "additionalProperties": False
                },
                "strict": True
            }
        }
        
        result = UnifiedLLMWrapper.generate(
            "gpt-5-mini-2025-08-07",
            messages,
            text_format=text_format
        )
        print(f"✅ Response: {result}")
        
        # Try parsing as JSON
        parsed = json.loads(result)
        print(f"✅ Valid JSON: {json.dumps(parsed, indent=2)}\n")
    except Exception as e:
        print(f"❌ Failed: {e}\n")
    
    # For gpt-4 with response_format
    print("2️⃣ Testing JSON with gpt-4...")
    try:
        result = UnifiedLLMWrapper.generate(
            "gpt-4",
            messages,
            response_format={"type": "json_object"},
            max_tokens=100
        )
        print(f"✅ Response: {result}")
        
        # Try parsing as JSON
        parsed = json.loads(result)
        print(f"✅ Valid JSON: {json.dumps(parsed, indent=2)}\n")
    except Exception as e:
        print(f"❌ Failed: {e}\n")


def main():
    """Run all tests"""
    print("\n" + "🚀 UNIFIED API WRAPPER TEST")
    print("This demonstrates the approach we'll implement\n")
    
    # Check API keys
    print("🔑 API Keys:")
    print(f"  OpenAI: {'✅' if os.getenv('OPENAI_API_KEY') else '❌'}")
    print(f"  Anthropic: {'✅' if os.getenv('ANTHROPIC_API_KEY') else '❌'}")
    print()
    
    # Run tests
    test_both_apis()
    test_json_generation()
    
    print("="*60)
    print("✅ TESTING COMPLETE")
    print("="*60)
    print("\n📝 Implementation Plan:")
    print("1. Add is_responses_api_model() check to UnifiedLLMProvider")
    print("2. Add message conversion for responses() API")
    print("3. Add response extraction for both formats")
    print("4. Update all kwargs handling")
    print("5. Test with existing codebase")


if __name__ == "__main__":
    main()