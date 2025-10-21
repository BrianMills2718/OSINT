#!/usr/bin/env python3
"""
Create a visual representation of the investigation graph
"""
import json
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import networkx as nx
from matplotlib.patches import FancyBboxPatch
import numpy as np

def create_graph_visualization(graph_file='current_investigation_graph.json'):
    """Create a visual diagram of the investigation graph"""
    
    # Load graph data
    with open(graph_file, 'r') as f:
        data = json.load(f)
    
    # Create NetworkX graph
    G = nx.DiGraph()
    
    # Track node types for coloring
    node_colors = []
    node_sizes = []
    node_labels = {}
    
    # Color scheme for different node types
    color_map = {
        'AnalyticQuestion': '#FF6B6B',      # Red - Root
        'InvestigationQuestion': '#4ECDC4',  # Teal - Strategic
        'SearchQuery': '#45B7D1',            # Blue - API calls
        'DataPoint': '#96CEB4',              # Green - Data
        'Insight': '#FFEAA7',                # Yellow - Insights
        'EmergentQuestion': '#DDA0DD'        # Purple - Emergent
    }
    
    # Size map for importance
    size_map = {
        'AnalyticQuestion': 3000,
        'InvestigationQuestion': 2000,
        'SearchQuery': 1500,
        'DataPoint': 800,
        'Insight': 1800,
        'EmergentQuestion': 1500
    }
    
    # Add nodes
    for node_id, node_data in data['nodes'].items():
        node_type = node_data.get('type', 'Unknown')
        G.add_node(node_id, node_type=node_type)
        
        # Set visual properties
        node_colors.append(color_map.get(node_type, '#888888'))
        node_sizes.append(size_map.get(node_type, 1000))
        
        # Create label
        props = node_data.get('properties', {})
        if 'text' in props:
            label = props['text'][:30] + '...' if len(props['text']) > 30 else props['text']
        elif node_type == 'SearchQuery':
            endpoint = props.get('endpoint', 'unknown')
            params = props.get('parameters', {})
            if 'query' in params:
                label = f"{endpoint}\n{params['query'][:20]}..."
            elif 'screenname' in params:
                label = f"{endpoint}\n@{params['screenname']}"
            else:
                label = endpoint
        else:
            label = node_type
        
        node_labels[node_id] = label
    
    # Add edges
    edge_labels = {}
    for edge in data['edges']:
        source = edge['source']
        target = edge['target']
        edge_type = edge['type']
        G.add_edge(source, target, edge_type=edge_type)
        edge_labels[(source, target)] = edge_type
    
    # Create figure with larger size
    fig, ax = plt.subplots(figsize=(16, 12))
    
    # Use hierarchical layout for better structure
    # Find root node (AnalyticQuestion)
    root_nodes = [n for n in G.nodes() if 
                  data['nodes'][n].get('type') == 'AnalyticQuestion']
    
    if root_nodes:
        # Create hierarchical positions
        pos = nx.spring_layout(G, k=3, iterations=50)
        
        # Manually adjust for hierarchy if root exists
        root = root_nodes[0]
        levels = nx.single_source_shortest_path_length(G, root)
        
        # Arrange nodes by level
        level_nodes = {}
        for node, level in levels.items():
            if level not in level_nodes:
                level_nodes[level] = []
            level_nodes[level].append(node)
        
        # Set positions based on hierarchy
        y_spacing = -2.0
        for level, nodes in level_nodes.items():
            x_spacing = 4.0 / max(len(nodes), 1)
            for i, node in enumerate(nodes):
                x = -2.0 + i * x_spacing
                y = level * y_spacing
                pos[node] = (x, y)
    else:
        # Fallback to spring layout
        pos = nx.spring_layout(G, k=2, iterations=50)
    
    # Draw the graph
    nx.draw_networkx_nodes(G, pos, 
                          node_color=node_colors,
                          node_size=node_sizes,
                          alpha=0.8,
                          ax=ax)
    
    # Draw edges with arrows
    nx.draw_networkx_edges(G, pos,
                          edge_color='gray',
                          arrows=True,
                          arrowsize=20,
                          width=2,
                          alpha=0.6,
                          connectionstyle='arc3,rad=0.1',
                          ax=ax)
    
    # Draw labels with better formatting
    for node, (x, y) in pos.items():
        node_type = data['nodes'][node].get('type', 'Unknown')
        label = node_labels[node]
        
        # Add text with background
        bbox_props = dict(boxstyle="round,pad=0.3", 
                         facecolor='white', 
                         edgecolor=color_map.get(node_type, '#888888'),
                         alpha=0.9)
        
        ax.text(x, y, label, 
               horizontalalignment='center',
               verticalalignment='center',
               fontsize=8,
               fontweight='bold' if node_type == 'AnalyticQuestion' else 'normal',
               bbox=bbox_props)
    
    # Add edge labels
    nx.draw_networkx_edge_labels(G, pos, 
                                 edge_labels,
                                 font_size=8,
                                 font_color='red',
                                 ax=ax)
    
    # Add title and statistics
    investigation = data.get('investigation', 'Investigation Graph')
    ax.set_title(f'Twitter Investigation Graph Visualization\n"{investigation}"',
                fontsize=16, fontweight='bold', pad=20)
    
    # Add legend
    legend_elements = []
    for node_type, color in color_map.items():
        count = sum(1 for n in data['nodes'].values() 
                   if n.get('type') == node_type)
        if count > 0:
            legend_elements.append(
                patches.Patch(color=color, label=f'{node_type} ({count})')
            )
    
    ax.legend(handles=legend_elements, loc='upper left', fontsize=10)
    
    # Add statistics box
    stats_text = f"Nodes: {len(G.nodes)}\nEdges: {len(G.edges)}"
    ax.text(0.98, 0.02, stats_text,
           transform=ax.transAxes,
           fontsize=10,
           verticalalignment='bottom',
           horizontalalignment='right',
           bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    
    # Remove axes
    ax.set_axis_off()
    
    # Adjust layout
    plt.tight_layout()
    
    # Save the figure
    output_file = graph_file.replace('.json', '_visual.png')
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    print(f"Graph visualization saved to: {output_file}")
    
    # Also show it
    plt.show()
    
    return output_file

if __name__ == "__main__":
    import sys
    
    graph_file = 'current_investigation_graph.json'
    if len(sys.argv) > 1:
        graph_file = sys.argv[1]
    
    output = create_graph_visualization(graph_file)
    print(f"Visualization complete: {output}")