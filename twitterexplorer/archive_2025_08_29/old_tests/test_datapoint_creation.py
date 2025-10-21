"""Test that DataPoints are created from findings"""
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

def test_datapoints_are_created():
    """EVIDENCE: DataPoints must be created from tweet findings"""
    
    api_key = "d72bcd77e2msh76c7e6cf37f0b89p1c51bcjsnaad0f6b01e4f"
    engine = InvestigationEngine(api_key)
    
    config = InvestigationConfig(max_searches=2, pages_per_search=1)
    
    # Add debugging to see what's happening
    print("\n=== DEBUGGING DATAPOINT CREATION ===")
    
    # Monkey-patch to add logging
    original_analyze = engine._analyze_round_results_with_llm
    
    def logged_analyze(session, round_obj, results):
        print(f"Analyzing {len(results)} search results")
        for r in results:
            if hasattr(r, '_raw_results'):
                print(f"  - Search has {len(r._raw_results)} raw results")
        
        # Call original
        result = original_analyze(session, round_obj, results)
        
        # Check graph after
        if hasattr(engine, 'graph_mode') and engine.graph_mode:
            if hasattr(engine.llm_coordinator, 'graph'):
                graph = engine.llm_coordinator.graph
                datapoints = [n for n in graph.nodes.values() if 'DataPoint' in str(type(n))]
                print(f"DataPoints after analysis: {len(datapoints)}")
        
        return result
    
    engine._analyze_round_results_with_llm = logged_analyze
    
    # Run investigation
    result = engine.conduct_investigation(
        "Elon Musk X platform news",
        config
    )
    
    # Check for DataPoints
    if hasattr(engine, 'graph_mode') and engine.graph_mode:
        graph = engine.llm_coordinator.graph
        datapoints = [n for n in graph.nodes.values() if 'DataPoint' in str(type(n))]
        
        print(f"\n=== RESULTS ===")
        print(f"Total nodes: {len(graph.nodes)}")
        print(f"DataPoint nodes: {len(datapoints)}")
        
        assert len(datapoints) > 0, "No DataPoints created despite having tweets"
        
        # Show DataPoint content
        for i, dp in enumerate(datapoints[:3], 1):
            content = dp.properties.get('content', 'NO CONTENT')
            print(f"DataPoint {i}: {content[:100]}...")
        
        print("PASSED: DataPoints are being created!")
    else:
        print("WARNING: Not in graph mode")

if __name__ == "__main__":
    test_datapoints_are_created()