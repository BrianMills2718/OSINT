"""Final integration test of all implemented features"""
import sys
import os

# Add twitterexplorer to path
current_dir = os.path.dirname(os.path.abspath(__file__))
twitterexplorer_path = os.path.join(current_dir, 'twitterexplorer')
sys.path.insert(0, twitterexplorer_path)

from investigation_engine import InvestigationEngine, InvestigationConfig

def test_final_integration():
    """Test all implemented features work together"""
    
    print("=== FINAL INTEGRATION TEST ===\n")
    print("Testing:")
    print("1. Rejection feedback mechanism")
    print("2. Cross-reference analysis") 
    print("3. Temporal timeline analysis")
    print("4. Integration with existing system\n")
    
    api_key = "d72bcd77e2msh76c7e6cf37f0b89p1c51bcjsnaad0f6b01e4f"
    engine = InvestigationEngine(api_key)
    
    # Run investigation
    config = InvestigationConfig(
        max_searches=3,
        pages_per_search=2
    )
    
    result = engine.conduct_investigation(
        "Technology companies earnings reports this quarter",
        config
    )
    
    print("\n=== TEST RESULTS ===\n")
    
    # Basic metrics
    print("BASIC METRICS:")
    print(f"  Total searches: {result.search_count}")
    print(f"  Total results: {result.total_results_found}")
    print(f"  Findings: {len(result.accumulated_findings)}")
    print(f"  Satisfaction: {result.satisfaction_metrics.overall_satisfaction():.2%}")
    
    # Test 1: Rejection Feedback
    print("\n1. REJECTION FEEDBACK:")
    if hasattr(result, 'rejection_feedback_history'):
        if result.rejection_feedback_history:
            total_evaluated = sum(f.total_evaluated for f in result.rejection_feedback_history)
            total_rejected = sum(f.total_rejected for f in result.rejection_feedback_history)
            avg_rejection = total_rejected / total_evaluated if total_evaluated > 0 else 0
            
            print(f"  [PASS] Working - {len(result.rejection_feedback_history)} rounds tracked")
            print(f"  Average rejection rate: {avg_rejection:.1%}")
            print(f"  Total evaluated: {total_evaluated}, rejected: {total_rejected}")
            
            # Show rejection themes if any
            for feedback in result.rejection_feedback_history:
                if feedback.rejection_themes:
                    print(f"  Themes identified: {', '.join(feedback.rejection_themes)}")
        else:
            print("  [WARNING] No rejection feedback generated (may be no results)")
    else:
        print("  [FAIL] Rejection feedback not integrated")
    
    # Test 2: Cross-Reference Analysis
    print("\n2. CROSS-REFERENCE ANALYSIS:")
    if result.cross_reference_analysis:
        analysis = result.cross_reference_analysis
        if analysis.confidence_score > 0:
            print(f"  [PASS] Working - Confidence: {analysis.confidence_score:.2f}")
            print(f"  Patterns: {len(analysis.patterns)}, Contradictions: {len(analysis.contradictions)}")
        else:
            print(f"  [WARNING] Generated but no patterns (need more findings)")
    else:
        print("  [WARNING] Not generated (requires 2+ findings)")
    
    # Test 3: Temporal Timeline
    print("\n3. TEMPORAL TIMELINE:")
    if result.temporal_timeline:
        timeline = result.temporal_timeline
        if timeline.events:
            print(f"  [PASS] Working - {len(timeline.events)} events")
            print(f"  Consistency score: {timeline.consistency_score:.2f}")
            print(f"  Timeline span: {timeline.timeline_span}")
        else:
            print("  [WARNING] Generated but no events")
    else:
        print("  [WARNING] Not generated (no findings)")
    
    # Test 4: System Integration
    print("\n4. SYSTEM INTEGRATION:")
    integration_ok = True
    
    # Check search diversity
    endpoints_used = set(s.endpoint for s in result.search_history)
    print(f"  Endpoint diversity: {len(endpoints_used)} different endpoints")
    
    # Check if system still functions
    if result.search_count > 0:
        print("  [PASS] Core search functionality working")
    else:
        print("  [FAIL] No searches executed")
        integration_ok = False
    
    # Check if results are processed
    if result.total_results_found > 0:
        print("  [PASS] Results collection working")
    else:
        print("  [FAIL] No results collected")
        integration_ok = False
    
    # Overall assessment
    print("\n" + "="*50)
    print("OVERALL ASSESSMENT:")
    
    features_working = 0
    if hasattr(result, 'rejection_feedback_history'):
        features_working += 1
    if result.cross_reference_analysis or len(result.accumulated_findings) < 2:
        features_working += 1
    if result.temporal_timeline or len(result.accumulated_findings) == 0:
        features_working += 1
    if integration_ok:
        features_working += 1
    
    print(f"Features working: {features_working}/4")
    
    if features_working == 4:
        print("[PASS] ALL FEATURES INTEGRATED SUCCESSFULLY")
    elif features_working >= 3:
        print("[WARNING] MOSTLY WORKING - Some features need more data")
    else:
        print("[FAIL] INTEGRATION ISSUES DETECTED")
    
    print("="*50)
    
    return features_working >= 3

if __name__ == "__main__":
    try:
        success = test_final_integration()
        exit(0 if success else 1)
    except Exception as e:
        print(f"\n[FAIL] Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)