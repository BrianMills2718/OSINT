"""Test the LLM-based FindingEvaluator"""
import os
from twitterexplorer.finding_evaluator_llm import LLMFindingEvaluator

# Set up API key if needed
if 'GEMINI_API_KEY' in os.environ:
    import litellm
    litellm.api_key = os.environ['GEMINI_API_KEY']

def test_llm_evaluator():
    """Test that LLM-based evaluator correctly identifies significant findings"""
    print("=== TESTING LLM-BASED FINDING EVALUATOR ===\n")
    
    evaluator = LLMFindingEvaluator()
    
    test_cases = [
        {
            'text': 'Court documents from March 15, 2002 show Trump and Epstein attended a private party at Mar-a-Lago with 28 guests.',
            'goal': 'Trump Epstein relationship investigation',
            'expected_significant': True,
            'description': 'Specific finding with date, names, location'
        },
        {
            'text': 'Click here to read more about this topic. Subscribe for updates.',
            'goal': 'Trump Epstein relationship investigation',
            'expected_significant': False,
            'description': 'Generic content'
        },
        {
            'text': 'Financial records indicate a $2.5 million transaction between Trump Organization and an Epstein associate in July 2002.',
            'goal': 'Trump Epstein financial connections',
            'expected_significant': True,
            'description': 'Specific financial information'
        },
        {
            'text': 'No specific information available at this time.',
            'goal': 'Any investigation',
            'expected_significant': False,
            'description': 'Empty/useless content'
        }
    ]
    
    print("Testing individual evaluations:\n")
    for i, test_case in enumerate(test_cases, 1):
        result = {
            'text': test_case['text'],
            'source': 'test_source',
            'metadata': {}
        }
        
        print(f"Test {i}: {test_case['description']}")
        print(f"Text: {test_case['text'][:80]}...")
        
        try:
            assessment = evaluator.evaluate_finding(result, test_case['goal'])
            
            print(f"  Is significant: {assessment.is_significant} (expected: {test_case['expected_significant']})")
            print(f"  Relevance score: {assessment.relevance_score:.2f}")
            print(f"  Specificity score: {assessment.specificity_score:.2f}")
            print(f"  Entities found: {list(assessment.entities.keys()) if assessment.entities else 'None'}")
            print(f"  Reasoning: {assessment.reasoning[:100]}...")
            
            if assessment.is_significant == test_case['expected_significant']:
                print("  [PASS] Correctly evaluated\n")
            else:
                print("  [FAIL] Incorrect evaluation\n")
                
        except Exception as e:
            print(f"  [ERROR] Evaluation failed: {e}\n")
    
    # Test batch evaluation
    print("\nTesting batch evaluation:\n")
    batch_results = [
        {'text': tc['text'], 'source': 'test', 'metadata': {}}
        for tc in test_cases
    ]
    
    try:
        batch_assessments = evaluator.evaluate_batch(
            batch_results, 
            'Trump Epstein investigation'
        )
        
        print(f"Batch evaluated {len(batch_assessments)} results")
        significant_count = sum(1 for a in batch_assessments if a.is_significant)
        print(f"Found {significant_count} significant findings out of {len(batch_assessments)}")
        
        for i, (test_case, assessment) in enumerate(zip(test_cases, batch_assessments), 1):
            match = "✓" if assessment.is_significant == test_case['expected_significant'] else "✗"
            print(f"  {match} Result {i}: Significant={assessment.is_significant}, Expected={test_case['expected_significant']}")
            
    except Exception as e:
        print(f"[ERROR] Batch evaluation failed: {e}")
    
    print("\n=== TEST COMPLETE ===")

if __name__ == "__main__":
    test_llm_evaluator()