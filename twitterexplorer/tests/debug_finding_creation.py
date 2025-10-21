"""Debug script to trace the complete finding creation pipeline"""

import sys
import os
sys.path.insert(0, 'twitterexplorer')

from investigation_engine import InvestigationEngine, InvestigationConfig

def debug_investigation():
    """Run investigation with detailed debugging"""
    
    print("=" * 60)
    print("DEBUGGING FINDING CREATION PIPELINE")
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
        max_searches=2,  # Just 2 searches
        pages_per_search=1
    )
    
    # Run investigation
    print("\nRunning investigation...")
    engine = InvestigationEngine(api_key)
    
    # Monkey-patch to add debug output
    original_execute = engine._execute_search
    def debug_execute(search_plan, search_id, round_number):
        print(f"\n[DEBUG] Executing search: {search_plan['endpoint']}")
        result = original_execute(search_plan, search_id, round_number)
        
        # Check if raw_results were stored
        if hasattr(result, '_raw_results'):
            print(f"[DEBUG] Raw results stored: {len(result._raw_results) if result._raw_results else 0}")
        else:
            print(f"[DEBUG] NO _raw_results attribute!")
        
        return result
    
    engine._execute_search = debug_execute
    
    # Also patch finding creation
    if hasattr(engine, 'finding_evaluator'):
        original_evaluate = engine.finding_evaluator.evaluate_batch
        def debug_evaluate(results, goal):
            print(f"\n[DEBUG] Evaluating {len(results)} results for findings")
            assessments = original_evaluate(results, goal)
            significant = sum(1 for a in assessments if a.is_significant)
            print(f"[DEBUG] {significant}/{len(assessments)} marked as significant")
            return assessments
        engine.finding_evaluator.evaluate_batch = debug_evaluate
    
    # Run test
    result = engine.conduct_investigation("AI technology news", config)
    
    print("\n" + "=" * 60)
    print("INVESTIGATION RESULTS:")
    print(f"  Total searches: {len(result.search_history)}")
    print(f"  Total results: {sum(s.results_count for s in result.search_history)}")
    print(f"  Findings created: {len(result.accumulated_findings)}")
    
    # Check each search attempt for raw results
    print("\nRAW RESULTS CHECK:")
    for i, attempt in enumerate(result.search_history):
        print(f"  Search {i+1}: {attempt.endpoint}")
        if hasattr(attempt, '_raw_results'):
            raw_count = len(attempt._raw_results) if attempt._raw_results else 0
            print(f"    Has _raw_results: {raw_count} items")
        else:
            print(f"    NO _raw_results attribute!")
    
    print("\n" + "=" * 60)
    if len(result.accumulated_findings) > 0:
        print("SUCCESS: Findings ARE being created!")
    else:
        print("PROBLEM CONFIRMED: 0 findings created")
        
        # Check if finding_evaluator exists
        if hasattr(engine, 'finding_evaluator'):
            print("Finding evaluator EXISTS")
        else:
            print("NO finding_evaluator - THIS IS THE PROBLEM")
            
        # Check if graph mode is enabled
        if hasattr(engine, 'graph_mode'):
            print(f"Graph mode: {engine.graph_mode}")
        else:
            print("No graph_mode attribute")
    
    print("=" * 60)

if __name__ == "__main__":
    debug_investigation()