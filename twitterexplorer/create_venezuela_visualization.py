#!/usr/bin/env python3
"""
Create hierarchical D3.js visualization for Trump-Venezuela investigation
Using the full 6-node ontology with all insights and relationships
"""

import sys
import json
import os

# Add the twitterexplorer directory to path
sys.path.insert(0, 'twitterexplorer')

from graph_visualizer import InvestigationGraphVisualizer
from investigation_graph import Node, Edge

def load_investigation_graph(filepath):
    """Load the investigation graph from JSON"""
    with open(filepath, 'r') as f:
        graph_data = json.load(f)
    
    # Parse nodes and edges
    nodes = {}
    edges = []
    
    # Load nodes
    for node_id, node_data in graph_data.get('nodes', {}).items():
        nodes[node_id] = Node.from_dict(node_data)
    
    # Load edges
    for edge_data in graph_data.get('edges', []):
        edges.append(Edge.from_dict(edge_data))
    
    return nodes, edges

def create_enhanced_visualizer():
    """Create an enhanced visualizer with the full ontology"""
    
    class EnhancedVisualizer(InvestigationGraphVisualizer):
        """Enhanced visualizer supporting the full 6-node ontology"""
        
        def add_ontology_node(self, node_data, parent_id=None):
            """Add a node based on the ontology type"""
            node_type = node_data.node_type
            node_id = node_data.id
            
            # Node type mapping for visualization
            type_mapping = {
                'AnalyticQuestion': 'query',
                'InvestigationQuestion': 'investigation',
                'SearchQuery': 'search', 
                'DataPoint': 'datapoint',
                'Insight': 'insight',
                'EmergentQuestion': 'emergent'
            }
            
            # Color mapping for the full ontology
            colors = {
                'query': {'background': '#9C27B0', 'border': '#7B1FA2'},  # Purple - Analytic Question
                'investigation': {'background': '#E91E63', 'border': '#C2185B'},  # Pink - Investigation Question  
                'search': {'background': '#4CAF50', 'border': '#388E3C'},  # Green - Search Query
                'datapoint': {'background': '#2196F3', 'border': '#1976D2'},  # Blue - DataPoint
                'insight': {'background': '#FF9800', 'border': '#F57C00'},  # Orange - Insight
                'emergent': {'background': '#9C27B0', 'border': '#7B1FA2'}  # Purple - Emergent Question
            }
            
            # Shape mapping
            shapes = {
                'query': 'star',
                'investigation': 'triangle', 
                'search': 'box',
                'datapoint': 'ellipse',
                'insight': 'diamond',
                'emergent': 'hexagon'
            }
            
            vis_type = type_mapping.get(node_type, 'datapoint')
            
            # Create label based on node type
            if node_type == 'AnalyticQuestion':
                label = f"Q: {node_data.properties.get('text', '')[:40]}..."
                content = node_data.properties.get('text', '')
            elif node_type == 'InvestigationQuestion':
                label = f"Investigate: {node_data.properties.get('text', '')[:30]}..."
                content = node_data.properties.get('text', '')
            elif node_type == 'SearchQuery':
                params = node_data.properties.get('parameters', {})
                query = params.get('query', params.get('screenname', 'Search'))
                label = f"Search: {query[:30]}..."
                content = f"{node_data.properties.get('endpoint', '')} - {query}"
            elif node_type == 'DataPoint':
                content = node_data.properties.get('content', node_data.properties.get('text', 'Finding'))
                label = f"Data: {content[:30]}..."
            elif node_type == 'Insight':
                content = node_data.properties.get('content', node_data.properties.get('text', 'Pattern'))
                confidence = node_data.properties.get('confidence', 0.5)
                label = f"Insight ({confidence:.1f}): {content[:25]}..."
            elif node_type == 'EmergentQuestion':
                content = node_data.properties.get('text', node_data.properties.get('content', 'New question'))
                label = f"New Q: {content[:30]}..."
            else:
                label = f"{node_type}: {str(node_data.properties)[:30]}..."
                content = str(node_data.properties)
            
            # Add to internal structures
            from graph_visualizer import GraphNode
            graph_node = GraphNode(
                id=node_id,
                node_type=vis_type,
                label=label,
                content=content,
                timestamp=node_data.created_at.isoformat() if hasattr(node_data.created_at, 'isoformat') else str(node_data.created_at),
                metadata={
                    'original_type': node_type,
                    'properties': node_data.properties,
                    'color': colors.get(vis_type, colors['datapoint']),
                    'shape': shapes.get(vis_type, 'ellipse')
                }
            )
            
            self.nodes[node_id] = graph_node
            self.nx_graph.add_node(node_id, **graph_node.metadata)
            
            return node_id
        
        def export_enhanced_hierarchy(self):
            """Export with enhanced ontology support"""
            data = self.export_hierarchy_data()
            
            # Add ontology information
            data['ontology'] = {
                'node_types': ['AnalyticQuestion', 'InvestigationQuestion', 'SearchQuery', 'DataPoint', 'Insight', 'EmergentQuestion'],
                'edge_types': ['MOTIVATES', 'OPERATIONALIZES', 'GENERATES', 'SUPPORTS', 'ANSWERS', 'SPAWNS'],
                'description': 'TwitterExplorer Investigation Ontology'
            }
            
            return data
    
    return EnhancedVisualizer()

