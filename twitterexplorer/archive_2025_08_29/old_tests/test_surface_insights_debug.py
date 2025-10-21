"""Debug test to see what's happening with summary generation"""
import sys
import os

# Setup paths - check if already in twitterexplorer directory
if os.path.basename(os.getcwd()) != 'twitterexplorer':
    sys.path.insert(0, 'twitterexplorer')
    if os.path.exists('twitterexplorer'):
        os.chdir('twitterexplorer')
else:
    sys.path.insert(0, '.')

from investigation_engine import InvestigationEngine, InvestigationConfig

def test_final_summary_debug():
    """Debug the summary generation"""
    
    # Use real API key
    api_key = "d72bcd77e2msh76c7e6cf37f0b89p1c51bcjsnaad0f6b01e4f"
    engine = InvestigationEngine(api_key)
    
    # Small config
    config = InvestigationConfig(max_searches=2, pages_per_search=1)
    
    print("Starting investigation...")
    
    # Run investigation
    result = engine.conduct_investigation(
        "What is Elon Musk announcing about X?",
        config
    )
    
    print(f"\nInvestigation complete!")
    print(f"Has final_summary attribute: {hasattr(result, 'final_summary')}")
    print(f"final_summary value: {result.final_summary}")
    print(f"Number of rounds: {len(result.rounds)}")
    
    # Check if rounds have key_insights
    for i, round_obj in enumerate(result.rounds):
        print(f"\nRound {i+1}:")
        print(f"  Has key_insights: {hasattr(round_obj, 'key_insights')}")
        if hasattr(round_obj, 'key_insights'):
            print(f"  key_insights: {round_obj.key_insights}")
    
    # Manually call _generate_final_summary to test it
    print("\n--- Testing _generate_final_summary directly ---")
    summary = engine._generate_final_summary(result)
    print(f"Generated summary: {summary[:500] if summary else 'None'}")
    
    return result

if __name__ == "__main__":
    test_final_summary_debug()