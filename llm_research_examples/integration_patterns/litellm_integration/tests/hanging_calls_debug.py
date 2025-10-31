#!/usr/bin/env python3
"""
Test the EXACT LLM calls that are hanging in AutoCoder system
Extract the real prompts and parameters from the system and test them in isolation
"""

import os
import sys
import time
import litellm
from dotenv import load_dotenv

# Add AutoCoder to path to access actual prompt files
sys.path.append('/home/brian/projects/autocoder4_cc')

load_dotenv()

def load_actual_autocoder_prompts():
    """Load the real prompts that AutoCoder uses"""
    prompts = {}
    
    # Load system prompt
    try:
        with open('prompts/component_generation/system_prompt.txt', 'r') as f:
            prompts['system'] = f.read().strip()
    except:
        prompts['system'] = "You are a Python code generator for enterprise applications."
    
    # Load component prompt 
    try:
        with open('prompts/component_generation/component_prompt.txt', 'r') as f:
            prompts['component'] = f.read().strip()
    except:
        prompts['component'] = "Generate a component class."
    
    return prompts

def get_real_component_generation_prompt():
    """Get the actual prompt that AutoCoder sends for component generation"""
    prompts = load_actual_autocoder_prompts()
    
    # This simulates what AutoCoder does for a Store component
    component_spec = {
        "name": "test_store",
        "type": "Store", 
        "base_primitive": "Transformer",
        "config": {"storage_backend": "sqlite"}
    }
    
    # Build the full prompt like AutoCoder does
    system_prompt = prompts['system']
    
    user_prompt = f"""
Generate a {component_spec['type']} component with the following requirements:

Component Name: {component_spec['name']}
Base Primitive: {component_spec['base_primitive']}
Configuration: {component_spec['config']}

{prompts['component']}

Requirements:
- Inherit from {component_spec['base_primitive']} primitive
- Implement all required methods for {component_spec['type']} functionality
- Include comprehensive error handling and logging
- Follow enterprise coding standards
- Include docstrings for all methods
- Handle the storage backend: {component_spec['config']['storage_backend']}

Generate ONLY the Python class code. No explanations or markdown formatting.
"""
    
    return system_prompt, user_prompt

def test_exact_autocoder_timeout_call():
    """Test the exact call that times out in AutoCoder"""
    print("="*70)
    print("🎯 TESTING EXACT AUTOCODER TIMEOUT SCENARIO")
    print("="*70)
    
    # Get real prompts
    system_prompt, user_prompt = get_real_component_generation_prompt()
    
    # Convert to AutoCoder's input format
    input_text = f"System: {system_prompt}\n\nUser: {user_prompt}"
    
    # Exact parameters AutoCoder uses
    model = "gpt-5-mini-2025-08-07"
    text_format = {"format": {"type": "text"}}
    
    print(f"📝 Model: {model}")
    print(f"📝 System prompt length: {len(system_prompt)} chars")
    print(f"📝 User prompt length: {len(user_prompt)} chars") 
    print(f"📝 Total input length: {len(input_text)} chars")
    print(f"📝 Input preview: {input_text[:300]}...")
    print()
    
    # Test 1: Without timeout (like current AutoCoder)
    print("🔴 Test 1: NO TIMEOUT (current AutoCoder behavior)")
    print("-" * 50)
    
    try:
        print(f"⏰ Starting call at {time.strftime('%H:%M:%S')}")
        start_time = time.time()
        
        # This is EXACTLY what AutoCoder does
        response = litellm.responses(
            model=model,
            input=input_text,
            text=text_format
            # NO TIMEOUT - like current AutoCoder
        )
        
        end_time = time.time()
        duration = end_time - start_time
        print(f"✅ Completed in {duration:.2f} seconds")
        
        # Extract content
        content = extract_content(response)
        print(f"📄 Response length: {len(content)} chars")
        print(f"📄 Response preview: {content[:200]}...")
        
        if duration > 120:
            print(f"⚠️ Would have TIMED OUT in AutoCoder (>120s)")
        else:
            print(f"✅ Would complete in AutoCoder (<120s)")
            
    except Exception as e:
        print(f"❌ Failed: {e}")
        print(f"❌ Exception type: {type(e)}")
    
    print()
    
    # Test 2: With 300s timeout (proposed fix)
    print("🟡 Test 2: WITH 300s TIMEOUT (proposed fix)")
    print("-" * 50)
    
    try:
        print(f"⏰ Starting call at {time.strftime('%H:%M:%S')}")
        start_time = time.time()
        
        # Proposed fix
        response = litellm.responses(
            model=model,
            input=input_text,
            text=text_format,
            timeout=300  # 5 minute timeout
        )
        
        end_time = time.time()
        duration = end_time - start_time
        print(f"✅ Completed in {duration:.2f} seconds")
        
        content = extract_content(response)
        print(f"📄 Response length: {len(content)} chars") 
        print(f"📄 Response preview: {content[:200]}...")
        
        print(f"✅ Proposed fix would work!")
        
    except Exception as e:
        print(f"❌ Failed: {e}")
        print(f"❌ Exception type: {type(e)}")

