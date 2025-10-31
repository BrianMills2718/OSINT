#!/usr/bin/env python3
"""
Controlled test to verify if async wrapper actually causes slowdown
Run the SAME prompt multiple times with both methods to compare
"""

import os
import time
import litellm
import asyncio
import statistics
from dotenv import load_dotenv

load_dotenv()

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

def test_direct_call(prompt, model="gpt-5-mini-2025-08-07"):
    """Test direct litellm.responses() call"""
    start_time = time.time()
    
    response = litellm.responses(
        model=model,
        input=prompt,
        text={"format": {"type": "text"}},
        timeout=300
    )
    
    duration = time.time() - start_time
    content = extract_content(response)
    
    return duration, len(content)

async def test_async_wrapper(prompt, model="gpt-5-mini-2025-08-07"):
    """Test with async executor wrapper (like AutoCoder)"""
    start_time = time.time()
    
    response = await asyncio.get_event_loop().run_in_executor(
        None,
        lambda: litellm.responses(
            model=model,
            input=prompt,
            text={"format": {"type": "text"}},
            timeout=300
        )
    )
    
    duration = time.time() - start_time
    content = extract_content(response)
    
    return duration, len(content)

async def run_async_test(prompt, model):
    """Helper to run async test"""
    return await test_async_wrapper(prompt, model)

def main():
    """Run controlled comparison test"""
    print("🔬 CONTROLLED ASYNC WRAPPER COMPARISON TEST")
    print("="*60)
    
    # Use consistent prompt for all tests
    test_prompt = """System: You are a Python expert.

User: Write a Python class called DataProcessor with these exact methods:
1. __init__(self, config)
2. process_data(self, data)
3. validate_input(self, data)
4. handle_error(self, error)
5. get_stats(self)

Each method should have 3-5 lines of implementation. Keep it simple and consistent."""

    print(f"📝 Test prompt length: {len(test_prompt)} chars")
    print(f"🔄 Running 3 iterations of each method...")
    print()
    
    # Test configurations
    num_iterations = 3
    direct_times = []
    async_times = []
    
    # Run direct calls
    print("📊 DIRECT CALLS (no async wrapper):")
    print("-" * 40)
    for i in range(num_iterations):
        print(f"  Run #{i+1}: ", end="", flush=True)
        try:
            duration, response_len = test_direct_call(test_prompt)
            direct_times.append(duration)
            print(f"{duration:.2f}s (response: {response_len} chars)")
        except Exception as e:
            print(f"Failed: {e}")
    
    print()
    
    # Run async wrapped calls
    print("📊 ASYNC WRAPPED CALLS (AutoCoder style):")
    print("-" * 40)
    for i in range(num_iterations):
        print(f"  Run #{i+1}: ", end="", flush=True)
        try:
            duration, response_len = asyncio.run(run_async_test(test_prompt, "gpt-5-mini-2025-08-07"))
            async_times.append(duration)
            print(f"{duration:.2f}s (response: {response_len} chars)")
        except Exception as e:
            print(f"Failed: {e}")
    
    print()
    print("="*60)
    print("📈 STATISTICAL ANALYSIS:")
    print("="*60)
    
    if direct_times:
        print("\n🔵 Direct Calls:")
        print(f"  Min:    {min(direct_times):.2f}s")
        print(f"  Max:    {max(direct_times):.2f}s")
        print(f"  Mean:   {statistics.mean(direct_times):.2f}s")
        if len(direct_times) > 1:
            print(f"  StdDev: {statistics.stdev(direct_times):.2f}s")
    
    if async_times:
        print("\n🟡 Async Wrapped:")
        print(f"  Min:    {min(async_times):.2f}s")
        print(f"  Max:    {max(async_times):.2f}s")
        print(f"  Mean:   {statistics.mean(async_times):.2f}s")
        if len(async_times) > 1:
            print(f"  StdDev: {statistics.stdev(async_times):.2f}s")
    
    if direct_times and async_times:
        mean_direct = statistics.mean(direct_times)
        mean_async = statistics.mean(async_times)
        
        print("\n📊 COMPARISON:")
        print(f"  Direct mean:   {mean_direct:.2f}s")
        print(f"  Async mean:    {mean_async:.2f}s")
        print(f"  Difference:    {mean_async - mean_direct:.2f}s")
        print(f"  Ratio:         {mean_async/mean_direct:.2f}x")
        
        # Statistical significance check
        if len(direct_times) > 1 and len(async_times) > 1:
            # Simple check: do the ranges overlap?
            direct_range = (min(direct_times), max(direct_times))
            async_range = (min(async_times), max(async_times))
            
            if direct_range[1] < async_range[0]:
                print("\n⚠️ SIGNIFICANT DIFFERENCE: Async is consistently slower")
            elif async_range[1] < direct_range[0]:
                print("\n⚠️ SIGNIFICANT DIFFERENCE: Direct is consistently slower")
            else:
                print("\n✅ NO SIGNIFICANT DIFFERENCE: Ranges overlap, likely natural variance")
    
    print("\n" + "="*60)
    print("🎯 CONCLUSION:")
    print("="*60)
    
    if not (direct_times and async_times):
        print("❌ Insufficient data for conclusion")
    elif mean_async / mean_direct > 1.5:
        print("🔴 Async wrapper appears to cause significant slowdown")
        print("   Recommendation: Remove async wrapper or investigate cause")
    elif mean_async / mean_direct > 1.1:
        print("🟡 Async wrapper adds minor overhead")
        print("   Recommendation: Acceptable overhead, increase timeout")
    else:
        print("🟢 No significant async wrapper overhead detected")
        print("   Recommendation: Natural API variance, just increase timeout")

if __name__ == "__main__":
    main()