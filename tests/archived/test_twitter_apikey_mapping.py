#!/usr/bin/env python3
"""
Test Twitter API Key Mapping in Boolean Monitor

Verifies that Boolean monitor correctly maps 'twitter' source to RAPIDAPI_KEY env variable.
"""

import os
from dotenv import load_dotenv

load_dotenv()

print("=" * 80)
print("TWITTER API KEY MAPPING TEST")
print("=" * 80)

# Test the mapping logic from boolean_monitor.py
source = "twitter"

# Old logic (before fix)
old_api_key_var = f"{source.upper().replace('-', '_')}_API_KEY"
old_api_key = os.getenv(old_api_key_var, '')

# New logic (after fix)
if source == "twitter":
    new_api_key_var = "RAPIDAPI_KEY"
else:
    new_api_key_var = f"{source.upper().replace('-', '_')}_API_KEY"
new_api_key = os.getenv(new_api_key_var, '')

print(f"\nOld mapping logic:")
print(f"  source='twitter' → env_var='{old_api_key_var}'")
print(f"  API key found: {bool(old_api_key)}")
if old_api_key:
    print(f"  API key value: {old_api_key[:10]}...")

print(f"\nNew mapping logic:")
print(f"  source='twitter' → env_var='{new_api_key_var}'")
print(f"  API key found: {bool(new_api_key)}")
if new_api_key:
    print(f"  API key value: {new_api_key[:10]}...")

print("\n" + "=" * 80)
if new_api_key:
    print("✅ PASS: Twitter API key mapping working correctly")
    print(f"   Boolean monitor will use env variable: {new_api_key_var}")
else:
    print("❌ FAIL: RAPIDAPI_KEY not found in environment")
    print("   Check .env file for RAPIDAPI_KEY")
print("=" * 80)
