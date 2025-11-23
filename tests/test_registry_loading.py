#!/usr/bin/env python3
"""
Quick test to verify registry-based tool loading works.

Tests:
1. deep_research.py imports without errors
2. Tool loading from registry succeeds
3. All expected sources are loaded
4. Mapping dictionaries are populated
5. Both MCP and direct integration paths work
"""

import sys
import os
import asyncio

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()


async def test_import():
    """Test 1: Import deep_research without errors."""
    print("\n" + "="*60)
    print("TEST 1: Import deep_research.py")
    print("="*60)

    try:
        from research.deep_research import SimpleDeepResearch
        print("✅ Import successful")
        return True
    except Exception as e:
        print(f"❌ Import failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_tool_loading():
    """Test 2: Tool loading from registry."""
    print("\n" + "="*60)
    print("TEST 2: Tool Loading from Registry")
    print("="*60)

    try:
        from research.deep_research import SimpleDeepResearch

        # Create instance (triggers tool loading)
        research = SimpleDeepResearch(
            max_time_minutes=60,
            max_tasks=5
        )

        print(f"✅ Tool loading successful")
        print(f"   Integrations loaded: {len(research.integrations)}")
        print(f"   MCP tools: {len(research.mcp_tools)}")
        print(f"   Web tools: {len(research.web_tools)}")
        print(f"   Display name mappings: {len(research.tool_name_to_display)}")

        return True
    except Exception as e:
        print(f"❌ Tool loading failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_source_coverage():
    """Test 3: Verify all expected sources are loaded."""
    print("\n" + "="*60)
    print("TEST 3: Source Coverage")
    print("="*60)

    try:
        from research.deep_research import SimpleDeepResearch

        research = SimpleDeepResearch(
            max_time_minutes=60,
            max_tasks=5
        )

        # Expected sources (from registry)
        expected_government = ["sam", "dvids", "usajobs", "clearancejobs", "fbi_vault",
                             "federal_register", "congress", "sec_edgar", "fec", "usaspending"]
        expected_social = ["twitter", "reddit", "discord", "brave_search"]
        expected_other = ["courtlistener", "icij_offshore_leaks", "propublica"]

        all_expected = expected_government + expected_social + expected_other

        loaded = list(research.integrations.keys())

        print(f"\nLoaded sources ({len(loaded)}):")
        for source_id in sorted(loaded):
            integration = research.integrations[source_id]
            tool_name = f"search_{source_id}"
            display_name = research.tool_name_to_display.get(tool_name, "???")
            print(f"  ✅ {display_name} ({source_id})")

        # Check for missing sources
        missing = set(all_expected) - set(loaded)
        if missing:
            print(f"\n⚠️  Missing sources: {missing}")
        else:
            print(f"\n✅ All expected sources loaded!")

        # Check for NEW sources we didn't expect (good!)
        extra = set(loaded) - set(all_expected)
        if extra:
            print(f"\n🎁 Additional sources loaded: {extra}")

        return len(missing) == 0

    except Exception as e:
        print(f"❌ Source coverage test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_mappings():
    """Test 4: Verify mapping dictionaries are populated."""
    print("\n" + "="*60)
    print("TEST 4: Mapping Dictionaries")
    print("="*60)

    try:
        from research.deep_research import SimpleDeepResearch

        research = SimpleDeepResearch(
            max_time_minutes=60,
            max_tasks=5
        )

        # Check bidirectional mappings
        print("\nChecking bidirectional mappings...")
        for tool_name, display_name in research.tool_name_to_display.items():
            reverse = research.display_to_tool_map.get(display_name)
            if reverse != tool_name:
                print(f"❌ Mapping mismatch: {tool_name} -> {display_name} -> {reverse}")
                return False

            # Check description exists
            if tool_name not in research.tool_descriptions:
                print(f"❌ Missing description for: {tool_name}")
                return False

        print(f"✅ All mappings valid ({len(research.tool_name_to_display)} sources)")

        # Sample some mappings
        print("\nSample mappings:")
        samples = list(research.tool_name_to_display.items())[:5]
        for tool_name, display_name in samples:
            desc = research.tool_descriptions[tool_name][:60] + "..."
            print(f"  {tool_name} -> '{display_name}'")
            print(f"    {desc}")

        return True

    except Exception as e:
        print(f"❌ Mapping test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_integration_types():
    """Test 5: Verify all integrations use direct calls (no MCP)."""
    print("\n" + "="*60)
    print("TEST 5: Integration Architecture (All Direct)")
    print("="*60)

    try:
        from research.deep_research import SimpleDeepResearch

        research = SimpleDeepResearch(
            max_time_minutes=60,
            max_tasks=5
        )

        # Verify ALL tools use direct calls (server=None)
        tools_with_mcp = [t for t in research.mcp_tools if t.get("server") is not None]
        direct_tools = [t for t in research.mcp_tools if t.get("server") is None]

        if tools_with_mcp:
            print(f"❌ Found {len(tools_with_mcp)} tools still using MCP servers:")
            for tool in tools_with_mcp:
                display_name = research.tool_name_to_display.get(tool["name"], "???")
                print(f"  📡 {display_name} ({tool['name']})")
            return False

        print(f"\n✅ All integrations use direct calls (no MCP layer)")
        print(f"   • {len(direct_tools)} integrations call directly via registry")
        print(f"   • {len(research.web_tools)} categorized as web tools")
        print(f"   • 0 using MCP servers (MCP exists only for external tool access)")

        print(f"\nSample direct integration tools:")
        for tool in direct_tools[:5]:  # Sample
            display_name = research.tool_name_to_display.get(tool["name"], "???")
            integration_id = tool.get("integration_id", "???")
            print(f"  🔗 {display_name} ({integration_id})")

        return True

    except Exception as e:
        print(f"❌ Integration type test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("Registry-Based Tool Loading Test Suite")
    print("="*60)

    tests = [
        ("Import", test_import),
        ("Tool Loading", test_tool_loading),
        ("Source Coverage", test_source_coverage),
        ("Mapping Dictionaries", test_mappings),
        ("Integration Types", test_integration_types),
    ]

    results = {}
    for test_name, test_func in tests:
        try:
            success = await test_func()
            results[test_name] = success
        except Exception as e:
            print(f"\n❌ TEST FAILED WITH EXCEPTION: {e}")
            import traceback
            traceback.print_exc()
            results[test_name] = False

    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)

    for test_name, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {test_name}")

    passed = sum(results.values())
    total = len(results)
    print(f"\nResults: {passed}/{total} tests passed")

    if passed == total:
        print("\n✅ ALL TESTS PASSED - Registry loading working correctly!")
        return 0
    else:
        print(f"\n❌ {total - passed} TESTS FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
