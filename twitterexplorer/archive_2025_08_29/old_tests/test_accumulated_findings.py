"""Test that findings are accumulated during investigation"""
import sys
import os

# Setup paths - check if already in twitterexplorer directory
if os.path.basename(os.getcwd()) != 'twitterexplorer':
    sys.path.insert(0, 'twitterexplorer')
    if os.path.exists('twitterexplorer'):
        os.chdir('twitterexplorer')
else:
    sys.path.insert(0, '.')

from investigation_engine import InvestigationEngine, InvestigationConfig

def test_findings_are_accumulated():
    """EVIDENCE: accumulated_findings must contain discovered content"""
    
    api_key = "d72bcd77e2msh76c7e6cf37f0b89p1c51bcjsnaad0f6b01e4f"
    engine = InvestigationEngine(api_key)
    
    config = InvestigationConfig(max_searches=2, pages_per_search=1)
    
    result = engine.conduct_investigation(
        "Elon Musk Twitter announcement",
        config
    )
    
    # Test accumulated findings
    assert hasattr(result, 'accumulated_findings'), "No accumulated_findings attribute"
    assert len(result.accumulated_findings) > 0, f"No findings accumulated (found {len(result.accumulated_findings)})"
    
    # Check findings have content
    for finding in result.accumulated_findings[:3]:
        assert hasattr(finding, 'content') or isinstance(finding, str), "Finding has no content"
        
        content = finding.content if hasattr(finding, 'content') else str(finding)
        print(f"Finding: {content[:100]}...")
    
    print(f"PASSED: Accumulated {len(result.accumulated_findings)} findings!")

if __name__ == "__main__":
    test_findings_are_accumulated()