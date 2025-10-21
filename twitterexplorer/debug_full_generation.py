#!/usr/bin/env python3
"""
Debug the full HTML generation process
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'twitterexplorer'))

from twitterexplorer.graph_visualizer import InvestigationGraphVisualizer

# Use simplified demo data for cleaner debugging
demo_wave_data = {
    "investigation_goal": "Test convergence visualization",
    "wave_count": 1,
    "nodes": [
        {"id": "s1", "name": "Search 1", "type": "Search", "wave": 1},
        {"id": "s2", "name": "Search 2", "type": "Search", "wave": 1},
        {"id": "d1", "name": "Data 1", "type": "DataPoint", "wave": 1},
        {"id": "i1", "name": "Insight 1", "type": "Insight", "wave": 1},
    ],
    "edges": [
        {"source": "s1", "target": "d1", "type": "PRODUCES"},
        {"source": "s2", "target": "d1", "type": "PRODUCES"},  # d1 from 2 sources
        {"source": "d1", "target": "i1", "type": "SUPPORTS"},
    ]
}

# Test the full generation process
visualizer = InvestigationGraphVisualizer()

# Step 1: Test convergence edge extraction
convergence_edges = visualizer._extract_convergence_edges(demo_wave_data)
print(f"Step 1 - Convergence edges extracted: {len(convergence_edges)}")
for edge in convergence_edges:
    print(f"  {edge['source']} --{edge['type']}--> {edge['target']}")

# Step 2: Test HTML generation
html = visualizer._generate_wave_network_html(demo_wave_data, "Test Visualization")

# Step 3: Check if convergence edges made it into the HTML
if "const convergenceEdges" in html:
    print(f"\nStep 3 - SUCCESS: convergenceEdges found in HTML")
    # Extract and show the convergence edges data
    start = html.find("const convergenceEdges = ")
    if start != -1:
        end = html.find(";", start)
        convergence_js = html[start:end]
        print(f"JavaScript declaration found: {convergence_js[:100]}...")
    else:
        print("ERROR: convergenceEdges declaration not found")
else:
    print(f"\nStep 3 - ERROR: convergenceEdges NOT found in HTML")
    print("Looking for other variables...")
    if "const hierarchyData" in html:
        print("  hierarchyData found")
    else:
        print("  hierarchyData also missing")

# Step 4: Check if the JavaScript convergence drawing function exists
if "drawConvergenceEdges" in html:
    print(f"Step 4 - SUCCESS: drawConvergenceEdges function found")
else:
    print(f"Step 4 - ERROR: drawConvergenceEdges function missing")

# Step 5: Save a test file
test_file = "test_convergence_visualization.html"
with open(test_file, 'w', encoding='utf-8') as f:
    f.write(html)
print(f"\nStep 5 - Test HTML saved to: {test_file}")
print("Open this file in your browser to see if convergence edges appear")