"""Debug the findings pipeline to see where results disappear"""
import sys
import os
import json

# Add path
current_dir = os.path.dirname(os.path.abspath(__file__))
twitterexplorer_path = os.path.join(current_dir, 'twitterexplorer')
sys.path.insert(0, twitterexplorer_path)

from investigation_engine import InvestigationEngine, InvestigationConfig

def debug_findings():
    print("=== DEBUGGING FINDINGS PIPELINE ===\n")
    
    api_key = "d72bcd77e2msh76c7e6cf37f0b89p1c51bcjsnaad0f6b01e4f"
    engine = InvestigationEngine(api_key)
    
    # Hook into the analyze method to see what's happening
    original_analyze = engine._analyze_round_results_with_llm
    
    def debug_analyze(session, current_round, results):
        print(f"\n>>> _analyze_round_results_with_llm called")
        print(f"    Number of SearchAttempts: {len(results)}")
        
        for i, attempt in enumerate(results):
            print(f"\n    SearchAttempt {i+1}:")
            print(f"      - Endpoint: {attempt.endpoint}")
            print(f"      - Results count: {attempt.results_count}")
            print(f"      - Has _raw_results: {hasattr(attempt, '_raw_results')}")
            
            if hasattr(attempt, '_raw_results'):
                raw = attempt._raw_results
                print(f"      - Length of _raw_results: {len(raw)}")
                if raw and len(raw) > 0:
                    print(f"      - Sample result text: {raw[0].get('text', 'NO TEXT')[:100]}...")
            
        print(f"\n    Session findings BEFORE: {len(session.accumulated_findings)}")
        
        # Call original
        original_analyze(session, current_round, results)
        
        print(f"    Session findings AFTER: {len(session.accumulated_findings)}")
        print("<<<\n")
    
    engine._analyze_round_results_with_llm = debug_analyze
    
    # Run minimal investigation
    config = InvestigationConfig(max_searches=1, pages_per_search=1)
    result = engine.conduct_investigation("Trump news", config)
    
    print("\n=== FINAL RESULTS ===")
    print(f"Total searches: {result.search_count}")
    print(f"Total results: {result.total_results_found}")
    print(f"Total findings: {len(result.accumulated_findings)}")
    
    if result.accumulated_findings:
        print("\nFirst finding:")
        print(f"  Content: {result.accumulated_findings[0].content[:200]}...")
    else:
        print("\nNO FINDINGS CREATED!")
        
        # Check what actually came back from API
        if result.search_history:
            attempt = result.search_history[0]
            print(f"\nBut API returned: {attempt.results_count} results")
            if hasattr(attempt, '_raw_results') and attempt._raw_results:
                print(f"Raw results exist: {len(attempt._raw_results)} items")
                print(f"First raw result: {attempt._raw_results[0]}")

if __name__ == "__main__":
    debug_findings()