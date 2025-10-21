"""Debug the exact flow from LLM evaluation to DataPoint creation"""
import sys
import os
import json
from datetime import datetime

# Setup paths
sys.path.insert(0, 'twitterexplorer')
os.chdir('twitterexplorer')

from investigation_engine import InvestigationEngine, InvestigationConfig
from finding_evaluator_llm import LLMFindingEvaluator

def test_findings_integration_flow():
    """EVIDENCE: Trace complete flow from evaluation to DataPoint creation"""
    
    print("=== FINDINGS INTEGRATION FLOW DEBUG ===")
    
    # Test 1: Verify LLM evaluation works in isolation
    print("\n1. TESTING LLM EVALUATION IN ISOLATION")
    evaluator = LLMFindingEvaluator()
    test_result = {
        'text': 'Elon Musk announced new X platform features including improved search',
        'source': 'timeline.php'
    }
    
    assessment = evaluator.evaluate_finding(test_result, 'What is Elon Musk announcing about X platform?')
    print(f"   LLM Assessment: significant={assessment.is_significant}, score={assessment.relevance_score}")
    
    # Test 2: Trace investigation engine flow
    print("\n2. TESTING INVESTIGATION ENGINE INTEGRATION")
    
    api_key = "d72bcd77e2msh76c7e6cf37f0b89p1c51bcjsnaad0f6b01e4f"  # From secrets.toml
    engine = InvestigationEngine(api_key)
    
    # Patch the analysis method to capture data flow
    original_analyze = engine._analyze_round_results_with_llm
    analysis_data = {}
    
    def debug_analyze(session, round_obj, results):
        print(f"   _analyze_round_results_with_llm called with {len(results)} results")
        
        # Check if LLM evaluator is called
        analysis_data['pre_analysis'] = {
            'session_findings': len(session.accumulated_findings),
            'results_count': len(results)
        }
        
        # Call original method
        result = original_analyze(session, round_obj, results)
        
        analysis_data['post_analysis'] = {
            'session_findings': len(session.accumulated_findings),
            'graph_nodes': len(engine.llm_coordinator.graph.nodes) if hasattr(engine, 'llm_coordinator') and hasattr(engine.llm_coordinator, 'graph') else 0,
            'datapoint_nodes': len([n for n in engine.llm_coordinator.graph.nodes.values() if 'DataPoint' in str(type(n))]) if hasattr(engine, 'llm_coordinator') and hasattr(engine.llm_coordinator, 'graph') else 0
        }
        
        print(f"   Analysis result: {analysis_data}")
        
        return result
    
    engine._analyze_round_results_with_llm = debug_analyze
    
    # Run minimal investigation
    config = InvestigationConfig(max_searches=1, pages_per_search=1)
    result = engine.conduct_investigation("What is Elon Musk announcing about X platform?", config)
    
    # Final state analysis
    final_state = {
        'total_findings': len(result.accumulated_findings),
        'satisfaction': result.satisfaction_metrics.overall_satisfaction(),
        'graph_nodes': len(engine.llm_coordinator.graph.nodes) if hasattr(engine, 'llm_coordinator') and hasattr(engine.llm_coordinator, 'graph') else 0,
        'datapoint_nodes': len([n for n in engine.llm_coordinator.graph.nodes.values() if 'DataPoint' in str(type(n))]) if hasattr(engine, 'llm_coordinator') and hasattr(engine.llm_coordinator, 'graph') else 0
    }
    
    print("\n3. FINAL INTEGRATION STATE")
    print(f"   Final findings: {final_state['total_findings']}")
    print(f"   Final DataPoints: {final_state['datapoint_nodes']}")
    print(f"   Final satisfaction: {final_state['satisfaction']}")
    
    # Save diagnostic data
    with open("findings_flow_debug.json", "w") as f:
        json.dump({
            "llm_evaluation": {
                "works": assessment.is_significant,
                "score": assessment.relevance_score
            },
            "analysis_flow": analysis_data,
            "final_state": final_state
        }, f, indent=2)
    
    # Evidence summary
    print("\n=== EVIDENCE SUMMARY ===")
    if assessment.is_significant and final_state['total_findings'] == 0:
        print("CONFIRMED: LLM evaluation works but findings integration fails")
        return "integration_disconnect"
    elif not assessment.is_significant:
        print("ISSUE: LLM evaluation itself is failing")  
        return "evaluation_failure"
    else:
        print("UNEXPECTED: Both systems appear to be working")
        return "unclear"

if __name__ == "__main__":
    result = test_findings_integration_flow()
    print(f"\nDIAGNOSIS: {result}")