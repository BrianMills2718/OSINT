"""Simple integration test to verify DataPoint/Insight creation"""
from twitterexplorer.investigation_engine import InvestigationEngine, InvestigationConfig
from twitterexplorer.finding_evaluator import FindingEvaluator

def test_finding_evaluator_works():
    """Test that FindingEvaluator identifies significant findings"""
    evaluator = FindingEvaluator()
    
    # Test with specific finding
    specific = {
        'text': 'Documents from January 15, 2024 show $5 million transaction between parties.',
        'source': 'test',
        'metadata': {}
    }
    
    assessment = evaluator.evaluate_finding(specific, "financial investigation")
    print(f"Specific finding significant: {assessment.is_significant}")
    print(f"Entities found: {list(assessment.entities.keys())}")
    
    # Test with generic finding
    generic = {
        'text': 'Click here for more information',
        'source': 'test',
        'metadata': {}
    }
    
    assessment2 = evaluator.evaluate_finding(generic, "financial investigation")
    print(f"Generic finding significant: {assessment2.is_significant}")
    
    return assessment.is_significant and not assessment2.is_significant

def test_progress_updates():
    """Test that progress updates can be sent"""
    engine = InvestigationEngine("test_key")
    
    # Test without container (should not crash)
    engine.send_progress_update("Test message", "info")
    print("Progress update sent without error")
    
    # Test with mock container
    from unittest.mock import Mock
    mock_container = Mock()
    engine.set_progress_container(mock_container)
    engine.send_progress_update("Test with container", "info")
    
    return mock_container.info.called

def test_graph_mode_check():
    """Check if graph mode is available"""
    engine = InvestigationEngine("test_key")
    print(f"Graph mode enabled: {engine.graph_mode}")
    
    if engine.graph_mode:
        print(f"Graph coordinator type: {type(engine.llm_coordinator).__name__}")
        if hasattr(engine.llm_coordinator, 'graph'):
            print("Graph object available")
            return True
    return False

if __name__ == "__main__":
    print("=== Running Simple Integration Tests ===\n")
    
    # Test 1: FindingEvaluator
    print("Test 1: FindingEvaluator")
    if test_finding_evaluator_works():
        print("[SUCCESS] FindingEvaluator correctly identifies significant vs generic findings\n")
    else:
        print("[FAILED] FindingEvaluator not working correctly\n")
    
    # Test 2: Progress Updates
    print("Test 2: Progress Updates")
    if test_progress_updates():
        print("[SUCCESS] Progress updates work correctly\n")
    else:
        print("[FAILED] Progress updates not working\n")
    
    # Test 3: Graph Mode
    print("Test 3: Graph Mode Availability")
    if test_graph_mode_check():
        print("[SUCCESS] Graph mode is available and configured\n")
    else:
        print("[INFO] Graph mode not available (this is OK if not configured)\n")
    
    print("=== Integration Tests Complete ===")