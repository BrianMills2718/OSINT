"""Final demonstration of DataPoint/Insight system"""
import json
from datetime import datetime
from twitterexplorer.investigation_engine import (
    InvestigationEngine, 
    InvestigationSession,
    InvestigationRound,
    InvestigationConfig,
    SearchAttempt
)

# Suppress warnings
import warnings
warnings.filterwarnings('ignore')
import logging
logging.getLogger().setLevel(logging.ERROR)

def run_demo():
    print("\n" + "="*80)
    print(" TWITTER INVESTIGATION - KNOWLEDGE GRAPH DEMONSTRATION")
    print("="*80)
    print("\nInvestigation: Trump-Epstein connections in 2002")
    print("-"*80)
    
    # Create engine
    engine = InvestigationEngine("demo_key")
    
    # Setup session
    config = InvestigationConfig(max_searches=10)
    session = InvestigationSession("Trump-Epstein 2002", config)
    round1 = InvestigationRound(1, "Initial search")
    
    # Create mock search results
    print("\n[EXECUTING SEARCHES]")
    print("-"*80)
    
    searches = []
    
    # Search 1
    print("Search 1: 'Trump Epstein 2002'")
    s1 = SearchAttempt(1, 1, "search.php", {"query": "Trump Epstein 2002"}, "General search", 4, 8.0, 1.0)
    s1._raw_results = [
        {'text': 'Court documents from March 15, 2002 reveal Trump and Epstein attended private party at Mar-a-Lago.', 'source': 'twitter', 'metadata': {}},
        {'text': 'Financial records show $3.5 million transaction between Trump Organization and Epstein associate in 2002.', 'source': 'twitter', 'metadata': {}},
        {'text': 'Click here to read more', 'source': 'twitter', 'metadata': {}},
        {'text': 'Flight logs confirm Trump flew on Epstein plane from Palm Beach to Newark on February 28, 2002.', 'source': 'twitter', 'metadata': {}}
    ]
    searches.append(s1)
    
    # Search 2
    print("Search 2: Timeline @realDonaldTrump")
    s2 = SearchAttempt(2, 1, "timeline.php", {"screenname": "realDonaldTrump"}, "Timeline", 1, 5.0, 1.0)
    s2._raw_results = [
        {'text': 'I barely knew Jeffrey Epstein! Fake news!', 'source': 'twitter', 'metadata': {}}
    ]
    searches.append(s2)
    
    # Search 3
    print("Search 3: 'Mar-a-Lago March 2002'")
    s3 = SearchAttempt(3, 1, "search.php", {"query": "Mar-a-Lago March 2002"}, "Event search", 2, 7.0, 1.0)
    s3._raw_results = [
        {'text': 'No results found', 'source': 'twitter', 'metadata': {}},
        {'text': 'Witness: March 15 party at Mar-a-Lago was calendar girl audition. Trump and Epstein recruiting.', 'source': 'twitter', 'metadata': {}}
    ]
    searches.append(s3)
    
    print("\n[ANALYZING WITH LLM]")
    print("-"*80)
    
    # Process through LLM
    engine._analyze_round_results_with_llm(session, round1, searches)
    
    # Show results
    graph = engine.llm_coordinator.graph
    
    print("\n[KNOWLEDGE GRAPH GENERATED]")
    print("-"*80)
    
    # Count nodes
    search_count = sum(1 for n in graph.nodes.values() if 'SearchQuery' in str(type(n)))
    dp_count = sum(1 for n in graph.nodes.values() if 'DataPoint' in str(type(n)))
    insight_count = sum(1 for n in graph.nodes.values() if 'Insight' in str(type(n)))
    
    print(f"\nGraph Statistics:")
    print(f"  Total Nodes: {len(graph.nodes)}")
    print(f"  - Search Queries: {search_count}")
    print(f"  - DataPoints (Findings): {dp_count}")
    print(f"  - Insights (Patterns): {insight_count}")
    print(f"  Total Edges: {len(graph.edges)}")
    
    # Show DataPoints
    datapoints = [n for n in graph.nodes.values() if 'DataPoint' in str(type(n))]
    if datapoints:
        print(f"\n[SIGNIFICANT FINDINGS]")
        print("-"*80)
        for i, dp in enumerate(datapoints[:5], 1):
            content = dp.properties.get('content', '')[:100]
            print(f"{i}. {content}...")
    
    # Show Insights
    insights = [n for n in graph.nodes.values() if 'Insight' in str(type(n))]
    if insights:
        print(f"\n[PATTERNS DETECTED]")
        print("-"*80)
        for i, ins in enumerate(insights[:3], 1):
            content = ins.properties.get('content', 'Pattern')[:100]
            conf = ins.properties.get('confidence', 0.5)
            print(f"{i}. {content}")
            print(f"   Confidence: {conf:.0%}")
    
    # What user sees
    print("\n" + "="*80)
    print(" STREAMLIT UI - WHAT USER SEES")
    print("="*80)
    
    print("\nProgress Panel:")
    print("-"*40)
    print("[START] Starting investigation...")
    print("[SEARCH] Executing: Trump Epstein 2002")
    print("[FOUND] 4 results")
    
    if dp_count > 0:
        print("\n[FINDINGS] Significant discoveries:")
        for dp in datapoints[:3]:
            c = dp.properties.get('content', '')[:60]
            print(f"  - {c}...")
    
    if insight_count > 0:
        print("\n[PATTERN] Pattern detected:")
        c = insights[0].properties.get('content', '')[:80]
        print(f"  - {c}")
    
    print(f"\n[COMPLETE] Investigation finished")
    print(f"[GRAPH] {len(graph.nodes)} nodes, {len(graph.edges)} connections")
    
    # Save visualization
    print("\n" + "="*80)
    print(" NETWORK VISUALIZATION")
    print("="*80)
    
    # Create JSON for vis.js
    nodes_data = []
    edges_data = []
    
    for nid, node in graph.nodes.items():
        n = {'id': nid[:8], 'label': '', 'group': 'other'}
        
        if 'SearchQuery' in str(type(node)):
            p = node.properties.get('parameters', {})
            n['label'] = f"Search: {p.get('query', p.get('screenname', ''))[:20]}"
            n['group'] = 'search'
        elif 'DataPoint' in str(type(node)):
            n['label'] = f"Finding: {node.properties.get('content', '')[:25]}..."
            n['group'] = 'datapoint'
        elif 'Insight' in str(type(node)):
            n['label'] = "Pattern"
            n['group'] = 'insight'
        
        nodes_data.append(n)
    
    for e in graph.edges:
        edges_data.append({
            'from': e.source_id[:8],
            'to': e.target_id[:8],
            'label': e.edge_type if e.edge_type != 'GENERATES' else ''
        })
    
    # Save data
    with open('graph_data.json', 'w') as f:
        json.dump({'nodes': nodes_data, 'edges': edges_data}, f, indent=2)
    
    print("\nGraph data saved to: graph_data.json")
    
    # Create HTML
    html = """<!DOCTYPE html>
<html>
<head>
    <title>Investigation Graph</title>
    <script src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
    <style>
        body { font-family: Arial; margin: 20px; }
        #network { width: 100%; height: 500px; border: 1px solid #ccc; }
        .legend { margin: 20px 0; }
        .legend span { margin: 0 15px; padding: 5px 10px; }
        .search { background: #4CAF50; color: white; }
        .finding { background: #2196F3; color: white; }
        .pattern { background: #FF9800; color: white; }
    </style>
</head>
<body>
    <h1>Investigation Knowledge Graph</h1>
    <div class="legend">
        <span class="search">Searches</span>
        <span class="finding">Findings</span>
        <span class="pattern">Patterns</span>
    </div>
    <div id="network"></div>
    <script>
        fetch('graph_data.json')
            .then(r => r.json())
            .then(data => {
                const nodes = new vis.DataSet(data.nodes.map(n => ({
                    ...n,
                    color: n.group === 'search' ? '#4CAF50' : 
                           n.group === 'insight' ? '#FF9800' : '#2196F3'
                })));
                const edges = new vis.DataSet(data.edges.map(e => ({
                    ...e, arrows: 'to'
                })));
                new vis.Network(
                    document.getElementById('network'),
                    {nodes, edges},
                    {physics: {enabled: true}}
                );
            });
    </script>
</body>
</html>"""
    
    with open('graph.html', 'w') as f:
        f.write(html)
    
    print("Interactive visualization saved to: graph.html")
    print("\nOpen graph.html in a browser to see the network!")
    
    print("\n" + "="*80)
    print(" DEMO COMPLETE")
    print("="*80)

if __name__ == "__main__":
    run_demo()