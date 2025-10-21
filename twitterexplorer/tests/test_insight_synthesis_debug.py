#!/usr/bin/env python3
"""
Debug insight synthesis to understand why Insights and EmergentQuestions are not being created
"""

import sys
import json
sys.path.append('twitterexplorer')

def debug_insight_synthesis():
    """Debug the insight synthesis system"""
    print("=== INSIGHT SYNTHESIS DEBUGGING ===")
    
    try:
        # Load the investigation engine
        from investigation_engine import InvestigationEngine
        engine = InvestigationEngine(rapidapi_key="test")
        
        print(f"Graph mode: {engine.graph_mode}")
        print(f"Insight synthesizer created: {engine.insight_synthesizer is not None}")
        print(f"Integration bridge created: {engine.integration_bridge is not None}")
        
        if engine.insight_synthesizer:
            print(f"Bridge wired to synthesizer: {hasattr(engine.insight_synthesizer, 'bridge') and engine.insight_synthesizer.bridge is not None}")
        
        # Load the current investigation graph
        with open('twitterexplorer/current_investigation_graph.json', 'r') as f:
            graph_data = json.load(f)
        
        # Count DataPoint nodes
        datapoint_nodes = [node for node_id, node in graph_data.get('nodes', {}).items() 
                          if node.get('node_type') == 'DataPoint']
        
        print(f"DataPoint nodes available for synthesis: {len(datapoint_nodes)}")
        
        if len(datapoint_nodes) > 0:
            print("\nTesting insight synthesis on existing DataPoints...")
            
            # Test synthesis on first few datapoints
            test_datapoints = datapoint_nodes[:3]  # Test on first 3
            
            for i, dp_data in enumerate(test_datapoints):
                print(f"\nTesting DataPoint {i+1}:")
                print(f"  Content preview: {dp_data.get('properties', {}).get('content', 'No content')[:100]}...")
                
                if engine.insight_synthesizer:
                    try:
                        # Find the datapoint ID
                        dp_id = None
                        for node_id, node_data in graph_data.get('nodes', {}).items():
                            if node_data == dp_data:
                                dp_id = node_id
                                break
                        
                        if dp_id:
                            print(f"  DataPoint ID: {dp_id}")
                            # Try to synthesize insights
                            insights = engine.insight_synthesizer.process_new_datapoint(dp_id)
                            print(f"  Insights created: {insights}")
                            
                        else:
                            print("  ERROR: Could not find DataPoint ID")
                            
                    except Exception as e:
                        print(f"  ERROR synthesizing insights: {e}")
                        import traceback
                        traceback.print_exc()
        
        # Check if any insights exist in graph after synthesis
        with open('twitterexplorer/current_investigation_graph.json', 'r') as f:
            updated_graph = json.load(f)
        
        insight_nodes = [node for node_id, node in updated_graph.get('nodes', {}).items() 
                        if node.get('node_type') == 'Insight']
        emergent_nodes = [node for node_id, node in updated_graph.get('nodes', {}).items() 
                         if node.get('node_type') == 'EmergentQuestion']
        
        print(f"\nPost-synthesis node counts:")
        print(f"  Insight nodes: {len(insight_nodes)}")
        print(f"  EmergentQuestion nodes: {len(emergent_nodes)}")
        
        if len(insight_nodes) == 0:
            print("\nINSIGHT SYNTHESIS FAILURE IDENTIFIED!")
            print("No Insight nodes were created despite having DataPoints available")
            
            # Check bridge integration
            if engine.insight_synthesizer and hasattr(engine.insight_synthesizer, 'bridge'):
                if engine.insight_synthesizer.bridge is None:
                    print("CAUSE: Bridge not wired to insight synthesizer")
                else:
                    print("Bridge is wired, issue must be in synthesis logic")
            
        return len(insight_nodes) > 0, len(emergent_nodes) > 0
        
    except Exception as e:
        print(f"ERROR in debugging: {e}")
        import traceback
        traceback.print_exc()
        return False, False

if __name__ == "__main__":
    insights_created, emergent_created = debug_insight_synthesis()
    
    print(f"\n=== DIAGNOSIS SUMMARY ===")
    print(f"Insights working: {insights_created}")
    print(f"EmergentQuestions working: {emergent_created}")
    
    if not insights_created:
        print("\n[CRITICAL] ISSUE: Insight synthesis is broken")
        print("   Investigation creates DataPoints but not Insights")
        print("   This breaks the full 6-node ontology")
    
    if not emergent_created:
        print("\n[CRITICAL] ISSUE: EmergentQuestion detection is broken") 
        print("   Insights (if created) do not spawn EmergentQuestions")
        print("   This prevents investigation expansion")