"""Create an interactive HTML visualization of the investigation graph"""

import json
import os

# Load the exported graph
with open('investigation_graph.json', 'r') as f:
    graph_data = json.load(f)

print("=" * 60)
print("INVESTIGATION GRAPH VISUALIZATION")
print("=" * 60)
print(f"Loaded graph with {len(graph_data['nodes'])} nodes and {len(graph_data['edges'])} edges")

# Create HTML visualization with vis.js
html_content = """<!DOCTYPE html>
<html>
<head>
    <title>Twitter Investigation Knowledge Graph</title>
    <script type="text/javascript" src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
    <style type="text/css">
        body {
            margin: 0;
            padding: 0;
            font-family: Arial, sans-serif;
            background: #1a1a1a;
            color: white;
        }
        #network {
            width: 100%;
            height: 80vh;
            border: 1px solid #333;
            background: #0a0a0a;
        }
        #info {
            padding: 20px;
            background: #1a1a1a;
            color: #ccc;
        }
        h1 {
            margin: 0;
            padding: 20px;
            background: linear-gradient(90deg, #9C27B0, #2196F3);
            color: white;
        }
        .legend {
            display: flex;
            gap: 30px;
            padding: 10px 20px;
            background: #2a2a2a;
        }
        .legend-item {
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .legend-box {
            width: 20px;
            height: 20px;
            border: 2px solid;
        }
        #details {
            padding: 20px;
            background: #2a2a2a;
            margin: 10px;
            border-radius: 5px;
            min-height: 100px;
            max-height: 200px;
            overflow-y: auto;
        }
    </style>
</head>
<body>
    <h1>Twitter Investigation Knowledge Graph</h1>
    
    <div class="legend">
        <div class="legend-item">
            <div class="legend-box" style="background:#9C27B0; border-color:#7B1FA2;"></div>
            <span>Investigation Questions</span>
        </div>
        <div class="legend-item">
            <div class="legend-box" style="background:#4CAF50; border-color:#388E3C;"></div>
            <span>Search Queries</span>
        </div>
        <div class="legend-item">
            <div class="legend-box" style="background:#2196F3; border-color:#1976D2;"></div>
            <span>DataPoints (Findings)</span>
        </div>
        <div class="legend-item">
            <div class="legend-box" style="background:#FF9800; border-color:#F57C00;"></div>
            <span>Insights</span>
        </div>
    </div>
    
    <div id="details">
        <strong>Click on a node to see details</strong>
    </div>
    
    <div id="network"></div>
    
    <div id="info">
        <h2>Graph Ontology</h2>
        <p><strong>Nodes:</strong></p>
        <ul>
            <li><strong>Investigation Questions:</strong> Strategic questions driving the investigation</li>
            <li><strong>Search Queries:</strong> API calls to Twitter endpoints</li>
            <li><strong>DataPoints:</strong> Individual findings/tweets discovered</li>
            <li><strong>Insights:</strong> Synthesized patterns from multiple DataPoints</li>
        </ul>
        <p><strong>Edges (Relationships):</strong></p>
        <ul>
            <li><strong>OPERATIONALIZES:</strong> Question is operationalized into searches</li>
            <li><strong>GENERATES:</strong> Search generates results</li>
            <li><strong>DISCOVERED:</strong> Search discovered specific datapoints</li>
            <li><strong>SUPPORTS:</strong> DataPoint supports an insight</li>
        </ul>
    </div>

    <script type="text/javascript">
        // Graph data from Python
        var graphData = """ + json.dumps(graph_data) + """;
        
        // Transform nodes for vis.js
        var nodes = new vis.DataSet();
        var nodeTypeColors = {
            'InvestigationQuestion': {background: '#9C27B0', border: '#7B1FA2'},
            'SearchQuery': {background: '#4CAF50', border: '#388E3C'},
            'DataPoint': {background: '#2196F3', border: '#1976D2'},
            'Insight': {background: '#FF9800', border: '#F57C00'}
        };
        
        var nodeTypeShapes = {
            'InvestigationQuestion': 'star',
            'SearchQuery': 'box',
            'DataPoint': 'ellipse',
            'Insight': 'diamond'
        };
        
        graphData.nodes.forEach(function(node) {
            var label = '';
            if (node.type === 'InvestigationQuestion') {
                label = 'Q: ' + (node.properties.text || '').substring(0, 30) + '...';
            } else if (node.type === 'SearchQuery') {
                var params = node.properties.parameters || {};
                label = node.properties.endpoint + '\\n' + 
                    (params.query || params.screenname || params.country || 'search').substring(0, 25);
            } else if (node.type === 'DataPoint') {
                label = 'Finding: ' + (node.properties.content || '').substring(0, 40) + '...';
            } else if (node.type === 'Insight') {
                label = 'Insight: ' + (node.properties.synthesis || node.properties.content || '').substring(0, 30) + '...';
            }
            
            nodes.add({
                id: node.id,
                label: label,
                title: JSON.stringify(node.properties, null, 2).substring(0, 1000),
                color: nodeTypeColors[node.type] || nodeTypeColors['DataPoint'],
                shape: nodeTypeShapes[node.type] || 'ellipse',
                size: node.type === 'InvestigationQuestion' ? 30 : 20,
                font: {color: 'white', size: 12},
                originalNode: node
            });
        });
        
        // Transform edges for vis.js
        var edges = new vis.DataSet();
        var edgeTypeStyles = {
            'OPERATIONALIZES': {color: '#9C27B0', width: 2},
            'GENERATES': {color: '#4CAF50', width: 2},
            'DISCOVERED': {color: '#4CAF50', width: 1},
            'SUPPORTS': {color: '#FF9800', width: 1, dashes: true}
        };
        
        graphData.edges.forEach(function(edge) {
            var style = edgeTypeStyles[edge.type] || {color: '#666', width: 1};
            edges.add({
                from: edge.source,
                to: edge.target,
                label: edge.type,
                arrows: 'to',
                color: {color: style.color},
                width: style.width,
                dashes: style.dashes || false,
                font: {color: '#aaa', size: 10}
            });
        });
        
        // Create network
        var container = document.getElementById('network');
        var data = {
            nodes: nodes,
            edges: edges
        };
        
        var options = {
            nodes: {
                borderWidth: 2
            },
            edges: {
                smooth: {
                    enabled: true,
                    type: 'dynamic'
                }
            },
            physics: {
                enabled: true,
                barnesHut: {
                    gravitationalConstant: -8000,
                    centralGravity: 0.3,
                    springLength: 200,
                    springConstant: 0.04,
                    damping: 0.09
                }
            },
            interaction: {
                hover: true,
                tooltipDelay: 200
            }
        };
        
        var network = new vis.Network(container, data, options);
        
        // Handle node clicks
        network.on("click", function(params) {
            if (params.nodes.length > 0) {
                var nodeId = params.nodes[0];
                var node = nodes.get(nodeId);
                var details = document.getElementById('details');
                
                var content = '<h3>' + node.originalNode.type + '</h3>';
                content += '<p><strong>ID:</strong> ' + nodeId.substring(0, 20) + '...</p>';
                
                if (node.originalNode.properties) {
                    var props = node.originalNode.properties;
                    if (props.text) {
                        content += '<p><strong>Text:</strong> ' + props.text + '</p>';
                    }
                    if (props.content) {
                        content += '<p><strong>Content:</strong> ' + props.content.substring(0, 300) + '...</p>';
                    }
                    if (props.parameters) {
                        content += '<p><strong>Parameters:</strong> ' + JSON.stringify(props.parameters) + '</p>';
                    }
                    if (props.source_info && props.source_info.entities) {
                        content += '<p><strong>Entities:</strong> ' + JSON.stringify(props.source_info.entities) + '</p>';
                    }
                }
                
                details.innerHTML = content;
            }
        });
        
        // Display statistics
        console.log('Graph loaded with', nodes.length, 'nodes and', edges.length, 'edges');
    </script>
</body>
</html>"""

