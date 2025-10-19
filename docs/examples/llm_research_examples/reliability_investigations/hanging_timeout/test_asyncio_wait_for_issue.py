#!/usr/bin/env python3
"""
Test if asyncio.wait_for timeout is working in system generation context
"""
import sys
import time
import asyncio
import os
sys.path.insert(0, '/home/brian/projects/autocoder4_cc')

async def test_asyncio_timeout_in_system_context():
    """Test if asyncio.wait_for works properly in system generation context"""
    
    print("🔍 TESTING ASYNCIO.WAIT_FOR TIMEOUT IN SYSTEM CONTEXT")
    print("=" * 60)
    
    from dotenv import load_dotenv
    load_dotenv('/home/brian/projects/autocoder4_cc/.env')
    
    # First, test simple asyncio.wait_for
    print("\n🧪 Test 1: Simple asyncio.wait_for with fast operation")
    try:
        async def fast_operation():
            await asyncio.sleep(1)
            return "fast result"
            
        start_time = time.time()
        result = await asyncio.wait_for(fast_operation(), timeout=5)
        duration = time.time() - start_time
        
        print(f"✅ Fast operation completed in {duration:.1f}s: {result}")
        
    except Exception as e:
        duration = time.time() - start_time
        print(f"❌ Fast operation failed in {duration:.1f}s: {e}")
        
    # Test 2: asyncio.wait_for with hanging operation
    print("\n🧪 Test 2: asyncio.wait_for with hanging operation")
    try:
        async def hanging_operation():
            # Simulate the hanging LLM call
            await asyncio.sleep(300)  # 5 minutes
            return "hanging result"
            
        start_time = time.time()
        result = await asyncio.wait_for(hanging_operation(), timeout=10)
        duration = time.time() - start_time
        
        print(f"❌ Hanging operation should have timed out but didn't: {result}")
        
    except asyncio.TimeoutError:
        duration = time.time() - start_time
        print(f"✅ Hanging operation timed out correctly after {duration:.1f}s")
        
    except Exception as e:
        duration = time.time() - start_time
        print(f"❌ Hanging operation failed unexpectedly in {duration:.1f}s: {e}")
        
    # Test 3: Actual LLM call with timeout in isolation
    print("\n🧪 Test 3: Actual LLM call with short timeout")
    try:
        from autocoder_cc.llm_providers.unified_llm_provider import UnifiedLLMProvider
        from autocoder_cc.llm_providers.base_provider import LLMRequest
        
        provider = UnifiedLLMProvider({'enable_fallback': False})
        
        request = LLMRequest(
            system_prompt="You are a helpful assistant.",
            user_prompt="Count to 100 slowly, taking about 60 seconds.",
            max_tokens=1000,
            temperature=0.0
        )
        
        start_time = time.time()
        # Test with aggressive timeout
        result = await asyncio.wait_for(provider.generate(request), timeout=15)
        duration = time.time() - start_time
        
        print(f"❌ LLM call should have timed out but didn't in {duration:.1f}s")
        
    except asyncio.TimeoutError:
        duration = time.time() - start_time
        print(f"✅ LLM call timed out correctly after {duration:.1f}s")
        
    except Exception as e:
        duration = time.time() - start_time
        print(f"❌ LLM call failed unexpectedly in {duration:.1f}s: {e}")
        
    # Test 4: System generation context setup + LLM call
    print("\n🧪 Test 4: LLM call within system generation context")
    try:
        # Set up system generation context
        from autocoder_cc.blueprint_language.natural_language_to_blueprint import NaturalLanguageToPydanticTranslator
        from autocoder_cc.blueprint_language.healing_integration import SystemGenerator
        from pathlib import Path
        
        translator = NaturalLanguageToPydanticTranslator()
        generator = SystemGenerator(Path("/tmp/timeout_test"), skip_deployment=True)
        
        # Now make LLM call in this context with timeout
        provider = UnifiedLLMProvider({'enable_fallback': False})
        
        request = LLMRequest(
            system_prompt="You are a helpful assistant.",
            user_prompt="Say hello.",
            max_tokens=100,
            temperature=0.0
        )
        
        start_time = time.time()
        # Use same timeout as system generation
        generation_timeout = float(os.getenv('COMPONENT_GENERATION_TIMEOUT', '20.0'))  # 20 second test
        result = await asyncio.wait_for(provider.generate(request), timeout=generation_timeout)
        duration = time.time() - start_time
        
        print(f"✅ System context LLM call succeeded in {duration:.1f}s")
        
    except asyncio.TimeoutError:
        duration = time.time() - start_time
        print(f"⏰ System context LLM call timed out after {duration:.1f}s")
        
    except Exception as e:
        duration = time.time() - start_time
        print(f"❌ System context LLM call failed in {duration:.1f}s: {e}")

if __name__ == "__main__":
    asyncio.run(test_asyncio_timeout_in_system_context())