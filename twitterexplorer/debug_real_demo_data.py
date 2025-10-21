#!/usr/bin/env python3
"""
Debug with the EXACT demo data from create_hierarchy_demo.py
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'twitterexplorer'))

from twitterexplorer.graph_visualizer import InvestigationGraphVisualizer

# Use the EXACT demo data from the create_demo_hierarchy function
demo_wave_data = {
    "investigation_goal": "Analyze impact of AI on employment and workforce transformation",
    "wave_count": 3,
    "nodes": [
        # Analytic Goal (root)
        {"id": "analytic_goal", "name": "Analyze AI employment impact", "type": "AnalyticGoal", "wave": 0,
         "full_text": "Analyze impact of AI on employment and workforce transformation"},
        
        # Wave 1: Initial investigation questions and searches
        {"id": "q1_1", "name": "What are AI employment impacts?", "type": "InvestigationQuestion", "wave": 1,
         "full_text": "What are the current and projected impacts of AI on employment across different sectors?"},
        {"id": "q1_2", "name": "How is workforce adapting?", "type": "InvestigationQuestion", "wave": 1,
         "full_text": "How is the workforce adapting to AI-driven changes and what trends are emerging?"},
        
        {"id": "s1_1", "name": "AI employment impact search", "type": "Search", "wave": 1, 
         "full_text": "Search for AI employment impact studies and reports", 
         "details": {"query": "AI employment impact studies", "endpoint": "search.php", "results": 45}},
        {"id": "s1_2", "name": "Workforce automation trends", "type": "Search", "wave": 1, 
         "full_text": "Search for workforce automation trends and predictions", 
         "details": {"query": "workforce automation trends", "endpoint": "search.php", "results": 38}},
        
        {"id": "d1_1", "name": "McKinsey automation report", "type": "DataPoint", "wave": 1,
         "full_text": "McKinsey report showing 375 million workers need reskilling by 2030"},
        {"id": "d1_2", "name": "MIT automation study", "type": "DataPoint", "wave": 1,
         "full_text": "MIT study on sector-specific AI adoption rates and job displacement patterns"},
        
        {"id": "i1_1", "name": "AI displaces routine jobs first", "type": "Insight", "wave": 1, 
         "full_text": "AI primarily displaces routine, predictable jobs across sectors"},
        {"id": "i1_2", "name": "Reskilling demand accelerating", "type": "Insight", "wave": 1, 
         "full_text": "Companies increasing investment in worker reskilling programs"},
         
        {"id": "eq1_1", "name": "Which sectors most vulnerable?", "type": "EmergentQuestion", "wave": 1, 
         "full_text": "Which specific sectors and job categories are most vulnerable to AI displacement?"},
        {"id": "eq1_2", "name": "How effective is reskilling?", "type": "EmergentQuestion", "wave": 1, 
         "full_text": "How effective are current reskilling programs at preventing unemployment?"}
    ],
    "edges": [
        # AnalyticGoal generates investigation questions
        {"source": "analytic_goal", "target": "q1_1", "type": "GENERATES"},
        {"source": "analytic_goal", "target": "q1_2", "type": "GENERATES"},
        
        # Investigation questions lead to searches
        {"source": "q1_1", "target": "s1_1", "type": "LEADS_TO"},
        {"source": "q1_2", "target": "s1_2", "type": "LEADS_TO"},
        
        # Searches produce data - CONVERGENCE HERE!
        {"source": "s1_1", "target": "d1_1", "type": "PRODUCES"},
        {"source": "s1_1", "target": "d1_2", "type": "PRODUCES"},
        {"source": "s1_2", "target": "d1_1", "type": "PRODUCES"},  # d1_1 from 2 searches
        {"source": "s1_2", "target": "d1_2", "type": "PRODUCES"},  # d1_2 from 2 searches
        
        # Data supports insights - CONVERGENCE HERE!
        {"source": "d1_1", "target": "i1_1", "type": "SUPPORTS"},
        {"source": "d1_2", "target": "i1_1", "type": "SUPPORTS"},  # i1_1 from 2 datapoints
        {"source": "d1_1", "target": "i1_2", "type": "SUPPORTS"},
        {"source": "d1_2", "target": "i1_2", "type": "SUPPORTS"},  # i1_2 from 2 datapoints
        
        # Insights spawn emergent questions
        {"source": "i1_1", "target": "eq1_1", "type": "SPAWNS"},
        {"source": "i1_2", "target": "eq1_2", "type": "SPAWNS"}
    ]
}

print("Real demo data analysis:")
print(f"Nodes: {len(demo_wave_data['nodes'])}")
print(f"Edges: {len(demo_wave_data['edges'])}")

print("\nExpected convergence points:")
print("  d1_1 (2 PRODUCES edges)")
print("  d1_2 (2 PRODUCES edges)")
print("  i1_1 (2 SUPPORTS edges)")
print("  i1_2 (2 SUPPORTS edges)")

# Test convergence detection
visualizer = InvestigationGraphVisualizer()
convergence_edges = visualizer._extract_convergence_edges(demo_wave_data)

print(f"\nActual convergence edges found: {len(convergence_edges)}")

if len(convergence_edges) > 0:
    print("\nConvergence edges:")
    for edge in convergence_edges:
        print(f"  {edge['source']} --{edge['type']}--> {edge['target']}")
else:
    print("\nNo convergence edges found - debugging...")
    
    # Debug the algorithm manually
    edges_by_target = {}
    for edge in demo_wave_data['edges']:
        target = edge['target']
        if target not in edges_by_target:
            edges_by_target[target] = []
        edges_by_target[target].append(edge)
    
    print("\nEdges by target (showing > 1):")
    for target, target_edges in edges_by_target.items():
        if len(target_edges) > 1:
            print(f"  {target}: {len(target_edges)} edges")
            for edge in target_edges:
                print(f"    {edge['source']} --{edge['type']}--> {edge['target']}")