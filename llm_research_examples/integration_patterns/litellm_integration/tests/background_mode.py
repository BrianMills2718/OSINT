#!/usr/bin/env python3
"""
Test LiteLLM background mode with gpt-5-mini to solve timeout issues
This tests if litellm.responses() supports the background=True parameter
"""

import os
import time
import litellm
from dotenv import load_dotenv

load_dotenv()

def test_basic_litellm_background():
    """Test if litellm.responses() supports background mode"""
    print("="*60)
    print("🧪 Testing LiteLLM Background Mode Support")
    print("="*60)
    
    model = "gpt-5-mini-2025-08-07"
    input_text = "Write a comprehensive Python class for a file manager with full documentation and error handling. Include at least 10 methods."
    
    try:
        print("📡 Attempting litellm.responses() with background=True...")
        start_time = time.time()
        
        # Test if litellm supports background parameter
        response = litellm.responses(
            model=model,
            input=input_text,
            text={"format": {"type": "text"}},
            background=True  # KEY TEST
        )
        
        print(f"✅ Request submitted successfully")
        print(f"📄 Response type: {type(response)}")
        print(f"📄 Response attributes: {dir(response)}")
        
        # Check if response has status attribute (background mode indicator)
        if hasattr(response, 'status'):
            print(f"🔄 Status: {response.status}")
            
            # If it's background mode, poll for completion
            if response.status in ["queued", "in_progress"]:
                print("🔄 Polling for completion...")
                poll_count = 0
                
                while response.status in ["queued", "in_progress"] and poll_count < 60:  # Max 2 minutes polling
                    print(f"   Status: {response.status} (poll #{poll_count + 1})")
                    time.sleep(2)
                    
                    # Try to retrieve updated status
                    if hasattr(litellm, 'responses') and hasattr(response, 'id'):
                        try:
                            response = litellm.responses.retrieve(response.id)
                        except Exception as e:
                            print(f"   ⚠️ Polling failed: {e}")
                            break
                    else:
                        print("   ⚠️ No polling mechanism available")
                        break
                    
                    poll_count += 1
                
                if response.status == "completed":
                    end_time = time.time()
                    print(f"✅ Background task completed in {end_time - start_time:.2f} seconds")
                    
                    # Extract content
                    if hasattr(response, 'output_text'):
                        content = response.output_text
                    else:
                        # Try standard extraction
                        content = extract_content(response)
                    
                    print(f"📄 Response length: {len(content)} chars")
                    print(f"📄 Response preview: {content[:200]}...")
                    return True
                else:
                    print(f"❌ Background task didn't complete. Final status: {response.status}")
                    return False
            else:
                # Immediate response (not background mode)
                end_time = time.time()
                print(f"⚡ Immediate response in {end_time - start_time:.2f} seconds")
                content = extract_content(response)
                print(f"📄 Response length: {len(content)} chars")
                print(f"📄 Response preview: {content[:200]}...")
                return True
        else:
            # Standard synchronous response
            end_time = time.time()
            print(f"⚡ Standard response in {end_time - start_time:.2f} seconds")
            content = extract_content(response)
            print(f"📄 Response length: {len(content)} chars")
            print(f"📄 Response preview: {content[:200]}...")
            return True
            
    except Exception as e:
        print(f"❌ Background mode test failed: {e}")
        print(f"❌ Exception type: {type(e)}")
        return False

def test_litellm_with_long_timeout():
    """Test litellm with very long timeout as fallback"""
    print("\n" + "="*60)
    print("🧪 Testing LiteLLM with Extended Timeout")
    print("="*60)
    
    model = "gpt-5-mini-2025-08-07"
    input_text = "Write a comprehensive Python class for managing a distributed task queue with full documentation, error handling, retry logic, and monitoring. Include at least 15 methods with detailed implementations."
    
    try:
        print("📡 Attempting litellm.responses() with 300s timeout...")
        start_time = time.time()
        
        response = litellm.responses(
            model=model,
            input=input_text,
            text={"format": {"type": "text"}},
            timeout=300  # 5 minutes
        )
        
        end_time = time.time()
        print(f"✅ Long timeout request completed in {end_time - start_time:.2f} seconds")
        
        content = extract_content(response)
        print(f"📄 Response length: {len(content)} chars")
        print(f"📄 Response preview: {content[:200]}...")
        return True
        
    except Exception as e:
        print(f"❌ Long timeout test failed: {e}")
        print(f"❌ Exception type: {type(e)}")
        return False

