#!/usr/bin/env python3
"""
Test unified API approach for supporting both completion() and responses() APIs
This tests our approach before implementing in the main codebase.
"""

import os
import json
import asyncio
from dotenv import load_dotenv
import litellm
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

# Load environment variables
load_dotenv()

# Test configuration
TEST_GPT5_MINI = "gpt-5-mini-2025-08-07"
TEST_GPT4 = "gpt-4"
TEST_CLAUDE = "claude-3-sonnet-20240229"

# ==========================================
# UNIFIED API WRAPPER
# ==========================================

class UnifiedLLMWrapper:
    """
    Wrapper that automatically uses the correct API based on the model.
    This is what we'll implement in our actual UnifiedLLMProvider.
    """
    
    @staticmethod
    def _is_responses_api_model(model: str) -> bool:
        """Determine if a model requires the responses() API"""
        RESPONSES_API_MODELS = ['gpt-5-mini', 'gpt-5']
        return any(m in model for m in RESPONSES_API_MODELS)
    
    @staticmethod
    def _convert_messages_to_input(messages: List[Dict[str, str]]) -> str:
        """Convert chat messages array to single input string for responses() API"""
        # For responses API, we need to convert messages to a single prompt
        prompt_parts = []
        for msg in messages:
            role = msg.get('role', 'user')
            content = msg.get('content', '')
            if role == 'system':
                prompt_parts.append(f"System: {content}")
            elif role == 'assistant':
                prompt_parts.append(f"Assistant: {content}")
            else:  # user
                prompt_parts.append(f"User: {content}")
        
        return "\n\n".join(prompt_parts)
    
    @staticmethod
    def _convert_response_format_to_text(response_format: Optional[Dict] = None) -> Optional[Dict]:
        """Convert completion API response_format to responses API text format"""
        if not response_format:
            return {"format": {"type": "text"}}
        
        if response_format.get("type") == "json_object":
            # For simple JSON object request without schema
            return {
                "format": {
                    "type": "json_schema",
                    "name": "response",
                    "schema": {
                        "type": "object",
                        "additionalProperties": True
                    },
                    "strict": False
                }
            }
        
        # If there's already a schema provided
        if "schema" in response_format:
            return {
                "format": {
                    "type": "json_schema",
                    "name": "response",
                    "schema": response_format["schema"],
                    "strict": response_format.get("strict", True)
                }
            }
        
        return {"format": {"type": "text"}}
    
    @staticmethod
    def _extract_response_content(response, is_responses_api: bool) -> str:
        """Extract content from either API response format"""
        if is_responses_api:
            # responses() API format
            if hasattr(response, 'output'):
                texts = []
                for item in response.output:
                    if hasattr(item, "content"):
                        for c in item.content:
                            if hasattr(c, "text"):
                                texts.append(c.text)
                return "\n".join(texts)
            return str(response)
        else:
            # completion() API format
            if hasattr(response, 'choices') and len(response.choices) > 0:
                return response.choices[0].message.content
            return str(response)
    
    @classmethod
    def call_llm(
        cls,
        model: str,
        messages: List[Dict[str, str]],
        response_format: Optional[Dict] = None,
        **kwargs
    ) -> str:
        """
        Unified method that calls the appropriate API based on model.
        Returns the extracted content as a string.
        """
        try:
            if cls._is_responses_api_model(model):
                print(f"🔄 Using responses() API for {model}")
                
                # Convert parameters for responses API
                input_text = cls._convert_messages_to_input(messages)
                text_format = cls._convert_response_format_to_text(response_format)
                
                response = litellm.responses(
                    model=model,
                    input=input_text,
                    text=text_format,
                    **kwargs
                )
                
                return cls._extract_response_content(response, is_responses_api=True)
            else:
                print(f"📝 Using completion() API for {model}")
                
                # Use traditional completion API
                params = {
                    "model": model,
                    "messages": messages,
                    **kwargs
                }
                
                if response_format:
                    params["response_format"] = response_format
                
                response = litellm.completion(**params)
                
                return cls._extract_response_content(response, is_responses_api=False)
                
        except Exception as e:
            print(f"❌ Error with {model}: {e}")
            raise

    @classmethod
    async def acall_llm(
        cls,
        model: str,
        messages: List[Dict[str, str]],
        response_format: Optional[Dict] = None,
        **kwargs
    ) -> str:
        """Async version of call_llm"""
        # For now, we'll use sync version in async context
        # In production, we'd implement proper async for responses() API
        return cls.call_llm(model, messages, response_format, **kwargs)


# ==========================================
# TEST CASES
# ==========================================

def test_basic_text_generation():
    """Test basic text generation with different models"""
    print("\n" + "="*60)
    print("TEST: Basic Text Generation")
    print("="*60)
    
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Write a haiku about programming."}
    ]
    
    # Test with gpt-5-mini (responses API)
    try:
        print(f"\n🧪 Testing {TEST_GPT5_MINI}...")
        result = UnifiedLLMWrapper.call_llm(TEST_GPT5_MINI, messages)
        print(f"✅ Success! Response:\n{result}")
    except Exception as e:
        print(f"❌ Failed: {e}")
    
    # Test with GPT-4 (completion API)
    try:
        print(f"\n🧪 Testing {TEST_GPT4}...")
        result = UnifiedLLMWrapper.call_llm(TEST_GPT4, messages)
        print(f"✅ Success! Response:\n{result}")
    except Exception as e:
        print(f"❌ Failed: {e}")
    
    # Test with Claude (completion API)
    if os.getenv("ANTHROPIC_API_KEY"):
        try:
            print(f"\n🧪 Testing {TEST_CLAUDE}...")
            result = UnifiedLLMWrapper.call_llm(TEST_CLAUDE, messages)
            print(f"✅ Success! Response:\n{result}")
        except Exception as e:
            print(f"❌ Failed: {e}")


