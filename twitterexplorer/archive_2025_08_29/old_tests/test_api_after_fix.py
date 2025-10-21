"""Test real Twitter API calls after config fix"""
import os
import sys

# We need to be in the twitterexplorer directory for imports to work
if os.path.basename(os.getcwd()) != 'twitterexplorer':
    os.chdir('twitterexplorer')

def test_real_api_call():
    """Test an actual API call to Twitter"""
    print("=" * 60)
    print(" TESTING REAL TWITTER API CALL AFTER CONFIG FIX")
    print("=" * 60)
    
    try:
        # Import modules
        import api_client
        import twitter_config as config
        from dotenv import load_dotenv
        
        print("[OK] Modules imported successfully")
        print(f"[OK] DEFAULT_MAX_PAGES_FALLBACK = {config.DEFAULT_MAX_PAGES_FALLBACK}")
        
        # Get RapidAPI key
        load_dotenv()
        
        # Try multiple sources for API key
        rapidapi_key = None
        
        # Try .streamlit/secrets.toml first
        secrets_path = os.path.join('twitterexplorer', '.streamlit', 'secrets.toml')
        if os.path.exists(secrets_path):
            try:
                import toml
                secrets = toml.load(secrets_path)
                rapidapi_key = secrets.get('RAPIDAPI_KEY')
                if rapidapi_key:
                    print(f"[OK] Using RapidAPI key from {secrets_path}")
            except Exception as e:
                print(f"[WARNING] Could not load secrets.toml: {e}")
        
        # Fallback to environment
        if not rapidapi_key:
            rapidapi_key = os.getenv('RAPIDAPI_KEY')
            if rapidapi_key:
                print("[OK] Using RapidAPI key from environment")
        
        if not rapidapi_key or rapidapi_key == "your_rapidapi_key_here":
            print("[ERROR] No valid RapidAPI key found")
            print("       Please set RAPIDAPI_KEY in environment or .streamlit/secrets.toml")
            return False
        
        print(f"[OK] RapidAPI key found: {rapidapi_key[:10]}...")
        
        # Test a simple search
        print("\n[EXECUTING API CALL]")
        print("-" * 40)
        
        step_plan = {
            'endpoint': 'search.php',
            'params': {'query': 'Elon Musk Twitter', 'search_type': 'Top'},
            'max_pages': 1,
            'reason': 'Test search after config fix'
        }
        
        print(f"Endpoint: {step_plan['endpoint']}")
        print(f"Parameters: {step_plan['params']}")
        print(f"Max pages: {step_plan['max_pages']}")
        
        # Execute API call
        result = api_client.execute_api_step(step_plan, {}, rapidapi_key)
        
        print("\n[RESULTS]")
        print("-" * 40)
        
        if 'error' in result:
            print(f"[ERROR] API call failed: {result['error']}")
            
            # Check if it's still the config error
            if "DEFAULT_MAX_PAGES_FALLBACK" in str(result['error']):
                print("[ERROR] Config issue NOT fixed - still getting attribute error")
            else:
                print("[INFO] Different error - config issue may be fixed but API has other problems")
            
            return False
        else:
            print(f"[SUCCESS] API call succeeded!")
            print(f"Results count: {result.get('count', 'unknown')}")
            
            # Show sample results
            if 'results' in result and result['results']:
                print(f"\nSample results (first 3):")
                for i, item in enumerate(result['results'][:3], 1):
                    if isinstance(item, dict):
                        text = item.get('text', item.get('full_text', str(item)))[:100]
                    else:
                        text = str(item)[:100]
                    print(f"  {i}. {text}...")
            
            return True
            
    except Exception as e:
        print(f"[ERROR] Exception: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_real_api_call()
    
    print("\n" + "=" * 60)
    if success:
        print(" CONFIG FIX SUCCESSFUL - API CALLS WORKING!")
        print(" You can now run real Twitter investigations!")
    else:
        print(" API CALLS STILL NOT WORKING - CHECK ERRORS ABOVE")
    print("=" * 60)