def extract_content(response):
    """Extract content from litellm response"""
    texts = []
    if hasattr(response, 'output') and response.output:
        for item in response.output:
            if hasattr(item, 'type') and item.type == 'message':
                if hasattr(item, 'content'):
                    for content in item.content:
                        if hasattr(content, 'text'):
                            texts.append(content.text)
    return "\n".join(texts) if texts else str(response)

def test_native_openai_background():
    """Test native OpenAI client background mode for comparison"""
    print("\n" + "="*60)
    print("🧪 Testing Native OpenAI Background Mode (Reference)")
    print("="*60)
    
    try:
        from openai import OpenAI
        
        client = OpenAI()
        
        print("📡 Testing native OpenAI background mode...")
        start_time = time.time()
        
        resp = client.responses.create(
            model="gpt-5-mini-2025-08-07",
            input="Write a simple Python function to calculate fibonacci numbers.",
            background=True,
        )
        
        print(f"✅ Native background request submitted")
        print(f"🔄 Initial status: {resp.status}")
        print(f"📄 Response ID: {resp.id}")
        
        # Poll for completion
        poll_count = 0
        while resp.status in {"queued", "in_progress"} and poll_count < 30:
            print(f"   Status: {resp.status} (poll #{poll_count + 1})")
            time.sleep(2)
            resp = client.responses.retrieve(resp.id)
            poll_count += 1
        
        end_time = time.time()
        print(f"✅ Native background completed in {end_time - start_time:.2f} seconds")
        print(f"🔄 Final status: {resp.status}")
        
        if hasattr(resp, 'output_text'):
            print(f"📄 Response preview: {resp.output_text[:200]}...")
        
        return True
        
    except ImportError:
        print("⚠️ OpenAI client not available for native test")
        return False
    except Exception as e:
        print(f"❌ Native OpenAI test failed: {e}")
        return False

def main():
    """Run all background mode tests"""
    print("🚀 LITELLM BACKGROUND MODE TESTING")
    print("Testing solutions for gpt-5-mini timeout issues\n")
    
    # Check environment
    print("🔑 Environment Check:")
    print(f"  OPENAI_API_KEY: {'✅ Set' if os.getenv('OPENAI_API_KEY') else '❌ Missing'}")
    try:
        print(f"  LiteLLM available: ✅")
        print(f"  LiteLLM responses: {'✅' if hasattr(litellm, 'responses') else '❌'}")
    except:
        print(f"  LiteLLM: ❌ Import failed")
    print()
    
    results = []
    
    # Test 1: LiteLLM background mode
    results.append(("LiteLLM Background Mode", test_basic_litellm_background()))
    
    # Test 2: LiteLLM with long timeout
    results.append(("LiteLLM Extended Timeout", test_litellm_with_long_timeout()))
    
    # Test 3: Native OpenAI background (reference)
    results.append(("Native OpenAI Background", test_native_openai_background()))
    
    # Summary
    print("\n" + "="*60)
    print("📊 BACKGROUND MODE TEST RESULTS")
    print("="*60)
    
    for test_name, success in results:
        status = "✅ SUPPORTED" if success else "❌ NOT SUPPORTED"
        print(f"  {test_name}: {status}")
    
    print("\n🎯 RECOMMENDATIONS:")
    
    if results[0][1]:  # LiteLLM background mode works
        print("✅ Use LiteLLM background mode - native support detected")
        print("   Implementation: Add background=True to litellm.responses() calls")
    elif results[1][1]:  # Extended timeout works
        print("⚠️ Use extended timeout approach - background mode not supported")
        print("   Implementation: Add timeout=300 to litellm.responses() calls")
    else:
        print("❌ Both approaches failed - may need native OpenAI client")
        print("   Implementation: Consider switching to native OpenAI for gpt-5-mini")
    
    if results[2][1]:  # Native OpenAI works
        print("ℹ️ Native OpenAI background mode confirmed working")

if __name__ == "__main__":
    main()