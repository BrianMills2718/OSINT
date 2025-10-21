"""Full integration test for LiteLLM structured output implementation"""

import os
import sys
import json
import time
from datetime import datetime

# Add v2 to path
sys.path.insert(0, r'C:\Users\Brian\projects\twitterexplorer\v2')

from llm_client import LLMClient
from models import StrategyOutput, EvaluationOutput
from strategy_litellm import IntelligentStrategyLiteLLM
from evaluator_litellm import ResultEvaluatorLiteLLM

def test_structured_output_mode():
    """Verify we're using structured output, not JSON mode"""
    client = LLMClient()
    
    # Check the generate method
    import inspect
    source = inspect.getsource(client.generate)
    
    # Check for structured output indicators
    has_structured = "response_format=response_model" in source
    has_json_mode = '"type": "json_object"' in source
    
    print("Structured Output Check:")
    print(f"  Uses response_format=response_model: {has_structured}")
    print(f"  Falls back to JSON mode: {has_json_mode}")
    
    if has_structured and not has_json_mode:
        print("  [PASS] Using true structured output!")
    elif has_json_mode:
        print("  [INFO] JSON mode available as fallback")
    else:
        print("  [FAIL] Not using structured output properly")
    
    return has_structured

def test_schema_compatibility():
    """Test that our models work with Gemini"""
    from models import EndpointPlan
    
    # Check if EndpointPlan has the problematic Dict[str, Any]
    import inspect
    source = inspect.getsource(EndpointPlan)
    
    has_dict_any = "Dict[str, Any]" in source
    has_flattened = "query: str" in source or "screenname: str" in source
    
    print("\nSchema Compatibility Check:")
    print(f"  Has problematic Dict[str, Any]: {has_dict_any}")
    print(f"  Has flattened fields: {has_flattened}")
    
    if not has_dict_any and has_flattened:
        print("  [PASS] Schema is Gemini-compatible!")
    else:
        print("  [FAIL] Schema may have compatibility issues")
    
    return not has_dict_any and has_flattened

def test_strategy_generation():
    """Test the strategy generator with real LLM"""
    strategy_gen = IntelligentStrategyLiteLLM()
    
    print("\nStrategy Generation Test:")
    print("  Generating strategy for 'AI developments 2024'...")
    
    start = time.time()
    try:
        result = strategy_gen.generate_strategy(
            investigation_goal="Find recent AI developments in 2024",
            current_understanding="Need to explore latest AI breakthroughs",
            information_gaps=["GPT updates", "Google AI news", "OpenAI announcements"],
            search_history=[],
            max_endpoints_per_round=3
        )
        elapsed = time.time() - start
        
        print(f"  [PASS] Strategy generated in {elapsed:.2f}s")
        print(f"  Reasoning: {result['reasoning'][:100]}...")
        print(f"  Endpoints: {len(result['endpoints'])}")
        
        # Check if endpoints have proper structure
        for ep in result['endpoints']:
            if 'params' in ep:
                print(f"    - {ep['endpoint']}: {ep['params']}")
            else:
                print(f"    - {ep['endpoint']}: (no params)")
        
        print(f"  Confidence: {result.get('confidence', 'N/A')}")
        
        return True
    except Exception as e:
        print(f"  [FAIL] Strategy generation failed: {e}")
        return False

def test_evaluation_generation():
    """Test the evaluator with real LLM"""
    evaluator = ResultEvaluatorLiteLLM()
    
    print("\nEvaluation Generation Test:")
    print("  Evaluating mock search results...")
    
    mock_results = [
        {"text": "OpenAI releases GPT-5 in 2024", "author": "tech_news"},
        {"text": "Google announces Gemini Ultra", "author": "google_ai"},
        {"text": "Anthropic Claude 3 breaks records", "author": "anthropic"}
    ]
    
    start = time.time()
    try:
        result = evaluator.evaluate_results(
            investigation_goal="Find AI developments",
            search_results=mock_results,
            endpoint="search.php",
            query="AI 2024",
            current_understanding="Exploring latest AI news",
            evaluation_criteria={"relevance_indicators": ["GPT", "Gemini", "Claude"]}
        )
        elapsed = time.time() - start
        
        print(f"  [PASS] Evaluation generated in {elapsed:.2f}s")
        print(f"  Findings: {len(result.get('findings', []))}")
        print(f"  Relevance score: {result.get('relevance_score', 0)}")
        print(f"  Remaining gaps: {len(result.get('remaining_gaps', []))}")
        
        return True
    except Exception as e:
        print(f"  [FAIL] Evaluation generation failed: {e}")
        return False

