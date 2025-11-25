#!/usr/bin/env python3
"""
Quick smoke test for all integrations.

Validates that all integrations:
- Can be imported without errors
- Can be instantiated
- Have valid metadata
- Are properly registered

This is much faster than running full integration tests.
Use this for quick regression checks.

Usage:
    python3 tests/test_smoke_integrations.py
"""

import sys
sys.path.insert(0, '/home/brian/sam_gov')

from integrations.registry import registry


def main():
    print("=" * 80)
    print("SMOKE TEST - Integration Registry")
    print("=" * 80)
    print()

    enabled = registry.list_enabled_ids()
    print(f"Testing {len(enabled)} enabled integrations...")
    print()

    failed = []
    passed = []

    for integration_id in sorted(enabled):
        try:
            # Test 1: Get instance (tests import and instantiation)
            instance = registry.get_instance(integration_id)

            if instance is None:
                failed.append((integration_id, "get_instance() returned None"))
                print(f"❌ {integration_id}: Failed to instantiate")
                continue

            # Test 2: Metadata is valid
            metadata = instance.metadata

            if not metadata.name:
                failed.append((integration_id, "Missing metadata.name"))
                print(f"❌ {integration_id}: Invalid metadata (no name)")
                continue

            if not metadata.id:
                failed.append((integration_id, "Missing metadata.id"))
                print(f"❌ {integration_id}: Invalid metadata (no id)")
                continue

            if metadata.id != integration_id:
                failed.append((integration_id, f"Metadata ID mismatch: {metadata.id} != {integration_id}"))
                print(f"❌ {integration_id}: Metadata ID mismatch ({metadata.id})")
                continue

            # Test 3: Has required methods
            if not hasattr(instance, 'is_relevant'):
                failed.append((integration_id, "Missing is_relevant() method"))
                print(f"❌ {integration_id}: Missing is_relevant() method")
                continue

            if not hasattr(instance, 'generate_query'):
                failed.append((integration_id, "Missing generate_query() method"))
                print(f"❌ {integration_id}: Missing generate_query() method")
                continue

            if not hasattr(instance, 'execute_search'):
                failed.append((integration_id, "Missing execute_search() method"))
                print(f"❌ {integration_id}: Missing execute_search() method")
                continue

            # All checks passed
            passed.append(integration_id)
            print(f"✅ {metadata.name:25s} ({integration_id})")

        except Exception as e:
            failed.append((integration_id, str(e)))
            print(f"❌ {integration_id}: Exception - {str(e)}")

    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Passed: {len(passed)}/{len(enabled)}")
    print(f"Failed: {len(failed)}/{len(enabled)}")
    print()

    if failed:
        print("Failed Integrations:")
        for integration_id, reason in failed:
            print(f"  ❌ {integration_id}: {reason}")
        print()
        return 1
    else:
        print("✅ ALL INTEGRATIONS PASSED SMOKE TEST")
        print()
        return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
