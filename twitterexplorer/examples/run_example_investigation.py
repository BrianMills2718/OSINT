"""Run an example investigation to demonstrate the DataPoint/Insight system"""
import json
import sys
from datetime import datetime
from twitterexplorer.investigation_engine import InvestigationEngine, InvestigationConfig
from unittest.mock import patch

def mock_api_responses(endpoint, params):
    """Mock realistic Twitter API responses for demonstration"""
    
    if endpoint == 'search.php' and 'Trump' in params.get('query', ''):
        return {
            'results': [
                {
                    'text': 'Breaking: Court filing from July 2019 reveals Trump flew on Epstein\'s private jet multiple times in 2002, contradicting earlier statements.',
                    'author': '@investigative_reporter',
                    'timestamp': '2024-01-15T10:30:00Z',
                    'retweets': 5432,
                    'likes': 12453
                },
                {
                    'text': 'New photos surface from Mar-a-Lago party in 2002 showing Trump and Epstein with several young women. Event was allegedly a "calendar girl" recruitment party.',
                    'author': '@miami_herald',
                    'timestamp': '2024-01-14T18:45:00Z',
                    'retweets': 3211,
                    'likes': 8976
                },
                {
                    'text': 'Click here for more updates on this developing story',
                    'author': '@news_bot',
                    'timestamp': '2024-01-14T12:00:00Z',
                    'retweets': 12,
                    'likes': 45
                },
                {
                    'text': 'Financial documents reveal $3.5 million property transaction between Trump Organization and Epstein associate in March 2002. Details of the deal remain sealed.',
                    'author': '@financial_times',
                    'timestamp': '2024-01-13T09:15:00Z',
                    'retweets': 2145,
                    'likes': 6789
                }
            ],
            'count': 4
        }
    elif endpoint == 'timeline.php' and params.get('screenname') == 'realDonaldTrump':
        return {
            'results': [
                {
                    'text': 'The Fake News Media is trying to bring up old stories again. I barely knew Jeffrey Epstein!',
                    'author': '@realDonaldTrump',
                    'timestamp': '2024-01-15T08:00:00Z',
                    'retweets': 45632,
                    'likes': 123456
                }
            ],
            'count': 1
        }
    elif endpoint == 'screenname.php':
        return {
            'results': [
                {
                    'profile': {
                        'name': 'Donald J. Trump',
                        'screenname': 'realDonaldTrump',
                        'followers': 87654321,
                        'description': '45th President of the United States',
                        'verified': True
                    }
                }
            ],
            'count': 1
        }
    else:
        return {'results': [], 'count': 0}

