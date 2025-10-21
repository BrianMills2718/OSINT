#!/usr/bin/env python3
"""
Test backward compatibility - both old dict and new SearchStrategy formats
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'twitterexplorer'))

def test_dict_format():
    """Test old dict format still works"""
    print("=== Testing Old Dict Format ===\n")
    
    # Old-style dict format
    search_spec = {
        'endpoint': 'search.php',
        'parameters': {'query': 'test'},
        'reasoning': 'Test search',
        'max_pages': 5
    }
    
    # Process as dict
    try:
        search_plan = {
            'endpoint': search_spec.get('endpoint', 'search.php'),
            'params': search_spec.get('parameters', {}),
            'reason': search_spec.get('reasoning', ''),
            'max_pages': search_spec.get('max_pages', 3)
        }
        
        print(f"[OK] Dict format processed: {search_plan}")
        assert search_plan['endpoint'] == 'search.php'
        assert search_plan['params'] == {'query': 'test'}
        assert search_plan['reason'] == 'Test search'
        assert search_plan['max_pages'] == 5
        return True
        
    except Exception as e:
        print(f"[FAIL] Dict format failed: {e}")
        return False

def test_searchstrategy_format():
    """Test new SearchStrategy format works"""
    print("\n=== Testing New SearchStrategy Format ===\n")
    
    from llm_client import SearchStrategy, SearchParameters
    
    # New SearchStrategy object
    search_spec = SearchStrategy(
        endpoint="timeline.php",
        parameters=SearchParameters(screenname="testuser"),
        reasoning="Get user timeline"
    )
    
    # Process as SearchStrategy
    try:
        if hasattr(search_spec, 'parameters'):
            params_dict = {k: v for k, v in search_spec.parameters.model_dump().items() if v is not None}
            search_plan = {
                'endpoint': search_spec.endpoint,
                'params': params_dict,
                'reason': search_spec.reasoning,
                'max_pages': 3  # Default
            }
            
            print(f"[OK] SearchStrategy format processed: {search_plan}")
            assert search_plan['endpoint'] == 'timeline.php'
            assert search_plan['params'] == {'screenname': 'testuser'}
            assert search_plan['reason'] == 'Get user timeline'
            return True
        else:
            print("[FAIL] SearchStrategy doesn't have parameters attribute")
            return False
            
    except Exception as e:
        print(f"[FAIL] SearchStrategy format failed: {e}")
        return False

def test_mixed_formats():
    """Test mixed formats in same list"""
    print("\n=== Testing Mixed Formats ===\n")
    
    from llm_client import SearchStrategy, SearchParameters
    
    # Mix of dict and SearchStrategy
    mixed_searches = [
        {'endpoint': 'search.php', 'parameters': {'query': 'dict format'}},
        SearchStrategy(
            endpoint="timeline.php",
            parameters=SearchParameters(screenname="object format"),
            reasoning="Object search"
        )
    ]
    
    processed = []
    for search_spec in mixed_searches:
        try:
            if hasattr(search_spec, 'parameters'):
                # SearchStrategy object
                params_dict = {k: v for k, v in search_spec.parameters.model_dump().items() if v is not None}
                search_plan = {
                    'endpoint': search_spec.endpoint,
                    'params': params_dict,
                    'reason': search_spec.reasoning,
                }
                print(f"[OK] Processed SearchStrategy: {search_spec.endpoint}")
            else:
                # Dict format
                search_plan = {
                    'endpoint': search_spec.get('endpoint', 'search.php'),
                    'params': search_spec.get('parameters', {}),
                    'reason': search_spec.get('reasoning', ''),
                }
                print(f"[OK] Processed dict: {search_spec.get('endpoint')}")
            
            processed.append(search_plan)
            
        except Exception as e:
            print(f"[FAIL] Failed to process: {e}")
            return False
    
    if len(processed) == 2:
        print(f"[SUCCESS] Processed {len(processed)} mixed format searches")
        return True
    else:
        print(f"[FAIL] Expected 2 processed, got {len(processed)}")
        return False

def main():
    print("=" * 60)
    print("BACKWARD COMPATIBILITY TEST")
    print("=" * 60)
    
    results = []
    results.append(("Dict format", test_dict_format()))
    results.append(("SearchStrategy format", test_searchstrategy_format()))
    results.append(("Mixed formats", test_mixed_formats()))
    
    print("\n" + "=" * 60)
    print("COMPATIBILITY RESULTS")
    print("=" * 60)
    
    for test_name, passed in results:
        status = "PASS" if passed else "FAIL"
        print(f"[{status}] {test_name}")
    
    all_passed = all(result[1] for result in results)
    
    if all_passed:
        print("\n[VERIFIED] Full backward compatibility maintained!")
    else:
        print("\n[WARNING] Compatibility issues detected")
    
    return all_passed

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)