"""Extract and visualize the graph from the Trump health investigation"""

import sys
import os
import json
sys.path.insert(0, 'twitterexplorer')

from investigation_engine import InvestigationEngine, InvestigationConfig
import toml

# Load API key
secrets_path = r'twitterexplorer\.streamlit\secrets.toml'
secrets = toml.load(secrets_path)
api_key = secrets.get('RAPIDAPI_KEY')

print("=" * 60)
print("TRUMP HEALTH INVESTIGATION GRAPH")
print("=" * 60)

# Create engine
engine = InvestigationEngine(api_key)

# Run the same Trump investigation to get the graph
config = InvestigationConfig(
    max_searches=3,  # Fewer searches for focused graph
    pages_per_search=1
)

print("Running Trump health investigation to capture graph...")

result = engine.conduct_investigation(
    "Donald Trump dead sick health rumors hospital 2024",
    config
)

print(f"\nInvestigation Results:")
print(f"  - Searches: {len(result.search_history)}")
print(f"  - Findings: {len(result.accumulated_findings)}")
print(f"  - Satisfaction: {result.satisfaction_metrics.overall_satisfaction():.2f}")

# Extract the graph
if engine.graph_mode and hasattr(engine.llm_coordinator, 'graph'):
    graph = engine.llm_coordinator.graph
    
    print(f"\n" + "=" * 60)
    print("TRUMP INVESTIGATION GRAPH STRUCTURE")
    print("=" * 60)
    
    print(f"Nodes: {len(graph.nodes)}")
    print(f"Edges: {len(graph.edges)}")
    
    # Export Trump-specific graph
    trump_graph = {
        'nodes': [],
        'edges': [],
        'investigation_topic': 'Donald Trump Health Rumors',
        'timestamp': 'Trump Investigation 2025-09-03'
    }
    
    # Export nodes
    if hasattr(graph, 'nodes'):
        for node_id, node in graph.nodes.items():
            node_data = {
                'id': node_id,
                'type': node.node_type,
                'properties': node.properties if hasattr(node, 'properties') else {},
                'created_at': node.created_at.isoformat() if hasattr(node, 'created_at') else None
            }
            trump_graph['nodes'].append(node_data)
    
    # Export edges
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
            trump_graph['edges'].append(edge_data)
    
    # Save Trump-specific graph
    output_file = 'trump_investigation_graph.json'
    with open(output_file, 'w') as f:
        json.dump(trump_graph, f, indent=2)
    
    print(f"\nTrump investigation graph exported to: {output_file}")
    
    # Show sample findings from the graph
    print(f"\n" + "=" * 60)
    print("SAMPLE TRUMP FINDINGS FROM GRAPH")
    print("=" * 60)
    
    datapoint_nodes = [node for node in trump_graph['nodes'] if node['type'] == 'DataPoint']
    print(f"Found {len(datapoint_nodes)} DataPoint nodes")
    
    for i, node in enumerate(datapoint_nodes[:5], 1):
        content = node['properties'].get('content', '')[:150]
        # Clean up content for display
        content = content.encode('ascii', 'ignore').decode('ascii')
        print(f"\n  Finding {i}:")
        print(f"    {content}...")
    
    # Create Trump-specific HTML visualization
    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>Trump Health Investigation Knowledge Graph</title>
    <script type="text/javascript" src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
    <style>
        body {{ margin: 0; padding: 0; font-family: Arial, sans-serif; background: #1a1a1a; color: white; }}
        #network {{ width: 100%; height: 80vh; border: 1px solid #333; background: #0a0a0a; }}
        h1 {{ margin: 0; padding: 20px; background: linear-gradient(90deg, #dc3545, #ffc107); color: white; }}
        .legend {{ display: flex; gap: 30px; padding: 10px 20px; background: #2a2a2a; }}
        .legend-item {{ display: flex; align-items: center; gap: 10px; }}
        .legend-box {{ width: 20px; height: 20px; border: 2px solid; }}
        #details {{ padding: 20px; background: #2a2a2a; margin: 10px; border-radius: 5px; min-height: 100px; max-height: 200px; overflow-y: auto; }}
    </style>
</head>
<body>
    <h1>🔍 Trump Health Investigation Knowledge Graph</h1>
    
    <div class="legend">
        <div class="legend-item">
            <div class="legend-box" style="background:#dc3545; border-color:#c82333;"></div>
            <span>Investigation Questions</span>
        </div>
        <div class="legend-item">
            <div class="legend-box" style="background:#28a745; border-color:#1e7e34;"></div>
            <span>Search Queries</span>
        </div>
        <div class="legend-item">
            <div class="legend-box" style="background:#007bff; border-color:#0056b3;"></div>
            <span>Findings about Trump</span>
        </div>
        <div class="legend-item">
            <div class="legend-box" style="background:#ffc107; border-color:#e0a800;"></div>
            <span>Insights & Analysis</span>
        </div>
    </div>
    
    <div id="details">
        <strong>Trump Health Investigation Results</strong><br>
        Click on nodes to explore the investigation flow and findings about health rumors.
    </div>
    
    <div id="network"></div>

    <script type="text/javascript">
        var trumpGraph = {json.dumps(trump_graph)};
        
        var nodes = new vis.DataSet();
        var nodeColors = {{
            'InvestigationQuestion': {{background: '#dc3545', border: '#c82333'}},
            'SearchQuery': {{background: '#28a745', border: '#1e7e34'}},
            'DataPoint': {{background: '#007bff', border: '#0056b3'}},
            'Insight': {{background: '#ffc107', border: '#e0a800'}}
        }};
        
        trumpGraph.nodes.forEach(function(node) {{
            var label = '';
            if (node.type === 'InvestigationQuestion') {{
                label = 'Q: Trump Health Investigation';
            }} else if (node.type === 'SearchQuery') {{
                var params = node.properties.parameters || {{}};
                label = node.properties.endpoint + '\\n' + 
                    (params.query || params.screenname || 'Trump search').substring(0, 30);
            }} else if (node.type === 'DataPoint') {{
                var content = node.properties.content || '';
                label = 'Finding: ' + content.substring(0, 40) + '...';
            }} else if (node.type === 'Insight') {{
                label = 'Insight: Trump Analysis';
            }}
            
            nodes.add({{
                id: node.id,
                label: label,
                title: JSON.stringify(node.properties, null, 2).substring(0, 1000),
                color: nodeColors[node.type] || nodeColors['DataPoint'],
                shape: node.type === 'InvestigationQuestion' ? 'star' : 
                      node.type === 'SearchQuery' ? 'box' :
                      node.type === 'Insight' ? 'diamond' : 'ellipse',
                size: node.type === 'InvestigationQuestion' ? 30 : 20,
                font: {{color: 'white', size: 12}},
                originalNode: node
            }});
        }});
        
        var edges = new vis.DataSet();
        trumpGraph.edges.forEach(function(edge) {{
            edges.add({{
                from: edge.source,
                to: edge.target,
                label: edge.type,
                arrows: 'to',
                color: {{color: '#666'}},
                width: 1.5,
                font: {{color: '#aaa', size: 10}}
            }});
        }});
        
        var container = document.getElementById('network');
        var data = {{nodes: nodes, edges: edges}};
        var options = {{
            physics: {{enabled: true}},
            nodes: {{borderWidth: 2}},
            edges: {{smooth: {{enabled: true}}}}
        }};
        
        var network = new vis.Network(container, data, options);
        
        network.on("click", function(params) {{
            if (params.nodes.length > 0) {{
                var nodeId = params.nodes[0];
                var node = nodes.get(nodeId);
                var details = document.getElementById('details');
                
                var content = '<h3>' + node.originalNode.type + '</h3>';
                content += '<p><strong>ID:</strong> ' + nodeId.substring(0, 20) + '...</p>';
                
                if (node.originalNode.properties) {{
                    var props = node.originalNode.properties;
                    if (props.text) {{
                        content += '<p><strong>Text:</strong> ' + props.text + '</p>';
                    }}
                    if (props.content) {{
                        content += '<p><strong>Content:</strong> ' + props.content.substring(0, 400) + '...</p>';
                    }}
                    if (props.parameters) {{
                        content += '<p><strong>Search Parameters:</strong> ' + JSON.stringify(props.parameters) + '</p>';
                    }}
                }}
                
                details.innerHTML = content;
            }}
        }});
    </script>
</body>
</html>"""
    
    # Save Trump-specific HTML
    trump_html = 'trump_investigation_graph.html'
    with open(trump_html, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"\nTrump investigation visualization: {trump_html}")
    print(f"Open this file to see the Trump health investigation graph")
    
else:
    print("No graph available")