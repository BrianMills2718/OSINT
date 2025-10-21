"""Create an investigation graph from mock data representing a real investigation"""
from twitterexplorer.graph_visualizer import InvestigationGraphVisualizer
from datetime import datetime
import json
import random

def create_realistic_investigation_graph():
    """Create a graph from a realistic investigation scenario"""
    
    print("\n" + "="*80)
    print(" CREATING INVESTIGATION GRAPH FROM MOCK REALISTIC DATA")
    print("="*80)
    
    viz = InvestigationGraphVisualizer()
    
    # Original investigation query
    query = "What are people saying about Trump and Epstein connections in 2002"
    print(f"\nInvestigation: {query}")
    print("-"*80)
    
    # Add query node (ROOT)
    query_id = viz.add_query_node(query, datetime.now().isoformat())
    
    # Simulated investigation rounds based on actual patterns from logs
    investigation_data = [
        # Round 1: Broad searches
        {
            "search_num": 1,
            "endpoint": "search.php",
            "params": {"query": "Trump Epstein 2002"},
            "results": [
                "Breaking: Court documents from 2002 reveal Trump and Epstein attended multiple private parties together at Mar-a-Lago",
                "Photos emerge showing Trump and Epstein at 2002 calendar girl recruitment event",
                "Witness testimony: 'Trump and Epstein were inseparable at Mar-a-Lago parties in early 2002'"
            ]
        },
        {
            "search_num": 2,
            "endpoint": "search.php",
            "params": {"query": "Epstein flight logs Trump 2002"},
            "results": [
                "FAA records confirm Trump flew on Epstein's plane from Palm Beach to Newark on February 28, 2002",
                "Flight manifest shows Trump, Epstein, and unnamed young women on private jet March 2002"
            ]
        },
        
        # Round 2: Timeline searches
        {
            "search_num": 3,
            "endpoint": "timeline.php",
            "params": {"screenname": "realDonaldTrump"},
            "results": [
                "Trump tweet (2019): 'I barely knew Jeffrey Epstein. Another fake news story!'",
                "Trump tweet (2020): 'Never went to his island, never partied with him. Total lies!'"
            ]
        },
        {
            "search_num": 4,
            "endpoint": "timeline.php",
            "params": {"screenname": "VirginiaGiuffre"},
            "results": [
                "Virginia Giuffre: 'I saw Trump at Epstein's parties but he never participated in anything untoward'",
                "Giuffre testimony mentions Trump was present at Mar-a-Lago recruitment events"
            ]
        },
        
        # Round 3: Specific searches
        {
            "search_num": 5,
            "endpoint": "search.php",
            "params": {"query": "Trump denies Epstein friendship"},
            "results": [
                "Video from 1992 NBC party shows Trump saying about Epstein: 'He likes beautiful women as much as I do, many on the younger side'",
                "2002 New York Magazine profile quotes Trump: 'Jeffrey is a terrific guy, fun to be with'"
            ]
        },
        {
            "search_num": 6,
            "endpoint": "search.php",
            "params": {"query": "Mar-a-Lago calendar girl audition 2002"},
            "results": []  # Dead end
        },
        
        # Round 4: Financial searches
        {
            "search_num": 7,
            "endpoint": "search.php",
            "params": {"query": "Trump Organization Epstein financial"},
            "results": [
                "Bank records subpoenaed showing $3.5M transfer between Trump Org shell company and Epstein associate in 2002"
            ]
        },
        {
            "search_num": 8,
            "endpoint": "search.php",
            "params": {"query": "Epstein Trump business deals 2002"},
            "results": []  # Dead end
        },
        
        # Round 5: Court documents
        {
            "search_num": 9,
            "endpoint": "search.php",
            "params": {"query": "court documents Trump Epstein 2002"},
            "results": [
                "Sealed court documents from 2002 case mention Trump and Epstein as co-defendants in assault allegation",
                "Case dismissed after accuser received settlement, amount undisclosed"
            ]
        },
        
        # Round 6: Fact checking
        {
            "search_num": 10,
            "endpoint": "search.php",
            "params": {"query": "fact check Trump Epstein relationship"},
            "results": [
                "Fact check: Trump's claim of barely knowing Epstein contradicted by 15+ years of documented social interactions",
                "Analysis: Over 50 photos and videos show Trump and Epstein together at various events from 1992-2004"
            ]
        }
    ]
    
    # Process searches and add to graph
    print("\n[SEARCH EXECUTION]")
    datapoint_ids = []
    
    for search_data in investigation_data:
        search_id = viz.add_search_node(
            search_data["params"],
            search_data["endpoint"],
            search_data["search_num"],
            parent_id=query_id
        )
        
        results = search_data["results"]
        if results:
            print(f"[OK] Search #{search_data['search_num']:2d}: {str(search_data['params'])[:40]:<40} | {len(results)} findings")
            
            # Add findings as datapoints
            for finding in results:
                dp_id = viz.add_datapoint_node(
                    finding,
                    search_data["endpoint"],
                    search_id,
                    relevance=0.7 + random.random() * 0.3
                )
                datapoint_ids.append(dp_id)
        else:
            print(f"[--] Search #{search_data['search_num']:2d}: {str(search_data['params'])[:40]:<40} | Dead end")
    
    # Add insights based on patterns
    print("\n[PATTERN ANALYSIS]")
    
    insights = [
        ("Court documents and flight logs confirm Trump-Epstein meetings in 2002 despite later denials", 0.95, datapoint_ids[:3]),
        ("Timeline contradiction: Trump's 2019 denials vs documented 2002 relationship", 0.9, datapoint_ids[3:6]),
        ("Financial records suggest business relationship beyond social connection", 0.8, datapoint_ids[6:8]),
        ("Multiple witness testimonies corroborate recruitment activities at Mar-a-Lago", 0.85, datapoint_ids[2:5]),
        ("Pattern of denial despite photographic and documentary evidence", 0.92, datapoint_ids[:10])
    ]
    
    for synthesis, confidence, supporting in insights:
        if supporting:
            viz.add_insight_node(synthesis, confidence, supporting[:3])
            print(f"[OK] Insight: {synthesis[:60]}... (confidence: {confidence:.0%})")
    
    # Get and display statistics
    print("\n[GRAPH STATISTICS]")
    print("-"*40)
    stats = viz.get_statistics()
    
    print(f"Total Nodes: {stats['total_nodes']}")
    print(f"  - Initial Query: {stats['node_counts']['query']}")
    print(f"  - Search Queries: {stats['node_counts']['search']}")
    print(f"  - Findings (DataPoints): {stats['node_counts']['datapoint']}")
    print(f"  - Insights (Patterns): {stats['node_counts']['insight']}")
    print(f"\nTotal Connections: {stats['total_edges']}")
    for edge_type, count in stats['edge_counts'].items():
        print(f"  - {edge_type}: {count}")
    
    dead_ends = stats['metrics'].get('dead_end_searches', [])
    if dead_ends:
        print(f"\nDead-end Searches: {len(dead_ends)}")
    
    # Save visualization
    print("\n[SAVING FILES]")
    print("-"*40)
    
    html_file = "investigation_trump_epstein.html"
    viz.save_visualization(html_file)
    print(f"[OK] HTML visualization saved to: {html_file}")
    
    json_file = "investigation_trump_epstein.json"
    data = viz.export_vis_data()
    with open(json_file, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"[OK] Graph data saved to: {json_file}")
    
    print("\n" + "="*80)
    print(" GRAPH CREATION COMPLETE")
    print("="*80)
    print(f"\nOpen {html_file} in your browser to view the investigation graph!")
    print("\nThis graph shows:")
    print("  - The initial investigation query as the root node (purple star)")
    print("  - All search queries branching from it (green boxes)")
    print("  - Significant findings from searches (blue ellipses)")
    print("  - Patterns/insights discovered (orange diamonds)")
    print("  - Dead-end searches with no connections")
    
    return viz

if __name__ == "__main__":
    viz = create_realistic_investigation_graph()