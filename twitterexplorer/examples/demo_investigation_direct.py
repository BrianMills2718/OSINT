"""Direct demonstration of DataPoint/Insight creation with mock data"""
import json
from datetime import datetime
from twitterexplorer.investigation_engine import (
    InvestigationEngine, 
    InvestigationSession,
    InvestigationRound,
    InvestigationConfig,
    SearchAttempt
)

def create_demo_investigation():
    """Create a demonstration with mock search results"""
    
    print("\n" + "="*80)
    print(" TWITTER INVESTIGATION SYSTEM - KNOWLEDGE GRAPH DEMONSTRATION")
    print("="*80)
    print("\nQuery: 'Find evidence of Trump-Epstein connections in 2002'")
    print("-"*80)
    
    # Create engine
    engine = InvestigationEngine("demo_key")
    
    if not engine.graph_mode:
        print("ERROR: Graph mode not enabled")
        return
    
    # Create session
    config = InvestigationConfig(max_searches=10)
    session = InvestigationSession("Trump-Epstein connections in 2002", config)
    
    # Create a round
    round1 = InvestigationRound(
        round_number=1,
        strategy_description="Initial broad search for connections"
    )
    
    print("\n[ROUND 1] Executing searches...")
    print("-"*80)
    
    # Mock search results
    search_attempts = []
    
    # Search 1: General search
    print("\n[1] Searching: 'Trump Epstein 2002'")
    attempt1 = SearchAttempt(
        search_id=1,
        round_number=1,
        endpoint="search.php",
        params={"query": "Trump Epstein 2002"},
        query_description="General search for connections",
        results_count=4,
        effectiveness_score=8.0,
        execution_time=1.5
    )
    attempt1._raw_results = [
        {
            'text': 'BREAKING: Court documents from March 15, 2002 reveal Trump and Epstein attended private party at Mar-a-Lago with 28 young women present.',
            'source': 'twitter',
            'metadata': {'author': '@investigative_journal', 'likes': 15234}
        },
        {
            'text': 'Financial records show $3.5 million property transaction between Trump Organization subsidiary and Epstein associate in July 2002. Details remain sealed by court order.',
            'source': 'twitter',
            'metadata': {'author': '@financial_reporter', 'likes': 8976}
        },
        {
            'text': 'Click here to read more about this story',
            'source': 'twitter',
            'metadata': {'author': '@clickbait_news', 'likes': 12}
        },
        {
            'text': 'Flight logs confirm Trump flew on Epstein plane from Palm Beach to Newark on February 28, 2002. This contradicts his 2019 statement that he never flew on the plane.',
            'source': 'twitter',
            'metadata': {'author': '@fact_checker', 'likes': 22456}
        }
    ]
    search_attempts.append(attempt1)
    
    # Search 2: Timeline search
    print("[2] Searching: Timeline of @realDonaldTrump")
    attempt2 = SearchAttempt(
        search_id=2,
        round_number=1,
        endpoint="timeline.php",
        params={"screenname": "realDonaldTrump"},
        query_description="Trump timeline search",
        results_count=1,
        effectiveness_score=5.0,
        execution_time=1.0
    )
    attempt2._raw_results = [
        {
            'text': 'The Fake News Media keeps bringing up old stories. I barely knew Jeffrey Epstein!',
            'source': 'twitter',
            'metadata': {'author': '@realDonaldTrump', 'likes': 145632}
        }
    ]
    search_attempts.append(attempt2)
    
    # Search 3: Specific date search
    print("[3] Searching: 'Mar-a-Lago party March 2002'")
    attempt3 = SearchAttempt(
        search_id=3,
        round_number=1,
        endpoint="search.php",
        params={"query": "Mar-a-Lago party March 2002"},
        query_description="Specific event search",
        results_count=2,
        effectiveness_score=7.0,
        execution_time=1.2
    )
    attempt3._raw_results = [
        {
            'text': 'No results found for your search',
            'source': 'twitter',
            'metadata': {}
        },
        {
            'text': 'Witness testimony: "I worked at Mar-a-Lago in 2002. The March 15 party was a calendar girl audition. Both Trump and Epstein were recruiting models."',
            'source': 'twitter',
            'metadata': {'author': '@anonymous_witness', 'likes': 5432}
        }
    ]
    search_attempts.append(attempt3)
    
    print("\n[ANALYZING] Analyzing results with LLM...")
    print("-"*80)
    
    # Process results through the analysis pipeline
    engine._analyze_round_results_with_llm(session, round1, search_attempts)
    
    # Display what happened
    print("\n[GRAPH] KNOWLEDGE GRAPH GENERATED")
    print("-"*80)
    
    graph = engine.llm_coordinator.graph
    
    # Count nodes
    search_nodes = []
    datapoint_nodes = []
    insight_nodes = []
    
    for node in graph.nodes.values():
        if 'SearchQuery' in node.__class__.__name__:
            search_nodes.append(node)
        elif 'DataPoint' in node.__class__.__name__:
            datapoint_nodes.append(node)
        elif 'Insight' in node.__class__.__name__:
            insight_nodes.append(node)
    
    print(f"\nGraph Statistics:")
    print(f"  • Total Nodes: {len(graph.nodes)}")
    print(f"  • Search Queries: {len(search_nodes)}")
    print(f"  • DataPoints (Significant Findings): {len(datapoint_nodes)}")
    print(f"  • Insights (Patterns): {len(insight_nodes)}")
    print(f"  • Edges (Connections): {len(graph.edges)}")
    
    # Show DataPoints
    if datapoint_nodes:
        print(f"\n📍 SIGNIFICANT FINDINGS (DataPoints):")
        print("-"*80)
        for i, dp in enumerate(datapoint_nodes[:6], 1):
            content = dp.properties.get('content', '')
            # Clean and truncate
            content = content.replace('\n', ' ').strip()
            if len(content) > 120:
                content = content[:117] + "..."
            
            print(f"\n[DataPoint {i}]")
            print(f"  Content: {content}")
            
            # Show entities if available
            if dp.properties.get('entities'):
                entities = dp.properties['entities']
                if entities:
                    print(f"  Entities: {', '.join(f'{k}: {len(v)} found' for k, v in entities.items())}")
            
            # Show follow-up if suggested
            if dp.properties.get('follow_up_needed'):
                print(f"  Suggested Follow-up: {dp.properties['follow_up_needed']}")
    
    # Show Insights
    if insight_nodes:
        print(f"\n💡 PATTERNS DETECTED (Insights):")
        print("-"*80)
        for i, insight in enumerate(insight_nodes[:3], 1):
            content = insight.properties.get('content', 'Pattern detected')
            confidence = insight.properties.get('confidence', 0.5)
            
            print(f"\n[Insight {i}]")
            print(f"  Pattern: {content[:150]}")
            print(f"  Confidence: {confidence:.0%}")
            
            # Show supporting DataPoints
            if insight.properties.get('supporting_datapoints'):
                support_count = len(insight.properties['supporting_datapoints'])
                print(f"  Based on: {support_count} related findings")
    
    # Show edges
    edge_types = {}
    for edge in graph.edges:
        edge_types[edge.edge_type] = edge_types.get(edge.edge_type, 0) + 1
    
    if edge_types:
        print(f"\n🔗 CONNECTIONS IN GRAPH:")
        print("-"*80)
        for edge_type, count in edge_types.items():
            if edge_type == "DISCOVERED":
                print(f"  • {count} findings discovered from searches")
            elif edge_type == "SUPPORTS":
                print(f"  • {count} findings support insights")
            elif edge_type == "GENERATES":
                print(f"  • {count} other connections")
    
    # What the user would see in Streamlit
    print("\n" + "="*80)
    print(" STREAMLIT UI - REAL-TIME UPDATES (What User Sees)")
    print("="*80)
    
    print("\n📱 Progress Panel:")
    print("-"*40)
    print("🚀 Starting investigation...")
    print("🔍 Round 1: Initial broad search")
    print("  ↳ Searching: Trump Epstein 2002")
    print("  ↳ Found 4 results")
    
    if len(datapoint_nodes) > 0:
        print("\n📍 Significant findings discovered:")
        for dp in datapoint_nodes[:3]:
            content = dp.properties.get('content', '')[:60]
            print(f"  • {content}...")
    
    if len(insight_nodes) > 0:
        print("\n[PATTERN] Pattern detected:")
        content = insight_nodes[0].properties.get('content', 'Multiple connections found')[:80]
        print(f"  • {content}")
    
    print("\n[DONE] Investigation round complete")
    print(f"[GRAPH] Knowledge graph: {len(graph.nodes)} nodes, {len(graph.edges)} connections")
    
    # Generate HTML visualization
    print("\n" + "="*80)
    print(" GENERATING INTERACTIVE VISUALIZATION")
    print("="*80)
    
    # Create data for visualization
    vis_nodes = []
    vis_edges = []
    
    for node_id, node in graph.nodes.items():
        node_data = {'id': node_id[:8]}  # Shorten IDs for display
        
        if 'SearchQuery' in node.__class__.__name__:
            params = node.properties.get('parameters', {})
            query = params.get('query', params.get('screenname', ''))
            node_data['label'] = f"Search:\\n{query[:25]}"
            node_data['color'] = '#4CAF50'
            node_data['shape'] = 'box'
        elif 'DataPoint' in node.__class__.__name__:
            content = node.properties.get('content', '')[:30]
            node_data['label'] = f"Finding:\\n{content}..."
            node_data['color'] = '#2196F3'
            node_data['shape'] = 'ellipse'
        elif 'Insight' in node.__class__.__name__:
            node_data['label'] = "Pattern\\nDetected"
            node_data['color'] = '#FF9800'
            node_data['shape'] = 'star'
        else:
            node_data['label'] = "Node"
            node_data['color'] = '#999'
            node_data['shape'] = 'dot'
        
        vis_nodes.append(node_data)
    
    for edge in graph.edges:
        vis_edges.append({
            'from': edge.source_id[:8],
            'to': edge.target_id[:8],
            'arrows': 'to',
            'label': edge.edge_type if edge.edge_type != 'GENERATES' else '',
            'color': {'color': '#4CAF50' if edge.edge_type == 'DISCOVERED' else '#FF9800' if edge.edge_type == 'SUPPORTS' else '#999'}
        })
    
    # Save visualization
    html_template = """<!DOCTYPE html>
<html>
<head>
    <title>Investigation Knowledge Graph</title>
    <script src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
        h1 { color: #333; margin-bottom: 10px; }
        .subtitle { color: #666; margin-bottom: 20px; }
        #network { width: 100%; height: 600px; border: 2px solid #ddd; background: white; border-radius: 8px; }
        .legend { margin-top: 20px; padding: 15px; background: white; border-radius: 8px; border: 1px solid #ddd; }
        .legend-item { display: inline-block; margin-right: 30px; }
        .color-box { width: 20px; height: 20px; display: inline-block; margin-right: 8px; vertical-align: middle; border-radius: 3px; }
    </style>
</head>
<body>
    <h1>Investigation Knowledge Graph</h1>
    <div class="subtitle">Trump-Epstein Connections in 2002</div>
    <div id="network"></div>
    <div class="legend">
        <div class="legend-item"><span class="color-box" style="background:#4CAF50;"></span>Search Queries</div>
        <div class="legend-item"><span class="color-box" style="background:#2196F3;"></span>Significant Findings</div>
        <div class="legend-item"><span class="color-box" style="background:#FF9800;"></span>Patterns Detected</div>
    </div>
    <script>
        const nodes = new vis.DataSet(""" + json.dumps(vis_nodes) + """);
        const edges = new vis.DataSet(""" + json.dumps(vis_edges) + """);
        
        const container = document.getElementById('network');
        const data = { nodes: nodes, edges: edges };
        const options = {
            nodes: {
                font: { size: 12, face: 'Arial' },
                borderWidth: 2,
                shadow: true
            },
            edges: {
                font: { size: 10, align: 'middle' },
                shadow: true
            },
            physics: {
                barnesHut: {
                    springLength: 150,
                    springConstant: 0.04,
                    damping: 0.09
                }
            },
            interaction: {
                hover: true,
                tooltipDelay: 200
            }
        };
        
        const network = new vis.Network(container, data, options);
    </script>
</body>
</html>"""
    
    with open('demo_investigation_graph.html', 'w', encoding='utf-8') as f:
        f.write(html_template)
    
    print("\n[DONE] Visualization saved to: demo_investigation_graph.html")
    print("[NOTE] Open this file in a web browser to see the interactive knowledge graph!")
    
    print("\n" + "="*80)
    print(" DEMONSTRATION COMPLETE")
    print("="*80)
    
    return graph

if __name__ == "__main__":
    graph = create_demo_investigation()