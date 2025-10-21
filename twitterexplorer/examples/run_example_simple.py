"""Simplified example investigation without unicode issues"""
import io
import sys
import json
from datetime import datetime
from twitterexplorer.investigation_engine import InvestigationEngine, InvestigationConfig
from unittest.mock import patch

# Force UTF-8 encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def mock_api_responses(endpoint, params):
    """Mock realistic Twitter API responses"""
    
    if endpoint == 'search.php' and 'Trump' in params.get('query', ''):
        return {
            'results': [
                {
                    'text': 'Breaking: Court filing from July 2019 reveals Trump flew on Epstein private jet multiple times in 2002, contradicting earlier statements.',
                    'author': '@investigative_reporter',
                    'timestamp': '2024-01-15T10:30:00Z'
                },
                {
                    'text': 'New photos surface from Mar-a-Lago party in 2002 showing Trump and Epstein with several young women at calendar girl recruitment party.',
                    'author': '@miami_herald',
                    'timestamp': '2024-01-14T18:45:00Z'
                },
                {
                    'text': 'Click here for more updates on this developing story',
                    'author': '@news_bot',
                    'timestamp': '2024-01-14T12:00:00Z'
                },
                {
                    'text': 'Financial documents reveal $3.5 million property transaction between Trump Organization and Epstein associate in March 2002.',
                    'author': '@financial_times',
                    'timestamp': '2024-01-13T09:15:00Z'
                }
            ],
            'count': 4
        }
    elif endpoint == 'timeline.php':
        return {
            'results': [
                {
                    'text': 'The Fake News Media is trying to bring up old stories again. I barely knew Jeffrey Epstein!',
                    'author': '@realDonaldTrump',
                    'timestamp': '2024-01-15T08:00:00Z'
                }
            ],
            'count': 1
        }
    else:
        return {'results': [], 'count': 0}

