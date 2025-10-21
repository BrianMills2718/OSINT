"""Working test for cross-reference pattern detection using a proven query"""
import sys
import os

# Add the twitterexplorer subdirectory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
twitterexplorer_path = os.path.join(current_dir, 'twitterexplorer')
sys.path.insert(0, twitterexplorer_path)

from investigation_engine import InvestigationEngine, InvestigationConfig

def test_cross_reference_with_working_query():
    """EVIDENCE: Test pattern detection using query proven to generate findings"""
    
    print("=== CROSS-REFERENCE PATTERN DETECTION TEST (WORKING QUERY) ===")
    
    api_key = "d72bcd77e2msh76c7e6cf37f0b89p1c51bcjsnaad0f6b01e4f"
    engine = InvestigationEngine(api_key)
    
    # Use the working query from the debug test
    working_query = "What is Elon Musk saying about AI"
    config = InvestigationConfig(max_searches=1, pages_per_search=2)
    result = engine.conduct_investigation(working_query, config)
    
    print(f"\\nGenerated {len(result.accumulated_findings)} findings for analysis")
    
    # Test cross-reference analysis
    if hasattr(result, 'cross_reference_analysis'):
        analysis = result.cross_reference_analysis
        if analysis is None:
            print("FAIL: cross_reference_analysis attribute is None")
            print(f"Debug: findings count = {len(result.accumulated_findings)}")
            return False
        else:
            print(f"Cross-reference patterns found: {len(analysis.patterns)}")
            print(f"Contradictions identified: {len(analysis.contradictions)}")
            print(f"Source credibility conflicts: {len(analysis.credibility_conflicts)}")
            print(f"Confidence score: {analysis.confidence_score:.3f}")
            print(f"Overall coherence: {analysis.overall_coherence:.3f}")
            
            # Show some pattern details
            if analysis.patterns:
                print("\\nPattern examples:")
                for i, pattern in enumerate(analysis.patterns[:3]):  # Show first 3 patterns
                    print(f"  Pattern {i+1}: {pattern.pattern_type} - {pattern.description}")
                    print(f"    Entities: {pattern.entities_involved}")
                    print(f"    Evidence: {pattern.evidence_count}, Confidence: {pattern.confidence_score:.2f}")
            
            # Evidence requirements
            assert len(analysis.patterns) > 0, "Should detect at least one pattern"
            assert hasattr(analysis, 'confidence_score'), "Should have confidence scoring"
            assert analysis.confidence_score > 0.0, "Should have non-zero confidence"
            
            return True
    else:
        print("FAIL: No cross_reference_analysis attribute found")
        return False

if __name__ == "__main__":
    success = test_cross_reference_with_working_query()
    print(f"\\nCROSS-REFERENCE ANALYSIS: {'PASS' if success else 'FAIL'}")