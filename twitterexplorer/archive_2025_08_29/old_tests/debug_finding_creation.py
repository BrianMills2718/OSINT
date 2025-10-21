"""Debug why findings aren't created despite acceptance"""
import sys
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
twitterexplorer_path = os.path.join(current_dir, 'twitterexplorer')
sys.path.insert(0, twitterexplorer_path)

from investigation_engine import InvestigationEngine, InvestigationConfig
from finding_evaluator_llm import LLMFindingEvaluator

def debug_findings():
    """Debug the finding creation issue"""
    
    print("=== DEBUGGING FINDING CREATION ===\n")
    
    api_key = "d72bcd77e2msh76c7e6cf37f0b89p1c51bcjsnaad0f6b01e4f"
    engine = InvestigationEngine(api_key)
    
    print(f"Graph mode: {engine.graph_mode}")
    
    # Hook the analysis to see what's happening
    original_analyze = engine._analyze_round_results_with_llm
    
    def debug_analyze(session, current_round, results):
        """Debug the analysis and finding creation"""
        print(f"\n=== ANALYZING ROUND {current_round.round_number} ===")
        print(f"Results to analyze: {len(results)}")
        print(f"Graph mode: {engine.graph_mode}")
        
        # Get the evaluator
        llm_client = None
        if hasattr(engine.llm_coordinator, 'llm'):
            llm_client = engine.llm_coordinator.llm
        elif hasattr(engine.llm_coordinator, 'llm_client'):
            llm_client = engine.llm_coordinator.llm_client
        
        finding_evaluator = LLMFindingEvaluator(llm_client)
        
        total_evaluated = 0
        total_significant = 0
        total_findings_before = len(session.accumulated_findings)
        
        for i, attempt in enumerate(results):
            if engine.graph_mode and hasattr(engine.llm_coordinator, 'graph'):
                if attempt.results_count > 0 and hasattr(attempt, '_raw_results'):
                    results_to_eval = attempt._raw_results[:5]  # Just check first 5
                    print(f"\n  Attempt {i+1}: {attempt.endpoint}")
                    print(f"    Raw results: {len(attempt._raw_results)}")
                    print(f"    Evaluating: {len(results_to_eval)}")
                    
                    # Sample result
                    if results_to_eval:
                        print(f"    Sample: '{results_to_eval[0].get('text', '')[:60]}...'")
                    
                    # Evaluate
                    assessments = finding_evaluator.evaluate_batch(
                        results_to_eval,
                        session.original_query
                    )
                    
                    total_evaluated += len(assessments)
                    
                    # Check significance
                    for j, assessment in enumerate(assessments):
                        if assessment.is_significant:
                            total_significant += 1
                            print(f"      Result {j+1}: SIGNIFICANT (score: {assessment.relevance_score:.2f})")
                        else:
                            print(f"      Result {j+1}: not significant (score: {assessment.relevance_score:.2f})")
                            print(f"        Reason: {assessment.reasoning[:80]}...")
        
        # Call original
        original_analyze(session, current_round, results)
        
        total_findings_after = len(session.accumulated_findings)
        findings_added = total_findings_after - total_findings_before
        
        print(f"\n  SUMMARY:")
        print(f"    Total evaluated: {total_evaluated}")
        print(f"    Total significant: {total_significant}")
        print(f"    Findings before: {total_findings_before}")
        print(f"    Findings after: {total_findings_after}")
        print(f"    Findings added: {findings_added}")
        
        if total_significant > 0 and findings_added == 0:
            print(f"\n    ERROR: {total_significant} results marked significant but 0 findings created!")
            print(f"    This suggests the finding creation code is not being reached.")
        elif total_significant == 0 and total_evaluated > 0:
            print(f"\n    ISSUE: All {total_evaluated} results marked as not significant")
            print(f"    The LLM evaluator is being too strict.")
    
    engine._analyze_round_results_with_llm = debug_analyze
    
    # Run a simple investigation
    config = InvestigationConfig(
        max_searches=3,  # Just one round
        pages_per_search=1
    )
    
    result = engine.conduct_investigation(
        "Latest news about artificial intelligence",
        config
    )
    
    print(f"\n=== FINAL RESULT ===")
    print(f"Total findings: {len(result.accumulated_findings)}")
    
    if len(result.accumulated_findings) == 0:
        print("\nPROBLEM CONFIRMED: No findings created")
        
        # Check rejection feedback for clues
        if hasattr(result, 'rejection_feedback_history') and result.rejection_feedback_history:
            feedback = result.rejection_feedback_history[0]
            print(f"\nRejection feedback:")
            print(f"  Evaluated: {feedback.total_evaluated}")
            print(f"  Accepted: {feedback.total_accepted}")
            print(f"  Rejected: {feedback.total_rejected}")
            print(f"  Rate: {feedback.rejection_rate:.1%}")
            
            if feedback.total_accepted > 0:
                print(f"\nERROR: {feedback.total_accepted} accepted but no findings!")
    else:
        print(f"\nSUCCESS: {len(result.accumulated_findings)} findings created")

if __name__ == "__main__":
    debug_findings()