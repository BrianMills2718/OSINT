"""Debug why rejection feedback isn't being generated"""
import sys
import os

# Add twitterexplorer to path
current_dir = os.path.dirname(os.path.abspath(__file__))
twitterexplorer_path = os.path.join(current_dir, 'twitterexplorer')
sys.path.insert(0, twitterexplorer_path)

from investigation_engine import InvestigationEngine, InvestigationConfig

def test_rejection_feedback_debug():
    """Debug rejection feedback generation"""
    
    print("=== DEBUGGING REJECTION FEEDBACK ===\n")
    
    api_key = "d72bcd77e2msh76c7e6cf37f0b89p1c51bcjsnaad0f6b01e4f"
    engine = InvestigationEngine(api_key)
    
    # Hook to see what happens in analysis
    original_analyze = engine._analyze_round_results_with_llm
    
    def analyze_with_debug(session, current_round, results):
        """Debug analysis process"""
        print(f"\n>>> Analyzing round {current_round.round_number}")
        print(f"    Results to analyze: {len(results)}")
        
        for i, attempt in enumerate(results):
            print(f"    Attempt {i+1}: {attempt.endpoint}")
            print(f"      Results count: {attempt.results_count}")
            print(f"      Has _raw_results: {hasattr(attempt, '_raw_results')}")
            if hasattr(attempt, '_raw_results'):
                print(f"      Raw results length: {len(attempt._raw_results)}")
        
        # Call original
        original_analyze(session, current_round, results)
        
        # Check rejection feedback
        print(f"    Rejection feedback history length: {len(session.rejection_feedback_history)}")
        if session.rejection_feedback_history:
            recent = session.rejection_feedback_history[-1]
            print(f"    Most recent rejection rate: {recent.rejection_rate:.1%}")
    
    engine._analyze_round_results_with_llm = analyze_with_debug
    
    # Run investigation with limited searches
    config = InvestigationConfig(
        max_searches=2,
        pages_per_search=1
    )
    
    result = engine.conduct_investigation(
        "Trump news today",
        config
    )
    
    print("\n=== FINAL RESULTS ===")
    print(f"Total searches: {result.search_count}")
    print(f"Findings generated: {len(result.accumulated_findings)}")
    print(f"Rejection feedback rounds: {len(result.rejection_feedback_history) if hasattr(result, 'rejection_feedback_history') else 'N/A'}")
    
    # Check if rejection feedback exists in session
    if hasattr(result, 'rejection_feedback_history'):
        print(f"\nRejection feedback history exists: {result.rejection_feedback_history}")
    else:
        print("\nNo rejection_feedback_history attribute on result")

if __name__ == "__main__":
    test_rejection_feedback_debug()