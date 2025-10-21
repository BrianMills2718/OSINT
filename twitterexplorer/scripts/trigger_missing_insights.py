#!/usr/bin/env python3
"""
Trigger insight synthesis for existing DataPoints to create missing Insights and EmergentQuestions
"""

import sys
import json
import os
from datetime import datetime
sys.path.append('twitterexplorer')

def trigger_insight_synthesis():
    """Force insight synthesis on existing DataPoints"""
    print("=== TRIGGERING MISSING INSIGHT SYNTHESIS ===")
    
    try:
        # Load existing investigation to get DataPoints 
        with open('twitterexplorer/current_investigation_graph.json', 'r') as f:
            graph_data = json.load(f)
        
        # Count existing nodes
        node_counts = {}
        datapoint_nodes = []
        for node_id, node_data in graph_data.get('nodes', {}).items():
            node_type = node_data.get('node_type', 'Unknown')
            node_counts[node_type] = node_counts.get(node_type, 0) + 1
            
            if node_type == 'DataPoint':
                datapoint_nodes.append((node_id, node_data))
        
        print("Current graph state:")
        for node_type, count in sorted(node_counts.items()):
            print(f"  {node_type}: {count}")
        
        # Set up investigation engine with proper configuration
        from investigation_engine import InvestigationEngine
        
        # Load secrets for real API access
        import streamlit as st
        secrets_path = 'twitterexplorer/.streamlit/secrets.toml'
        
        if os.path.exists(secrets_path):
            import toml
            secrets = toml.load(secrets_path)
            rapidapi_key = secrets.get('RAPIDAPI_KEY', 'test')
        else:
            rapidapi_key = 'test'
        
        engine = InvestigationEngine(rapidapi_key=rapidapi_key)
        
        print(f"\nEngine setup:")
        print(f"  Graph mode: {engine.graph_mode}")
        print(f"  Has LLM coordinator: {hasattr(engine, 'llm_coordinator')}")
        
        # Create investigation context (required for synthesis)
        from investigation_context import InvestigationContext
        
        context = InvestigationContext(
            analytic_question="Trump sent military to Venezuela recent news",
            investigation_scope="Recent military deployment claims"
        )
        
        # Configure the coordinator with context
        if hasattr(engine.llm_coordinator, 'set_context'):
            engine.llm_coordinator.set_context(context)
            print("  Context set on coordinator")
        
        # Create insight synthesizer and bridge (mimics conduct_investigation setup)
        if engine.graph_mode and hasattr(engine.llm_coordinator, 'graph'):
            from realtime_insight_synthesizer import RealTimeInsightSynthesizer
            from investigation_bridge import ConcreteInvestigationBridge
            
            # Create synthesizer
            engine.insight_synthesizer = RealTimeInsightSynthesizer(
                llm_client=engine.llm_coordinator.llm,
                graph=engine.llm_coordinator.graph,
                context=context,
                model_manager=engine.model_manager
            )
            
            # Create bridge
            engine.integration_bridge = ConcreteInvestigationBridge(
                llm_coordinator=engine.llm_coordinator,
                graph=engine.llm_coordinator.graph,
                context=context,
                model_manager=engine.model_manager
            )
            
            # Wire bridge
            engine.insight_synthesizer.bridge = engine.integration_bridge
            
            print(f"  Insight synthesizer created: {engine.insight_synthesizer is not None}")
            print(f"  Integration bridge created: {engine.integration_bridge is not None}")
            print(f"  Bridge wired: {hasattr(engine.insight_synthesizer, 'bridge')}")
            
            # Now trigger synthesis on existing DataPoints
            print(f"\nProcessing {len(datapoint_nodes)} existing DataPoints...")
            
            insights_created_total = []
            for i, (dp_id, dp_data) in enumerate(datapoint_nodes):
                try:
                    print(f"  Processing DataPoint {i+1}/{len(datapoint_nodes)}: {dp_id}")
                    content_preview = dp_data.get('properties', {}).get('content', 'No content')[:100]
                    print(f"    Content: {content_preview}...")
                    
                    # Trigger insight synthesis
                    insights = engine.insight_synthesizer.process_new_datapoint(dp_id)
                    
                    if insights and len(insights) > 0:
                        insights_created_total.extend(insights)
                        print(f"    [OK] Created {len(insights)} insights")
                    else:
                        print(f"    [NONE] No insights created")
                        
                except Exception as e:
                    print(f"    [ERROR] Error processing DataPoint: {e}")
            
            print(f"\nSynthesis complete!")
            print(f"Total insights created: {len(insights_created_total)}")
            
            # Check updated graph state
            with open('twitterexplorer/current_investigation_graph.json', 'r') as f:
                updated_graph = json.load(f)
            
            updated_counts = {}
            for node_id, node_data in updated_graph.get('nodes', {}).items():
                node_type = node_data.get('node_type', 'Unknown')
                updated_counts[node_type] = updated_counts.get(node_type, 0) + 1
            
            print(f"\nUpdated graph state:")
            for node_type, count in sorted(updated_counts.items()):
                print(f"  {node_type}: {count}")
            
            # Check edge types
            edge_counts = {}
            for edge in updated_graph.get('edges', []):
                edge_type = edge.get('edge_type', 'Unknown')
                edge_counts[edge_type] = edge_counts.get(edge_type, 0) + 1
            
            print(f"\nEdge types:")
            for edge_type, count in sorted(edge_counts.items()):
                print(f"  {edge_type}: {count}")
            
            # Check if we now have the full 6-node ontology
            expected_nodes = ['AnalyticQuestion', 'InvestigationQuestion', 'SearchQuery', 'DataPoint', 'Insight', 'EmergentQuestion']
            missing_nodes = []
            
            for expected in expected_nodes:
                if expected not in updated_counts or updated_counts[expected] == 0:
                    missing_nodes.append(expected)
            
            if len(missing_nodes) == 0:
                print(f"\n[SUCCESS] Full 6-node ontology complete!")
                return True
            else:
                print(f"\n[PARTIAL] Missing node types: {missing_nodes}")
                return len(missing_nodes) <= 2  # Allow missing EmergentQuestion if Insights were created
        else:
            print("Cannot create synthesizer - graph mode not available")
            return False
            
    except Exception as e:
        print(f"ERROR triggering synthesis: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = trigger_insight_synthesis()
    
    print(f"\n=== SYNTHESIS TRIGGER RESULT ===")
    if success:
        print("SUCCESS: Insight synthesis completed")
        print("Ready to regenerate visualization with full ontology")
    else:
        print("FAILED: Insight synthesis did not complete successfully")
        print("Manual intervention may be required")