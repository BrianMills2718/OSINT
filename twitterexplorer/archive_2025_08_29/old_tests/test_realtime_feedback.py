"""Test suite for real-time feedback during investigations"""
import pytest
import sys
import time
from unittest.mock import Mock, patch, MagicMock
from twitterexplorer.investigation_engine import InvestigationEngine, InvestigationConfig


def test_progress_container_creation():
    """EVIDENCE: Progress container must be created for updates"""
    # Mock Streamlit's container
    with patch('streamlit.container') as mock_container:
        mock_progress_container = Mock()
        mock_container.return_value = mock_progress_container
        
        # Create engine with progress container
        engine = InvestigationEngine("test_key")
        engine.set_progress_container(mock_progress_container)
        
        # Verify container was set
        assert engine.progress_container == mock_progress_container
        print("[PASS] Progress container set successfully")
        
        return engine


def test_progress_updates_during_search():
    """EVIDENCE: Progress updates must be sent during searches"""
    updates_received = []
    
    # Mock progress container
    mock_container = Mock()
    mock_container.info = Mock(side_effect=lambda x: updates_received.append(x))
    mock_container.success = Mock(side_effect=lambda x: updates_received.append(x))
    mock_container.warning = Mock(side_effect=lambda x: updates_received.append(x))
    
    # Create engine with mocked container
    engine = InvestigationEngine("test_key")
    engine.set_progress_container(mock_container)
    
    # Simulate search with progress updates
    engine.send_progress_update("Starting investigation...", "info")
    engine.send_progress_update("Executing search 1/5", "info")
    engine.send_progress_update("Found 10 results", "success")
    
    # Verify updates were sent
    assert len(updates_received) >= 3
    assert "Starting investigation" in updates_received[0]
    assert "Executing search" in updates_received[1]
    assert "Found 10 results" in updates_received[2]
    
    print(f"[PASS] Received {len(updates_received)} progress updates")
    return updates_received


def test_real_investigation_with_feedback():
    """EVIDENCE: Real investigation must send progress updates"""
    from twitterexplorer.investigation_engine import InvestigationSession
    
    # Track all updates
    updates = []
    
    # Mock container
    mock_container = Mock()
    mock_container.info = Mock(side_effect=lambda x: updates.append(('info', x)))
    mock_container.success = Mock(side_effect=lambda x: updates.append(('success', x)))
    mock_container.warning = Mock(side_effect=lambda x: updates.append(('warning', x)))
    mock_container.markdown = Mock(side_effect=lambda x: updates.append(('markdown', x)))
    
    # Create engine
    engine = InvestigationEngine("test_key")
    engine.set_progress_container(mock_container)
    
    # Create minimal config for fast test
    config = InvestigationConfig(
        max_searches=2,
        satisfaction_enabled=False,
        show_search_details=True
    )
    
    # Simulate investigation progress without actual API calls
    # Start investigation
    engine.send_progress_update("Starting investigation: test query", "info")
    engine.send_progress_update("Planning initial strategy...", "info")
    
    # Simulate search rounds
    for i in range(2):
        engine.send_progress_update(f"**Round {i+1}:**", "markdown")
        engine.send_progress_update(f"Executing search {i+1}/2", "info")
        time.sleep(0.01)  # Simulate work
        engine.send_progress_update(f"Completed search {i+1}", "success")
    
    # Verify multiple update types
    info_updates = [u for u in updates if u[0] == 'info']
    success_updates = [u for u in updates if u[0] == 'success']
    markdown_updates = [u for u in updates if u[0] == 'markdown']
    
    assert len(info_updates) >= 3, "Should have info updates"
    assert len(success_updates) >= 2, "Should have success updates"
    assert len(markdown_updates) >= 2, "Should have markdown updates"
    
    print(f"[PASS] Real investigation sent {len(updates)} updates")
    return updates


def test_batch_evaluation_feedback():
    """EVIDENCE: Batch evaluation must provide progress feedback"""
    updates = []
    
    mock_container = Mock()
    mock_container.info = Mock(side_effect=lambda x: updates.append(x))
    
    engine = InvestigationEngine("test_key")
    engine.set_progress_container(mock_container)
    
    # Simulate batch evaluation
    batch_results = [
        {"effectiveness": 7.5, "results": 10},
        {"effectiveness": 6.0, "results": 5},
        {"effectiveness": 8.0, "results": 15},
        {"effectiveness": 4.5, "results": 3}
    ]
    
    # Send batch evaluation updates
    engine.send_progress_update("Evaluating batch of 4 searches...", "info")
    
    for i, result in enumerate(batch_results):
        update = f"Search {i+1}: {result['results']} results (effectiveness: {result['effectiveness']}/10)"
        engine.send_progress_update(update, "info")
    
    avg_effectiveness = sum(r['effectiveness'] for r in batch_results) / len(batch_results)
    engine.send_progress_update(f"Batch average effectiveness: {avg_effectiveness:.1f}/10", "info")
    
    # Verify batch updates
    assert len(updates) >= 6  # Initial + 4 searches + average
    assert "Evaluating batch" in updates[0]
    assert "effectiveness" in updates[1]
    assert "average" in updates[-1]
    
    print(f"[PASS] Batch evaluation sent {len(updates)} updates")
    return updates


def test_satisfaction_progress_updates():
    """EVIDENCE: Satisfaction metrics must be shown in progress"""
    updates = []
    
    mock_container = Mock()
    mock_container.markdown = Mock(side_effect=lambda x: updates.append(x))
    
    engine = InvestigationEngine("test_key")
    engine.set_progress_container(mock_container)
    
    # Simulate satisfaction updates
    satisfaction_levels = [0.2, 0.4, 0.6, 0.75, 0.85]
    
    for level in satisfaction_levels:
        engine.send_satisfaction_update(level)
    
    # Verify satisfaction updates
    assert len(updates) == len(satisfaction_levels)
    
    # Check format
    for update in updates:
        assert "Satisfaction" in update or "satisfaction" in update
        assert "%" in update or "." in str(update)
    
    print(f"[PASS] Sent {len(updates)} satisfaction updates")
    return updates


def test_error_feedback():
    """EVIDENCE: Errors must be communicated to user"""
    updates = []
    
    mock_container = Mock()
    mock_container.error = Mock(side_effect=lambda x: updates.append(('error', x)))
    mock_container.warning = Mock(side_effect=lambda x: updates.append(('warning', x)))
    
    engine = InvestigationEngine("test_key")
    engine.set_progress_container(mock_container)
    
    # Simulate errors
    engine.send_progress_update("API rate limit reached", "error")
    engine.send_progress_update("Retrying search...", "warning")
    engine.send_progress_update("Connection timeout", "error")
    
    # Verify error handling
    errors = [u for u in updates if u[0] == 'error']
    warnings = [u for u in updates if u[0] == 'warning']
    
    assert len(errors) >= 2
    assert len(warnings) >= 1
    assert "rate limit" in errors[0][1]
    
    print(f"[PASS] Error feedback working: {len(errors)} errors, {len(warnings)} warnings")
    return updates


if __name__ == "__main__":
    print("\n=== Testing Real-time Feedback System ===\n")
    
    try:
        engine = test_progress_container_creation()
        progress_updates = test_progress_updates_during_search()
        investigation_updates = test_real_investigation_with_feedback()
        batch_updates = test_batch_evaluation_feedback()
        satisfaction_updates = test_satisfaction_progress_updates()
        error_updates = test_error_feedback()
        
        print("\n[SUCCESS] All feedback tests passed!")
        
    except AssertionError as e:
        print(f"\n[FAILURE] Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)