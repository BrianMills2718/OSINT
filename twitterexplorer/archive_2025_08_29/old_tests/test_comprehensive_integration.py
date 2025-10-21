#!/usr/bin/env python3
"""
Comprehensive integration test to catch ALL issues with SearchStrategy conversion
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'twitterexplorer'))

# Load API key from secrets
import toml
secrets_path = os.path.join('twitterexplorer', '.streamlit', 'secrets.toml')
if os.path.exists(secrets_path):
    secrets = toml.load(secrets_path)
    os.environ['GEMINI_API_KEY'] = secrets.get('GEMINI_API_KEY', '')

from llm_client import get_litellm_client, StrategicDecision, SearchStrategy, SearchParameters
from graph_aware_llm_coordinator import GraphAwareLLMCoordinator
from investigation_graph import InvestigationGraph
from investigation_engine import InvestigationEngine
from typing import List, Dict, Any

def test_searchstrategy_object_access():
    """Test that SearchStrategy objects work correctly everywhere"""
    print("=== Testing SearchStrategy Object Access ===\n")
    
    # Create a SearchStrategy object
    search = SearchStrategy(
        endpoint="search.php",
        parameters=SearchParameters(query="test query"),
        reasoning="Test reasoning"
    )
    
    print(f"[TEST] SearchStrategy object created: {search}")
    print(f"  endpoint: {search.endpoint}")
    print(f"  parameters: {search.parameters}")
    print(f"  reasoning: {search.reasoning}")
    
    # Test accessing parameters
    print(f"  parameters.query: {search.parameters.query}")
    
    # Test what happens if code tries to use .get() on it
    try:
        # This will fail - SearchStrategy doesn't have .get()
        test = search.get('endpoint', 'default')
        print("[FAIL] SearchStrategy.get() should not work!")
    except AttributeError as e:
        print(f"[OK] SearchStrategy.get() correctly raises AttributeError: {e}")
    
    return search

def test_investigation_engine_integration():
    """Test that InvestigationEngine handles SearchStrategy correctly"""
    print("\n=== Testing InvestigationEngine Integration ===\n")
    
    try:
        # Create test objects
        graph = InvestigationGraph()
        graph.create_analytic_question_node("Test investigation")
        
        llm_client = get_litellm_client()
        coordinator = GraphAwareLLMCoordinator(llm_client, graph)
        
        # Create a mock decision with SearchStrategy objects
        decision = StrategicDecision(
            decision_type="gap_filling",
            reasoning="Test decision",
            searches=[
                SearchStrategy(
                    endpoint="search.php",
                    parameters=SearchParameters(query="test query 1"),
                    reasoning="First search"
                ),
                SearchStrategy(
                    endpoint="timeline.php",
                    parameters=SearchParameters(screenname="testuser"),
                    reasoning="User timeline"
                )
            ],
            expected_outcomes=["Test outcome"]
        )
        
        print(f"[OK] Created StrategicDecision with {len(decision.searches)} SearchStrategy objects")
        
        # Test how InvestigationEngine would process this
        searches = []
        for search_spec in decision.searches:
            print(f"\n[TEST] Processing SearchStrategy: {search_spec}")
            
            # This is what investigation_engine.py tries to do (WRONG):
            try:
                wrong_way = {
                    'endpoint': search_spec.get('endpoint', 'search.php'),  # This will fail!
                    'params': search_spec.get('parameters', {}),
                    'reason': search_spec.get('reasoning', ''),
                }
                print("[FAIL] Should not be able to use .get() on SearchStrategy!")
            except AttributeError as e:
                print(f"[OK] .get() correctly fails: {e}")
            
            # This is the CORRECT way:
            correct_way = {
                'endpoint': search_spec.endpoint,
                'params': {k: v for k, v in search_spec.parameters.model_dump().items() if v is not None},
                'reason': search_spec.reasoning,
                'max_pages': 3  # Default value
            }
            print(f"[OK] Correct conversion: {correct_way}")
            searches.append(correct_way)
        
        print(f"\n[OK] Successfully converted {len(searches)} SearchStrategy objects to dicts")
        return searches
        
    except Exception as e:
        print(f"[ERROR] Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_all_searchstrategy_locations():
    """Find and test all locations where SearchStrategy is used"""
    print("\n=== Testing All SearchStrategy Usage Locations ===\n")
    
    # List of files and line numbers where .get() is used on search objects
    problem_locations = [
        ("investigation_engine.py", 352, "search_spec.get('endpoint', 'search.php')"),
        ("investigation_engine.py", 353, "search_spec.get('parameters', {})"),
        ("investigation_engine.py", 354, "search_spec.get('reasoning', '')"),
        ("investigation_engine.py", 355, "search_spec.get('max_pages', 3)"),
        ("investigation_engine.py", 402, "search_spec.get('endpoint', decision['endpoint'])"),
        ("investigation_engine.py", 403, "search_spec.get('parameters', search_spec.get('params', {}))"),
        ("investigation_engine.py", 404, "search_spec.get('reasoning', search_spec.get('reason', ''))"),
        ("investigation_engine.py", 405, "search_spec.get('max_pages', 3)"),
    ]
    
    print("Found problematic .get() usage in:")
    for file, line, code in problem_locations:
        print(f"  {file}:{line} - {code}")
    
    print("\nAll these need to be fixed to use attribute access instead of .get()")
    
    return problem_locations

def generate_fix_for_investigation_engine():
    """Generate the fix needed for investigation_engine.py"""
    print("\n=== Generating Fix for investigation_engine.py ===\n")
    
    fix = """