def test_json_generation():
    """Test JSON generation with schema"""
    print("\n" + "="*60)
    print("TEST: JSON Schema Generation")
    print("="*60)
    
    # Define a simple schema
    class StoreComponent(BaseModel):
        name: str
        type: str
        description: str
        methods: List[str]
    
    messages = [
        {"role": "system", "content": "You are a code generation assistant."},
        {"role": "user", "content": "Generate a JSON description of a Store component with methods: get, set, delete"}
    ]
    
    # For responses API, we need full schema
    response_format = {
        "type": "json_object",
        "schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "type": {"type": "string"},
                "description": {"type": "string"},
                "methods": {
                    "type": "array",
                    "items": {"type": "string"}
                }
            },
            "required": ["name", "type", "description", "methods"]
        },
        "strict": True
    }
    
    # Test with gpt-5-mini
    try:
        print(f"\n🧪 Testing JSON with {TEST_GPT5_MINI}...")
        result = UnifiedLLMWrapper.call_llm(TEST_GPT5_MINI, messages, response_format)
        print(f"✅ Success! Response:\n{result}")
        
        # Try to parse as JSON
        json_result = json.loads(result)
        print(f"📋 Parsed JSON: {json.dumps(json_result, indent=2)}")
    except Exception as e:
        print(f"❌ Failed: {e}")
    
    # Test with GPT-4
    try:
        print(f"\n🧪 Testing JSON with {TEST_GPT4}...")
        # For completion API, we use simpler format
        simple_format = {"type": "json_object"}
        result = UnifiedLLMWrapper.call_llm(TEST_GPT4, messages, simple_format)
        print(f"✅ Success! Response:\n{result}")
        
        # Try to parse as JSON
        json_result = json.loads(result)
        print(f"📋 Parsed JSON: {json.dumps(json_result, indent=2)}")
    except Exception as e:
        print(f"❌ Failed: {e}")


def test_component_generation_prompt():
    """Test with actual component generation prompt like our system uses"""
    print("\n" + "="*60)
    print("TEST: Component Generation (Real Use Case)")
    print("="*60)
    
    # This mimics what our actual component generator does
    system_prompt = """You are an expert Python developer creating production-ready components.
Generate complete, working implementations with no placeholders or TODOs."""
    
    user_prompt = """Create a Store component that:
1. Inherits from Store base class
2. Has methods: get(key), set(key, value), delete(key)
3. Uses in-memory dictionary for storage
4. Includes proper error handling"""
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
    
    # Test with gpt-5-mini
    try:
        print(f"\n🧪 Testing component generation with {TEST_GPT5_MINI}...")
        result = UnifiedLLMWrapper.call_llm(TEST_GPT5_MINI, messages)
        print(f"✅ Success! Generated component (first 500 chars):\n{result[:500]}...")
    except Exception as e:
        print(f"❌ Failed: {e}")


async def test_async_calls():
    """Test async version of the wrapper"""
    print("\n" + "="*60)
    print("TEST: Async API Calls")
    print("="*60)
    
    messages = [
        {"role": "user", "content": "Say 'Hello from async' in 5 words or less"}
    ]
    
    # Test async with gpt-5-mini
    try:
        print(f"\n🧪 Testing async with {TEST_GPT5_MINI}...")
        result = await UnifiedLLMWrapper.acall_llm(TEST_GPT5_MINI, messages)
        print(f"✅ Success! Response: {result}")
    except Exception as e:
        print(f"❌ Failed: {e}")


def test_model_detection():
    """Test model detection logic"""
    print("\n" + "="*60)
    print("TEST: Model Detection Logic")
    print("="*60)
    
    test_models = [
        ("gpt-5-mini", True),
        ("gpt-5-mini-2025-08-07", True),
        ("gpt-5", True),
        ("gpt-4", False),
        ("gpt-4-turbo", False),
        ("claude-3-sonnet", False),
        ("gpt-3.5-turbo", False),
    ]
    
    for model, expected in test_models:
        result = UnifiedLLMWrapper._is_responses_api_model(model)
        status = "✅" if result == expected else "❌"
        print(f"{status} {model}: {result} (expected: {expected})")


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("UNIFIED API WRAPPER TESTING")
    print("Testing approach for gpt-5-mini support")
    print("="*60)
    
    # Check API keys
    print("\n🔑 API Keys Status:")
    print(f"  OpenAI: {'✅' if os.getenv('OPENAI_API_KEY') else '❌'}")
    print(f"  Anthropic: {'✅' if os.getenv('ANTHROPIC_API_KEY') else '❌'}")
    
    # Run tests
    test_model_detection()
    test_basic_text_generation()
    test_json_generation()
    test_component_generation_prompt()
    
    # Run async test
    print("\nRunning async test...")
    asyncio.run(test_async_calls())
    
    print("\n" + "="*60)
    print("TESTING COMPLETE")
    print("="*60)
    print("\n📝 Summary:")
    print("- If gpt-5-mini tests pass: Our approach works!")
    print("- If other models pass: Backward compatibility maintained")
    print("- Next step: Implement this in UnifiedLLMProvider")


if __name__ == "__main__":
    main()