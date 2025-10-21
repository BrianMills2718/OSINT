#!/usr/bin/env python3

"""
Test script to demonstrate the finding evaluator failure that prevents 
121 API results from creating any DataPoints
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'twitterexplorer'))

from finding_evaluator_llm import LLMFindingEvaluator

def test_finding_evaluator_failure():
    """Test the finding evaluator with the invalid model to confirm it's failing"""
    
    print("TESTING ROOT CAUSE: Finding Evaluator with Invalid Model")
    print("=" * 60)
    
    # Create sample results like the 121 from the real investigation
    sample_results = [
        {"text": "Climate change policy debate continues with economic concerns", "source": "twitter"},
        {"text": "IPCC reports show need for immediate action on global warming", "source": "twitter"},
        {"text": "Industry groups oppose new environmental regulations", "source": "twitter"}
    ]
    
    investigation_goal = "What are different perspectives on climate change policies"
    
    try:
        evaluator = LLMFindingEvaluator()
        
        print(f"Testing batch evaluation with {len(sample_results)} results...")
        print(f"Investigation goal: {investigation_goal}")
        print()
        
        # This should fail due to invalid model "gpt-5-mini"
        assessments = evaluator.evaluate_batch(sample_results, investigation_goal)
        
        print("UNEXPECTED: Evaluation succeeded when it should have failed!")
        print(f"Got {len(assessments)} assessments")
        for i, assessment in enumerate(assessments):
            print(f"  Result {i}: significant={assessment.is_significant}, score={assessment.relevance_score}")
            
    except Exception as e:
        print("CONFIRMED: Finding evaluator failed as expected")
        print(f"Error: {str(e)}")
        print()
        print("ROOT CAUSE ANALYSIS:")
        print("- finding_evaluator_llm.py line 142 uses model='gpt-5-mini'")
        print("- This model doesn't exist, causing LLM API failure")
        print("- When finding evaluator fails, no DataPoints are created")
        print("- 121 API results -> 0 DataPoints -> 0 Insights -> 0 EmergentQuestions")
        print()
        print("SOLUTION: Change model to valid model name")
        
        return False  # Test confirmed the failure
    
    return True  # Test unexpectedly passed

if __name__ == "__main__":
    test_finding_evaluator_failure()