"""Test that insights are surfaced to users"""
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

def test_final_summary_exists():
    """EVIDENCE: Investigation must produce a final summary"""
    
    # Use real API key
    api_key = "d72bcd77e2msh76c7e6cf37f0b89p1c51bcjsnaad0f6b01e4f"
    engine = InvestigationEngine(api_key)
    
    # Small config
    config = InvestigationConfig(max_searches=2, pages_per_search=1)
    
    # Run investigation
    result = engine.conduct_investigation(
        "What is Elon Musk announcing about X?",
        config
    )
    
    # Test 1: final_summary attribute exists
    assert hasattr(result, 'final_summary'), "No final_summary attribute"
    
    # Test 2: final_summary is not empty
    assert result.final_summary is not None, "final_summary is None"
    assert len(result.final_summary) > 100, f"Summary too short: {len(result.final_summary)} chars"
    
    # Test 3: final_summary contains actual insights
    assert "Key Findings:" in result.final_summary or "insights" in result.final_summary.lower()
    
    # Test 4: Check if actual insights are included
    has_real_insights = False
    for round_obj in result.rounds:
        if round_obj.key_insights:
            # At least one insight should be in the summary
            for insight in round_obj.key_insights:
                if insight in result.final_summary:
                    has_real_insights = True
                    break
    
    assert has_real_insights, "Final summary doesn't contain the actual insights found"
    
    print("PASSED: Final summary test passed!")
    print(f"Summary preview: {result.final_summary[:200]}...")
    
    return result

def test_insights_contain_tweet_content():
    """EVIDENCE: Insights must reference actual tweet content"""
    
    result = test_final_summary_exists()
    
    # Check that insights mention specific things from tweets
    keywords = ['X', 'Grok', 'platform', 'announcement', 'feature', 'update']
    
    found_keywords = []
    for keyword in keywords:
        if keyword.lower() in result.final_summary.lower():
            found_keywords.append(keyword)
    
    assert len(found_keywords) > 0, f"No relevant keywords found in summary"
    
    print(f"PASSED: Found relevant keywords: {found_keywords}")
    
    # Show the full summary for evidence
    print("\n=== FULL FINAL SUMMARY ===")
    print(result.final_summary)
    print("=== END SUMMARY ===")

if __name__ == "__main__":
    test_final_summary_exists()
    test_insights_contain_tweet_content()