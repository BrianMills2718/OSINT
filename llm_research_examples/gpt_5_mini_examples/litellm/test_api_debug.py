#!/usr/bin/env python3
"""
Debug API issues - check what's happening
"""

import os
import sys
from dotenv import load_dotenv
import litellm

# Enable debug mode
litellm.set_verbose = True

# Load environment variables
load_dotenv()

print("API Debug Test")
print("="*50)

# Check environment
api_key = os.getenv("OPENAI_API_KEY")
print(f"API Key present: {bool(api_key)}")
if api_key:
    print(f"API Key starts with: {api_key[:7]}...")

# Check what models litellm knows about
print("\nChecking model configuration...")

# Try the simplest possible call with timeout
import signal

def timeout_handler(signum, frame):
    raise TimeoutError("API call timed out")

# Set a 5 second timeout
signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm(5)

try:
    print("\nAttempting responses() API call with 5 second timeout...")
    response = litellm.responses(
        model="gpt-5-mini",
        input="Hi"
    )
    print(f"Success! Response: {response}")
except TimeoutError:
    print("❌ API call timed out after 5 seconds")
    print("This suggests the model name or API endpoint might be incorrect")
except Exception as e:
    print(f"❌ Error: {e}")
finally:
    signal.alarm(0)  # Cancel alarm

# Try with gpt-4 to see if it's a general API issue
signal.alarm(5)
try:
    print("\nAttempting completion() with gpt-4...")
    response = litellm.completion(
        model="gpt-4",
        messages=[{"role": "user", "content": "Hi"}],
        max_tokens=5
    )
    print(f"✅ GPT-4 works! Response: {response.choices[0].message.content}")
except TimeoutError:
    print("❌ GPT-4 also timed out - might be API key or network issue")
except Exception as e:
    print(f"❌ GPT-4 error: {e}")
finally:
    signal.alarm(0)