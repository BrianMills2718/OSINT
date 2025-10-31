#!/usr/bin/env python3
"""
Simple test to verify responses() API works with gpt-5-mini
"""

import os
import sys
from dotenv import load_dotenv
import litellm
import traceback

# Load environment variables
load_dotenv()

print("Testing gpt-5-mini with responses() API")
print("="*50)

# Check API key
if not os.getenv("OPENAI_API_KEY"):
    print("❌ No OPENAI_API_KEY found in environment")
    sys.exit(1)

print("✅ OpenAI API key found")

# Test 1: Simple text response
print("\nTest 1: Basic text response")
try:
    response = litellm.responses(
        model="gpt-5-mini-2025-08-07",
        input="Say 'Hello from gpt-5-mini' in exactly 5 words",
        text={"format": {"type": "text"}}
    )
    
    # Extract text from response
    if hasattr(response, 'output'):
        texts = []
        for item in response.output:
            if hasattr(item, "content"):
                for c in item.content:
                    if hasattr(c, "text"):
                        texts.append(c.text)
        result = "\n".join(texts)
        print(f"✅ Success! Response: {result}")
    else:
        print(f"✅ Response received: {response}")
        
except Exception as e:
    print(f"❌ Failed: {e}")
    traceback.print_exc()

# Test 2: Compare with completion() API for GPT-4
print("\nTest 2: GPT-4 with completion() API")
try:
    response = litellm.completion(
        model="gpt-4",
        messages=[{"role": "user", "content": "Say 'Hello from gpt-4' in exactly 5 words"}]
    )
    
    if hasattr(response, 'choices'):
        result = response.choices[0].message.content
        print(f"✅ Success! Response: {result}")
    else:
        print(f"✅ Response received: {response}")
        
except Exception as e:
    print(f"❌ Failed: {e}")
    traceback.print_exc()

print("\nTest complete!")