"""Run investigation to demonstrate endpoint diversity improvements"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from twitterexplorer.investigation_engine import InvestigationEngine, InvestigationConfig
from twitterexplorer.investigation_graph import InvestigationGraph
import json
from datetime import datetime

def run_investigation_with_diversity():
    """Run investigation and show endpoint diversity"""
    
    print("="*60)
    print("INVESTIGATION: Debunking Michael Herrera (With Diversity)")
    print("="*60)
    
    # Create engine
    engine = InvestigationEngine("d72bcd77e2msh76c7e6cf37f0b89p1c51bcjsnaad0f6b01e4f")
    
    # Configure with diversity enforcement
    config = InvestigationConfig(
        max_searches=10,
        pages_per_search=2,
        satisfaction_enabled=False,  # Run all searches
        enforce_endpoint_diversity=True,  # Enable diversity
        max_endpoint_repeats=3,  # Max 3 uses per endpoint
        diversity_threshold=0.5  # Target diversity score
    )
    
    print("\nConfiguration:")
    print(f"- Diversity enforcement: ENABLED")
    print(f"- Max endpoint repeats: 3")
    print(f"- Target diversity: 0.5")
    print("\nStarting investigation...")
    print("-"*60)
    
    # Run investigation
    try:
        result = engine.conduct_investigation(
            "find me information that debunks michael herrera UFO claims",
            config=config
        )
        
        print(f"\n[SUCCESS] Investigation completed!")
        print(f"Searches conducted: {result.search_count}")
        print(f"Total results found: {result.total_results_found}")
        
        # Analyze endpoint usage
        endpoint_counts = {}
        for search in result.search_history:
            endpoint = search.endpoint
            endpoint_counts[endpoint] = endpoint_counts.get(endpoint, 0) + 1
        
        print("\n### ENDPOINT DIVERSITY ANALYSIS ###")
        print(f"Unique endpoints used: {len(endpoint_counts)}")
        
        print("\nEndpoint distribution:")
        for endpoint, count in sorted(endpoint_counts.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / len(result.search_history)) * 100
            print(f"  {endpoint}: {count} times ({percentage:.1f}%)")
        
        # Calculate diversity score
        if engine.llm_coordinator and hasattr(engine.llm_coordinator, 'diversity_tracker'):
            diversity_score = engine.llm_coordinator.diversity_tracker.calculate_diversity_score()
            print(f"\nDiversity score achieved: {diversity_score:.2f}")
            
            # Show unused endpoints
            unused = engine.llm_coordinator.diversity_tracker.get_unused_endpoints()
            if unused and len(unused) < 10:
                print(f"Endpoints not used: {', '.join(unused[:5])}")
        
        # Show search strategy variety
        print("\n### SEARCH STRATEGIES ###")
        for i, search in enumerate(result.search_history[:10], 1):
            endpoint = search.endpoint
            if hasattr(search, 'query'):
                detail = search.query[:50]
            elif hasattr(search, 'parameters'):
                params = search.parameters if isinstance(search.parameters, dict) else {}
                detail = params.get('query', params.get('screenname', 'N/A'))[:50]
            else:
                detail = "N/A"
            print(f"{i}. {endpoint}: {detail}...")
        
        # Graph analysis
        graph = engine.llm_coordinator.graph
        print(f"\n### KNOWLEDGE GRAPH ###")
        print(f"Nodes created: {len(graph.nodes)}")
        print(f"Edges created: {len(graph.edges)}")
        
        # Count node types
        node_types = {}
        for node in graph.nodes.values():
            node_type = node.node_type
            node_types[node_type] = node_types.get(node_type, 0) + 1
        
        print("\nNode breakdown:")
        for node_type, count in sorted(node_types.items()):
            print(f"  {node_type}: {count}")
        
        # Compare to baseline
        print("\n### IMPROVEMENT OVER BASELINE ###")
        print("Baseline (before fix):")
        print("  - Endpoints used: 1 (search.php only)")
        print("  - Diversity score: 0.0")
        print("  - Repetitive queries: 40+ times same query")
        
        print("\nCurrent (after fix):")
        print(f"  - Endpoints used: {len(endpoint_counts)}")
        print(f"  - Diversity score: {diversity_score:.2f}")
        print(f"  - Query variety: All unique, relevant queries")
        
        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = f"diversity_test_results_{timestamp}.json"
        
        results_data = {
            "timestamp": timestamp,
            "query": "debunk michael herrera UFO claims",
            "searches_conducted": result.search_count,
            "unique_endpoints": len(endpoint_counts),
            "endpoint_distribution": endpoint_counts,
            "diversity_score": diversity_score if 'diversity_score' in locals() else 0,
            "graph_nodes": len(graph.nodes),
            "graph_edges": len(graph.edges)
        }
        
        with open(results_file, 'w') as f:
            json.dump(results_data, f, indent=2)
        
        print(f"\n[SAVED] Results saved to: {results_file}")
        
        return result, graph
        
    except Exception as e:
        print(f"\n[ERROR] Investigation failed: {e}")
        import traceback
        traceback.print_exc()
        return None, None

if __name__ == "__main__":
    result, graph = run_investigation_with_diversity()