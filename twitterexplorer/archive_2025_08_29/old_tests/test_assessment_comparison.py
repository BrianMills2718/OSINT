"""Compare assessment generation between isolated and integrated contexts"""
import sys
import os
import json

# Setup paths
project_root = os.path.dirname(__file__)
twitterexplorer_path = os.path.join(project_root, 'twitterexplorer')
sys.path.insert(0, twitterexplorer_path)

from finding_evaluator_llm import LLMFindingEvaluator
import litellm
import os

# Configure API key for litellm
os.environ["GEMINI_API_KEY"] = "AIzaSyAhwSgnnZrVbTECNCXDp1nODEVh3rtoTq8"

def test_assessment_generation_consistency():
    """EVIDENCE: Compare assessment results across contexts"""
    
    print("=== ASSESSMENT CONSISTENCY TEST ===")
    
    # Test data - real tweet-like content
    test_results = [
        {
            "text": "xAI's latest Grok model has finished pre-training and will be natively multimodal.",
            "source": "timeline.php"
        },
        {
            "text": "For those considering putting their work on the X platform, consider that Tucker Carlson's show when...",
            "source": "search.php" 
        },
        {
            "text": "Grok 4 now offers a free tier for all users on X, with a limited number of daily queries.",
            "source": "timeline.php"
        }
    ]
    
    investigation_goal = "Elon Musk X platform announcement"
    
    # Test 1: Direct LLMFindingEvaluator
    evaluator = LLMFindingEvaluator(llm_client=litellm)
    assessments_direct = evaluator.evaluate_batch(test_results, investigation_goal)
    
    print("\n--- DIRECT ASSESSMENTS ---")
    for i, assessment in enumerate(assessments_direct):
        print(f"Result {i+1}:")
        print(f"  is_significant: {assessment.is_significant}")
        print(f"  relevance_score: {assessment.relevance_score}")
        print(f"  reasoning: {assessment.reasoning}")
    
    # Test 2: No LLM client (fallback behavior)
    evaluator_fallback = LLMFindingEvaluator(llm_client=None)
    assessments_fallback = evaluator_fallback.evaluate_batch(test_results, investigation_goal)
    
    print("\n--- FALLBACK ASSESSMENTS ---")
    for i, assessment in enumerate(assessments_fallback):
        print(f"Result {i+1}:")
        print(f"  is_significant: {assessment.is_significant}")
        print(f"  relevance_score: {assessment.relevance_score}")
        print(f"  reasoning: {assessment.reasoning}")
    
    # Compare results
    significant_direct = sum(1 for a in assessments_direct if a.is_significant)
    significant_fallback = sum(1 for a in assessments_fallback if a.is_significant)
    
    print(f"\n--- COMPARISON ---")
    print(f"Direct significant findings: {significant_direct}/{len(test_results)}")
    print(f"Fallback significant findings: {significant_fallback}/{len(test_results)}")
    print(f"Assessment consistency: {'PASS' if significant_direct > 0 else 'FAIL'}")
    
    # Save detailed comparison
    comparison_data = {
        "direct_assessments": [
            {
                "is_significant": a.is_significant,
                "relevance_score": a.relevance_score,
                "reasoning": a.reasoning
            }
            for a in assessments_direct
        ],
        "fallback_assessments": [
            {
                "is_significant": a.is_significant,
                "relevance_score": a.relevance_score,
                "reasoning": a.reasoning
            }
            for a in assessments_fallback
        ]
    }
    
    with open("assessment_comparison.json", "w") as f:
        json.dump(comparison_data, f, indent=2)
    
    return comparison_data

if __name__ == "__main__":
    test_assessment_generation_consistency()