def create_venezuela_visualization():
    """Create the comprehensive Trump-Venezuela visualization"""
    
    print("Creating hierarchical D3.js visualization for Trump-Venezuela investigation")
    print("="*80)
    
    # Load the investigation graph
    graph_file = "twitterexplorer/current_investigation_graph.json"
    if not os.path.exists(graph_file):
        print(f"[ERROR] Graph file not found: {graph_file}")
        return False
    
    print(f"[INFO] Loading investigation graph: {graph_file}")
    nodes, edges = load_investigation_graph(graph_file)
    
    print(f"[INFO] Loaded {len(nodes)} nodes and {len(edges)} edges")
    
    # Create enhanced visualizer  
    visualizer = create_enhanced_visualizer()
    
    # Add all nodes
    node_count_by_type = {}
    for node_id, node_data in nodes.items():
        visualizer.add_ontology_node(node_data)
        node_type = node_data.node_type
        node_count_by_type[node_type] = node_count_by_type.get(node_type, 0) + 1
    
    # Add all edges
    for edge in edges:
        if edge.source_id in visualizer.nodes and edge.target_id in visualizer.nodes:
            visualizer.add_edge(edge.source_id, edge.target_id, edge.edge_type, 1.0)
    
    print(f"[INFO] Node distribution:")
    for node_type, count in node_count_by_type.items():
        print(f"   {node_type}: {count}")
    
    # Generate the visualization
    title = "Trump-Venezuela Military Deployment Investigation - Full Ontology Analysis"
    html_content = visualizer.generate_html(title, include_stats=True)
    
    # Save the visualization
    output_file = "venezuela_investigation_visualization.html"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"[SUCCESS] Visualization created: {output_file}")
    
    # Show statistics
    stats = visualizer.get_statistics()
    print(f"\n[STATISTICS]")
    print(f"   Total nodes: {stats['total_nodes']}")
    print(f"   Total edges: {stats['total_edges']}")
    print(f"   Graph density: {stats['metrics'].get('density', 0):.3f}")
    
    # Export data for inspection
    hierarchy_data = visualizer.export_enhanced_hierarchy() 
    with open("venezuela_investigation_data.json", 'w', encoding='utf-8') as f:
        json.dump(hierarchy_data, f, indent=2)
    
    print(f"[SUCCESS] Data exported: venezuela_investigation_data.json")
    
    return True

def main():
    success = create_venezuela_visualization()
    
    if success:
        print(f"\n" + "="*80)
        print("VENEZUELA INVESTIGATION VISUALIZATION COMPLETE")
        print("="*80)
        print("[OK] Hierarchical D3.js visualization generated")
        print("[OK] Full 6-node ontology represented")
        print("[OK] All insights and relationships visualized")
        print("[OK] Interactive exploration enabled")
        print("\n[FILES] Files Created:")
        print("   [HTML] venezuela_investigation_visualization.html - Main visualization")
        print("   [JSON] venezuela_investigation_data.json - Raw data export")
        print("\n[BROWSER] Open venezuela_investigation_visualization.html in your browser!")
        
        # Show file size
        try:
            html_size = os.path.getsize("venezuela_investigation_visualization.html")
            data_size = os.path.getsize("venezuela_investigation_data.json") 
            print(f"\n[SIZE] File sizes:")
            print(f"   HTML: {html_size:,} bytes")
            print(f"   JSON: {data_size:,} bytes")
        except:
            pass
    else:
        print("[ERROR] Visualization creation failed")
    
    print(f"\n[RESULT] {'SUCCESS' if success else 'FAILED'}")

if __name__ == "__main__":
    main()