def run_example_investigation():
    """Run a complete investigation with mocked data"""
    
    print("="*70)
    print("EXAMPLE INVESTIGATION: Trump-Epstein Connections in 2002")
    print("="*70)
    print()
    
    # Create engine
    engine = InvestigationEngine("test_api_key")
    
    # Create a mock progress container to capture updates
    progress_messages = []
    
    class MockProgressContainer:
        def info(self, msg):
            progress_messages.append(("INFO", msg))
            print(f"[INFO] {msg}")
        
        def success(self, msg):
            progress_messages.append(("SUCCESS", msg))
            print(f"[SUCCESS] {msg}")
        
        def warning(self, msg):
            progress_messages.append(("WARNING", msg))
            print(f"[WARNING] {msg}")
        
        def markdown(self, msg):
            progress_messages.append(("MARKDOWN", msg))
            print(f"[UPDATE] {msg}")
    
    mock_container = MockProgressContainer()
    engine.set_progress_container(mock_container)
    
    # Mock the API calls
    with patch('twitterexplorer.api_client.execute_api_step') as mock_api:
        mock_api.side_effect = lambda plan, deps, key: mock_api_responses(
            plan['endpoint'], 
            plan['params']
        )
        
        # Configure investigation
        config = InvestigationConfig(
            max_searches=6,  # Small number for demo
            satisfaction_threshold=0.7
        )
        
        print("STARTING INVESTIGATION...")
        print("-"*70)
        
        # Run investigation
        session = engine.conduct_investigation(
            "Find evidence of Trump-Epstein connections and meetings in 2002",
            config
        )
        
    print("\n" + "="*70)
    print("INVESTIGATION COMPLETE - SUMMARY")
    print("="*70)
    
    # Show results
    print(f"\nSession ID: {session.session_id}")
    print(f"Total Searches: {session.search_count}")
    print(f"Total Results Found: {sum(s.results_count for r in session.rounds for s in r.searches)}")
    print(f"Satisfaction Score: {session.satisfaction_metrics.overall_satisfaction():.1%}")
    
    # Show graph statistics if available
    if engine.graph_mode and hasattr(engine.llm_coordinator, 'graph'):
        graph = engine.llm_coordinator.graph
        
        print(f"\n📊 KNOWLEDGE GRAPH STATISTICS:")
        print(f"  Total Nodes: {len(graph.nodes)}")
        print(f"  Total Edges: {len(graph.edges)}")
        
        # Count node types
        node_types = {}
        for node in graph.nodes.values():
            node_type = node.__class__.__name__
            node_types[node_type] = node_types.get(node_type, 0) + 1
        
        print(f"\n  Node Breakdown:")
        for node_type, count in node_types.items():
            print(f"    - {node_type}: {count}")
        
        # Show DataPoints
        datapoints = [n for n in graph.nodes.values() if 'DataPoint' in n.__class__.__name__]
        if datapoints:
            print(f"\n📍 KEY FINDINGS (DataPoints):")
            for i, dp in enumerate(datapoints[:5], 1):  # Show first 5
                content = dp.properties.get('content', '')[:120]
                print(f"  {i}. {content}...")
                if dp.properties.get('entities'):
                    print(f"     Entities: {list(dp.properties['entities'].keys())}")
        
        # Show Insights
        insights = [n for n in graph.nodes.values() if 'Insight' in n.__class__.__name__]
        if insights:
            print(f"\n💡 PATTERNS DETECTED (Insights):")
            for i, insight in enumerate(insights[:3], 1):  # Show first 3
                content = insight.properties.get('content', '')[:150]
                confidence = insight.properties.get('confidence', 0)
                print(f"  {i}. {content}...")
                print(f"     Confidence: {confidence:.1%}")
        
        # Export graph for visualization
        print(f"\n🌐 GENERATING NETWORK VISUALIZATION...")
        try:
            # Export to JSON for visualization
            graph_data = {
                'nodes': [],
                'edges': []
            }
            
            for node_id, node in graph.nodes.items():
                node_data = {
                    'id': node_id,
                    'type': node.__class__.__name__,
                    'label': '',
                    'properties': {}
                }
                
                if 'SearchQuery' in node.__class__.__name__:
                    params = node.properties.get('parameters', {})
                    node_data['label'] = f"Search: {params.get('query', params.get('screenname', 'unknown'))}"
                    node_data['color'] = '#4CAF50'  # Green for searches
                elif 'DataPoint' in node.__class__.__name__:
                    content = node.properties.get('content', '')[:50]
                    node_data['label'] = f"Finding: {content}..."
                    node_data['color'] = '#2196F3'  # Blue for DataPoints
                elif 'Insight' in node.__class__.__name__:
                    content = node.properties.get('content', '')[:50]
                    node_data['label'] = f"Pattern: {content}..."
                    node_data['color'] = '#FF9800'  # Orange for Insights
                else:
                    node_data['label'] = node_id[:20]
                    node_data['color'] = '#9E9E9E'  # Gray for others
                
                graph_data['nodes'].append(node_data)
            
            for edge in graph.edges:
                edge_data = {
                    'source': edge.source_id,
                    'target': edge.target_id,
                    'type': edge.edge_type,
                    'label': edge.edge_type
                }
                graph_data['edges'].append(edge_data)
            
            # Save graph data
            with open('example_investigation_graph.json', 'w') as f:
                json.dump(graph_data, f, indent=2)
            print(f"  Graph data saved to: example_investigation_graph.json")
            
            # Generate HTML visualization
            html_content = """<!DOCTYPE html>
<html>
<head>
    <title>Investigation Knowledge Graph</title>
    <script src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 20px; }
        h1 { color: #333; }
        #network { width: 100%; height: 600px; border: 1px solid #ddd; }
        .legend { margin-top: 20px; }
        .legend-item { display: inline-block; margin-right: 20px; }
        .legend-color { width: 20px; height: 20px; display: inline-block; margin-right: 5px; vertical-align: middle; }
    </style>
</head>
<body>
    <h1>Investigation Knowledge Graph: Trump-Epstein 2002</h1>
    <div id="network"></div>
    <div class="legend">
        <div class="legend-item"><span class="legend-color" style="background: #4CAF50;"></span>Search Queries</div>
        <div class="legend-item"><span class="legend-color" style="background: #2196F3;"></span>Data Points (Findings)</div>
        <div class="legend-item"><span class="legend-color" style="background: #FF9800;"></span>Insights (Patterns)</div>
    </div>
    <script>
        // Load graph data
        const graphData = """ + json.dumps(graph_data) + """;
        
        // Create nodes and edges
        const nodes = new vis.DataSet(graphData.nodes.map(n => ({
            id: n.id,
            label: n.label,
            color: n.color,
            shape: n.type.includes('Insight') ? 'diamond' : (n.type.includes('Search') ? 'box' : 'dot'),
            size: n.type.includes('Insight') ? 30 : 20
        })));
        
        const edges = new vis.DataSet(graphData.edges.map(e => ({
            from: e.source,
            to: e.target,
            label: e.type,
            arrows: 'to',
            color: e.type === 'DISCOVERED' ? '#4CAF50' : (e.type === 'SUPPORTS' ? '#FF9800' : '#999')
        })));
        
        // Create network
        const container = document.getElementById('network');
        const data = { nodes: nodes, edges: edges };
        const options = {
            physics: {
                enabled: true,
                barnesHut: {
                    springLength: 150,
                    springConstant: 0.04
                }
            },
            interaction: { hover: true },
            layout: { randomSeed: 42 }
        };
        
        const network = new vis.Network(container, data, options);
    </script>
</body>
</html>"""
            
            with open('example_investigation_network.html', 'w') as f:
                f.write(html_content)
            print(f"  Interactive visualization saved to: example_investigation_network.html")
            
        except Exception as e:
            print(f"  Error generating visualization: {e}")
    
    print("\n" + "="*70)
    print("EXAMPLE COMPLETE")
    print("="*70)
    
    return session

if __name__ == "__main__":
    session = run_example_investigation()