"""Comprehensive debugging test to identify DataPoint creation divergence"""
import sys
import os
import json
from datetime import datetime

# Setup paths
project_root = os.path.dirname(__file__)
twitterexplorer_path = os.path.join(project_root, 'twitterexplorer')
sys.path.insert(0, twitterexplorer_path)

from investigation_engine import InvestigationEngine, InvestigationConfig

def test_datapoint_diagnostic_logging():
    """EVIDENCE: Capture complete execution flow for DataPoint creation"""
    
    print("=== DATAPOINT DIAGNOSTIC TEST ===")
    
    api_key = "d72bcd77e2msh76c7e6cf37f0b89p1c51bcjsnaad0f6b01e4f"
    engine = InvestigationEngine(api_key)
    config = InvestigationConfig(max_searches=2, pages_per_search=1)
    
    # Capture execution state at critical points
    execution_log = {
        "test_type": "isolated_diagnostic",
        "timestamp": datetime.now().isoformat(),
        "checkpoints": []
    }
    
    def log_checkpoint(name, data):
        execution_log["checkpoints"].append({
            "checkpoint": name,
            "timestamp": datetime.now().isoformat(),
            "data": data
        })
        print(f"CHECKPOINT [{name}]: {data}")
    
    # Patch _analyze_round_results_with_llm for full visibility
    original_analyze = engine._analyze_round_results_with_llm
    
    def diagnostic_analyze(session, round_obj, results):
        log_checkpoint("analyze_entry", {
            "session_id": getattr(session, 'session_id', 'unknown'),
            "results_count": len(results),
            "graph_mode": getattr(engine, 'graph_mode', None),
            "llm_coordinator_exists": hasattr(engine, 'llm_coordinator'),
            "accumulated_findings_before": len(session.accumulated_findings)
        })
        
        # Check raw results structure
        for i, result in enumerate(results):
            if hasattr(result, '_raw_results'):
                log_checkpoint(f"raw_results_{i}", {
                    "raw_count": len(result._raw_results),
                    "endpoint": result.endpoint,
                    "search_id": getattr(result, 'search_id', 'missing'),
                    "sample_text": result._raw_results[0].get('text', 'NO TEXT')[:100] if result._raw_results else "NO RESULTS"
                })
        
        # Call original method
        result = original_analyze(session, round_obj, results)
        
        log_checkpoint("analyze_exit", {
            "accumulated_findings_after": len(session.accumulated_findings),
            "graph_nodes": len(engine.llm_coordinator.graph.nodes) if hasattr(engine, 'llm_coordinator') and hasattr(engine.llm_coordinator, 'graph') else 0,
            "datapoint_count": len([n for n in engine.llm_coordinator.graph.nodes.values() if 'DataPoint' in str(type(n))]) if hasattr(engine, 'llm_coordinator') and hasattr(engine.llm_coordinator, 'graph') else 0
        })
        
        return result
    
    engine._analyze_round_results_with_llm = diagnostic_analyze
    
    # Run investigation
    result = engine.conduct_investigation(
        "Elon Musk X platform announcement",
        config
    )
    
    log_checkpoint("investigation_complete", {
        "final_datapoints": len([n for n in engine.llm_coordinator.graph.nodes.values() if 'DataPoint' in str(type(n))]) if hasattr(engine, 'llm_coordinator') and hasattr(engine.llm_coordinator, 'graph') else 0,
        "final_findings": len(result.accumulated_findings),
        "final_summary_exists": hasattr(result, 'final_summary') and result.final_summary is not None,
        "search_count": result.search_count,
        "total_results": result.total_results_found
    })
    
    # Save diagnostic log
    with open("datapoint_diagnostic.json", "w") as f:
        json.dump(execution_log, f, indent=2)
    
    print("\n=== DIAGNOSTIC SUMMARY ===")
    for checkpoint in execution_log["checkpoints"]:
        print(f"{checkpoint['checkpoint']}: {checkpoint['data']}")
    
    return execution_log

if __name__ == "__main__":
    test_datapoint_diagnostic_logging()