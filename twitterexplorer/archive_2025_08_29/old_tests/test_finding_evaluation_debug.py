"""Debug why findings aren't being created despite low rejection rate"""
import sys
import os

# Add twitterexplorer to path
current_dir = os.path.dirname(os.path.abspath(__file__))
twitterexplorer_path = os.path.join(current_dir, 'twitterexplorer')
sys.path.insert(0, twitterexplorer_path)

from investigation_engine import InvestigationEngine, InvestigationConfig

def test_finding_evaluation_debug():
    """Debug finding evaluation process"""
    
    print("=== DEBUGGING FINDING EVALUATION ===\n")
    
    api_key = "d72bcd77e2msh76c7e6cf37f0b89p1c51bcjsnaad0f6b01e4f"
    engine = InvestigationEngine(api_key)
    
    # Hook to debug evaluation
    original_analyze = engine._analyze_round_results_with_llm
    
    def analyze_with_deep_debug(session, current_round, results):
        """Deep debug of evaluation"""
        print(f"\n>>> Analyzing round {current_round.round_number}")
        
        from finding_evaluator_llm import LLMFindingEvaluator
        
        # Get LLM client
        llm_client = None
        if hasattr(engine.llm_coordinator, 'llm'):
            llm_client = engine.llm_coordinator.llm
        elif hasattr(engine.llm_coordinator, 'llm_client'):
            llm_client = engine.llm_coordinator.llm_client
            
        finding_evaluator = LLMFindingEvaluator(llm_client)
        
        for i, attempt in enumerate(results):
            if attempt.results_count > 0 and hasattr(attempt, '_raw_results'):
                print(f"\n  Attempt {i+1}: {attempt.endpoint}")
                results_to_eval = attempt._raw_results[:5]  # Just check first 5
                
                print(f"    Evaluating {len(results_to_eval)} results...")
                
                # Show sample raw result
                if results_to_eval:
                    print(f"    Sample raw result: {results_to_eval[0].get('text', '')[:100]}...")
                
                # Evaluate
                try:
                    assessments = finding_evaluator.evaluate_batch(
                        results_to_eval,
                        session.original_query
                    )
                    
                    print(f"    Assessments generated: {len(assessments)}")
                    
                    # Check assessments
                    significant_count = sum(1 for a in assessments if a.is_significant)
                    print(f"    Significant findings: {significant_count}/{len(assessments)}")
                    
                    # Show details of first assessment
                    if assessments:
                        first = assessments[0]
                        print(f"    First assessment:")
                        print(f"      is_significant: {first.is_significant}")
                        print(f"      relevance_score: {first.relevance_score}")
                        print(f"      reasoning: {first.reasoning[:100]}...")
                        
                except Exception as e:
                    print(f"    ERROR in evaluation: {e}")
        
        # Call original
        original_analyze(session, current_round, results)
        
        print(f"\n  After analysis:")
        print(f"    Total findings: {len(session.accumulated_findings)}")
        print(f"    Graph mode: {engine.graph_mode}")
    
    engine._analyze_round_results_with_llm = analyze_with_deep_debug
    
    # Run simple investigation
    config = InvestigationConfig(
        max_searches=1,
        pages_per_search=1
    )
    
    result = engine.conduct_investigation(
        "Trump economic policies",
        config
    )
    
    print("\n=== FINAL RESULTS ===")
    print(f"Total findings: {len(result.accumulated_findings)}")
    print(f"Graph mode was: {engine.graph_mode}")

if __name__ == "__main__":
    test_finding_evaluation_debug()