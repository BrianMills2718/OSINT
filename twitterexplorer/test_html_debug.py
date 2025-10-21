#!/usr/bin/env python3
"""
Debug script to test HTML generation with convergence edges
"""

import sys
import os
import json
sys.path.append(os.path.join(os.path.dirname(__file__), 'twitterexplorer'))

from twitterexplorer.graph_visualizer import InvestigationGraphVisualizer

# Test data with convergence edges
demo_wave_data = {
    "investigation_goal": "Test convergence HTML generation",
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

# Test HTML generation
visualizer = InvestigationGraphVisualizer()

# Test the methods individually
hierarchy_data = visualizer._build_investigation_hierarchy(demo_wave_data)
convergence_edges = visualizer._extract_convergence_edges(demo_wave_data)

print("Hierarchy data nodes:")
def print_nodes(node, indent=0):
    print("  " * indent + f"- {node['name']} ({node['type']})")
    for child in node.get('children', []):
        print_nodes(child, indent + 1)
        
print_nodes(hierarchy_data)

print(f"\nConvergence edges ({len(convergence_edges)}):")
for edge in convergence_edges:
    print(f"  {edge['source']} --{edge['type']}--> {edge['target']}")

# Generate HTML
html = visualizer._generate_wave_network_html(demo_wave_data, "Debug Test")

# Check if convergence edges are in HTML
if "convergenceEdges" in html:
    print("\n[OK] convergenceEdges found in HTML")
    # Extract the JavaScript part with convergence edges
    start = html.find("const convergenceEdges")
    if start != -1:
        end = html.find(";", start)
        print(f"Found: {html[start:end + 1]}")
else:
    print("\n[ERROR] convergenceEdges NOT found in HTML")
    # Check what variables are defined
    if "const hierarchyData" in html:
        print("[OK] hierarchyData found in HTML")
    else:
        print("[ERROR] hierarchyData also missing")