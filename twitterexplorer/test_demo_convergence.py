#!/usr/bin/env python3
"""
Debug the actual demo data for convergence edge detection
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'twitterexplorer'))

# Import the exact same data structure from the demo
from create_hierarchy_demo import create_demo_hierarchy
from twitterexplorer.graph_visualizer import InvestigationGraphVisualizer

# Extract the demo data (copy from create_hierarchy_demo.py)
demo_wave_data = {
    "investigation_goal": "Analyze impact of AI on employment and workforce transformation",
    "wave_count": 3,
    "nodes": [
        # ... (we'll just check the edges for now)
    ],
    "edges": [
        # Data supports insights - These should create convergence!
        {"source": "d1_1", "target": "i1_1", "type": "SUPPORTS"},
        {"source": "d1_2", "target": "i1_1", "type": "SUPPORTS"},  # i1_1 has 2 sources!
        {"source": "d1_1", "target": "i1_2", "type": "SUPPORTS"},
        {"source": "d1_2", "target": "i1_2", "type": "SUPPORTS"},  # i1_2 has 2 sources!
        
        # Insights spawn emergent questions
        {"source": "i1_1", "target": "eq1_1", "type": "SPAWNS"},
        {"source": "i1_2", "target": "eq1_2", "type": "SPAWNS"},
        
        # Additional edges...
        {"source": "s1_1", "target": "d1_1", "type": "PRODUCES"},
        {"source": "s1_1", "target": "d1_2", "type": "PRODUCES"},
        {"source": "s1_2", "target": "d1_1", "type": "PRODUCES"},  # d1_1 has 2 sources!
        {"source": "s1_2", "target": "d1_2", "type": "PRODUCES"},  # d1_2 has 2 sources!
    ]
}

# Test convergence detection
visualizer = InvestigationGraphVisualizer()
convergence_edges = visualizer._extract_convergence_edges(demo_wave_data)

print("Expected convergence targets:")
print("  i1_1 (should have 2 SUPPORTS edges: d1_1, d1_2)")
print("  i1_2 (should have 2 SUPPORTS edges: d1_1, d1_2)")
print("  d1_1 (should have 2 PRODUCES edges: s1_1, s1_2)")
print("  d1_2 (should have 2 PRODUCES edges: s1_1, s1_2)")

print(f"\nActual convergence edges found: {len(convergence_edges)}")

# Group by target to show convergence
by_target = {}
for edge in convergence_edges:
    target = edge['target']
    if target not in by_target:
        by_target[target] = []
    by_target[target].append(edge)

for target, edges in by_target.items():
    print(f"\nTarget {target} has {len(edges)} convergent edges:")
    for edge in edges:
        print(f"  {edge['source']} --{edge['type']}--> {edge['target']}")