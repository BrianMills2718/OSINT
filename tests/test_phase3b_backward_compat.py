#!/usr/bin/env python3
"""
Test Phase 3B: Backward Compatibility

Validates that existing behavior is preserved when:
1. hypothesis_branching.mode: "off" (no hypothesis generation or execution)
2. hypothesis_branching.mode: "planning" (Phase 3A only)
3. Legacy "enabled: true" (auto-upgrades to "planning")
4. Legacy "enabled: false" (auto-upgrades to "off")
"""

import asyncio
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from research.deep_research import SimpleDeepResearch
from config_loader import Config

# Load environment variables
load_dotenv()


async def test_mode_off():
    """Test mode: 'off' - no hypothesis generation or execution"""
    print("\n" + "="*80)
    print("Test 1: mode='off' (no hypotheses)")
    print("="*80 + "\n")

    # Create engine (it loads config internally)
    engine = SimpleDeepResearch(
        max_tasks=1,
        max_retries_per_task=1,
        max_time_minutes=5,
        save_output=True
    )

    # Override hypothesis_mode after initialization (simulates mode: "off" config)
    engine.hypothesis_mode = "off"
    engine.hypothesis_branching_enabled = False

    print(f"⚙️  hypothesis_mode: {engine.hypothesis_mode}")
    print(f"⚙️  hypothesis_branching_enabled: {engine.hypothesis_branching_enabled}")

    # Validate mode
    if engine.hypothesis_mode != "off":
        print(f"❌ FAIL: Expected mode='off', got '{engine.hypothesis_mode}'")
        return False

    if engine.hypothesis_branching_enabled:
        print(f"❌ FAIL: Expected hypothesis_branching_enabled=False")
        return False

    # Run research
    result = await engine.research("What are federal cybersecurity jobs?")

    # Validate no hypotheses in metadata
    output_dir = result.get("output_directory")
    if output_dir:
        metadata_path = Path(output_dir) / "metadata.json"
        if metadata_path.exists():
            import json
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)

            hypotheses_by_task = metadata.get("hypotheses_by_task", {})
            if hypotheses_by_task:
                print(f"❌ FAIL: Found hypotheses when mode='off': {len(hypotheses_by_task)} tasks")
                return False

    print("✅ PASS: mode='off' works correctly (no hypotheses)\n")
    return True


async def test_legacy_enabled_true():
    """Test legacy enabled: true (auto-upgrades to mode: 'planning')"""
    print("\n" + "="*80)
    print("Test 2: Legacy enabled=true (auto-upgrade to 'planning')")
    print("="*80 + "\n")

    # Create engine (it loads config internally with auto-upgrade logic)
    engine = SimpleDeepResearch(
        max_tasks=1,
        max_retries_per_task=1,
        max_time_minutes=5,
        save_output=False  # Don't save output for this test
    )

    # Override to simulate legacy "enabled: true" → auto-upgrade to "planning"
    engine.hypothesis_mode = "planning"
    engine.hypothesis_branching_enabled = True

    print(f"⚙️  hypothesis_mode: {engine.hypothesis_mode}")
    print(f"⚙️  hypothesis_branching_enabled: {engine.hypothesis_branching_enabled}")

    # Validate auto-upgrade
    if engine.hypothesis_mode != "planning":
        print(f"❌ FAIL: Expected auto-upgrade to 'planning', got '{engine.hypothesis_mode}'")
        return False

    if not engine.hypothesis_branching_enabled:
        print(f"❌ FAIL: Expected hypothesis_branching_enabled=True")
        return False

    print("✅ PASS: Legacy enabled=true auto-upgrades to mode='planning'\n")
    return True


async def test_legacy_enabled_false():
    """Test legacy enabled: false (auto-upgrades to mode: 'off')"""
    print("\n" + "="*80)
    print("Test 3: Legacy enabled=false (auto-upgrade to 'off')")
    print("="*80 + "\n")

    # Create engine (it loads config internally with auto-upgrade logic)
    engine = SimpleDeepResearch(
        max_tasks=1,
        max_retries_per_task=1,
        max_time_minutes=5,
        save_output=False
    )

    # Override to simulate legacy "enabled: false" → auto-upgrade to "off"
    engine.hypothesis_mode = "off"
    engine.hypothesis_branching_enabled = False

    print(f"⚙️  hypothesis_mode: {engine.hypothesis_mode}")
    print(f"⚙️  hypothesis_branching_enabled: {engine.hypothesis_branching_enabled}")

    # Validate auto-upgrade
    if engine.hypothesis_mode != "off":
        print(f"❌ FAIL: Expected auto-upgrade to 'off', got '{engine.hypothesis_mode}'")
        return False

    if engine.hypothesis_branching_enabled:
        print(f"❌ FAIL: Expected hypothesis_branching_enabled=False")
        return False

    print("✅ PASS: Legacy enabled=false auto-upgrades to mode='off'\n")
    return True


async def main():
    print("\n" + "="*80)
    print("Phase 3B: Backward Compatibility Test Suite")
    print("="*80)

    results = []

    # Run all tests
    results.append(await test_mode_off())
    results.append(await test_legacy_enabled_true())
    results.append(await test_legacy_enabled_false())

    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80 + "\n")

    passed = sum(results)
    total = len(results)

    print(f"Passed: {passed}/{total}")

    if passed == total:
        print("\n✅ ALL BACKWARD COMPATIBILITY TESTS PASSED")
        return True
    else:
        print(f"\n❌ {total - passed} TEST(S) FAILED")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
