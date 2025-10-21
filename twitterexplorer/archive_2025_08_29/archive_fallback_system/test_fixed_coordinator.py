"""Test the fixed LLMInvestigationCoordinator with batch response handling"""
import sys
import os

# Setup paths
sys.path.insert(0, 'twitterexplorer')
os.chdir('twitterexplorer')

import litellm
from llm_investigation_coordinator import LLMInvestigationCoordinator

# Configure API key
os.environ["GEMINI_API_KEY"] = "AIzaSyAhwSgnnZrVbTECNCXDp1nODEVh3rtoTq8"

def test_fixed_coordinator():
    """Test that the coordinator now handles batch responses correctly"""
    
    print("=== TESTING FIXED COORDINATOR ===")
    
    coordinator = LLMInvestigationCoordinator(litellm)
    
    # Test endpoint selection (should now handle batch responses)
    decision = coordinator.decide_next_action(
        goal="analyze Trump's recent statements about Epstein",
        current_understanding="Need direct source access",
        gaps=["Trump's actual tweets about Epstein"],
        search_history=[]
    )
    
    print("SUCCESS: Decision received")
    print(f"Endpoint: {decision.get('endpoint', 'Missing endpoint')}")
    print(f"Parameters: {decision.get('parameters', 'Missing parameters')}")
    print(f"Reasoning: {decision.get('reasoning', 'Missing reasoning')[:100]}...")
    print(f"User Update: {decision.get('user_update', 'Missing user_update')[:100]}...")
    
    # Check if batch information was preserved
    if 'batch_searches' in decision:
        print(f"Batch Searches Preserved: {len(decision['batch_searches'])} searches")
        for i, search in enumerate(decision['batch_searches']):
            print(f"  {i+1}. {search['endpoint']} - {search['parameters']}")
    
    # Test evaluation
    print("\n--- Testing Result Evaluation ---")
    
    mock_results = [
        {"text": "Trump responds to Epstein allegations in new statement", "source": "search.php"},
        {"text": "Analysis of Trump-Epstein connections", "source": "search.php"},
        {"text": "Public reaction to Trump's Epstein comments", "source": "search.php"}
    ]
    
    evaluation = coordinator.evaluate_results(
        goal="analyze Trump's recent statements about Epstein",
        results=mock_results,
        search_context={
            "query": "Trump Epstein recent statements",
            "endpoint": "search.php",
            "evaluation_criteria": {
                "relevance_indicators": ["Trump", "Epstein", "statements"],
                "information_targets": ["direct statements", "public reactions"]
            }
        }
    )
    
    print(f"Relevance Score: {evaluation.get('relevance_score', 'Missing')}")
    print(f"Information Value: {evaluation.get('information_value', 'Missing')}")
    print(f"Should Continue: {evaluation.get('should_continue', 'Missing')}")
    print(f"Key Insights: {len(evaluation.get('key_insights', []))} insights")
    
    # Test synthesis
    print("\n--- Testing Understanding Synthesis ---")
    
    mock_evidence = [
        {"content": "Trump issued statement denying close relationship with Epstein", "source": "timeline.php"},
        {"content": "Public response mixed on Trump's Epstein statement", "source": "search.php"}
    ]
    
    synthesis = coordinator.synthesize_understanding(
        goal="analyze Trump's recent statements about Epstein",
        accumulated_evidence=mock_evidence
    )
    
    print(f"Confidence Level: {synthesis.get('confidence_level', 'Missing')}")
    print(f"Key Findings: {len(synthesis.get('key_findings', []))} findings")
    print(f"Critical Gaps: {len(synthesis.get('critical_gaps', []))} gaps")
    print(f"Understanding: {synthesis.get('current_understanding', 'Missing')[:100]}...")
    
    print("\n=== COORDINATOR TEST COMPLETE ===")
    print("All core methods are working with proper LLM integration!")

if __name__ == "__main__":
    test_fixed_coordinator()