def test_performance_comparison():
    """Compare structured output vs JSON mode performance"""
    client = LLMClient()
    
    print("\nPerformance Comparison:")
    
    # Simple prompt for testing
    prompt = "Generate a strategy for finding information about 'quantum computing breakthroughs'"
    
    # Test structured output
    structured_times = []
    for i in range(3):
        start = time.time()
        try:
            result = client.generate(prompt, StrategyOutput)
            structured_times.append(time.time() - start)
            print(f"  Structured attempt {i+1}: {structured_times[-1]:.2f}s")
        except Exception as e:
            print(f"  Structured attempt {i+1} failed: {e}")
    
    # Test JSON mode fallback if available
    if hasattr(client, '_generate_with_json_mode'):
        json_times = []
        for i in range(3):
            start = time.time()
            try:
                result = client._generate_with_json_mode(prompt, StrategyOutput, 0.7)
                json_times.append(time.time() - start)
                print(f"  JSON mode attempt {i+1}: {json_times[-1]:.2f}s")
            except Exception as e:
                print(f"  JSON mode attempt {i+1} failed: {e}")
        
        if structured_times and json_times:
            avg_structured = sum(structured_times) / len(structured_times)
            avg_json = sum(json_times) / len(json_times)
            improvement = ((avg_json - avg_structured) / avg_json) * 100
            print(f"\n  Average structured: {avg_structured:.2f}s")
            print(f"  Average JSON mode: {avg_json:.2f}s")
            print(f"  Performance difference: {improvement:+.1f}%")
    
    return len(structured_times) > 0

def test_error_handling():
    """Test error handling and recovery"""
    client = LLMClient()
    
    print("\nError Handling Test:")
    
    # Test with invalid model
    try:
        bad_client = LLMClient(model="invalid/model")
        result = bad_client.generate("test", StrategyOutput)
        print("  [FAIL] Should have failed with invalid model")
        return False
    except Exception as e:
        print(f"  [PASS] Invalid model properly rejected: {type(e).__name__}")
    
    # Test with empty prompt
    try:
        result = client.generate("", StrategyOutput)
        print("  [FAIL] Should have failed with empty prompt")
        return False
    except Exception as e:
        print(f"  [PASS] Empty prompt properly rejected: {type(e).__name__}")
    
    return True

def run_all_tests():
    """Run comprehensive integration tests"""
    print("=" * 60)
    print("LITELLM STRUCTURED OUTPUT INTEGRATION TEST")
    print("=" * 60)
    print(f"Test started: {datetime.now()}")
    print()
    
    tests = [
        ("Structured Output Mode", test_structured_output_mode),
        ("Schema Compatibility", test_schema_compatibility),
        ("Strategy Generation", test_strategy_generation),
        ("Evaluation Generation", test_evaluation_generation),
        ("Performance Comparison", test_performance_comparison),
        ("Error Handling", test_error_handling)
    ]
    
    results = {}
    for name, test_func in tests:
        print(f"\n{'='*60}")
        print(f"Running: {name}")
        print('='*60)
        try:
            results[name] = test_func()
        except Exception as e:
            print(f"Test crashed: {e}")
            results[name] = False
        print()
    
    print("=" * 60)
    print("FINAL RESULTS:")
    print("=" * 60)
    
    for name, passed in results.items():
        status = "[PASS]" if passed else "[FAIL]"
        print(f"{name:25} {status}")
    
    success_count = sum(1 for p in results.values() if p)
    total_count = len(results)
    success_rate = (success_count / total_count) * 100
    
    print("\n" + "=" * 60)
    print(f"Success Rate: {success_count}/{total_count} ({success_rate:.0f}%)")
    
    if success_rate == 100:
        print("[SUCCESS] All tests passed! LiteLLM structured output is working perfectly!")
    elif success_rate >= 80:
        print("[MOSTLY SUCCESS] Most tests passed, minor issues remain")
    else:
        print("[NEEDS WORK] Significant issues found")
    
    print("=" * 60)
    
    return success_rate == 100

if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)