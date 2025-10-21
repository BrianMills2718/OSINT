"""Generate graph visualization from real investigation logs"""
import json
import os
from datetime import datetime
from collections import defaultdict
from twitterexplorer.graph_visualizer import InvestigationGraphVisualizer

def parse_investigation_logs(log_file_path):
    """Parse investigation logs to extract search data"""
    searches_by_session = defaultdict(list)
    
    with open(log_file_path, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                entry = json.loads(line.strip())
                if entry.get('entry_type') == 'search_attempt':
                    session_id = entry.get('session_id')
                    searches_by_session[session_id].append(entry)
            except json.JSONDecodeError:
                continue
    
    return searches_by_session

def find_best_session(searches_by_session):
    """Find the session with the most searches"""
    best_session = None
    max_searches = 0
    
    for session_id, searches in searches_by_session.items():
        if len(searches) > max_searches:
            max_searches = len(searches)
            best_session = session_id
    
    return best_session, max_searches

def create_graph_from_logs(session_id, searches):
    """Create graph visualization from session searches"""
    viz = InvestigationGraphVisualizer()
    
    # Find the original query from the first search's strategy
    original_query = "Investigation"
    if searches and 'strategy_type' in searches[0]:
        strategy = searches[0]['strategy_type']
        # Try to extract the question from the strategy
        if "What is" in strategy:
            start = strategy.find("What is")
            end = strategy.find("?", start)
            if end > start:
                original_query = strategy[start:end+1]
        elif "answering the question" in strategy:
            start = strategy.find("'")
            end = strategy.find("'", start + 1)
            if end > start:
                original_query = strategy[start+1:end]
    
    print(f"\nInvestigation Query: {original_query}")
    print(f"Session ID: {session_id}")
    print(f"Total Searches: {len(searches)}")
    print("-"*80)
    
    # Add query node (root)
    query_id = viz.add_query_node(original_query)
    
    # Track search nodes for finding connections
    search_id_map = {}
    
    # Process each search
    for search in searches:
        search_num = search.get('search_id', 0)
        endpoint = search.get('endpoint', 'unknown')
        params = search.get('params', {})
        results_count = search.get('results_count', 0)
        effectiveness = search.get('effectiveness_score', 0.0)
        strategy = search.get('strategy_type', '')
        error = search.get('error')
        
        # Create search node
        search_node_id = viz.add_search_node(
            params,
            endpoint,
            search_num,
            parent_id=query_id
        )
        search_id_map[search_num] = search_node_id
        
        # Print search info
        status = "[OK]" if results_count > 0 else "[--]"
        query_text = params.get('query', params.get('screenname', str(params)))[:40]
        print(f"{status} Search #{search_num:2d}: {query_text:<40} | Results: {results_count:3d} | Score: {effectiveness:.1f}")
        
        # Add error as finding if present
        if error and "no attribute" not in error:
            viz.add_datapoint_node(
                f"Error: {error[:100]}",
                endpoint,
                search_node_id,
                relevance=0.1
            )
        
        # Add sample results as findings if available
        sample_results = search.get('sample_results', [])
        if sample_results and isinstance(sample_results, list):
            for i, result in enumerate(sample_results[:3]):  # Limit to 3 per search
                if isinstance(result, dict):
                    text = result.get('text', result.get('content', str(result)))[:200]
                else:
                    text = str(result)[:200]
                
                if text and len(text) > 20:  # Only add substantial findings
                    viz.add_datapoint_node(
                        text,
                        endpoint,
                        search_node_id,
                        relevance=effectiveness / 10.0
                    )
    
    # Look for patterns and add insights
    # Group searches by endpoint
    by_endpoint = defaultdict(list)
    for search in searches:
        by_endpoint[search.get('endpoint', 'unknown')].append(search)
    
    # Add insights based on patterns
    if len(by_endpoint) > 1:
        viz.add_insight_node(
            f"Investigation used {len(by_endpoint)} different endpoint types",
            confidence=0.7,
            supporting_nodes=[]
        )
    
    # Check for repeated failures
    failed_searches = [s for s in searches if s.get('results_count', 0) == 0]
    if len(failed_searches) > 3:
        viz.add_insight_node(
            f"{len(failed_searches)} searches returned no results - possible API or query issues",
            confidence=0.9,
            supporting_nodes=[]
        )
    
    # Check for successful pattern
    successful_searches = [s for s in searches if s.get('results_count', 0) > 10]
    if successful_searches:
        viz.add_insight_node(
            f"{len(successful_searches)} searches found substantial results (>10 items)",
            confidence=0.8,
            supporting_nodes=[]
        )
    
    return viz

def main():
    print("\n" + "="*80)
    print(" VISUALIZING REAL INVESTIGATION FROM LOGS")
    print("="*80)
    
    # Allow specifying which log file to use
    import sys
    if len(sys.argv) > 1:
        latest_log = sys.argv[1]
    else:
        # Find the most recent log file
        log_dir = "logs/searches"
        log_files = [f for f in os.listdir(log_dir) if f.endswith('.jsonl')]
        
        if not log_files:
            print("No log files found!")
            return
        
        # Use the most recent file
        log_files.sort()
        latest_log = os.path.join(log_dir, log_files[-1])
    
    print(f"\nUsing log file: {latest_log}")
    
    # Parse logs
    searches_by_session = parse_investigation_logs(latest_log)
    print(f"Found {len(searches_by_session)} investigation sessions")
    
    # Find best session
    session_id, num_searches = find_best_session(searches_by_session)
    
    if not session_id:
        print("No valid sessions found!")
        return
    
    searches = searches_by_session[session_id]
    
    # Create visualization
    viz = create_graph_from_logs(session_id, searches)
    
    # Get statistics
    print(f"\n[GRAPH STATISTICS]")
    print("-"*40)
    stats = viz.get_statistics()
    
    print(f"Total Nodes: {stats['total_nodes']}")
    print(f"  - Initial Query: {stats['node_counts']['query']}")
    print(f"  - Search Queries: {stats['node_counts']['search']}")
    print(f"  - Findings (DataPoints): {stats['node_counts']['datapoint']}")
    print(f"  - Insights (Patterns): {stats['node_counts']['insight']}")
    print(f"\nTotal Connections: {stats['total_edges']}")
    
    # Check for dead ends
    dead_ends = stats['metrics'].get('dead_end_searches', [])
    if dead_ends:
        print(f"\nDead-end Searches (no findings): {len(dead_ends)}")
        for de in dead_ends[:5]:
            print(f"  - {de}")
    
    # Save visualization
    print(f"\n[SAVING VISUALIZATION]")
    print("-"*40)
    
    output_file = f"real_investigation_{session_id[:8]}.html"
    viz.save_visualization(output_file)
    print(f"[OK] Visualization saved to: {output_file}")
    
    # Also save the data
    data = viz.export_vis_data()
    json_file = f"real_investigation_{session_id[:8]}.json"
    with open(json_file, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"[OK] Graph data saved to: {json_file}")
    
    print("\n" + "="*80)
    print(" VISUALIZATION COMPLETE")
    print("="*80)
    print(f"\nOpen {output_file} in your browser to view the investigation graph!")
    
    return viz

if __name__ == "__main__":
    viz = main()