"""Test if the config import fix actually works"""
import os
import sys

# DO NOT add twitterexplorer to path - we're already IN it
# sys.path.insert(0, 'twitterexplorer')

print("Testing config import fix...")
print("-" * 40)
print(f"Current directory: {os.getcwd()}")
print(f"Python path: {sys.path[:3]}")

# Test the import
try:
    import config
    print(f"[OK] config module imported from: {config.__file__}")
    print(f"[OK] config attributes: {[a for a in dir(config) if not a.startswith('_')]}")
    if hasattr(config, 'DEFAULT_MAX_PAGES_FALLBACK'):
        print(f"[OK] DEFAULT_MAX_PAGES_FALLBACK = {config.DEFAULT_MAX_PAGES_FALLBACK}")
    else:
        print(f"[ERROR] DEFAULT_MAX_PAGES_FALLBACK not found in config!")
        print(f"       Available: {dir(config)}")
    
    import api_client
    print(f"[OK] api_client module imported")
    
    # Simulate what happens in api_client.py line 43
    test_plan = {'endpoint': 'test', 'params': {}}
    max_pages = test_plan.get('max_pages', config.DEFAULT_MAX_PAGES_FALLBACK)
    print(f"[OK] api_client can access config.DEFAULT_MAX_PAGES_FALLBACK: {max_pages}")
    
    print("\n[SUCCESS] Config issue is FIXED!")
    print("API calls should now work without the config error.")
    
except AttributeError as e:
    print(f"[ERROR] AttributeError: {e}")
    print("The config issue is NOT fixed yet.")
    
except ImportError as e:
    print(f"[ERROR] ImportError: {e}")
    print("Cannot import modules.")
    
except Exception as e:
    print(f"[ERROR] Unexpected error: {e}")
    import traceback
    traceback.print_exc()