#!/usr/bin/env python3
"""
Test Structured Output Hang - Check if complex Pydantic schemas cause LLM timeouts
"""
import sys
import time
import asyncio
sys.path.insert(0, '/home/brian/projects/autocoder4_cc')

async def test_simple_vs_structured_calls():
    """Compare simple LLM calls vs structured output calls"""
    
    print("🔍 TESTING SIMPLE VS STRUCTURED LLM CALLS")
    print("=" * 60)
    
    from dotenv import load_dotenv
    load_dotenv('/home/brian/projects/autocoder4_cc/.env')
    
    from autocoder_cc.llm_providers.unified_llm_provider import UnifiedLLMProvider
    from autocoder_cc.llm_providers.base_provider import LLMRequest
    
    provider = UnifiedLLMProvider({'enable_fallback': False})
    
    # Test 1: Simple text call (should work)
    print("\n🧪 Test 1: Simple text call")
    try:
        start_time = time.time()
        simple_request = LLMRequest(
            system_prompt="You are a helpful assistant.",
            user_prompt="Say 'Hello' and nothing else.",
            max_tokens=50,
            temperature=0.0
        )
        
        response = await asyncio.wait_for(provider.generate(simple_request), timeout=30)
        duration = time.time() - start_time
        
        print(f"✅ Simple call succeeded in {duration:.1f}s: {response.content}")
        
    except Exception as e:
        duration = time.time() - start_time
        print(f"❌ Simple call failed in {duration:.1f}s: {e}")
        
    # Test 2: Structured output with simple schema
    print("\n🧪 Test 2: Structured output with simple schema")
    try:
        from pydantic import BaseModel
        from typing import List
        
        class SimpleResponse(BaseModel):
            message: str
            
        start_time = time.time()
        structured_request = LLMRequest(
            system_prompt="You are a helpful assistant.",
            user_prompt="Say 'Hello structured' in the required format.",
            max_tokens=50,
            temperature=0.0,
            json_mode=True,
            response_schema=SimpleResponse
        )
        
        response = await asyncio.wait_for(provider.generate(structured_request), timeout=30)
        duration = time.time() - start_time
        
        print(f"✅ Simple structured call succeeded in {duration:.1f}s: {response.content}")
        
    except Exception as e:
        duration = time.time() - start_time
        print(f"❌ Simple structured call failed in {duration:.1f}s: {e}")
        
    # Test 3: Complex structured output (like component generation)
    print("\n🧪 Test 3: Complex structured output (component-like)")
    try:
        from pydantic import BaseModel, Field
        from typing import List, Dict, Any, Optional
        
        class Port(BaseModel):
            name: str
            type: str
            description: Optional[str] = None
            
        class ComponentMetadata(BaseModel):
            version: str
            author: Optional[str] = None
            tags: List[str] = []
            
        class ComplexComponentResponse(BaseModel):
            component_code: str = Field(description="Complete Python code for the component")
            class_name: str = Field(description="Name of the generated class")
            inputs: List[Port] = Field(description="Input port definitions")
            outputs: List[Port] = Field(description="Output port definitions") 
            dependencies: List[str] = Field(description="Required Python packages")
            metadata: ComponentMetadata = Field(description="Component metadata")
            validation_results: Dict[str, Any] = Field(description="Validation status")
            
        start_time = time.time()
        complex_request = LLMRequest(
            system_prompt="You are a Python code generator. Generate a simple Python class with the required schema.",
            user_prompt="Generate a simple Python class called HelloWorld with a method that returns 'Hello World'.",
            max_tokens=2000,
            temperature=0.0,
            json_mode=True,
            response_schema=ComplexComponentResponse
        )
        
        response = await asyncio.wait_for(provider.generate(complex_request), timeout=45)
        duration = time.time() - start_time
        
        print(f"✅ Complex structured call succeeded in {duration:.1f}s")
        print(f"   Response length: {len(response.content)} chars")
        
    except asyncio.TimeoutError:
        duration = time.time() - start_time
        print(f"⏰ Complex structured call TIMED OUT after {duration:.1f}s")
        return "COMPLEX_TIMEOUT"
        
    except Exception as e:
        duration = time.time() - start_time
        print(f"❌ Complex structured call failed in {duration:.1f}s: {e}")
        return "COMPLEX_ERROR"
        
    # Test 4: The actual component generation schema
    print("\n🧪 Test 4: Actual component generation schema")
    try:
        # Import the actual schema used in component generation
        from autocoder_cc.blueprint_language.llm_component_generator import GeneratedComponent
        
        start_time = time.time()
        actual_request = LLMRequest(
            system_prompt="You are a component generator. Generate a simple source component.",
            user_prompt="Generate a simple data source component that yields numbers.",
            max_tokens=4000,
            temperature=0.3,
            json_mode=True,
            response_schema=GeneratedComponent
        )
        
        response = await asyncio.wait_for(provider.generate(actual_request), timeout=60)
        duration = time.time() - start_time
        
        print(f"✅ Actual schema call succeeded in {duration:.1f}s")
        print(f"   Response length: {len(response.content)} chars")
        
    except asyncio.TimeoutError:
        duration = time.time() - start_time
        print(f"⏰ Actual schema call TIMED OUT after {duration:.1f}s")
        return "ACTUAL_TIMEOUT"
        
    except Exception as e:
        duration = time.time() - start_time
        print(f"❌ Actual schema call failed in {duration:.1f}s: {e}")
        return "ACTUAL_ERROR"
        
    return "ALL_SUCCESS"

async def test_schema_complexity_hypothesis():
    """Test if schema complexity causes the hanging"""
    
    print("\n🎯 TESTING SCHEMA COMPLEXITY HYPOTHESIS")
    print("=" * 60)
    
    result = await test_simple_vs_structured_calls()
    
    print(f"\n📊 RESULT: {result}")
    
    if result in ["COMPLEX_TIMEOUT", "ACTUAL_TIMEOUT"]:
        print("🎯 HYPOTHESIS CONFIRMED: Complex schemas cause LLM timeouts")
        print("   - Simple calls work")
        print("   - Complex structured output hangs")
        print("   - Solution: Simplify schemas or use different approach")
    elif result == "ALL_SUCCESS":
        print("🤔 HYPOTHESIS NOT CONFIRMED: All schema types work")
        print("   - Issue might be elsewhere")
    else:
        print("❓ HYPOTHESIS UNCLEAR: Mixed results need investigation")
        
    return result

if __name__ == "__main__":
    result = asyncio.run(test_schema_complexity_hypothesis())
    
    print(f"\n🎯 FINAL VERDICT:")
    if result in ["COMPLEX_TIMEOUT", "ACTUAL_TIMEOUT"]:
        print("✅ CONFIRMED: Structured output schema complexity causes hanging")
    else:
        print("❌ NOT CONFIRMED: Schema complexity is not the issue")
        
    exit(0 if result == "ALL_SUCCESS" else 1)