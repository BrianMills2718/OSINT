#!/usr/bin/env python3
"""
Debug investigation setup to see why insights weren't created during the Trump-Venezuela investigation
"""

import sys
import os
sys.path.append('twitterexplorer')

def debug_investigation_setup():
    """Debug the full investigation setup flow"""
    print("=== INVESTIGATION SETUP DEBUGGING ===")
    
    try:
        from investigation_engine import InvestigationEngine, InvestigationConfig
        
        # Create engine 
        engine = InvestigationEngine(rapidapi_key="test")
        print(f"Engine created successfully")
        print(f"Graph mode: {engine.graph_mode}")
        print(f"Initial insight_synthesizer: {engine.insight_synthesizer}")
        print(f"Initial integration_bridge: {engine.integration_bridge}")
        
        # Simulate investigation setup (without actually running searches)
        config = InvestigationConfig(max_searches=1)
        
        # This should trigger the insight synthesizer and bridge creation
        print(f"\nTesting investigation setup...")
        
        # Create session (this should trigger context creation)
        from investigation_engine import InvestigationSession
        session = InvestigationSession("Test investigation setup", config)
        
        # Create context (mimics what happens in conduct_investigation)
        from investigation_context import InvestigationContext
        investigation_context = InvestigationContext(
            original_query="Test investigation setup",
            search_log=[],  # Empty for testing
            satisfaction_log=[]
        )
        
        # Pass context to coordinator (mimics conduct_investigation setup)
        session.context = investigation_context
        
        if hasattr(engine.llm_coordinator, 'set_context'):
            engine.llm_coordinator.set_context(investigation_context)
            print("Context set on coordinator")
        
        # This should create the insight synthesizer and bridge
        print(f"\nCreating insight synthesizer and bridge...")
        
        if engine.graph_mode and hasattr(engine.llm_coordinator, 'graph'):
            print("Graph mode confirmed, creating synthesizer...")
            
            try:
                from realtime_insight_synthesizer import RealTimeInsightSynthesizer
                engine.insight_synthesizer = RealTimeInsightSynthesizer(
                    llm_client=engine.llm_coordinator.llm,
                    graph=engine.llm_coordinator.graph,
                    context=investigation_context,
                    model_manager=engine.model_manager
                )
                print("Insight synthesizer created successfully")
                
                # Create bridge 
                try:
                    from investigation_bridge import ConcreteInvestigationBridge
                    engine.integration_bridge = ConcreteInvestigationBridge(
                        llm_coordinator=engine.llm_coordinator,
                        graph=engine.llm_coordinator.graph,
                        context=investigation_context,
                        model_manager=engine.model_manager
                    )
                    print("Integration bridge created successfully")
                    
                    # Wire bridge
                    engine.insight_synthesizer.bridge = engine.integration_bridge
                    print("Bridge wired to synthesizer")
                    
                    # Test the integration
                    print(f"\nTesting integration...")
                    print(f"Synthesizer has bridge: {hasattr(engine.insight_synthesizer, 'bridge')}")
                    print(f"Bridge is not None: {engine.insight_synthesizer.bridge is not None}")
                    
                    return True
                    
                except Exception as bridge_error:
                    print(f"ERROR creating bridge: {bridge_error}")
                    import traceback
                    traceback.print_exc()
                    return False
                    
            except Exception as synth_error:
                print(f"ERROR creating synthesizer: {synth_error}")
                import traceback
                traceback.print_exc()
                return False
        else:
            print("Graph mode not available or coordinator missing graph")
            return False
            
    except Exception as e:
        print(f"ERROR in setup debugging: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_insight_creation():
    """Test actual insight creation on existing DataPoints"""
    print("\n=== TESTING INSIGHT CREATION ===")
    
    try:
        import json
        
        # Load graph data
        with open('twitterexplorer/current_investigation_graph.json', 'r') as f:
            graph_data = json.load(f)
        
        # Find DataPoint nodes
        datapoint_ids = []
        for node_id, node_data in graph_data.get('nodes', {}).items():
            if node_data.get('node_type') == 'DataPoint':
                datapoint_ids.append(node_id)
        
        print(f"Found {len(datapoint_ids)} DataPoint nodes to test")
        
        if len(datapoint_ids) > 0:
            # Set up investigation engine with full context
            from investigation_engine import InvestigationEngine
            from investigation_context import InvestigationContext
            from investigation_engine import InvestigationConfig
            
            engine = InvestigationEngine(rapidapi_key="test")
            
            # Create investigation context
            context = InvestigationContext(
                original_query="Trump sent military to Venezuela recent news",
                search_log=[],
                satisfaction_log=[]
            )
            
            # Set up insight synthesizer (full setup)
            if hasattr(engine.llm_coordinator, 'set_context'):
                engine.llm_coordinator.set_context(context)
            
            if engine.graph_mode and hasattr(engine.llm_coordinator, 'graph'):
                from realtime_insight_synthesizer import RealTimeInsightSynthesizer
                from investigation_bridge import ConcreteInvestigationBridge
                
                engine.insight_synthesizer = RealTimeInsightSynthesizer(
                    llm_client=engine.llm_coordinator.llm,
                    graph=engine.llm_coordinator.graph,
                    context=context,
                    model_manager=engine.model_manager
                )
                
                engine.integration_bridge = ConcreteInvestigationBridge(
                    llm_coordinator=engine.llm_coordinator,
                    graph=engine.llm_coordinator.graph,
                    context=context,
                    model_manager=engine.model_manager
                )
                
                engine.insight_synthesizer.bridge = engine.integration_bridge
                
                print("Full setup complete, testing insight synthesis...")
                
                # Test on first datapoint
                test_dp_id = datapoint_ids[0]
                print(f"Testing synthesis on DataPoint: {test_dp_id}")
                
                insights_created = engine.insight_synthesizer.process_new_datapoint(test_dp_id)
                print(f"Insights created: {insights_created}")
                
                if insights_created and len(insights_created) > 0:
                    print("SUCCESS: Insights created!")
                    
                    # Check if EmergentQuestions were also created
                    print("Checking for EmergentQuestions...")
                    # Load updated graph
                    with open('twitterexplorer/current_investigation_graph.json', 'r') as f:
                        updated_graph = json.load(f)
                    
                    emergent_count = len([n for n_id, n in updated_graph.get('nodes', {}).items() 
                                        if n.get('node_type') == 'EmergentQuestion'])
                    print(f"EmergentQuestion nodes found: {emergent_count}")
                    
                    return True
                else:
                    print("FAILURE: No insights created")
                    return False
            else:
                print("Cannot set up synthesizer - graph mode not available")
                return False
        else:
            print("No DataPoint nodes available for testing")
            return False
            
    except Exception as e:
        print(f"ERROR in insight creation test: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    setup_success = debug_investigation_setup()
    
    if setup_success:
        print("\n[SUCCESS] Investigation setup working - components can be created")
        insight_success = test_insight_creation()
        
        if insight_success:
            print("\n[SUCCESS] Insight creation working - full ontology functional")
        else:
            print("\n[FAILED] Insight creation broken - synthesis logic issue")
    else:
        print("\n[FAILED] Investigation setup broken - components cannot be created")