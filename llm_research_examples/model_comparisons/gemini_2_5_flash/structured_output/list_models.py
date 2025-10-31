#!/usr/bin/env python3
"""
List available Gemini models to find the correct model name
"""
import litellm
import os

# Set API key
os.environ['GEMINI_API_KEY'] = 'AIzaSyCwNW6kO6R0AewqsUgG9IgrDg6vCRFhhHw'

def main():
    try:
        # Try simple completion first
        print("Testing basic Gemini completion...")
        response = litellm.completion(
            model="gemini/gemini-1.5-pro",
            messages=[{"role": "user", "content": "Say hello"}]
        )
        print(f"✓ Success with gemini-1.5-pro: {response.choices[0].message.content}")
        
    except Exception as e:
        print(f"✗ Error with gemini-1.5-pro: {e}")
        
    # Try other model names including 2.5 Flash-Lite
    models_to_try = [
        "gemini/gemini-2.5-flash-lite",
        "gemini/gemini-2.5-flash",
        "gemini/gemini-1.5-flash",
        "gemini/gemini-2.0-flash-exp"
    ]
    
    for model in models_to_try:
        try:
            print(f"\nTesting {model}...")
            response = litellm.completion(
                model=model,
                messages=[{"role": "user", "content": "Say hello"}]
            )
            print(f"✓ Success with {model}: {response.choices[0].message.content}")
            break
        except Exception as e:
            print(f"✗ Error with {model}: {str(e)[:100]}...")

if __name__ == "__main__":
    main()