def run_simple_example():
    """Run investigation with simplified output"""
    
    print("\n" + "="*70)
    print("INVESTIGATION EXAMPLE: Trump-Epstein 2002 Connections")
    print("="*70)
    print("\nThis demonstrates how the system:")
    print("1. Searches for information")
    print("2. Identifies significant findings (DataPoints)")
    print("3. Detects patterns (Insights)")
    print("4. Builds a knowledge graph")
    print("\n" + "-"*70)
    
    # Create engine
    engine = InvestigationEngine("test_api_key")
    
    # Simple progress capture
    progress_log = []
    
    class SimpleProgressContainer:
        def info(self, msg):
            # Remove emojis
            clean_msg = msg.encode('ascii', 'ignore').decode('ascii')
            progress_log.append(f"[SEARCH] {clean_msg}")
            
        def success(self, msg):
            clean_msg = msg.encode('ascii', 'ignore').decode('ascii')
            progress_log.append(f"[FOUND] {clean_msg}")
            
        def warning(self, msg):
            clean_msg = msg.encode('ascii', 'ignore').decode('ascii')
            progress_log.append(f"[NOTE] {clean_msg}")
            
        def markdown(self, msg):
            clean_msg = msg.encode('ascii', 'ignore').decode('ascii')
            if "satisfaction" in clean_msg.lower():
                progress_log.append(f"[PROGRESS] {clean_msg}")
    
    container = SimpleProgressContainer()
    engine.set_progress_container(container)
    
    # Mock API calls
    with patch('twitterexplorer.api_client.execute_api_step') as mock_api:
        mock_api.side_effect = lambda plan, deps, key: mock_api_responses(
            plan['endpoint'], 
            plan['params']
        )
        
        config = InvestigationConfig(
            max_searches=4,
            satisfaction_threshold=0.6
        )
        
        print("\nSTARTING INVESTIGATION...")
        print("-"*70)
        
        # Suppress most logging
        import logging
        logging.getLogger().setLevel(logging.ERROR)
        
        try:
            session = engine.conduct_investigation(
                "Find evidence of Trump-Epstein connections in 2002",
                config
            )
            print("\nINVESTIGATION COMPLETED SUCCESSFULLY")
        except Exception as e:
            print(f"\nINVESTIGATION ERROR: {e}")
            return None
    
    print("\n" + "="*70)
    print("STREAMLIT UI OUTPUT (What User Would See)")
    print("="*70)
    
    # Show progress updates
    print("\nReal-time Progress Updates:")
    for update in progress_log[-10:]:  # Show last 10 updates
        if "Found significant:" in update:
            print(f"  {update[:100]}...")
        elif "Pattern detected:" in update:
            print(f"  {update}")
        elif "SEARCH" in update:
            parts = update.split(":")
            if len(parts) > 1:
                print(f"  [SEARCHING] {parts[-1].strip()[:80]}")
    
    print("\n" + "-"*70)
    print("INVESTIGATION RESULTS")
    print("-"*70)
    
    print(f"\nTotal Searches Executed: {session.search_count}")
    print(f"Satisfaction Score: {session.satisfaction_metrics.overall_satisfaction():.0%}")
    
    # Show knowledge graph
    if engine.graph_mode and hasattr(engine.llm_coordinator, 'graph'):
        graph = engine.llm_coordinator.graph
        
        print(f"\n📊 KNOWLEDGE GRAPH CREATED:")
        print(f"  Total Nodes: {len(graph.nodes)}")
        print(f"  Total Edges: {len(graph.edges)}")
        
        # Count types
        searches = 0
        datapoints = 0
        insights = 0
        
        for node in graph.nodes.values():
            if 'SearchQuery' in node.__class__.__name__:
                searches += 1
            elif 'DataPoint' in node.__class__.__name__:
                datapoints += 1
            elif 'Insight' in node.__class__.__name__:
                insights += 1
        
        print(f"\n  Node Types:")
        print(f"    • Search Queries: {searches}")
        print(f"    • Data Points (Findings): {datapoints}")
        print(f"    • Insights (Patterns): {insights}")
        
        # Show some DataPoints
        dp_nodes = [n for n in graph.nodes.values() if 'DataPoint' in n.__class__.__name__]
        if dp_nodes:
            print(f"\n📍 KEY FINDINGS DISCOVERED:")
            for i, dp in enumerate(dp_nodes[:4], 1):
                content = dp.properties.get('content', '')
                # Clean content
                content = content.replace('\n', ' ').strip()[:100]
                print(f"  {i}. {content}...")
                
                # Show entities if found
                if dp.properties.get('entities'):
                    entities = dp.properties['entities']
                    if entities:
                        entity_types = list(entities.keys())
                        print(f"     → Entities: {', '.join(entity_types)}")
        
        # Show insights
        insight_nodes = [n for n in graph.nodes.values() if 'Insight' in n.__class__.__name__]
        if insight_nodes:
            print(f"\n💡 PATTERNS DETECTED:")
            for i, insight in enumerate(insight_nodes[:2], 1):
                content = insight.properties.get('content', 'Pattern identified')[:100]
                confidence = insight.properties.get('confidence', 0.5)
                print(f"  {i}. {content}")
                print(f"     → Confidence: {confidence:.0%}")
        
        # Generate visualization
        print("\n" + "="*70)
        print("NETWORK VISUALIZATION")
        print("="*70)
        
        print("\nGenerating interactive network graph...")
        
        # Create visualization data
        vis_data = {
            'nodes': [],
            'edges': [],
            'stats': {
                'searches': searches,
                'findings': datapoints,
                'patterns': insights
            }
        }
        
        # Add nodes
        for node_id, node in graph.nodes.items():
            node_info = {
                'id': node_id,
                'type': node.__class__.__name__
            }
            
            if 'SearchQuery' in node.__class__.__name__:
                params = node.properties.get('parameters', {})
                query = params.get('query', params.get('screenname', 'search'))
                node_info['label'] = f"Search: {query[:30]}"
                node_info['group'] = 'search'
            elif 'DataPoint' in node.__class__.__name__:
                content = node.properties.get('content', '')[:40]
                node_info['label'] = f"Finding: {content}..."
                node_info['group'] = 'datapoint'
            elif 'Insight' in node.__class__.__name__:
                node_info['label'] = "Pattern Detected"
                node_info['group'] = 'insight'
            
            vis_data['nodes'].append(node_info)
        
        # Add edges
        for edge in graph.edges:
            vis_data['edges'].append({
                'from': edge.source_id,
                'to': edge.target_id,
                'type': edge.edge_type
            })
        
        # Save JSON
        with open('investigation_graph.json', 'w') as f:
            json.dump(vis_data, f, indent=2)
        
        print("✓ Graph data saved to: investigation_graph.json")
        
        # Create HTML visualization
        html = """<!DOCTYPE html>
<html>
<head>
    <title>Investigation Knowledge Graph</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/vis/4.21.0/vis.min.js"></script>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/vis/4.21.0/vis.min.css" rel="stylesheet">
    <style>
        body { font-family: Arial; margin: 20px; }
        #network { width: 100%; height: 500px; border: 1px solid #ccc; }
        .legend { margin: 20px 0; }
        .legend span { margin: 0 15px; padding: 5px 10px; border-radius: 3px; }
        .search { background: #4CAF50; color: white; }
        .finding { background: #2196F3; color: white; }
        .pattern { background: #FF9800; color: white; }
    </style>
</head>
<body>
    <h1>Investigation Knowledge Graph</h1>
    <div class="legend">
        <span class="search">Searches</span>
        <span class="finding">Findings (DataPoints)</span>
        <span class="pattern">Patterns (Insights)</span>
    </div>
    <div id="network"></div>
    <script>
        const data = """ + json.dumps(vis_data) + """;
        
        const nodes = new vis.DataSet(data.nodes.map(n => ({
            id: n.id,
            label: n.label,
            group: n.group,
            color: n.group === 'search' ? '#4CAF50' : 
                   (n.group === 'insight' ? '#FF9800' : '#2196F3')
        })));
        
        const edges = new vis.DataSet(data.edges.map(e => ({
            from: e.from,
            to: e.to,
            arrows: 'to'
        })));
        
        const container = document.getElementById('network');
        const network = new vis.Network(container, {nodes, edges}, {
            physics: { enabled: true },
            layout: { randomSeed: 2 }
        });
    </script>
</body>
</html>"""
        
        with open('investigation_network.html', 'w', encoding='utf-8') as f:
            f.write(html)
        
        print("✓ Interactive visualization saved to: investigation_network.html")
        print("\nOpen investigation_network.html in a browser to see the interactive graph!")
    
    print("\n" + "="*70)
    print("EXAMPLE COMPLETE")
    print("="*70)
    
    return session

if __name__ == "__main__":
    result = run_simple_example()