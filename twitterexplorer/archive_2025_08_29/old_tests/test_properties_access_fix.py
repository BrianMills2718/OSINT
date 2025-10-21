#!/usr/bin/env python3
"""
Test Properties Access Fix - Addresses DataPointNodeWrapper properties interface

EVIDENCE REQUIREMENT: This test verifies the specific fix for the integration failure:
- investigation_engine.py:1071 calls dp.properties['content'] 
- DataPointNodeWrapper must provide .properties interface
- This is the PRIMARY technical integration failure
"""

import sys
import os
from datetime import datetime

# Add the twitterexplorer directory to Python path  
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'twitterexplorer'))

def test_datapoint_wrapper_properties_interface():
    """EVIDENCE: Verify fix for properties access error"""
    print("=== TESTING DATAPOINT WRAPPER PROPERTIES ACCESS FIX ===")
    
    try:
        from investigation_graph import InvestigationGraph
        
        # Create graph and DataPoint  
        graph = InvestigationGraph()
        dp = graph.create_datapoint_node(
            content="Test content for properties access", 
            source="test.php",
            timestamp=datetime.now().isoformat()
        )
        
        print(f"[OK] DataPoint created: {dp.id}")
        print(f"[OK] DataPoint type: {type(dp)}")
        
        # CRITICAL TEST: This specific access pattern from investigation_engine.py:1071
        try:
            content_via_properties = dp.properties['content']
            print(f"[OK] Properties access WORKS: {content_via_properties}")
            properties_access_works = True
        except AttributeError as e:
            print(f"[ERROR] Properties access FAILED: {e}")
            properties_access_works = False
            
        # Verify attributes still work (backward compatibility)
        try:
            content_via_attributes = dp.attributes['content'] 
            print(f"[OK] Attributes access works: {content_via_attributes}")
            attributes_access_works = True
        except AttributeError as e:
            print(f"[ERROR] Attributes access failed: {e}")
            attributes_access_works = False
        
        # EVIDENCE VALIDATION
        print("\n=== EVIDENCE SUMMARY ===")
        print(f"Properties interface available: {properties_access_works}")
        print(f"Attributes interface available: {attributes_access_works}")
        print(f"Content consistency: {content_via_properties == content_via_attributes}")
        
        # CRITICAL: Properties interface must work for integration
        assert properties_access_works, "CRITICAL: DataPoint wrapper needs .properties interface"
        assert content_via_properties == "Test content for properties access"
        
        print("[SUCCESS] PROPERTIES ACCESS FIX - SUCCESS")
        return True
        
    except Exception as e:
        print(f"[FAILED] PROPERTIES ACCESS FIX - FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_insight_wrapper_properties_interface():
    """EVIDENCE: Verify InsightNodeWrapper also has properties interface (consistency)"""
    print("\n=== TESTING INSIGHT WRAPPER PROPERTIES ACCESS ===")
    
    try:
        from investigation_graph import InvestigationGraph
        
        # Create graph and Insight
        graph = InvestigationGraph()
        insight = graph.create_insight_node_enhanced(
            content="Test insight for properties access",
            confidence=0.8,
            supporting_datapoints=[]
        )
        
        print(f"[OK] Insight created: {insight.id}")
        
        # Test properties access
        content_via_properties = insight.properties['content']
        print(f"[OK] Insight properties access works: {content_via_properties}")
        
        assert content_via_properties == "Test insight for properties access"
        print("[SUCCESS] INSIGHT PROPERTIES ACCESS - SUCCESS")
        return True
        
    except Exception as e:
        print(f"[FAILED] INSIGHT PROPERTIES ACCESS - FAILED: {e}")
        return False

if __name__ == "__main__":
    print("TESTING PROPERTIES ACCESS FIX - PRIMARY INTEGRATION FAILURE")
    print("=" * 60)
    
    success_1 = test_datapoint_wrapper_properties_interface()
    success_2 = test_insight_wrapper_properties_interface()
    
    overall_success = success_1 and success_2
    
    print("\n" + "=" * 60)
    print(f"OVERALL RESULT: {'[SUCCESS] Properties access fix working' if overall_success else '[FAILED] Properties access still broken'}")
    
    if overall_success:
        print("\nEVIDENCE: DataPoint wrapper .properties interface now available")
        print("NEXT: This should resolve investigation_engine.py:1071 AttributeError")
    else:
        print("\nERROR: Properties interface still not working")
        print("IMPACT: integration_engine.py will still fail at DataPoint access")
        
    sys.exit(0 if overall_success else 1)