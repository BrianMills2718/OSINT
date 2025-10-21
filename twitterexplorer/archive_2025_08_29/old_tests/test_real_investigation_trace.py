"""Run a real investigation and capture the full trace for critical analysis"""
import sys
import os

# Add twitterexplorer to path
current_dir = os.path.dirname(os.path.abspath(__file__))
twitterexplorer_path = os.path.join(current_dir, 'twitterexplorer')
sys.path.insert(0, twitterexplorer_path)

from investigation_engine import InvestigationEngine, InvestigationConfig

def test_real_investigation():
    """Run a real investigation with detailed tracing"""
    
    print("=== REAL INVESTIGATION WITH FULL TRACE ===\n")
    
    api_key = "d72bcd77e2msh76c7e6cf37f0b89p1c51bcjsnaad0f6b01e4f"
    engine = InvestigationEngine(api_key)
    
    # Hook to capture EVERYTHING
    original_generate = engine._generate_strategy
    original_analyze = engine._analyze_round_results_with_llm
    
    round_count = [0]
    
    def generate_with_full_trace(session):
        """Trace strategy generation"""
        round_count[0] += 1
        print(f"\n{'='*60}")
        print(f"ROUND {round_count[0]} - STRATEGY GENERATION")
        print(f"{'='*60}")
        
        # Check rejection context
        if session.rejection_feedback_history:
            recent = session.rejection_feedback_history[-1]
            print(f"\nREJECTION FEEDBACK FROM PREVIOUS ROUND:")
            print(f"  Rejection rate: {recent.rejection_rate:.1%}")
            print(f"  Total evaluated: {recent.total_evaluated}")
            print(f"  Rejected: {recent.total_rejected}")
            
            if recent.rejection_samples:
                print(f"\n  Sample rejections:")
                for i, sample in enumerate(recent.rejection_samples[:2], 1):
                    print(f"    {i}. Text: '{sample['text'][:60]}...'")
                    print(f"       Reason: {sample['reason'][:80]}...")
            
            # Get the context string
            context = recent.to_strategy_context()
            print(f"\n  Context passed to LLM:")
            print(f"    {context[:200]}...")
        else:
            print("\nNO REJECTION FEEDBACK YET")
        
        # Call original and capture result
        result = original_generate(session)
        
        print(f"\nSTRATEGY DECIDED:")
        print(f"  Searches planned: {len(result.get('searches', []))}")
        for i, search in enumerate(result.get('searches', []), 1):
            print(f"    {i}. {search['endpoint']}: {search['params'].get('query', search['params'].get('screenname', 'N/A'))}")
        
        return result
    
    def analyze_with_full_trace(session, current_round, results):
        """Trace result analysis"""
        print(f"\n{'='*60}")
        print(f"ROUND {current_round.round_number} - RESULT ANALYSIS")
        print(f"{'='*60}")
        
        total_raw_results = 0
        for attempt in results:
            if hasattr(attempt, '_raw_results'):
                total_raw_results += len(attempt._raw_results)
        
        print(f"\nRESULTS TO ANALYZE:")
        print(f"  Search attempts: {len(results)}")
        print(f"  Total raw results: {total_raw_results}")
        
        # Call original
        original_analyze(session, current_round, results)
        
        print(f"\nAFTER ANALYSIS:")
        print(f"  Total findings saved: {len(session.accumulated_findings)}")
        
        if session.rejection_feedback_history:
            recent = session.rejection_feedback_history[-1]
            print(f"  Rejection rate this round: {recent.rejection_rate:.1%}")
            
            # Show what was accepted vs rejected
            if recent.total_accepted > 0:
                print(f"  ACCEPTED: {recent.total_accepted} results as significant")
            if recent.total_rejected > 0:
                print(f"  REJECTED: {recent.total_rejected} results as irrelevant")
                if recent.rejection_themes:
                    print(f"  Themes in rejections: {', '.join(recent.rejection_themes)}")
    
    engine._generate_strategy = generate_with_full_trace
    engine._analyze_round_results_with_llm = analyze_with_full_trace
    
    # Run a focused investigation
    config = InvestigationConfig(
        max_searches=6,  # Allow multiple rounds
        pages_per_search=1
    )
    
    # Use a query that should generate rejections and adaptations
    result = engine.conduct_investigation(
        "Elon Musk Twitter acquisition impact on free speech debate",
        config
    )
    
    print(f"\n{'='*60}")
    print("FINAL INVESTIGATION RESULTS")
    print(f"{'='*60}")
    print(f"Total searches: {result.search_count}")
    print(f"Total results evaluated: {result.total_results_found}")
    print(f"Total findings saved: {len(result.accumulated_findings)}")
    print(f"Satisfaction score: {result.satisfaction_metrics.overall_satisfaction():.2%}")
    
    # Analyze the rejection feedback evolution
    if hasattr(result, 'rejection_feedback_history'):
        print(f"\n{'='*60}")
        print("REJECTION FEEDBACK EVOLUTION")
        print(f"{'='*60}")
        
        for i, feedback in enumerate(result.rejection_feedback_history, 1):
            print(f"\nRound {i}:")
            print(f"  Rejection rate: {feedback.rejection_rate:.1%}")
            print(f"  Accepted/Rejected: {feedback.total_accepted}/{feedback.total_rejected}")
        
        # Check if rejection feedback actually influenced queries
        print(f"\n{'='*60}")
        print("DID REJECTION FEEDBACK ACTUALLY HELP?")
        print(f"{'='*60}")
        
        if len(result.search_history) > 1:
            queries = [s.params.get('query', '') for s in result.search_history if s.params.get('query')]
            unique_queries = set(queries)
            
            print(f"\nQuery diversity: {len(unique_queries)}/{len(queries)} unique")
            print("\nQuery evolution:")
            for i, q in enumerate(queries[:6], 1):
                print(f"  {i}. {q[:60]}...")
            
            # Check if later queries avoided rejected themes
            if result.rejection_feedback_history:
                first_rejection_rate = result.rejection_feedback_history[0].rejection_rate
                last_rejection_rate = result.rejection_feedback_history[-1].rejection_rate if len(result.rejection_feedback_history) > 1 else first_rejection_rate
                
                print(f"\nRejection rate improvement:")
                print(f"  First round: {first_rejection_rate:.1%}")
                print(f"  Last round: {last_rejection_rate:.1%}")
                
                if last_rejection_rate < first_rejection_rate:
                    print("  ✓ IMPROVEMENT - Rejection rate decreased")
                elif last_rejection_rate > first_rejection_rate:
                    print("  ✗ WORSE - Rejection rate increased")
                else:
                    print("  = SAME - No change in rejection rate")

if __name__ == "__main__":
    test_real_investigation()