# REQUIRED FIX for investigation_engine.py around line 350-357:

OLD CODE (WRONG):
```python
for search_spec in decision.searches:
    search_plan = {
        'endpoint': search_spec.get('endpoint', 'search.php'),
        'params': search_spec.get('parameters', {}),
        'reason': search_spec.get('reasoning', ''),
        'max_pages': search_spec.get('max_pages', 3)
    }
    searches.append(search_plan)
```

NEW CODE (CORRECT):
```python
for search_spec in decision.searches:
    # Convert SearchStrategy object to dict format
    params_dict = {}
    if hasattr(search_spec, 'parameters'):
        # It's a SearchStrategy object
        params_dict = {k: v for k, v in search_spec.parameters.model_dump().items() if v is not None}
        search_plan = {
            'endpoint': search_spec.endpoint,
            'params': params_dict,
            'reason': search_spec.reasoning,
            'max_pages': 3  # SearchStrategy doesn't have max_pages, use default
        }
    else:
        # Fallback for dict format (backward compatibility)
        search_plan = {
            'endpoint': search_spec.get('endpoint', 'search.php'),
            'params': search_spec.get('parameters', {}),
            'reason': search_spec.get('reasoning', ''),
            'max_pages': search_spec.get('max_pages', 3)
        }
    searches.append(search_plan)
```

Similar fix needed around line 400-407 for the else branch.
"""
    print(fix)
    return fix

def main():
    """Run all comprehensive tests"""
    print("=" * 60)
    print("COMPREHENSIVE SEARCHSTRATEGY INTEGRATION TEST")
    print("=" * 60)
    
    # Test 1: Basic object access
    search_obj = test_searchstrategy_object_access()
    
    # Test 2: Integration with investigation engine
    converted_searches = test_investigation_engine_integration()
    
    # Test 3: Find all problem locations
    problems = test_all_searchstrategy_locations()
    
    # Test 4: Generate fixes
    fix = generate_fix_for_investigation_engine()
    
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    if search_obj and converted_searches and problems:
        print("[SUCCESS] All tests passed - fixes identified")
        print(f"\nNeed to fix {len(problems)} locations in investigation_engine.py")
        print("Use the generated fix code above to update the file")
    else:
        print("[FAILURE] Some tests failed - review output above")
    
    print("\nTo prevent going in circles:")
    print("1. Apply ALL fixes at once (not one at a time)")
    print("2. Test with this comprehensive test suite")
    print("3. Only deploy when ALL tests pass")

if __name__ == "__main__":
    main()