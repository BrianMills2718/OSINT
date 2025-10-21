import sys
import os

# Add v2 directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

def test_compare_old_vs_new():
    """Compare old and new implementations"""
    from strategy_corrected import IntelligentStrategy
    from strategy_litellm import IntelligentStrategyLiteLLM
    
    # Same inputs
    kwargs = {
        "investigation_goal": "Trump Epstein investigation",
        "current_understanding": "Initial search",
        "information_gaps": ["Recent mentions"],
        "search_history": []
    }
    
    # Old system
    print("\nTesting OLD system...")
    old_strategy = IntelligentStrategy("gemini-1.5-flash-latest")
    old_result = old_strategy.generate_strategy(**kwargs)
    
    # New system
    print("\nTesting NEW system...")
    new_strategy = IntelligentStrategyLiteLLM()
    new_result = new_strategy.generate_strategy(**kwargs)
    
    # Both should produce valid strategies
    assert old_result.get("endpoints"), "Old system failed to generate endpoints"
    assert new_result.get("endpoints"), "New system failed to generate endpoints"
    
    # Log for manual comparison
    print(f"\nOld result keys: {old_result.keys()}")
    print(f"Old endpoints count: {len(old_result.get('endpoints', []))}")
    print(f"\nNew result keys: {new_result.keys()}")
    print(f"New endpoints count: {len(new_result.get('endpoints', []))}")
    
    # Check structure compatibility
    assert "reasoning" in old_result and "reasoning" in new_result
    assert "user_update" in old_result and "user_update" in new_result
    assert "endpoints" in old_result and "endpoints" in new_result
    
    print("\n✅ Both systems work and are compatible!")
    
def test_evaluator_comparison():
    """Compare old and new evaluator implementations"""
    from evaluator import ResultEvaluator
    from evaluator_litellm import ResultEvaluatorLiteLLM
    
    # Test data
    kwargs = {
        "investigation_goal": "AI developments in 2024",
        "search_results": [
            {"text": "New AI model released", "author": "techuser"},
            {"text": "AI breakthrough in healthcare", "author": "medtech"}
        ],
        "endpoint": "search.php",
        "query": "AI 2024",
        "current_understanding": "Looking for recent AI news"
    }
    
    # Old evaluator
    print("\nTesting OLD evaluator...")
    old_evaluator = ResultEvaluator("gemini-1.5-flash-latest")
    old_result = old_evaluator.evaluate_results(**kwargs)
    
    # New evaluator
    print("\nTesting NEW evaluator...")
    new_evaluator = ResultEvaluatorLiteLLM()
    new_result = new_evaluator.evaluate_results(**kwargs)
    
    # Check results
    assert "findings" in old_result and "findings" in new_result
    assert "relevance_score" in old_result and "relevance_score" in new_result
    
    print(f"\nOld findings count: {len(old_result.get('findings', []))}")
    print(f"New findings count: {len(new_result.get('findings', []))}")
    
    print("\n✅ Both evaluators work and are compatible!")

if __name__ == "__main__":
    test_compare_old_vs_new()
    test_evaluator_comparison()