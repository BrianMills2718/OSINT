#!/usr/bin/env python
"""Test real API and create visualization from actual data"""
import os
import sys
import json

# Must run from twitterexplorer directory
if not os.path.exists('investigation_engine.py'):
    os.chdir('twitterexplorer')

# Now we can import
from investigation_engine import InvestigationEngine, InvestigationConfig

# Add parent for graph visualizer
sys.path.insert(0, '..')
from graph_visualizer import InvestigationGraphVisualizer

def main():
    print("=" * 80)
    print(" REAL TWITTER API TEST WITH VISUALIZATION")
    print("=" * 80)
    
    # Load real API key
    api_key = "d72bcd77e2msh76c7e6cf37f0b89p1c51bcjsnaad0f6b01e4f"
    
    # Create engine
    engine = InvestigationEngine(api_key)
    
    # Small config for test
    config = InvestigationConfig(
        max_searches=4,  # Just 1 round
        pages_per_search=1
    )
    
    # Run investigation
    query = "Elon Musk Twitter news"
    print(f"\nQuery: {query}")
    print("-" * 40)
    
    result = engine.conduct_investigation(query, config)
    
    print(f"\n[RESULTS]")
    print(f"Searches: {result.search_count}")
    print(f"Total results: {result.total_results_found}")
    
    # Create visualization
    print("\n[CREATING GRAPH]")
    viz = InvestigationGraphVisualizer()
    
    # Add query
    query_id = viz.add_query_node(query)
    
    # Add searches
    for round_obj in result.rounds:
        for search in round_obj.searches:
            search_id = viz.add_search_node(
                search.params,
                search.endpoint,
                search.search_id,
                parent_id=query_id
            )
            
            if search.results_count > 0:
                viz.add_datapoint_node(
                    f"{search.results_count} results",
                    search.endpoint,
                    search_id
                )
    
    # Save
    viz.save_visualization("../real_api_graph.html")
    print(f"✅ Graph saved to: real_api_graph.html")
    print("   Open in browser to see REAL Twitter data visualization!")

if __name__ == "__main__":
    main()