def test_async_executor_version():
    """Test the async executor approach that AutoCoder uses"""
    print("\n" + "="*70)
    print("🔄 TESTING ASYNC EXECUTOR (AutoCoder's actual implementation)")
    print("="*70)
    
    import asyncio
    
    async def run_async_test():
        system_prompt, user_prompt = get_real_component_generation_prompt()
        input_text = f"System: {system_prompt}\n\nUser: {user_prompt}"
        
        model = "gpt-5-mini-2025-08-07"
        text_format = {"format": {"type": "text"}}
        
        print("🔄 Testing async executor (current AutoCoder approach)")
        
        try:
            print(f"⏰ Starting async call at {time.strftime('%H:%M:%S')}")
            start_time = time.time()
            
            # EXACT AutoCoder implementation
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: litellm.responses(
                    model=model,
                    input=input_text,
                    text=text_format
                )
            )
            
            end_time = time.time()
            duration = end_time - start_time
            print(f"✅ Async completed in {duration:.2f} seconds")
            
            content = extract_content(response)
            print(f"📄 Response length: {len(content)} chars")
            
            if duration > 120:
                print(f"⚠️ This explains the AutoCoder timeout (>{duration:.0f}s > 120s)")
            else:
                print(f"✅ Would work in AutoCoder")
                
        except Exception as e:
            print(f"❌ Async failed: {e}")
    
    try:
        asyncio.run(run_async_test())
    except Exception as e:
        print(f"❌ Async test setup failed: {e}")

def extract_content(response):
    """Extract content using AutoCoder's method"""
    texts = []
    if hasattr(response, 'output') and response.output:
        for item in response.output:
            if hasattr(item, 'type') and item.type == 'message':
                if hasattr(item, 'content'):
                    for content in item.content:
                        if hasattr(content, 'text'):
                            texts.append(content.text)
    return "\n".join(texts) if texts else str(response)

def main():
    """Run exact AutoCoder scenario tests"""
    print("🚀 EXACT AUTOCODER HANGING CALL ANALYSIS")
    print("Testing the real prompts and calls that cause timeouts\n")
    
    # Environment check
    print("🔑 Environment:")
    print(f"  OPENAI_API_KEY: {'✅ Set' if os.getenv('OPENAI_API_KEY') else '❌ Missing'}")
    print(f"  AutoCoder prompts: {'✅' if os.path.exists('prompts') else '❌ Missing'}")
    print()
    
    # Test the exact hanging scenario
    test_exact_autocoder_timeout_call()
    
    # Test async approach
    test_async_executor_version()
    
    print("\n" + "="*70)
    print("📊 DIAGNOSIS CONCLUSION")
    print("="*70)
    print("If both tests take >120 seconds:")
    print("  ✅ Confirms AutoCoder timeout issue")
    print("  ✅ Validates 300s timeout fix")
    print("\nIf tests complete <120 seconds:")
    print("  🤔 Suggests AutoCoder has additional bottlenecks")
    print("  🔍 Need to investigate AutoCoder's environment/setup")

if __name__ == "__main__":
    main()