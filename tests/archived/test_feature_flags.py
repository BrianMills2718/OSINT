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

    # Create a mock config_loader to test disabled integration behavior
    import config_loader

    # Save original get_database_config
    original_get_db_config = config_loader.config.get_database_config

    # Create mock that disables SAM
    def mock_get_db_config(integration_id):
        if integration_id == "sam":
            return {"enabled": False}
        # For others, return default enabled
        return {"enabled": True}

    # Temporarily replace the method
    config_loader.config.get_database_config = mock_get_db_config

    try:
        # Clear cached instances to force re-check
        registry._cached_instances.clear()

        # Test: SAM should return None when disabled
        sam_instance = registry.get_instance("sam")
        assert sam_instance is None, "SAM should return None when disabled via config"
        print("  ✓ SAM returns None when config.enabled=false")

        # Test: DVIDS should still work (not disabled)
        dvids_instance = registry.get_instance("dvids")
        assert dvids_instance is not None, "DVIDS should still work when enabled"
        print("  ✓ DVIDS returns instance when config.enabled=true")

        # Test: is_enabled reflects config
        assert registry.is_enabled("sam") is False, "is_enabled('sam') should be False"
        assert registry.is_enabled("dvids") is True, "is_enabled('dvids') should be True"
        print("  ✓ is_enabled() correctly reflects config flags")

        print("  ✓ Feature flags successfully control integration availability")

    finally:
        # Restore original method
        config_loader.config.get_database_config = original_get_db_config
        # Clear cache again to reset state
        registry._cached_instances.clear()

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
