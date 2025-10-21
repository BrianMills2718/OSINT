"""Test that rejection feedback is properly integrated into strategy generation"""
import sys
import os

# Add twitterexplorer to path
current_dir = os.path.dirname(os.path.abspath(__file__))
twitterexplorer_path = os.path.join(current_dir, 'twitterexplorer')
sys.path.insert(0, twitterexplorer_path)

from investigation_engine import InvestigationEngine, InvestigationConfig

def test_rejection_feedback_integration():
    """Test that rejection feedback improves subsequent queries"""
    
    print("=== TESTING REJECTION FEEDBACK INTEGRATION ===\n")
    
    api_key = "d72bcd77e2msh76c7e6cf37f0b89p1c51bcjsnaad0f6b01e4f"
    engine = InvestigationEngine(api_key)
    
    # Hook to monitor rejection feedback
    original_generate = engine._generate_strategy
    rejection_contexts = []
    
    def generate_with_monitoring(session):
        """Monitor rejection context being passed to strategy"""
        # Check if rejection context exists
        if session.rejection_feedback_history:
            recent_feedback = session.rejection_feedback_history[-1]
            context = recent_feedback.to_strategy_context()
            rejection_contexts.append(context)
            print(f"\n>>> Round {len(rejection_contexts)} Rejection Context:")
            print(f"    {context[:200]}...")
        
        # Call original
        return original_generate(session)
    
    engine._generate_strategy = generate_with_monitoring
    
    # Run investigation with limited searches
    config = InvestigationConfig(
        max_searches=3,
        pages_per_search=1
    )
    
    result = engine.conduct_investigation(
        "Trump Epstein connection investigation latest developments",
        config
    )
    
    print("\n=== RESULTS ===")
    print(f"Total searches: {result.search_count}")
    print(f"Findings generated: {len(result.accumulated_findings)}")
    print(f"Rejection feedback rounds: {len(rejection_contexts)}")
    
    # Verify rejection feedback was generated and passed
    success = True
    
    if len(rejection_contexts) == 0:
        print("\n❌ FAIL: No rejection feedback generated")
        success = False
    else:
        print(f"\n✅ Rejection feedback generated for {len(rejection_contexts)} rounds")
        
        # Check that rejection context contains useful info
        for i, context in enumerate(rejection_contexts, 1):
            print(f"\n   Round {i} feedback:")
            if "rejected" in context.lower() and "%" in context:
                print(f"   ✅ Contains rejection rate")
            else:
                print(f"   ❌ Missing rejection rate")
                success = False
                
            if "examples of rejected" in context.lower() or "common" in context.lower():
                print(f"   ✅ Contains rejection examples or themes")
            else:
                print(f"   ❌ Missing rejection examples")
    
    # Check if rejection feedback affected queries
    if result.search_history and len(result.search_history) > 1:
        first_query = result.search_history[0].params.get('query', '')
        last_query = result.search_history[-1].params.get('query', '')
        
        if first_query != last_query:
            print(f"\n✅ Queries evolved: '{first_query}' -> '{last_query}'")
        else:
            print(f"\n⚠️ Queries didn't evolve despite feedback")
    
    return success

if __name__ == "__main__":
    try:
        success = test_rejection_feedback_integration()
        print(f"\n{'='*60}")
        print(f"REJECTION FEEDBACK INTEGRATION: {'PASS' if success else 'FAIL'}")
        print(f"{'='*60}\n")
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()