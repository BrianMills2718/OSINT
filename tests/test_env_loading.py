#!/usr/bin/env python3
"""
Test 1: Verify .env file loads correctly and API keys are accessible.

This tests the most basic layer - can we even read the .env file?
"""
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

def test_env_loading():
    """Test that .env loads and contains expected keys."""
    print("=" * 60)
    print("TEST 1: Environment Variable Loading")
    print("=" * 60)

    # Load .env
    env_path = Path(__file__).parent.parent / ".env"
    print(f"\n1. Checking .env file exists: {env_path}")
    print(f"   Exists: {env_path.exists()}")

    if not env_path.exists():
        print("   ❌ FAILED: .env file not found")
        return False

    # Load environment
    print(f"\n2. Loading .env file...")
    load_dotenv(env_path)
    print(f"   ✓ load_dotenv() called")

    # Check for required keys
    required_keys = {
        "OPENAI_API_KEY": "OpenAI API",
        "BRAVE_SEARCH_API_KEY": "Brave Search API",
        "SAM_GOV_API_KEY": "SAM.gov API",
        "DVIDS_API_KEY": "DVIDS API"
    }

    print(f"\n3. Checking for required API keys:")
    all_found = True

    for key, name in required_keys.items():
        value = os.getenv(key)
        if value:
            # Show first 10 chars only for security
            masked = value[:10] + "..." if len(value) > 10 else value
            print(f"   ✅ {name:25} = {masked}")
        else:
            print(f"   ❌ {name:25} = NOT FOUND")
            all_found = False

    print("\n" + "=" * 60)
    if all_found:
        print("✅ TEST 1 PASSED: All API keys loaded successfully")
    else:
        print("❌ TEST 1 FAILED: Some API keys missing")
    print("=" * 60)

    return all_found


if __name__ == "__main__":
    success = test_env_loading()
    sys.exit(0 if success else 1)
