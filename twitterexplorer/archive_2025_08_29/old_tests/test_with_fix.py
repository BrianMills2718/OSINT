"""Test with the quick fix - increase max_searches to allow multiple rounds"""
import sys
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
twitterexplorer_path = os.path.join(current_dir, 'twitterexplorer')
sys.path.insert(0, twitterexplorer_path)

from investigation_engine import InvestigationEngine, InvestigationConfig

def test_with_fix():
    """Test if increasing max_searches allows multiple rounds"""
    
    print("=== TESTING WITH FIX: Higher max_searches ===\n")
    
    api_key = "d72bcd77e2msh76c7e6cf37f0b89p1c51bcjsnaad0f6b01e4f"
    engine = InvestigationEngine(api_key)
    
    # The fix: Set max_searches high enough for multiple rounds
    # If each round does 3 searches, 15 allows 5 rounds
    config = InvestigationConfig(
        max_searches=15,  # FIX: Was 3-10, now 15
        pages_per_search=1,
        satisfaction_enabled=False,  # Disable to test iteration
        max_time_minutes=5  # Limit time
    )
    
    print(f"Config: max_searches={config.max_searches} (should allow ~5 rounds)")
    
    # Track rounds
    round_count = [0]
    original_generate = engine._generate_strategy
    
    def count_rounds(session):
        round_count[0] += 1
        print(f"\n>>> Round {round_count[0]} starting (search_count: {session.search_count})")
        result = original_generate(session)
        searches = len(result.get('searches', []))
        print(f"    Planning {searches} searches")
        print(f"    After this round: {session.search_count + searches} total searches")
        return result
    
    engine._generate_strategy = count_rounds
    
    # Run investigation
    result = engine.conduct_investigation(
        "test query for multiple rounds",
        config
    )
    
    print(f"\n=== RESULTS ===")
    print(f"Total rounds executed: {round_count[0]}")
    print(f"Total searches: {result.search_count}")
    print(f"Total findings: {len(result.accumulated_findings)}")
    
    # Check rejection feedback
    if hasattr(result, 'rejection_feedback_history'):
        print(f"Rejection feedback rounds: {len(result.rejection_feedback_history)}")
        
        if len(result.rejection_feedback_history) > 1:
            print("\nRejection rates by round:")
            for i, feedback in enumerate(result.rejection_feedback_history, 1):
                print(f"  Round {i}: {feedback.rejection_rate:.1%}")
            
            # Check if it improved
            first_rate = result.rejection_feedback_history[0].rejection_rate
            last_rate = result.rejection_feedback_history[-1].rejection_rate
            
            if last_rate < first_rate:
                print(f"\nIMPROVEMENT: Rejection rate decreased from {first_rate:.1%} to {last_rate:.1%}")
            else:
                print(f"\nNO IMPROVEMENT: Rejection rate {first_rate:.1%} -> {last_rate:.1%}")
    
    # Diagnosis
    print(f"\n=== DIAGNOSIS ===")
    if round_count[0] > 1:
        print("SUCCESS: System ran multiple rounds with higher max_searches")
        print("ROOT CAUSE CONFIRMED: max_searches was limiting rounds, not iterations")
    else:
        print("FAILED: Still only one round even with max_searches=15")
        print("There may be another issue preventing iteration")
    
    return round_count[0] > 1

if __name__ == "__main__":
    success = test_with_fix()
    exit(0 if success else 1)