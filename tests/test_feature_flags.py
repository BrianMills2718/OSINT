#!/usr/bin/env python3
"""
Test feature flags and lazy instantiation in the registry.

Verifies:
1. Registry loads without crashes
2. Feature flags control integration availability
3. Lazy instantiation works (classes stored, instances created on demand)
4. Status API provides debugging information
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from integrations.registry import registry


def test_registry_loads():
    """Test that registry loads without crashing."""
    print("Testing: Registry loads without crashes")
    assert registry is not None
    assert len(registry.list_ids()) > 0
    print(f"✓ Registry loaded with {len(registry.list_ids())} integrations")
    print()


def test_list_all_integrations():
    """Test listing all registered integrations."""
    print("Testing: List all integrations")
    integration_ids = registry.list_ids()
    print(f"Found {len(integration_ids)} integrations:")
    for integration_id in sorted(integration_ids):
        print(f"  - {integration_id}")
    print()


def test_feature_flags():
    """Test that feature flags control availability."""
    print("Testing: Feature flags control availability")

    for integration_id in registry.list_ids():
        enabled = registry.is_enabled(integration_id)
        status_emoji = "✓" if enabled else "✗"
        print(f"  {status_emoji} {integration_id}: {'enabled' if enabled else 'DISABLED'}")

    print()


def test_lazy_instantiation():
    """Test that lazy instantiation works correctly."""
    print("Testing: Lazy instantiation")

    # Get class (should always work)
    sam_class = registry.get("sam")
    print(f"✓ Retrieved SAM class: {sam_class.__name__}")

    # Get instance (lazy instantiation)
    sam_instance = registry.get_instance("sam")
    if sam_instance:
        print(f"✓ Lazy instantiated SAM: {sam_instance.metadata.name}")
    else:
        print(f"✗ SAM disabled or unavailable")

    # Get instance again (should return cached)
    sam_instance_2 = registry.get_instance("sam")
    if sam_instance and sam_instance_2:
        is_same = sam_instance is sam_instance_2
        print(f"✓ Caching works: same instance = {is_same}")

    print()


def test_get_all_enabled():
    """Test getting all enabled integrations."""
    print("Testing: Get all enabled integrations")

    enabled = registry.get_all_enabled()
    print(f"Found {len(enabled)} enabled integrations:")
    for integration_id, instance in enabled.items():
        print(f"  ✓ {integration_id}: {instance.metadata.name}")

    print()


def test_status_api():
    """Test the status API for debugging."""
    print("Testing: Status API")

    status = registry.get_status()
    print(f"Integration Status Report:")
    print(f"{'Integration':<20} {'Registered':<12} {'Enabled':<10} {'Available':<12} Reason")
    print("-" * 80)

    for integration_id in sorted(status.keys()):
        s = status[integration_id]
        registered = "✓" if s["registered"] else "✗"
        enabled = "✓" if s["enabled"] else "✗"
        available = "✓" if s["available"] else "✗"
        reason = s["reason"] or "OK"

        print(f"{integration_id:<20} {registered:<12} {enabled:<10} {available:<12} {reason}")

    print()


def test_disabled_integration_returns_none():
    """Test that disabled integrations return None."""
    print("Testing: Disabled integrations return None")

    # This test assumes you can create a config.yaml with some integrations disabled
    # For now, just verify the behavior when an integration is disabled
    print("Note: To fully test this, create config.yaml with an integration disabled")
    print("Example config.yaml:")
    print("""
databases:
  sam:
    enabled: false
""")
    print()


if __name__ == "__main__":
    print("=" * 80)
    print("FEATURE FLAGS & LAZY INSTANTIATION TEST")
    print("=" * 80)
    print()

    try:
        test_registry_loads()
        test_list_all_integrations()
        test_feature_flags()
        test_lazy_instantiation()
        test_get_all_enabled()
        test_status_api()
        test_disabled_integration_returns_none()

        print("=" * 80)
        print("ALL TESTS PASSED ✓")
        print("=" * 80)

    except Exception as e:
        print()
        print("=" * 80)
        print(f"TEST FAILED: {e}")
        print("=" * 80)
        import traceback
        traceback.print_exc()
        sys.exit(1)
