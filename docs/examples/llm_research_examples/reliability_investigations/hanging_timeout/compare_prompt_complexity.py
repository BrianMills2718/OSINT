#!/usr/bin/env python3
"""
Compare prompt complexity between simple tests and actual system generation
"""
import sys
import time
import asyncio
sys.path.insert(0, '/home/brian/projects/autocoder4_cc')

async def compare_prompt_sizes():
    """Compare the prompt sizes being sent in different scenarios"""
    
    print("🔍 COMPARING PROMPT COMPLEXITY")
    print("=" * 60)
    
    from dotenv import load_dotenv
    load_dotenv('/home/brian/projects/autocoder4_cc/.env')
    
    # Test 1: Simple prompt (like my successful tests)
    print("\n🧪 Test 1: Simple prompt analysis")
    simple_system = "You are a helpful assistant."
    simple_user = "Say hello."
    simple_total = len(simple_system) + len(simple_user)
    print(f"   System prompt: {len(simple_system)} chars")
    print(f"   User prompt: {len(simple_user)} chars")
    print(f"   Total: {simple_total} chars")
    
    # Test 2: Check actual prompt used in system generation
    print("\n🧪 Test 2: System generation prompt analysis")
    try:
        from autocoder_cc.blueprint_language.llm_component_generator import LLMComponentGenerator
        
        generator = LLMComponentGenerator()
        
        # Build actual system generation prompt
        component_type = "Source"
        component_name = "test_source"
        component_description = "Test source component"
        component_config = {}
        class_name = "TestSource"
        system_context = {"test": "context"}
        blueprint = {
            "schema_version": "1.0.0",
            "system": {
                "name": "test_system",
                "components": [
                    {
                        "name": "test_source",
                        "type": "Source",
                        "description": "Test source",
                        "outputs": [{"name": "output_data", "schema": "common_object_schema"}]
                    }
                ]
            },
            "schemas": {},
            "metadata": {},
            "policy": {}
        }
        
        # Build the actual prompts used in system generation
        user_prompt = generator.context_builder.build_context_aware_prompt(
            component_type, component_name, component_description,
            component_config, class_name, system_context,
            generator.prompt_engine.build_component_prompt, blueprint
        )
        
        system_prompt = generator.prompt_engine.build_system_prompt(
            component_type, component_name
        )
        
        print(f"   System prompt: {len(system_prompt)} chars")
        print(f"   User prompt: {len(user_prompt)} chars")
        print(f"   Total: {len(system_prompt) + len(user_prompt)} chars")
        
        # Show prompt previews
        print(f"\n   System prompt preview (first 200 chars):")
        print(f"   {system_prompt[:200]}...")
        
        print(f"\n   User prompt preview (first 200 chars):")
        print(f"   {user_prompt[:200]}...")
        
        # Now test with this complex prompt
        print(f"\n🧪 Test 3: LLM call with actual system generation prompt")
        
        from autocoder_cc.llm_providers.unified_llm_provider import UnifiedLLMProvider
        from autocoder_cc.llm_providers.base_provider import LLMRequest
        
        provider = UnifiedLLMProvider({'enable_fallback': False})
        
        request = LLMRequest(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=8192,
            temperature=0.3
        )
        
        start_time = time.time()
        response = await asyncio.wait_for(provider.generate(request), timeout=60)
        duration = time.time() - start_time
        
        print(f"   ✅ Complex prompt call completed in {duration:.1f}s")
        print(f"   Response length: {len(response.content)} chars")
        
        # Compare durations
        print(f"\n📊 DURATION COMPARISON:")
        print(f"   Simple prompt: ~1-6 seconds")  
        print(f"   Complex prompt: {duration:.1f} seconds")
        
        if duration > 20:
            print(f"   🎯 FOUND THE ISSUE: Complex prompts take {duration:.1f}s")
            print(f"   When 2+ components generated sequentially: {duration:.1f}s × 2+ = 40+ seconds")
            print(f"   This explains the 30-45 second hanging!")
        else:
            print(f"   🤔 Complex prompt is still fast - issue elsewhere")
            
    except Exception as e:
        print(f"   ❌ Error testing complex prompt: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(compare_prompt_sizes())