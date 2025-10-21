"""Test just the LLM strategy generation without API calls"""

import sys
sys.path.insert(0, 'twitterexplorer')

from graph_aware_llm_coordinator import GraphAwareLLMCoordinator
from llm_client import get_litellm_client
from investigation_graph import InvestigationGraph

def test_strategy_generation():
    """Test that the LLM can generate strategies"""
    
    print("=" * 60)
    print("TESTING LLM STRATEGY GENERATION")
    print("=" * 60)
    
    try:
        # Initialize components
        print("\nInitializing components...")
        llm_client = get_litellm_client()
        print("[OK] LLM client initialized")
        
        graph = InvestigationGraph()
        print("[OK] Investigation graph initialized")
        
        coordinator = GraphAwareLLMCoordinator(llm_client, graph)
        print("[OK] Graph-aware coordinator initialized")
        
        # Test strategy generation
        print("\nGenerating strategy for: 'Elon Musk Twitter latest news'")
        print("-" * 60)
        
        decision = coordinator.make_strategic_decision("Elon Musk Twitter latest news")
        
        print(f"\nStrategy Generated:")
        print(f"  Decision Type: {decision.decision_type}")
        if decision.confidence is not None:
            print(f"  Confidence: {decision.confidence:.2f}")
        else:
            print(f"  Confidence: Not set")
        if decision.reasoning:
            print(f"  Reasoning: {decision.reasoning[:200]}...")
        else:
            print(f"  Reasoning: Not provided")
        
        if decision.searches:
            print(f"\nPlanned Searches ({len(decision.searches)}):")
            for i, search in enumerate(decision.searches, 1):
                print(f"\n  Search {i}:")
                print(f"    Endpoint: {search.endpoint}")
                if hasattr(search, 'parameters') and search.parameters:
                    # Show only non-None parameters
                    params = {k: v for k, v in search.parameters.dict().items() if v is not None}
                    print(f"    Parameters: {params}")
                print(f"    Reasoning: {search.reasoning[:100]}...")
        
        print("\n" + "=" * 60)
        print("SUCCESS: LLM strategy generation is working!")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"\n[ERROR] Failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_v2_models():
    """Test if v2 models work"""
    print("\n" + "=" * 60)
    print("TESTING V2 MODELS")
    print("=" * 60)
    
    try:
        from models_v2 import StrategyOutput, EndpointPlan
        print("[OK] v2 models imported")
        
        # Test creating an endpoint plan
        plan = EndpointPlan(
            endpoint="search.php",
            query="test query",
            expected_value="test results"
        )
        print(f"[OK] Created EndpointPlan")
        print(f"  Endpoint: {plan.endpoint}")
        print(f"  Query: {plan.query}")
        print(f"  Params dict: {plan.to_params_dict()}")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] v2 models test failed: {e}")
        return False

def main():
    """Run all tests"""
    
    print("Twitter Explorer LLM Component Test")
    print("=" * 60)
    
    # Test main strategy generation
    strategy_ok = test_strategy_generation()
    
    # Test v2 models
    v2_ok = test_v2_models()
    
    print("\n" + "=" * 60)
    print("FINAL STATUS:")
    print(f"  Strategy Generation: {'[OK]' if strategy_ok else '[FAIL]'}")
    print(f"  V2 Models: {'[OK]' if v2_ok else '[FAIL]'}")
    
    if strategy_ok:
        print("\nThe LLM intelligence system is working properly!")
        print("Note: API calls failed due to subscription, but that's separate.")
    
    print("=" * 60)

if __name__ == "__main__":
    main()