"""Test cross-reference pattern detection functionality"""
import sys
import os

# Add the twitterexplorer subdirectory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
twitterexplorer_path = os.path.join(current_dir, 'twitterexplorer')
sys.path.insert(0, twitterexplorer_path)

from investigation_engine import InvestigationEngine, InvestigationConfig

def test_cross_reference_pattern_detection():
    """EVIDENCE: Test pattern detection across multiple findings"""
    
    print("=== CROSS-REFERENCE PATTERN DETECTION TEST ===")
    
    api_key = "d72bcd77e2msh76c7e6cf37f0b89p1c51bcjsnaad0f6b01e4f"
    engine = InvestigationEngine(api_key)
    
    # Run investigation that should generate multiple findings
    config = InvestigationConfig(max_searches=3, pages_per_search=2)
    result = engine.conduct_investigation("What are different perspectives on climate change policies", config)
    
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
            
            # Evidence requirements
            assert len(analysis.patterns) > 0, "Should detect at least one pattern"
            assert hasattr(analysis, 'confidence_score'), "Should have confidence scoring"
            
            return True
    else:
        print("FAIL: No cross_reference_analysis attribute found")
        return False

if __name__ == "__main__":
    success = test_cross_reference_pattern_detection()
    print(f"\\nCROSS-REFERENCE ANALYSIS: {'PASS' if success else 'FAIL'}")