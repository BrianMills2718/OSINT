#!/usr/bin/env python3
"""
Test cost tracking and gpt-5-nano support.

This script tests:
1. gpt-5-nano model support
2. Cost tracking functionality
3. Cost comparison between models
"""

import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

from llm_utils import acompletion, get_cost_summary, get_cost_breakdown, reset_cost_tracking


async def main():
    print("=" * 80)
    print("COST TRACKING TEST")
    print("=" * 80)
    print()

    # Test 1: gpt-5-nano
    print("Test 1: gpt-5-nano - Basic query")
    print("-" * 80)

    try:
        response = await acompletion(
            model="gpt-5-nano",
            messages=[
                {"role": "system", "content": "You are a helpful assistant. Be concise."},
                {"role": "user", "content": "What is 2+2? Answer in one word."}
            ]
        )

        answer = response.choices[0].message.content
        print(f"✓ gpt-5-nano responded: {answer}")

    except Exception as e:
        print(f"✗ gpt-5-nano failed: {e}")

    # Test 2: gpt-5-mini for comparison
    print("\nTest 2: gpt-5-mini - Same query")
    print("-" * 80)

    try:
        response = await acompletion(
            model="gpt-5-mini",
            messages=[
                {"role": "system", "content": "You are a helpful assistant. Be concise."},
                {"role": "user", "content": "What is 2+2? Answer in one word."}
            ]
        )

        answer = response.choices[0].message.content
        print(f"✓ gpt-5-mini responded: {answer}")

    except Exception as e:
        print(f"✗ gpt-5-mini failed: {e}")

    # Test 3: Show cost breakdown
    print("\nTest 3: Cost Breakdown")
    print("-" * 80)

    breakdown = get_cost_breakdown()

    print(f"Total cost: ${breakdown['total_cost']:.6f}")
    print(f"Total calls: {breakdown['num_calls']}")
    print()

    if breakdown['by_model']:
        print("Per-model costs:")
        for model, data in sorted(breakdown['by_model'].items()):
            avg = data['cost'] / data['calls'] if data['calls'] > 0 else 0
            print(f"  {model}: ${data['cost']:.6f} ({data['calls']} calls, ${avg:.6f}/call)")

        # Compare costs
        if 'gpt-5-nano' in breakdown['by_model'] and 'gpt-5-mini' in breakdown['by_model']:
            nano_cost = breakdown['by_model']['gpt-5-nano']['cost']
            mini_cost = breakdown['by_model']['gpt-5-mini']['cost']

            if nano_cost > 0:
                savings = ((mini_cost - nano_cost) / nano_cost) * 100
                print(f"\n  💰 Cost comparison: gpt-5-mini is {savings:.1f}% more expensive than gpt-5-nano")
    else:
        print("⚠ No cost data available (LiteLLM may not have pricing for these models yet)")

    # Test 4: Full cost summary
    print("\nTest 4: Full Cost Summary")
    print("-" * 80)
    print(get_cost_summary())

    print("\n" + "=" * 80)
    print("✅ COST TRACKING TEST COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
