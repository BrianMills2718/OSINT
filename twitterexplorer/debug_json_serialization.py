#!/usr/bin/env python3
"""
Debug JSON serialization of convergence edges
"""

import sys
import os
import json
sys.path.append(os.path.join(os.path.dirname(__file__), 'twitterexplorer'))

from twitterexplorer.graph_visualizer import InvestigationGraphVisualizer

# Test data
demo_wave_data = {
    "investigation_goal": "Test JSON serialization",
    "wave_count": 1,
    "nodes": [
        {"id": "s1", "name": "Search 1", "type": "Search", "wave": 1},
        {"id": "d1", "name": "Data 1", "type": "DataPoint", "wave": 1},
    ],
    "edges": [
        {"source": "s1", "target": "d1", "type": "PRODUCES"},
        {"source": "s1", "target": "d1", "type": "PRODUCES"},  # duplicate to create convergence
    ]
}

visualizer = InvestigationGraphVisualizer()
convergence_edges = visualizer._extract_convergence_edges(demo_wave_data)

print(f"Convergence edges extracted: {len(convergence_edges)}")
for edge in convergence_edges:
    print(f"  {edge}")

# Test JSON serialization
try:
    json_str = json.dumps(convergence_edges, indent=2)
    print(f"\nJSON serialization successful:")
    print(json_str[:200] + "..." if len(json_str) > 200 else json_str)
except Exception as e:
    print(f"\nJSON serialization ERROR: {e}")
    print(f"Error type: {type(e)}")
    
    # Check what's causing the error
    for i, edge in enumerate(convergence_edges):
        try:
            json.dumps(edge)
            print(f"  Edge {i} OK")
        except Exception as edge_error:
            print(f"  Edge {i} ERROR: {edge_error}")
            print(f"  Edge {i} data: {edge}")

# Test the template formatting directly
try:
    test_template = f"""const convergenceEdges = {json.dumps(convergence_edges, indent=2)};"""
    print(f"\nTemplate formatting successful:")
    print(test_template[:100] + "..." if len(test_template) > 100 else test_template)
except Exception as e:
    print(f"\nTemplate formatting ERROR: {e}")
    print(f"Variables available: convergence_edges = {type(convergence_edges)}")