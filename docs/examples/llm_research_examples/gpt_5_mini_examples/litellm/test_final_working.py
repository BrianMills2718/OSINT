#!/usr/bin/env python3
"""
FINAL WORKING VERSION - Ready for implementation in UnifiedLLMProvider
This shows exactly what needs to be implemented.
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
    Final version ready for implementation in UnifiedLLMProvider
    """
    
    @staticmethod
    def is_responses_api_model(model: str) -> bool:
        """Check if model needs responses() API"""
        # gpt-5-mini and future gpt-5 models use responses API
        return 'gpt-5' in model.lower()
    
    @staticmethod
    def convert_messages_to_input(messages: List[Dict[str, str]]) -> str:
        """Convert messages array to input string for responses() API"""
        parts = []
        for msg in messages:
            role = msg.get('role', 'user')
            content = msg.get('content', '')
            
            # For responses API, we just concatenate the messages
            # System messages become part of the context
            if role == 'system':
                parts.append(f"System: {content}")
            elif role == 'assistant':
                parts.append(f"Assistant: {content}")
            else:  # user
                if len(parts) > 0 and parts[0].startswith("System:"):
                    # If we have a system message, just add the user content
                    parts.append(content)
                else:
                    parts.append(f"User: {content}")
        
        return "\n\n".join(parts)
    
    @staticmethod
    def extract_responses_content(response) -> str:
        """Extract text from responses() API response - FIXED VERSION"""
        # The response.output contains items, we need to find the message
        if hasattr(response, 'output') and response.output:
            for item in response.output:
                # Look for the message type output
                if hasattr(item, 'type') and item.type == 'message':
                    if hasattr(item, 'content'):
                        texts = []
                        for content in item.content:
                            if hasattr(content, 'text'):
                                texts.append(content.text)
                        if texts:
                            return "\n".join(texts)
        
        # Fallback: return string representation
        return str(response)
    
    @staticmethod
    def convert_response_format_to_text(response_format: Optional[Dict] = None, 
                                       json_schema: Optional[Dict] = None) -> Dict:
        """Convert completion API format to responses API text parameter"""
        if json_schema:
            # If explicit schema provided, use it
            return {
                "format": {
                    "type": "json_schema",
                    "name": "response",
                    "schema": json_schema,
                    "strict": True
                }
            }
        elif response_format and response_format.get("type") == "json_object":
            # Generic JSON object request
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
        else:
            # Default text format
            return {"format": {"type": "text"}}
    
    @classmethod
    def generate(
        cls, 
        model: str, 
        messages: List[Dict[str, str]], 
        response_format: Optional[Dict] = None,
        json_schema: Optional[Dict] = None,
        **kwargs
    ) -> str:
        """
        Main generation method that automatically uses the right API
        """
        try:
            if cls.is_responses_api_model(model):
                # Use responses() API for gpt-5 models
                print(f"🚀 Using responses() API for {model}")
                
                # Convert messages to input
                input_text = cls.convert_messages_to_input(messages)
                print(f"📝 Input: {input_text[:100]}...")
                
                # Convert response format
                text_format = cls.convert_response_format_to_text(response_format, json_schema)
                
                # Remove completion-only params
                kwargs.pop('response_format', None)
                kwargs.pop('max_tokens', None)  # responses uses max_output_tokens
                
                # Convert max_tokens to max_output_tokens if present
                if 'max_tokens' in kwargs:
                    kwargs['max_output_tokens'] = kwargs.pop('max_tokens')
                
                response = litellm.responses(
                    model=model,
                    input=input_text,
                    text=text_format,
                    **kwargs
                )
                
                return cls.extract_responses_content(response)
                
            else:
                # Use completion() API for other models
                print(f"📚 Using completion() API for {model}")
                
                # Build params
                params = {
                    "model": model,
                    "messages": messages,
                    **kwargs
                }
                
                # Only add response_format for models that support it
                if response_format and 'turbo' in model.lower():
                    params["response_format"] = response_format
                
                response = litellm.completion(**params)
                
                if hasattr(response, 'choices') and response.choices:
                    return response.choices[0].message.content
                return str(response)
                
        except Exception as e:
            print(f"❌ Error with {model}: {e}")
            raise


def main():
    """Test the final implementation"""
    print("\n" + "="*60)
    print("🎯 FINAL UNIFIED API WRAPPER TEST")
    print("="*60)
    
    # 1. Test basic text generation
    print("\n1️⃣  Basic Text Generation")
    print("-"*40)
    
    messages = [
        {"role": "system", "content": "You are a helpful assistant. Be concise."},
        {"role": "user", "content": "What is 2+2?"}
    ]
    
    # Test with gpt-5-mini
    try:
        result = UnifiedLLMWrapper.generate(
            "gpt-5-mini-2025-08-07",
            messages,
            max_output_tokens=50
        )
        print(f"✅ gpt-5-mini: {result}")
    except Exception as e:
        print(f"❌ gpt-5-mini failed: {e}")
    
    # Test with gpt-4-turbo (supports response_format)
    try:
        result = UnifiedLLMWrapper.generate(
            "gpt-4-turbo",
            messages,
            max_tokens=50
        )
        print(f"✅ gpt-4-turbo: {result}")
    except Exception as e:
        print(f"❌ gpt-4-turbo failed: {e}")
    
    # 2. Test JSON generation
    print("\n2️⃣  JSON Generation with Schema")
    print("-"*40)
    
    json_messages = [
        {"role": "user", "content": "Create a person object with name='John', age=30, active=true"}
    ]
    
    schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "age": {"type": "number"},
            "active": {"type": "boolean"}
        },
        "required": ["name", "age", "active"],
        "additionalProperties": False
    }
    
    # Test with gpt-5-mini
    try:
        result = UnifiedLLMWrapper.generate(
            "gpt-5-mini-2025-08-07",
            json_messages,
            json_schema=schema
        )
        parsed = json.loads(result)
        print(f"✅ gpt-5-mini JSON: {json.dumps(parsed, indent=2)}")
    except Exception as e:
        print(f"❌ gpt-5-mini JSON failed: {e}")
    
    # Test with gpt-4-turbo
    try:
        result = UnifiedLLMWrapper.generate(
            "gpt-4-turbo",
            json_messages,
            response_format={"type": "json_object"}
        )
        parsed = json.loads(result)
        print(f"✅ gpt-4-turbo JSON: {json.dumps(parsed, indent=2)}")
    except Exception as e:
        print(f"❌ gpt-4-turbo JSON failed: {e}")
    
    # 3. Test component generation (our actual use case)
    print("\n3️⃣  Component Generation (Real Use Case)")
    print("-"*40)
    
    component_messages = [
        {"role": "system", "content": "You are a Python code generator. Generate only code, no explanations."},
        {"role": "user", "content": "Create a simple Store class with get() and set() methods using a dict for storage."}
    ]
    
    # Test with gpt-5-mini
    try:
        result = UnifiedLLMWrapper.generate(
            "gpt-5-mini-2025-08-07",
            component_messages,
            max_output_tokens=200
        )
        print(f"✅ gpt-5-mini generated:\n{result[:300]}...")
    except Exception as e:
        print(f"❌ gpt-5-mini failed: {e}")
    
    print("\n" + "="*60)
    print("✅ IMPLEMENTATION READY")
    print("="*60)
    print("\nNext Steps:")
    print("1. Copy this logic to UnifiedLLMProvider")
    print("2. Update generate() and generate_sync() methods")
    print("3. Test with actual component generation")


if __name__ == "__main__":
    main()