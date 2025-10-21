"""Debug script to understand why findings aren't being created"""

import sys
import json
sys.path.insert(0, 'twitterexplorer')

from finding_evaluator_llm import LLMFindingEvaluator
from llm_client import get_litellm_client

def test_finding_creation():
    """Test if the finding evaluator works with sample data"""
    
    print("=" * 60)
    print("TESTING FINDING EVALUATOR")
    print("=" * 60)
    
    # Initialize evaluator
    llm_client = get_litellm_client()
    evaluator = LLMFindingEvaluator(llm_client)
    print("[OK] Finding evaluator initialized")
    
    # Create sample tweet data
    sample_results = [
        {
            'text': 'OpenAI announces GPT-5 with improved reasoning capabilities and 10x faster inference speed.',
            'source': 'twitter',
            'author': 'sama',
            'metadata': {'retweets': 1000, 'likes': 5000}
        },
        {
            'text': 'Breaking: Microsoft integrates GPT-4 into Office 365, revolutionizing document creation.',
            'source': 'twitter', 
            'author': 'microsoft',
            'metadata': {'retweets': 500, 'likes': 2000}
        },
        {
            'text': 'Random tweet about cats and coffee.',
            'source': 'twitter',
            'author': 'randomuser',
            'metadata': {'retweets': 5, 'likes': 10}
        }
    ]
    
    investigation_goal = "Latest GPT and AI developments"
    
    print(f"\nTesting with {len(sample_results)} sample tweets")
    print(f"Investigation goal: {investigation_goal}")
    print("-" * 60)
    
    try:
        # Test evaluate_batch
        print("\nCalling evaluate_batch...")
        assessments = evaluator.evaluate_batch(sample_results, investigation_goal)
        
        print(f"\nResults:")
        print(f"  Assessments returned: {len(assessments)}")
        
        for i, assessment in enumerate(assessments):
            print(f"\n  Assessment {i+1}:")
            print(f"    Is significant: {assessment.is_significant}")
            print(f"    Relevance score: {assessment.relevance_score}")
            print(f"    Specificity score: {assessment.specificity_score}")
            print(f"    Key claims: {assessment.key_claims[:2] if assessment.key_claims else 'None'}")
            print(f"    Reasoning: {assessment.reasoning[:100]}...")
            
        # Count significant findings
        significant_count = sum(1 for a in assessments if a.is_significant)
        print(f"\n[SUMMARY] {significant_count}/{len(assessments)} marked as significant")
        
        if significant_count == 0:
            print("[WARNING] No findings marked as significant!")
            print("This explains why 0 findings are created in investigations.")
        
        return assessments
        
    except Exception as e:
        print(f"\n[ERROR] Finding evaluation failed: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_single_evaluation():
    """Test evaluating a single finding"""
    
    print("\n" + "=" * 60)
    print("TESTING SINGLE FINDING EVALUATION")
    print("=" * 60)
    
    llm_client = get_litellm_client()
    evaluator = LLMFindingEvaluator(llm_client)
    
    single_result = {
        'text': 'OpenAI CEO Sam Altman reveals GPT-5 training is complete, launch expected Q1 2025.',
        'source': 'twitter',
        'author': 'sama'
    }
    
    try:
        assessment = evaluator.evaluate_finding(single_result, "GPT-5 news")
        print(f"Single evaluation result:")
        print(f"  Significant: {assessment.is_significant}")
        print(f"  Relevance: {assessment.relevance_score}")
        print(f"  Should create finding: {assessment.is_significant and assessment.relevance_score > 5}")
    except Exception as e:
        print(f"[ERROR] Single evaluation failed: {e}")

if __name__ == "__main__":
    # Test batch evaluation
    assessments = test_finding_creation()
    
    # Test single evaluation
    test_single_evaluation()
    
    print("\n" + "=" * 60)
    if assessments and any(a.is_significant for a in assessments):
        print("Finding evaluator CAN create findings - issue is elsewhere")
    else:
        print("Finding evaluator is NOT creating significant findings - THIS IS THE PROBLEM")
    print("=" * 60)