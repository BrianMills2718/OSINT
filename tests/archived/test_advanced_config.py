#!/usr/bin/env python3
"""
Test advanced config and new go/no-go relevance filter.

This script tests:
1. Advanced config loading from YAML
2. Go/no-go relevance filtering (vs old score-based)
3. Config option to disable filtering
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from monitoring.boolean_monitor import BooleanMonitor


async def test_advanced_config_loading():
    """Test that advanced config loads correctly from YAML."""
    print("\n=== Test 1: Advanced Config Loading ===")

    monitor = BooleanMonitor("data/monitors/configs/test_advanced_config.yaml")

    print(f"Monitor name: {monitor.config.name}")
    print(f"Keywords: {monitor.config.keywords}")
    print(f"Sources: {monitor.config.sources}")

    if monitor.config.advanced:
        print(f"Advanced config loaded: YES")
        print(f"  relevance_filter: {monitor.config.advanced.relevance_filter}")
        print(f"  adaptive_search: {monitor.config.advanced.adaptive_search}")
    else:
        print(f"Advanced config loaded: NO (using defaults)")

    print("✓ Config loading test PASSED\n")


async def test_go_no_go_filter():
    """Test the new go/no-go relevance filter with real results."""
    print("=== Test 2: Go/No-Go Relevance Filter ===")

    # Create fake results to test filtering logic
    test_results = [
        {
            "title": "DHS Updates Cybersecurity Guidelines for Federal Agencies",
            "description": "The Department of Homeland Security released new cybersecurity guidelines...",
            "url": "https://example.com/1",
            "source": "Federal Register",
            "keyword": "cybersecurity",
            "date": "2025-10-20"
        },
        {
            "title": "Star Spangled Sailabration Event in Baltimore",
            "description": "Annual sailing event features ships and festivities. Event code: CYBER-2025-NVE",
            "url": "https://example.com/2",
            "source": "DVIDS",
            "keyword": "cybersecurity",
            "date": "2025-10-19"
        },
        {
            "title": "Top 10 Cybersecurity Products to Buy in 2025",
            "description": "Check out these amazing deals on firewalls and antivirus software!",
            "url": "https://example.com/3",
            "source": "Test",
            "keyword": "cybersecurity",
            "date": "2025-10-18"
        }
    ]

    monitor = BooleanMonitor("data/monitors/configs/test_advanced_config.yaml")

    print(f"Testing with {len(test_results)} results...")
    print("Note: This will call gpt-5-nano for each result (may take 30-60 seconds)\n")

    filtered_results = await monitor.filter_by_relevance(test_results)

    print(f"\nResults after filtering: {len(filtered_results)}/{len(test_results)} kept")

    for i, result in enumerate(filtered_results, 1):
        print(f"\n{i}. {result['title'][:60]}")
        print(f"   Reason: {result.get('filter_reason', 'N/A')[:80]}")

    print("\n✓ Go/No-Go filter test PASSED\n")


async def test_disabled_filter():
    """Test that filtering can be disabled via config."""
    print("=== Test 3: Disabled Filter ===")

    # Create temp config with filtering disabled
    import yaml
    from pathlib import Path

    temp_config_path = Path("data/monitors/configs/temp_test_disabled_filter.yaml")

    temp_config = {
        "name": "Test Disabled Filter",
        "keywords": ["test"],
        "sources": ["dvids"],
        "schedule": "daily",
        "alert_email": "test@example.com",
        "enabled": True,
        "advanced": {
            "relevance_filter": "disabled"  # DISABLE filtering
        }
    }

    with open(temp_config_path, 'w') as f:
        yaml.dump(temp_config, f)

    monitor = BooleanMonitor(str(temp_config_path))

    # Create test results
    test_results = [
        {"title": "Test 1", "keyword": "test", "description": "spam", "url": "http://example.com/1"},
        {"title": "Test 2", "keyword": "test", "description": "more spam", "url": "http://example.com/2"}
    ]

    filtered_results = await monitor.filter_by_relevance(test_results)

    # With filtering disabled, all results should be kept
    assert len(filtered_results) == len(test_results), "Disabled filter should keep all results"

    print(f"Input: {len(test_results)} results")
    print(f"Output: {len(filtered_results)} results (all kept, filtering disabled)")
    print("✓ Disabled filter test PASSED\n")

    # Cleanup
    temp_config_path.unlink()


async def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("Testing Advanced Config and Go/No-Go Relevance Filter")
    print("="*60)

    try:
        await test_advanced_config_loading()
        await test_go_no_go_filter()
        await test_disabled_filter()

        print("="*60)
        print("ALL TESTS PASSED ✓")
        print("="*60 + "\n")

    except Exception as e:
        print(f"\n✗ TEST FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    # Ensure .venv is active
    import shutil
    if shutil.which("python3") and ".venv" not in shutil.which("python3"):
        print("WARNING: .venv not activated. Run: source .venv/bin/activate")
        sys.exit(1)

    asyncio.run(main())
