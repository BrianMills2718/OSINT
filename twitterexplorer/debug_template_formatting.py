#!/usr/bin/env python3
"""
Debug template formatting issue
"""

import sys
import os
import json
sys.path.append(os.path.join(os.path.dirname(__file__), 'twitterexplorer'))

# Test a simplified version of the template formatting to isolate the issue
demo_wave_data = {
    "investigation_goal": "Test template formatting",
    "nodes": [{"id": "test", "name": "Test Node", "type": "Test"}],
    "edges": []
}

# Simulate the method variables
hierarchy_data = {"name": "Test", "type": "AnalyticGoal"}
convergence_edges = [{"source": "a", "target": "b", "type": "TEST"}]
title = "Test Title"
node_colors = {"Test": "#FF0000"}
node_sizes = {"Test": 10}

print("Variables defined:")
print(f"  hierarchy_data: {type(hierarchy_data)}")
print(f"  convergence_edges: {type(convergence_edges)} (len={len(convergence_edges)})")
print(f"  title: {title}")

# Test a simple template first
try:
    simple_template = f"""
    <script>
        const hierarchyData = {json.dumps(hierarchy_data, indent=2)};
        const convergenceEdges = {json.dumps(convergence_edges, indent=2)};
    </script>
    """
    print("\nSimple template SUCCESS:")
    print(simple_template)
except Exception as e:
    print(f"\nSimple template ERROR: {e}")

# Now test with the exact same structure as the original template
try:
    # This matches the structure in graph_visualizer.py lines 2085-2086
    complex_template = f"""    <script>
        // Wave hierarchy data from Python
        const hierarchyData = {json.dumps(hierarchy_data, indent=2)};
        const convergenceEdges = {json.dumps(convergence_edges, indent=2)};
        
        // Set up SVG dimensions
        const margin = {{top: 60, right: 120, bottom: 60, left: 120}};"""
    
    print("\nComplex template SUCCESS:")
    print(complex_template[:300] + "...")
    
    # Check if both variables are present
    if "hierarchyData" in complex_template and "convergenceEdges" in complex_template:
        print("Both variables found in complex template")
    else:
        print("ERROR: Variables missing from complex template")
        
except Exception as e:
    print(f"\nComplex template ERROR: {e}")
    import traceback
    traceback.print_exc()