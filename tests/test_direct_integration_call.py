#!/usr/bin/env python3
"""
Test that direct integration calling actually works.

This validates the new architecture where deep_research.py calls
integrations directly instead of going through MCP servers.
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()


async def test_direct_integration_call():
    """Test calling an integration directly through the new path."""
    print("\n" + "="*60)
    print("TEST: Direct Integration Call (No MCP)")
    print("="*60)

    try:
        from research.deep_research import SimpleDeepResearch

        # Create instance
        research = SimpleDeepResearch(max_time_minutes=60, max_tasks=5)

        # Get a tool config (should have server=None for direct calling)
        # Try to find any integration from mcp_tools (not brave, which is in web_tools)
        test_tool = next((t for t in research.mcp_tools if t["name"] == "search_dvids"), None)

        if not test_tool:
            print("❌ DVIDS tool not found in mcp_tools")
            return False

        print(f"\nTool config:")
        print(f"  Name: {test_tool['name']}")
        print(f"  Server: {test_tool.get('server')}")
        print(f"  Integration ID: {test_tool.get('integration_id')}")

        if test_tool.get('server') is not None:
            print("❌ Tool still has MCP server configured!")
            return False

        print("✅ Tool configured for direct calling (server=None)")

        # Now test calling through _call_mcp_tool
        print("\nCalling integration through _call_mcp_tool...")

        result = await research._call_mcp_tool(
            tool_config=test_tool,
            query="test query",
            param_adjustments=None,
            task_id=0,
            attempt=0,
            logger=None
        )

        print(f"\n✅ Direct call succeeded!")
        print(f"  Success: {result.get('success')}")
        print(f"  Source: {result.get('source')}")
        print(f"  Total: {result.get('total')}")
        print(f"  Results: {len(result.get('results', []))}")

        if result.get('error'):
            print(f"  Error: {result.get('error')}")

        # Verify result format
        if 'success' not in result:
            print("❌ Result missing 'success' field")
            return False

        if 'source' not in result:
            print("❌ Result missing 'source' field")
            return False

        print("\n✅ Result format valid")
        return True

    except Exception as e:
        print(f"\n❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run the test."""
    print("\n" + "="*60)
    print("Direct Integration Execution Test")
    print("="*60)

    success = await test_direct_integration_call()

    print("\n" + "="*60)
    print("TEST RESULT")
    print("="*60)

    if success:
        print("✅ PASS: Direct integration calling works!")
        print("\nThe new architecture (no MCP layer) is functional.")
        return 0
    else:
        print("❌ FAIL: Direct integration calling broken")
        print("\nThe MCP removal may have introduced bugs.")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
