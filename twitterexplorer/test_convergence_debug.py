#!/usr/bin/env python3
"""
Debug script to test convergence edge extraction
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'twitterexplorer'))

from twitterexplorer.graph_visualizer import InvestigationGraphVisualizer

# Test data with convergence edges
demo_wave_data = {
    "investigation_goal": "Test convergence extraction",
    "wave_count": 1,
    "nodes": [
        {"id": "d1", "name": "Data 1", "type": "DataPoint", "wave": 1},
        {"id": "d2", "name": "Data 2", "type": "DataPoint", "wave": 1},
        {"id": "i1", "name": "Insight 1", "type": "Insight", "wave": 1},
    ],
    "edges": [
        {"source": "d1", "target": "i1", "type": "SUPPORTS"},
        {"source": "d2", "target": "i1", "type": "SUPPORTS"},
    ]
}

# Test convergence edge extraction
visualizer = InvestigationGraphVisualizer()
convergence_edges = visualizer._extract_convergence_edges(demo_wave_data)

print("Test data edges:")
for edge in demo_wave_data["edges"]:
    print(f"  {edge}")

print(f"\nExtracted convergence edges ({len(convergence_edges)}):")
for edge in convergence_edges:
    print(f"  {edge['source']} --{edge['type']}--> {edge['target']} (convergence: {edge['is_convergence']})")

print(f"\nConvergence edges found: {len(convergence_edges) > 0}")