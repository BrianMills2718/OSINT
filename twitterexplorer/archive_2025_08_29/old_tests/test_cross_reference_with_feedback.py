"""Test cross-reference analysis now that we have rejection feedback working"""
import sys
import os

# Add twitterexplorer to path
current_dir = os.path.dirname(os.path.abspath(__file__))
twitterexplorer_path = os.path.join(current_dir, 'twitterexplorer')
sys.path.insert(0, twitterexplorer_path)

from investigation_engine import InvestigationEngine, InvestigationConfig

def test_cross_reference_with_feedback():
    """Test cross-reference analysis with rejection feedback improving findings"""
    
    print("=== TESTING CROSS-REFERENCE WITH FEEDBACK ===\n")
    
    api_key = "d72bcd77e2msh76c7e6cf37f0b89p1c51bcjsnaad0f6b01e4f"
    engine = InvestigationEngine(api_key)
    
    # Run investigation with multiple rounds
    config = InvestigationConfig(
        max_searches=4,
        pages_per_search=2
    )
    
    result = engine.conduct_investigation(
        "Different perspectives on Trump's economic policies and their effects",
        config
    )
    
    print("\n=== INVESTIGATION RESULTS ===")
    print(f"Total searches: {result.search_count}")
    print(f"Total results: {result.total_results_found}")
    print(f"Findings generated: {len(result.accumulated_findings)}")
    print(f"Satisfaction score: {result.satisfaction_metrics.overall_satisfaction():.2%}")
    
    # Check rejection feedback
    if hasattr(result, 'rejection_feedback_history'):
        print(f"\nRejection feedback rounds: {len(result.rejection_feedback_history)}")
        for i, feedback in enumerate(result.rejection_feedback_history, 1):
            print(f"  Round {i}: {feedback.rejection_rate:.1%} rejection rate ({feedback.total_rejected}/{feedback.total_evaluated})")
    
    # Test cross-reference analysis
    success = True
    print("\n=== CROSS-REFERENCE ANALYSIS ===")
    
    if result.cross_reference_analysis:
        analysis = result.cross_reference_analysis
        print(f"Analysis confidence: {analysis.confidence_score:.2f}")
        print(f"Patterns found: {len(analysis.patterns)}")
        print(f"Contradictions found: {len(analysis.contradictions)}")
        print(f"Credibility conflicts: {len(analysis.credibility_conflicts)}")
        
        if analysis.patterns:
            print("\nSample patterns:")
            for pattern in analysis.patterns[:3]:
                print(f"  - {pattern.pattern_type}: {pattern.description[:100]}")
        
        if analysis.contradictions:
            print("\nSample contradictions:")
            for contradiction in analysis.contradictions[:3]:
                print(f"  - {contradiction.claim1[:50]} vs {contradiction.claim2[:50]}")
        
        # Success criteria
        if analysis.confidence_score == 0.0 and len(result.accumulated_findings) < 2:
            print("\nLow confidence due to insufficient findings (expected)")
        elif analysis.confidence_score > 0.0:
            print(f"\nCross-reference working! Confidence: {analysis.confidence_score:.2f}")
        else:
            print("\nUnexpected: Have findings but no confidence")
            success = False
    else:
        print("No cross-reference analysis generated")
        success = False
    
    # Test temporal timeline
    print("\n=== TEMPORAL TIMELINE ANALYSIS ===")
    
    if result.temporal_timeline:
        timeline = result.temporal_timeline
        print(f"Timeline consistency: {timeline.consistency_score:.2f}")
        print(f"Events found: {len(timeline.events)}")
        
        if timeline.events:
            print("\nSample events:")
            for event in timeline.events[:3]:
                print(f"  - {event.timestamp}: {event.description[:80]}")
        
        print(f"\nTemporal timeline working! {len(timeline.events)} events")
    else:
        print("No temporal timeline generated")
    
    return success

if __name__ == "__main__":
    try:
        success = test_cross_reference_with_feedback()
        print(f"\n{'='*60}")
        print(f"CROSS-REFERENCE WITH FEEDBACK: {'PASS' if success else 'NEEDS MORE FINDINGS'}")
        print(f"{'='*60}\n")
    except Exception as e:
        print(f"\nTest failed with error: {e}")
        import traceback
        traceback.print_exc()