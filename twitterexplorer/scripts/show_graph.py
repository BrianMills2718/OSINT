"""Script to extract and visualize the investigation graph"""

import sys
import os
import json
sys.path.insert(0, 'twitterexplorer')

from investigation_engine import InvestigationEngine, InvestigationConfig
from investigation_graph import InvestigationGraph
from graph_visualizer import InvestigationGraphVisualizer
import toml

# Load API key
secrets_path = r'twitterexplorer\.streamlit\secrets.toml'
secrets = toml.load(secrets_path)
api_key = secrets.get('RAPIDAPI_KEY')

print("=" * 60)
print("INVESTIGATION GRAPH STRUCTURE & VISUALIZATION")
print("=" * 60)

# Create engine
engine = InvestigationEngine(api_key)

print(f"\n1. Graph Mode Active: {engine.graph_mode}")

if engine.graph_mode and hasattr(engine.llm_coordinator, 'graph'):
    graph = engine.llm_coordinator.graph
    print(f"2. Graph Object Found: {type(graph)}")
    
    # Check graph structure
    if hasattr(graph, 'nodes'):
        print(f"3. Nodes in graph: {len(graph.nodes)}")
    if hasattr(graph, 'edges'):
        print(f"4. Edges in graph: {len(graph.edges)}")
    
    # Run a quick investigation to populate the graph
    print("\n" + "=" * 60)
    print("RUNNING TEST INVESTIGATION TO POPULATE GRAPH")
    print("=" * 60)
    
    config = InvestigationConfig(
        max_searches=2,
        pages_per_search=1
    )
    
    result = engine.conduct_investigation("AI technology trends", config)
    
    print(f"\nInvestigation complete:")
    print(f"  - Searches: {len(result.search_history)}")
    print(f"  - Findings: {len(result.accumulated_findings)}")
    
    # Now check the graph again
    print("\n" + "=" * 60)
    print("GRAPH ONTOLOGY & STRUCTURE")
    print("=" * 60)
    
    if hasattr(graph, 'nodes'):
        print(f"\nTotal nodes: {len(graph.nodes)}")
        
        # Count node types
        node_types = {}
        for node_id, node in graph.nodes.items():
            node_type = node.node_type
            node_types[node_type] = node_types.get(node_type, 0) + 1
        
        print("\nNode Types (Ontology):")
        for node_type, count in node_types.items():
            print(f"  - {node_type}: {count}")
        
        # Show sample nodes
        print("\nSample Nodes:")
        for i, (node_id, node) in enumerate(list(graph.nodes.items())[:5]):
            print(f"\n  Node {i+1}:")
            print(f"    ID: {node_id[:20]}...")
            print(f"    Type: {node.node_type}")
            if hasattr(node, 'properties'):
                props = node.properties
                if 'text' in props:
                    text = props['text'][:100] if len(props['text']) > 100 else props['text']
                    print(f"    Text: {text}")
                elif 'content' in props:
                    content = props['content'][:100] if len(props['content']) > 100 else props['content']
                    print(f"    Content: {content}")
    
    if hasattr(graph, 'edges'):
        print(f"\n\nTotal edges: {len(graph.edges)}")
        
        # Count edge types
        edge_types = {}
        # Handle both list and dict formats
        if isinstance(graph.edges, dict):
            edges_iter = graph.edges.items()
        else:  # It's a list
            edges_iter = enumerate(graph.edges)
        
        for edge_id, edge in edges_iter:
            edge_type = edge.edge_type
            edge_types[edge_type] = edge_types.get(edge_type, 0) + 1
        
        print("\nEdge Types (Relationships):")
        for edge_type, count in edge_types.items():
            print(f"  - {edge_type}: {count}")
    
    # Export graph to JSON
    print("\n" + "=" * 60)
    print("EXPORTING GRAPH DATA")
    print("=" * 60)
    
    # Create export
    graph_export = {
        'nodes': [],
        'edges': []
    }
    
    if hasattr(graph, 'nodes'):
        for node_id, node in graph.nodes.items():
            node_data = {
                'id': node_id,
                'type': node.node_type,
                'properties': node.properties if hasattr(node, 'properties') else {},
                'created_at': node.created_at.isoformat() if hasattr(node, 'created_at') else None
            }
            graph_export['nodes'].append(node_data)
    
    if hasattr(graph, 'edges'):
        # Handle both list and dict formats
        if isinstance(graph.edges, dict):
            edges_iter = graph.edges.items()
        else:
            edges_iter = enumerate(graph.edges)
            
        for edge_id, edge in edges_iter:
            edge_data = {
                'id': str(edge_id),
                'source': edge.source_id,
                'target': edge.target_id,
                'type': edge.edge_type,
                'properties': edge.properties if hasattr(edge, 'properties') else {}
            }
            graph_export['edges'].append(edge_data)
    
    # Save to file
    output_file = 'investigation_graph.json'
    with open(output_file, 'w') as f:
        json.dump(graph_export, f, indent=2)
    
    print(f"Graph exported to: {output_file}")
    print(f"  - Nodes: {len(graph_export['nodes'])}")
    print(f"  - Edges: {len(graph_export['edges'])}")
    
    # Create HTML visualization
    print("\n" + "=" * 60)
    print("CREATING VISUALIZATION")
    print("=" * 60)
    
    # Use the graph visualizer
    visualizer = InvestigationGraphVisualizer()
    
    # Add nodes to visualizer
    if graph_export['nodes']:
        # Add query node
        query_node = graph_export['nodes'][0]  # Assuming first is query
        if query_node['type'] == 'AnalyticQuestion':
            visualizer.add_query_node(
                query_node['properties'].get('text', 'Investigation')
            )
        
        # Add other nodes
        for node in graph_export['nodes'][1:10]:  # Limit to first 10 for clarity
            node_type = node['type']
            if node_type == 'SearchQuery':
                # Add search nodes
                endpoint = node['properties'].get('endpoint', 'search')
                params = node['properties'].get('parameters', {})
                query_text = params.get('query', params.get('screenname', 'search'))
                visualizer.add_search_node(
                    search_id=node['id'][:8],
                    endpoint=endpoint,
                    query=query_text,
                    results_count=node['properties'].get('results_count', 0)
                )
            elif node_type == 'DataPoint':
                # Add datapoint nodes
                content = node['properties'].get('content', '')[:100]
                visualizer.add_datapoint_node(
                    datapoint_id=node['id'][:8],
                    content=content,
                    source=node['properties'].get('source', 'unknown'),
                    credibility=0.5
                )
    
    # Generate HTML
    html_file = visualizer.generate_html('investigation_graph.html')
    print(f"Visualization created: {html_file}")
    
    print("\n" + "=" * 60)
    print("GRAPH ONTOLOGY SUMMARY")
    print("=" * 60)
    print("""
Node Types:
1. AnalyticQuestion - Root investigation question
2. InvestigationQuestion - Specific operational questions
3. SearchQuery - API search nodes with parameters
4. DataPoint - Individual findings/tweets
5. Insight - Synthesized patterns from DataPoints
6. EmergentQuestion - New questions that arise

Edge Types (Relationships):
- MOTIVATES: Question motivates searches
- OPERATIONALIZES: Breaks down into specific queries
- GENERATES: Search generates results
- SUPPORTS: DataPoint supports insights
- ANSWERS: Results answer questions
- SPAWNS: Insights spawn new questions
- DISCOVERED: Search discovered datapoints
    """)
    
else:
    print("Graph mode not active or graph not found")