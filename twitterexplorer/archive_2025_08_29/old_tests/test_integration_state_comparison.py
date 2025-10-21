"""Compare system state between working isolated test and failing integration test"""
import sys
import os
import json

# Setup paths
project_root = os.path.dirname(__file__)
twitterexplorer_path = os.path.join(project_root, 'twitterexplorer')
sys.path.insert(0, twitterexplorer_path)

from investigation_engine import InvestigationEngine, InvestigationConfig

def capture_system_state(context_name):
    """Capture comprehensive system state during execution"""
    
    print(f"\n=== CAPTURING STATE: {context_name} ===")
    
    api_key = "d72bcd77e2msh76c7e6cf37f0b89p1c51bcjsnaad0f6b01e4f"
    engine = InvestigationEngine(api_key)
    config = InvestigationConfig(max_searches=1, pages_per_search=1)  # Minimal for comparison
    
    state_capture = {
        "context": context_name,
        "pre_investigation": {},
        "during_analysis": {},
        "post_investigation": {}
    }
    
    # Capture pre-investigation state
    state_capture["pre_investigation"] = {
        "graph_mode": getattr(engine, 'graph_mode', None),
        "llm_coordinator_exists": hasattr(engine, 'llm_coordinator'),
        "llm_coordinator_type": str(type(engine.llm_coordinator)) if hasattr(engine, 'llm_coordinator') else None
    }
    
    # Patch analysis method to capture mid-execution state
    original_analyze = engine._analyze_round_results_with_llm
    
    def state_capturing_analyze(session, round_obj, results):
        # Capture state during analysis
        state_capture["during_analysis"] = {
            "session_accumulated_findings": len(session.accumulated_findings),
            "results_count": len(results),
            "graph_exists": hasattr(engine, 'llm_coordinator') and hasattr(engine.llm_coordinator, 'graph'),
            "graph_nodes_before": len(engine.llm_coordinator.graph.nodes) if hasattr(engine, 'llm_coordinator') and hasattr(engine.llm_coordinator, 'graph') else 0,
            "raw_results_samples": []
        }
        
        # Sample raw results structure
        for i, result in enumerate(results[:2]):
            if hasattr(result, '_raw_results'):
                state_capture["during_analysis"]["raw_results_samples"].append({
                    "index": i,
                    "endpoint": result.endpoint,
                    "raw_count": len(result._raw_results),
                    "has_text": bool(result._raw_results and result._raw_results[0].get('text'))
                })
        
        # Call original
        analysis_result = original_analyze(session, round_obj, results)
        
        # Capture state after analysis
        state_capture["during_analysis"]["graph_nodes_after"] = len(engine.llm_coordinator.graph.nodes) if hasattr(engine, 'llm_coordinator') and hasattr(engine.llm_coordinator, 'graph') else 0
        state_capture["during_analysis"]["datapoints_created"] = len([n for n in engine.llm_coordinator.graph.nodes.values() if 'DataPoint' in str(type(n))]) if hasattr(engine, 'llm_coordinator') and hasattr(engine.llm_coordinator, 'graph') else 0
        state_capture["during_analysis"]["session_accumulated_findings_after"] = len(session.accumulated_findings)
        
        return analysis_result
    
    engine._analyze_round_results_with_llm = state_capturing_analyze
    
    # Run investigation
    result = engine.conduct_investigation(
        "Elon Musk X platform news",
        config
    )
    
    # Capture post-investigation state
    state_capture["post_investigation"] = {
        "final_datapoints": len([n for n in engine.llm_coordinator.graph.nodes.values() if 'DataPoint' in str(type(n))]) if hasattr(engine, 'llm_coordinator') and hasattr(engine.llm_coordinator, 'graph') else 0,
        "final_findings": len(result.accumulated_findings),
        "final_graph_nodes": len(engine.llm_coordinator.graph.nodes) if hasattr(engine, 'llm_coordinator') and hasattr(engine.llm_coordinator, 'graph') else 0,
        "search_count": result.search_count,
        "total_results": result.total_results_found
    }
    
    return state_capture

def test_state_comparison():
    """EVIDENCE: Compare system states between different execution contexts"""
    
    # Capture state from isolated context (like individual tests)
    isolated_state = capture_system_state("isolated_test")
    
    # Capture state from integration context (like full test_full_flow.py)
    integration_state = capture_system_state("integration_test")
    
    # Compare states
    comparison = {
        "isolated": isolated_state,
        "integration": integration_state,
        "differences": []
    }
    
    # Identify key differences
    iso_final = isolated_state["post_investigation"]
    int_final = integration_state["post_investigation"]
    
    if iso_final["final_datapoints"] != int_final["final_datapoints"]:
        comparison["differences"].append(f"DataPoints: isolated={iso_final['final_datapoints']}, integration={int_final['final_datapoints']}")
    
    if iso_final["final_findings"] != int_final["final_findings"]:
        comparison["differences"].append(f"Findings: isolated={iso_final['final_findings']}, integration={int_final['final_findings']}")
        
    if iso_final["final_graph_nodes"] != int_final["final_graph_nodes"]:
        comparison["differences"].append(f"Graph nodes: isolated={iso_final['final_graph_nodes']}, integration={int_final['final_graph_nodes']}")
    
    print("\n=== STATE COMPARISON RESULTS ===")
    print(f"Isolated final datapoints: {iso_final['final_datapoints']}")
    print(f"Integration final datapoints: {int_final['final_datapoints']}")
    print(f"Isolated final findings: {iso_final['final_findings']}")
    print(f"Integration final findings: {int_final['final_findings']}")
    
    if comparison["differences"]:
        print("\nKEY DIFFERENCES FOUND:")
        for diff in comparison["differences"]:
            print(f"  - {diff}")
    else:
        print("\nNo significant differences detected")
    
    # Save detailed comparison
    with open("state_comparison.json", "w") as f:
        json.dump(comparison, f, indent=2)
    
    return comparison

if __name__ == "__main__":
    test_state_comparison()