# Save HTML file
output_file = 'investigation_graph.html'
with open(output_file, 'w', encoding='utf-8') as f:
    f.write(html_content)

print(f"\nVisualization saved to: {output_file}")
print(f"Open this file in a web browser to see the interactive graph")

# Show graph statistics
print("\n" + "=" * 60)
print("GRAPH STATISTICS")
print("=" * 60)

node_types = {}
for node in graph_data['nodes']:
    node_type = node['type']
    node_types[node_type] = node_types.get(node_type, 0) + 1

print("\nNode Distribution:")
for node_type, count in node_types.items():
    print(f"  {node_type}: {count}")

edge_types = {}
for edge in graph_data['edges']:
    edge_type = edge['type']
    edge_types[edge_type] = edge_types.get(edge_type, 0) + 1

print("\nEdge Distribution:")
for edge_type, count in edge_types.items():
    print(f"  {edge_type}: {count}")

print("\n" + "=" * 60)
print("HOW TO VIEW THE GRAPH:")
print("=" * 60)
print("1. Open 'investigation_graph.html' in your web browser")
print("2. The graph will show the investigation flow:")
print("   - Purple stars: Investigation questions")
print("   - Green boxes: Search queries to Twitter API")
print("   - Blue circles: DataPoints (individual findings)")
print("   - Orange diamonds: Insights synthesized from findings")
print("3. Click and drag to move nodes around")
print("4. Click on any node to see its details")
print("5. The physics simulation will organize the graph automatically")

# Get current directory
import os
abs_path = os.path.abspath(output_file)
print(f"\nFull path: {abs_path}")