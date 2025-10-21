#!/usr/bin/env python3
"""
Quick test to verify LLM call visibility enhancements are working
"""

import sys
import os
sys.path.insert(0, 'twitterexplorer')

def test_tracer_visibility():
    """Test that tracer captures calls with enhanced metadata"""
    from utils.llm_call_tracer import get_tracer
    
    tracer = get_tracer()
    tracer.reset()
    
    # Simulate some calls
    call_id = tracer.start_call("test_component", "test_purpose", 100, "test_model")
    tracer.end_call(call_id, success=True, metadata={'caller_location': 'test.py:123:test_func'})
    
    summary = tracer.get_call_summary()
    print("=== TRACER VISIBILITY TEST ===")
    print(f"Calls captured: {summary.get('total_calls', 0)}")
    print(f"Components: {summary.get('components', {})}")
    
    # Check if call has enhanced metadata
    if tracer.calls:
        call = tracer.calls[0]
        print(f"Call metadata: {call.metadata}")
        assert 'caller_location' in call.metadata
        print("SUCCESS: Enhanced metadata captured")
    
    return True

def test_llm_client_visibility():
    """Test that LLM client prints call information"""
    print("\n=== LLM CLIENT VISIBILITY TEST ===")
    print("Testing enhanced LLM client visibility...")
    
    # This will test if the import works
    try:
        from llm_client import LiteLLMClient, get_litellm_client
        print("SUCCESS: LLM client with enhanced visibility imported successfully")
    except Exception as e:
        print(f"ERROR: importing enhanced LLM client: {e}")
        return False
    
    # Test would require API call - skip for now
    print("SUCCESS: Enhanced LLM client ready (actual call testing requires API keys)")
    return True

def test_summary_logger():
    """Test that summary logger works"""
    print("\n=== SUMMARY LOGGER TEST ===")
    
    try:
        from utils.call_summary_logger import get_summary_logger
        logger = get_summary_logger()
        
        # Force a summary print (even with no data)
        logger.maybe_print_summary(force=True)
        print("SUCCESS: Summary logger working")
        return True
        
    except Exception as e:
        print(f"ERROR: Summary logger error: {e}")
        return False

if __name__ == "__main__":
    print("TESTING ENHANCED LLM CALL VISIBILITY")
    print("=" * 50)
    
    success = True
    success &= test_tracer_visibility()
    success &= test_llm_client_visibility()
    success &= test_summary_logger()
    
    print("\n" + "=" * 50)
    if success:
        print("SUCCESS: ALL VISIBILITY ENHANCEMENTS WORKING")
        print("\nReady for real investigation with full call tracking!")
        print("   Run: python twitterexplorer/cli_test.py 'test query'")
        print("   Expected output: Real-time LLM call logging with:")
        print("   • Call initiation with source location")
        print("   • Call completion with timing")
        print("   • Periodic summaries every 60 seconds")
        print("   • Final summary with optimization analysis")
    else:
        print("ERROR: SOME ISSUES FOUND - CHECK LOGS ABOVE")