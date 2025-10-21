#!/usr/bin/env python3
"""
Debug the convergence detection algorithm step by step
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'twitterexplorer'))

from twitterexplorer.graph_visualizer import InvestigationGraphVisualizer

# Simple test data to debug the algorithm
demo_edges = [
    {"source": "d1_1", "target": "i1_1", "type": "SUPPORTS"},
    {"source": "d1_2", "target": "i1_1", "type": "SUPPORTS"},  # i1_1 should be convergence target
    {"source": "d1_1", "target": "i1_2", "type": "SUPPORTS"},
    {"source": "d1_2", "target": "i1_2", "type": "SUPPORTS"},  # i1_2 should be convergence target
]

demo_nodes = [
    {"id": "d1_1", "name": "Data 1", "type": "DataPoint"},
    {"id": "d1_2", "name": "Data 2", "type": "DataPoint"},
    {"id": "i1_1", "name": "Insight 1", "type": "Insight"},
    {"id": "i1_2", "name": "Insight 2", "type": "Insight"},
]

wave_data = {
    "nodes": demo_nodes,
    "edges": demo_edges
}

print("Input data:")
print("Nodes:", [n["id"] for n in demo_nodes])
print("Edges:")
for edge in demo_edges:
    print(f"  {edge['source']} --{edge['type']}--> {edge['target']}")

# Test the algorithm step by step
visualizer = InvestigationGraphVisualizer()

# Manually run the convergence detection algorithm
edges = wave_data.get('edges', [])
nodes = wave_data.get('nodes', [])
node_dict = {node['id']: node for node in nodes}

print(f"\nNode dictionary: {list(node_dict.keys())}")

convergence_edges = []

# Group edges by target to find convergence points
edges_by_target = {}
for edge in edges:
    target = edge['target']
    if target not in edges_by_target:
        edges_by_target[target] = []
    edges_by_target[target].append(edge)

print(f"\nEdges by target:")
for target, target_edges in edges_by_target.items():
    print(f"  {target}: {len(target_edges)} edges")
    for edge in target_edges:
        print(f"    {edge['source']} --{edge['type']}--> {edge['target']}")

# Find convergence points (nodes with multiple incoming edges of same type)
print(f"\nChecking for convergence points...")
for target_id, target_edges in edges_by_target.items():
    print(f"\nTarget {target_id} has {len(target_edges)} incoming edges")
    
    if len(target_edges) > 1:
        print(f"  -> CONVERGENCE DETECTED for {target_id}")
        target_node = node_dict.get(target_id)
        if target_node:
            print(f"  -> Target node found: {target_node}")
            for edge in target_edges:
                source_node = node_dict.get(edge['source'])
                if source_node:
                    convergence_edge = {
                        'source': edge['source'],
                        'target': target_id,
                        'type': edge.get('type', 'UNKNOWN'),
                        'source_node': source_node,
                        'target_node': target_node,
                        'is_convergence': True
                    }
                    convergence_edges.append(convergence_edge)
                    print(f"    -> Added convergence edge: {convergence_edge['source']} --{convergence_edge['type']}--> {convergence_edge['target']}")
                else:
                    print(f"    -> ERROR: Source node {edge['source']} not found")
        else:
            print(f"  -> ERROR: Target node {target_id} not found")
    else:
        print(f"  -> No convergence (only {len(target_edges)} edge)")

print(f"\nFinal result: {len(convergence_edges)} convergence edges")
for edge in convergence_edges:
    print(f"  {edge['source']} --{edge['type']}--> {edge['target']}")