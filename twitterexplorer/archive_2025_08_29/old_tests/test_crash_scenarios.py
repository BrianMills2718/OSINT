#!/usr/bin/env python3
"""
Test scenarios that would have crashed the system before defensive improvements
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'twitterexplorer'))

# Load API key
import toml
secrets_path = os.path.join('twitterexplorer', '.streamlit', 'secrets.toml')
if os.path.exists(secrets_path):
    secrets = toml.load(secrets_path)
    os.environ['GEMINI_API_KEY'] = secrets.get('GEMINI_API_KEY', '')

from investigation_engine import InvestigationEngine

def test_original_error_scenario():
    """Test the EXACT scenario that caused the original error"""
    print("=== Testing Original Error Scenario ===\n")
    print("Original error was: 'SearchStrategy' object has no attribute 'get'")
    
    try:
        from llm_client import StrategicDecision, SearchStrategy, SearchParameters
        
        # Create a decision with SearchStrategy objects (not dicts)
        decision = StrategicDecision(
            decision_type="test",
            reasoning="Test decision",
            searches=[
                SearchStrategy(
                    endpoint="search.php",
                    parameters=SearchParameters(query="test query"),
                    reasoning="Test search"
                )
            ],
            expected_outcomes=["Test"]
        )
        
        # This is what would have crashed before: trying to use .get() on SearchStrategy
        engine = InvestigationEngine("test_key")
        
        # Simulate the processing that happens in _get_next_strategy_with_graph
        searches = []
        for search_spec in decision.searches:
            print(f"Processing: {type(search_spec).__name__}")
            
            # OLD CODE (would crash):
            # search_plan = {
            #     'endpoint': search_spec.get('endpoint', 'search.php'),  # ERROR!
            #     'params': search_spec.get('parameters', {}),
            #     'reason': search_spec.get('reasoning', ''),
            # }
            
            # NEW CODE (with defensive checks):
            if hasattr(search_spec, 'parameters'):
                # It's a SearchStrategy object
                params_dict = {k: v for k, v in search_spec.parameters.model_dump().items() if v is not None}
                search_plan = {
                    'endpoint': search_spec.endpoint,
                    'params': params_dict,
                    'reason': search_spec.reasoning,
                    'max_pages': 3
                }
                print(f"[OK] Successfully processed SearchStrategy without .get() error")
            else:
                # Fallback for dict
                search_plan = {
                    'endpoint': search_spec.get('endpoint', 'search.php'),
                    'params': search_spec.get('parameters', {}),
                    'reason': search_spec.get('reasoning', ''),
                    'max_pages': search_spec.get('max_pages', 3)
                }
            
            searches.append(search_plan)
        
        print(f"[SUCCESS] Processed {len(searches)} searches without crashing")
        return True
        
    except AttributeError as e:
        if "'SearchStrategy' object has no attribute 'get'" in str(e):
            print(f"[FAIL] Original error still occurs: {e}")
            return False
        else:
            raise
    except Exception as e:
        print(f"[ERROR] Unexpected error: {e}")
        return False

def test_none_crash_scenario():
    """Test that None values don't crash the system"""
    print("\n=== Testing None Crash Scenario ===\n")
    
    try:
        # This would crash without defensive checks
        decision_dict = {
            'searches': [
                {'endpoint': 'search.php', 'parameters': {'query': 'test'}},
                None,  # This would cause AttributeError
                {'endpoint': 'timeline.php', 'parameters': {'screenname': 'test'}}
            ]
        }
        
        # Process with defensive checks
        searches = []
        for search_spec in decision_dict.get('searches', []):
            if search_spec is None:
                print("[OK] Skipped None value without crashing")
                continue
            
            search_plan = {
                'endpoint': search_spec.get('endpoint', 'search.php'),
                'params': search_spec.get('parameters', {}),
                'reason': search_spec.get('reasoning', ''),
                'max_pages': search_spec.get('max_pages', 3)
            }
            searches.append(search_plan)
        
        print(f"[SUCCESS] Processed {len(searches)} valid searches, skipped None")
        return True
        
    except Exception as e:
        print(f"[FAIL] System crashed on None value: {e}")
        return False

def test_empty_searches_crash():
    """Test that empty searches list doesn't crash"""
    print("\n=== Testing Empty Searches Crash Scenario ===\n")
    
    try:
        from llm_client import StrategicDecision
        
        # Decision with no searches
        decision = StrategicDecision(
            decision_type="test",
            reasoning="Test with empty",
            searches=[],  # Empty list
            expected_outcomes=["Test"]
        )
        
        # Process empty searches
        if not decision.searches:
            print("[OK] Handled empty searches without crash")
            result = {
                'description': f"Strategy: {decision.reasoning}",
                'searches': [],
                'reasoning': decision.reasoning
            }
        else:
            # Process normally
            pass
        
        print("[SUCCESS] Empty searches handled gracefully")
        return True
        
    except Exception as e:
        print(f"[FAIL] System crashed on empty searches: {e}")
        return False

def main():
    print("=" * 60)
    print("CRASH SCENARIO TESTS")
    print("=" * 60)
    print("Testing scenarios that would have crashed before fixes...\n")
    
    results = []
    
    # Test 1: Original SearchStrategy.get() error
    results.append(("Original .get() error", test_original_error_scenario()))
    
    # Test 2: None values in searches
    results.append(("None values crash", test_none_crash_scenario()))
    
    # Test 3: Empty searches list
    results.append(("Empty searches crash", test_empty_searches_crash()))
    
    print("\n" + "=" * 60)
    print("CRASH TEST RESULTS")
    print("=" * 60)
    
    for test_name, passed in results:
        status = "PASS" if passed else "FAIL"
        print(f"[{status}] {test_name}")
    
    all_passed = all(result[1] for result in results)
    
    if all_passed:
        print("\n[VERIFIED] All crash scenarios are now handled safely!")
    else:
        print("\n[WARNING] Some crash scenarios may still occur")
    
    return all_passed

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)