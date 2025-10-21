"""Debug test for cross-reference analyzer directly"""
import sys
import os

# Add the twitterexplorer subdirectory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
twitterexplorer_path = os.path.join(current_dir, 'twitterexplorer')
sys.path.insert(0, twitterexplorer_path)

from cross_reference_analyzer import CrossReferenceAnalyzer
from dataclasses import dataclass

@dataclass
class MockFinding:
    content: str
    source: str
    credibility_score: float = 0.8

def test_analyzer_directly():
    print("=== DIRECT ANALYZER TEST ===")
    
    # Create mock findings
    findings = [
        MockFinding("Elon Musk talks about xAI progress", "twitter", 0.9),
        MockFinding("AI safety concerns from Musk", "twitter", 0.8),
        MockFinding("Neuralink advances in brain interfaces", "twitter", 0.7)
    ]
    
    print(f"Created {len(findings)} mock findings")
    
    # Test analyzer
    try:
        analyzer = CrossReferenceAnalyzer(None)  # No LLM client for basic test
        print("Analyzer created successfully")
        
        result = analyzer.analyze_findings(findings, "AI developments")
        print("Analysis completed successfully")
        
        print(f"Patterns: {len(result.patterns)}")
        print(f"Contradictions: {len(result.contradictions)}")
        print(f"Confidence: {result.confidence_score}")
        
        return True
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_analyzer_directly()
    print(f"Direct test: {'PASS' if success else 'FAIL'}")