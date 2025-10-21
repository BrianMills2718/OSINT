"""Test advanced features integration - Cross-Reference and Temporal Timeline together"""
import sys
import os

# Add the twitterexplorer subdirectory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
twitterexplorer_path = os.path.join(current_dir, 'twitterexplorer')
sys.path.insert(0, twitterexplorer_path)

from investigation_engine import InvestigationEngine, InvestigationConfig

def test_advanced_features_integration():
    """EVIDENCE: Test both cross-reference and temporal timeline features working together"""
    
    print("=== ADVANCED FEATURES INTEGRATION TEST ===")
    
    api_key = "d72bcd77e2msh76c7e6cf37f0b89p1c51bcjsnaad0f6b01e4f"
    engine = InvestigationEngine(api_key)
    
    # Run investigation that should generate both analyses
    config = InvestigationConfig(max_searches=2, pages_per_search=2)
    result = engine.conduct_investigation("Recent SpaceX and Tesla developments", config)
    
    print(f"\\nGenerated {len(result.accumulated_findings)} findings for analysis")
    
    # Test both features are present and working
    success_count = 0
    
    # Test 1: Cross-reference analysis
    if hasattr(result, 'cross_reference_analysis') and result.cross_reference_analysis is not None:
        analysis = result.cross_reference_analysis
        print(f"PASS Cross-reference analysis: {len(analysis.patterns)} patterns, confidence: {analysis.confidence_score:.2f}")
        success_count += 1
    else:
        print("FAIL Cross-reference analysis: Missing or None")
    
    # Test 2: Temporal timeline analysis  
    if hasattr(result, 'temporal_timeline') and result.temporal_timeline is not None:
        timeline = result.temporal_timeline
        print(f"PASS Temporal timeline: {len(timeline.events)} events, consistency: {timeline.consistency_score:.2f}")
        success_count += 1
    else:
        print("FAIL Temporal timeline: Missing or None")
    
    # Test 3: Integration - both features working together
    if success_count == 2:
        print("PASS Integration: Both features working together")
        success_count += 1
    else:
        print("FAIL Integration: Not all features working")
    
    # Test 4: Existing functionality preservation
    satisfaction = result.satisfaction_metrics.overall_satisfaction()
    if satisfaction > 0.0:
        print(f"PASS Existing functionality: Satisfaction {satisfaction:.3f} preserved")
        success_count += 1
    else:
        print(f"FAIL Existing functionality: Satisfaction {satisfaction:.3f} degraded")
    
    # Test 5: Performance check
    search_count = result.search_count
    if search_count <= 5:  # Should be efficient
        print(f"PASS Performance: {search_count} searches (efficient)")
        success_count += 1
    else:
        print(f"FAIL Performance: {search_count} searches (inefficient)")
    
    print(f"\\nIntegration test results: {success_count}/5 tests passed")
    
    # Show some detailed results if available
    if success_count >= 3:
        print("\\nDetailed results:")
        if hasattr(result, 'cross_reference_analysis') and result.cross_reference_analysis:
            cr = result.cross_reference_analysis
            print(f"  Cross-reference: {len(cr.patterns)} patterns, {len(cr.contradictions)} contradictions")
            if cr.patterns:
                print(f"    Sample pattern: {cr.patterns[0].pattern_type} - {cr.patterns[0].description[:100]}...")
        
        if hasattr(result, 'temporal_timeline') and result.temporal_timeline:
            tl = result.temporal_timeline
            print(f"  Temporal timeline: {tl.start_date} to {tl.end_date}")
            if tl.events:
                print(f"    Sample event: {tl.events[0].timestamp} - {tl.events[0].description[:100]}...")
    
    return success_count >= 4  # At least 4 out of 5 tests must pass

if __name__ == "__main__":
    success = test_advanced_features_integration()
    print(f"\\nADVANCED FEATURES INTEGRATION: {'PASS' if success else 'FAIL'}")