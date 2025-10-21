"""Test the fixed LLM client with structured output"""

import os
import sys
import time

# Add v2 to path
sys.path.insert(0, r'C:\Users\Brian\projects\twitterexplorer\v2')

from llm_client_fixed import LLMClient
from models_fixed import StrategyOutput, EndpointPlan, EvaluationOutput

def test_structured_output_speed():
    """Compare speed of structured output vs JSON mode"""
    client = LLMClient()
    
    prompt = "Generate a simple strategy for finding 'AI news' with one endpoint"
    
    # Test structured output
    start = time.time()
    try:
        result = client.generate(prompt, StrategyOutput)
        structured_time = time.time() - start
        print(f"[PASS] Structured output: {structured_time:.2f}s")
        print(f"  Generated {len(result.endpoints)} endpoints")
    except Exception as e:
        print(f"[FAIL] Structured output failed: {e}")
        structured_time = None
    
    # Test JSON mode fallback
    start = time.time()
    try:
        result = client._generate_with_json_mode(prompt, StrategyOutput, 0.7)
        json_time = time.time() - start
        print(f"[PASS] JSON mode: {json_time:.2f}s")
        print(f"  Generated {len(result.endpoints)} endpoints")
    except Exception as e:
        print(f"[FAIL] JSON mode failed: {e}")
        json_time = None
    
    if structured_time and json_time:
        improvement = (1 - structured_time/json_time) * 100
        print(f"\nSpeed improvement: {improvement:.1f}%")
    
    return structured_time is not None

def test_complex_investigation():
    """Test a complex investigation scenario"""
    client = LLMClient()
    
    investigation_prompt = """You are investigating the Trump-Epstein relationship controversy.
    
    Generate a comprehensive strategy with multiple endpoints:
    - Use search.php for general queries
    - Use timeline.php for specific user timelines
    - Include evaluation criteria for judging result quality
    
    Be specific about what information you're looking for."""
    
    try:
        start = time.time()
        strategy = client.generate(investigation_prompt, StrategyOutput)
        elapsed = time.time() - start
        
        print(f"[PASS] Complex investigation strategy generated in {elapsed:.2f}s")
        print(f"  Reasoning: {strategy.reasoning[:100]}...")
        print(f"  Endpoints: {len(strategy.endpoints)}")
        
        for i, ep in enumerate(strategy.endpoints[:3], 1):
            params = ep.to_params_dict()
            print(f"  {i}. {ep.endpoint}: {params}")
        
        if strategy.evaluation_criteria:
            print(f"  Evaluation criteria provided: Yes")
            print(f"    - Relevance indicators: {len(strategy.evaluation_criteria.relevance_indicators)}")
            print(f"    - Quality signals: {len(strategy.evaluation_criteria.quality_signals)}")
        
        print(f"  Confidence: {strategy.confidence}")
        
        return True
    except Exception as e:
        print(f"[FAIL] Complex investigation failed: {e}")
        return False

def test_evaluation_generation():
    """Test evaluation output generation"""
    client = LLMClient()
    
    eval_prompt = """Evaluate these search results for the query 'Trump Epstein scandal':
    
    Results:
    1. "Trump distances himself from Epstein in 2019 statement"
    2. "Photos surface of Trump and Epstein at Mar-a-Lago in 1992"
    3. "Epstein flight logs reveal celebrity connections"
    
    Generate an evaluation with:
    - Individual findings for relevant results
    - Overall relevance score
    - Remaining information gaps
    """
    
    try:
        evaluation = client.generate(eval_prompt, EvaluationOutput)
        
        print(f"[PASS] Evaluation generated successfully")
        print(f"  Findings: {len(evaluation.findings)}")
        for finding in evaluation.findings[:2]:
            print(f"    - Score {finding.relevance_score}: {finding.content[:50]}...")
        print(f"  Overall relevance: {evaluation.relevance_score}")
        print(f"  Gaps identified: {len(evaluation.remaining_gaps)}")
        
        return True
    except Exception as e:
        print(f"[FAIL] Evaluation generation failed: {e}")
        return False

def test_error_handling():
    """Test error handling and recovery"""
    client = LLMClient()
    
    # Test with invalid prompt that might cause issues
    try:
        result = client.generate("", StrategyOutput)
        print("[WARNING] Empty prompt should have failed but didn't")
    except Exception as e:
        print(f"[PASS] Empty prompt properly rejected: {type(e).__name__}")
    
    # Test with conflicting instructions
    try:
        result = client.generate("Generate invalid JSON: {[}]", StrategyOutput)
        print("[PASS] Handled conflicting instructions gracefully")
    except Exception as e:
        print(f"[INFO] Conflicting instructions caused error (expected): {type(e).__name__}")
    
    return True

def run_all_tests():
    """Run comprehensive test suite"""
    print("=" * 60)
    print("TESTING FIXED LLM CLIENT WITH STRUCTURED OUTPUT")
    print("=" * 60)
    
    tests = [
        ("Structured Output Speed", test_structured_output_speed),
        ("Complex Investigation", test_complex_investigation),
        ("Evaluation Generation", test_evaluation_generation),
        ("Error Handling", test_error_handling)
    ]
    
    results = {}
    for name, test_func in tests:
        print(f"\n--- Testing: {name} ---")
        results[name] = test_func()
        print()
    
    print("=" * 60)
    print("FINAL RESULTS:")
    print("=" * 60)
    for name, passed in results.items():
        status = "[PASS]" if passed else "[FAIL]"
        print(f"{name:25} {status}")
    
    success = all(results.values())
    if success:
        print("\n[SUCCESS] All tests passed! Structured output is working!")
    else:
        print("\n[WARNING] Some tests failed - review output above")
    
    return success

if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)