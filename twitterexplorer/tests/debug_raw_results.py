"""Debug script to check if raw results are being stored"""

import sys
import os
sys.path.insert(0, 'twitterexplorer')

from investigation_engine import InvestigationEngine, InvestigationConfig

def debug_investigation():
    """Run investigation and check raw results"""
    
    print("=" * 60)
    print("DEBUGGING RAW RESULTS STORAGE")
    print("=" * 60)
    
    # Load API key
    try:
        import toml
        secrets_path = r'twitterexplorer\.streamlit\secrets.toml'
        secrets = toml.load(secrets_path)
        api_key = secrets.get('RAPIDAPI_KEY')
        print(f"[OK] Loaded API key")
    except:
        api_key = "test_key"
        print("[WARNING] Using test key")
    
    # Create simple config
    config = InvestigationConfig(
        max_searches=1,  # Just one search
        pages_per_search=1
    )
    
    # Run investigation
    print("\nRunning investigation...")
    engine = InvestigationEngine(api_key)
    
    # Monkey-patch to add debug output
    original_execute = engine._execute_search
    def debug_execute(session, search_spec, round_number):
        print(f"\n[DEBUG] Executing search: {search_spec.endpoint}")
        result = original_execute(session, search_spec, round_number)
        print(f"[DEBUG] Result type: {type(result)}")
        if hasattr(result, '_raw_results'):
            print(f"[DEBUG] Raw results count: {len(result._raw_results) if result._raw_results else 0}")
            if result._raw_results and len(result._raw_results) > 0:
                print(f"[DEBUG] First raw result keys: {result._raw_results[0].keys() if isinstance(result._raw_results[0], dict) else 'Not a dict'}")
        else:
            print(f"[DEBUG] No _raw_results attribute!")
        print(f"[DEBUG] Results count: {result.results_count}")
        return result
    
    engine._execute_search = debug_execute
    
    # Run test
    result = engine.conduct_investigation("AI news", config)
    
    print("\n" + "=" * 60)
    print("INVESTIGATION RESULTS:")
    print(f"  Total searches: {len(result.search_history)}")
    print(f"  Total results: {sum(s.results_count for s in result.search_history)}")
    print(f"  Findings created: {len(result.accumulated_findings)}")
    
    # Check search attempts for raw results
    print("\nRAW RESULTS CHECK:")
    for i, attempt in enumerate(result.search_history):
        print(f"\n  Search {i+1}: {attempt.endpoint}")
        print(f"    Results count: {attempt.results_count}")
        if hasattr(attempt, '_raw_results'):
            raw_count = len(attempt._raw_results) if attempt._raw_results else 0
            print(f"    Raw results: {raw_count}")
            if raw_count > 0:
                first = attempt._raw_results[0]
                if isinstance(first, dict):
                    print(f"    Sample keys: {list(first.keys())[:5]}")
                    if 'text' in first:
                        print(f"    Sample text: {first['text'][:50]}...")
        else:
            print(f"    [ERROR] No _raw_results attribute!")
    
    print("\n" + "=" * 60)
    if any(hasattr(s, '_raw_results') and s._raw_results for s in result.search_history):
        print("Raw results ARE being stored - check finding creation logic")
    else:
        print("Raw results are NOT being stored - THIS IS THE PROBLEM")
    print("=" * 60)

if __name__ == "__main__":
    debug_investigation()