"""Test rejection feedback - show what's being filtered out"""
import sys
import os
import json

current_dir = os.path.dirname(os.path.abspath(__file__))
twitterexplorer_path = os.path.join(current_dir, 'twitterexplorer')
sys.path.insert(0, twitterexplorer_path)

from investigation_engine import InvestigationEngine, InvestigationConfig
from finding_evaluator_llm import LLMFindingEvaluator

def test_rejection_visibility():
    print("=== TESTING WHAT GETS REJECTED ===\n")
    
    api_key = "d72bcd77e2msh76c7e6cf37f0b89p1c51bcjsnaad0f6b01e4f"
    engine = InvestigationEngine(api_key)
    
    # Hook to see rejections
    original_analyze = engine._analyze_round_results_with_llm
    rejection_log = []
    
    def analyze_with_rejection_tracking(session, current_round, results):
        """Track what gets rejected and why"""
        
        # Get the finding evaluator
        llm_client = None
        if hasattr(engine.llm_coordinator, 'llm'):
            llm_client = engine.llm_coordinator.llm
        elif hasattr(engine.llm_coordinator, 'llm_client'):
            llm_client = engine.llm_coordinator.llm_client
        finding_evaluator = LLMFindingEvaluator(llm_client)
        
        for attempt in results:
            if attempt.results_count > 0 and hasattr(attempt, '_raw_results'):
                results_to_eval = attempt._raw_results[:20]
                
                print(f"\n>>> Evaluating {len(results_to_eval)} results for: {session.original_query}")
                
                try:
                    assessments = finding_evaluator.evaluate_batch(
                        results_to_eval,
                        session.original_query
                    )
                    
                    # Track rejections
                    accepted = 0
                    rejected = 0
                    rejection_samples = []
                    
                    for raw_result, assessment in zip(results_to_eval, assessments):
                        if assessment.is_significant:
                            accepted += 1
                        else:
                            rejected += 1
                            # Save rejection info
                            text = raw_result.get('text', '')[:100]
                            rejection_samples.append({
                                'text_preview': text,
                                'relevance_score': assessment.relevance_score,
                                'reasoning': assessment.reasoning
                            })
                    
                    print(f"ACCEPTED: {accepted}, REJECTED: {rejected}")
                    
                    if rejection_samples:
                        print("\nREJECTED SAMPLES:")
                        for i, rej in enumerate(rejection_samples[:3], 1):
                            print(f"  {i}. Score: {rej['relevance_score']:.2f}")
                            print(f"     Text: {rej['text_preview']}")
                            print(f"     Why rejected: {rej['reasoning'][:150]}")
                        
                        # This is what should be passed to next strategy!
                        rejection_log.append({
                            'round': current_round.round_number,
                            'rejected_count': rejected,
                            'rejection_themes': rejection_samples[:3]
                        })
                        
                except Exception as e:
                    print(f"Evaluation error: {e}")
        
        # Call original
        original_analyze(session, current_round, results)
    
    engine._analyze_round_results_with_llm = analyze_with_rejection_tracking
    
    # Run investigation
    config = InvestigationConfig(max_searches=2, pages_per_search=1)
    result = engine.conduct_investigation("Trump Epstein connection investigation", config)
    
    print("\n=== REJECTION FEEDBACK SUMMARY ===")
    print(f"Total searches: {result.search_count}")
    print(f"Total findings saved: {len(result.accumulated_findings)}")
    
    if rejection_log:
        print("\nREJECTION PATTERNS:")
        for log_entry in rejection_log:
            print(f"\nRound {log_entry['round']}: {log_entry['rejected_count']} rejections")
            print("What was filtered out (this should inform next query):")
            for theme in log_entry['rejection_themes']:
                print(f"  - {theme['text_preview'][:50]}...")
    
    print("\n💡 INSIGHT: The LLM coordinator should receive this rejection info!")
    print("   It could then avoid similar irrelevant queries in the next round.")

if __name__ == "__main__":
    test_rejection_visibility()