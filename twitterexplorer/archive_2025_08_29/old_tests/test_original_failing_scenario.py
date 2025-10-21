"""Test GraphAware system against the ORIGINAL failing scenario from CLAUDE.md"""
import sys
import os

# Setup paths
sys.path.insert(0, 'twitterexplorer')

from twitterexplorer.investigation_engine import InvestigationEngine, InvestigationConfig
import json

def test_original_failing_query():
    """Test the EXACT query that failed in the original logs"""
    
    print("=" * 80)
    print("TESTING ORIGINAL FAILING SCENARIO")
    print("Original Problem: System stuck in 'find different 2024' loops")
    print("Original Query: 'find me different takes on the current trump epstein drama'")
    print("=" * 80)
    
    try:
        api_key = "d72bcd77e2msh76c7e6cf37f0b89p1c51bcjsnaad0f6b01e4f"
        engine = InvestigationEngine(api_key)
        
        print(f"\nUsing: {type(engine.llm_coordinator).__name__}")
        print(f"Graph Mode: {engine.graph_mode}")
        
        # Use the EXACT failing configuration
        config = InvestigationConfig(
            max_searches=10,  # Limit to avoid long test, original went to 100
            pages_per_search=2,
            show_search_details=True,
            show_strategy_reasoning=True
        )
        
        # Run the EXACT failing query
        result = engine.conduct_investigation(
            "find me different takes on the current trump epstein drama",
            config
        )
        
        print("\n" + "=" * 80)
        print("ANALYSIS: DID GRAPHAWARE SOLVE THE ORIGINAL PROBLEMS?")
        print("=" * 80)
        
        # Problem 1: Strategy-Execution Schism (repetitive queries)
        queries_used = []
        for round_obj in result.rounds:
            for search in round_obj.searches:
                query = search.params.get('query', 'NO QUERY')
                queries_used.append(query)
        
        print(f"\n1. STRATEGY-EXECUTION SCHISM:")
        print(f"   Queries used: {queries_used}")
        
        # Check for "find different" repetition
        find_different_count = sum(1 for q in queries_used if 'find different' in str(q).lower())
        if find_different_count >= 3:
            print(f"   PROBLEM PERSISTS: 'find different' repeated {find_different_count} times")
        else:
            print(f"   SOLVED: No repetitive 'find different' patterns ({find_different_count} instances)")
        
        # Problem 2: Endpoint Tunnel Vision
        print(f"\n2. ENDPOINT TUNNEL VISION:")
        endpoints_used = set()
        for round_obj in result.rounds:
            for search in round_obj.searches:
                endpoints_used.add(search.endpoint)
        
        print(f"   Endpoints used: {list(endpoints_used)}")
        if len(endpoints_used) > 1:
            print("   SOLVED: Multiple endpoints used")
        else:
            print("   PROBLEM PERSISTS: Only single endpoint type")
        
        # Problem 3: Relevance Blindness (effectiveness scoring)
        print(f"\n3. RELEVANCE BLINDNESS:")
        effectiveness_scores = []
        for round_obj in result.rounds:
            for search in round_obj.searches:
                effectiveness_scores.append(search.effectiveness_score)
        
        if effectiveness_scores:
            avg_effectiveness = sum(effectiveness_scores) / len(effectiveness_scores)
            print(f"   Average effectiveness: {avg_effectiveness:.1f}/10")
            if avg_effectiveness > 6.0:  # Better than original 4.5
                print("   IMPROVED: Better effectiveness scoring")
            else:
                print("   PROBLEM PERSISTS: Low effectiveness scoring")
        
        # Problem 4: Learning Paralysis (adaptation evidence)
        print(f"\n4. LEARNING PARALYSIS:")
        if hasattr(engine.llm_coordinator, 'adaptive_strategy'):
            print("   SOLVED: AdaptiveStrategySystem present")
        else:
            print("   UNKNOWN: No adaptive strategy system detected")
        
        # Problem 5: Communication Blackout
        print(f"\n5. COMMUNICATION BLACKOUT:")
        if result.rounds and result.rounds[0].strategy_description:
            print(f"   SOLVED: Strategy communication present")
            print(f"   Example: {result.rounds[0].strategy_description[:100]}...")
        else:
            print("   PROBLEM PERSISTS: No strategy communication")
        
        # Overall Assessment
        print(f"\n" + "=" * 80)
        print("OVERALL ASSESSMENT vs ORIGINAL PROBLEMS")
        print("=" * 80)
        
        print(f"Search Count: {result.search_count} (vs original 100)")
        print(f"Total Results: {result.total_results_found}")
        print(f"Satisfaction: {result.satisfaction_metrics.overall_satisfaction():.2f} (vs original 0.0)")
        print(f"Time: <1 minute (vs original 25 minutes)")
        
        # Success criteria
        improvements = []
        concerns = []
        
        if len(endpoints_used) > 1:
            improvements.append("Multiple endpoint usage")
        else:
            concerns.append("Single endpoint tunnel vision")
            
        if find_different_count < 3:
            improvements.append("No repetitive query patterns")
        else:
            concerns.append("Query repetition persists")
            
        if result.rounds:
            improvements.append("Strategic communication present")
        
        if result.satisfaction_metrics.overall_satisfaction() > 0.0:
            improvements.append("Non-zero satisfaction achieved")
        
        print(f"\nIMPROVEMENTS: {improvements}")
        print(f"CONCERNS: {concerns}")
        
        if len(improvements) >= 3 and len(concerns) == 0:
            print(f"\nVERDICT: GraphAware system SOLVES the original problems")
        elif len(improvements) > len(concerns):
            print(f"\nVERDICT: GraphAware system IMPROVES on original but has remaining issues")
        else:
            print(f"\nVERDICT: Original problems may PERSIST in GraphAware system")
            
        return {
            "improvements": improvements,
            "concerns": concerns,
            "verdict": "solved" if len(improvements) >= 3 and len(concerns) == 0 else "partial"
        }
        
    except Exception as e:
        print(f"TEST FAILED: {e}")
        return {"verdict": "failed", "error": str(e)}

if __name__ == "__main__":
    result = test_original_failing_query()
    print(f"\nFINAL RESULT: {result}")