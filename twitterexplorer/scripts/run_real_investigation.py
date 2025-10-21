"""Run a real Twitter investigation with actual API calls and create visualization"""
import os
import sys

# Add parent directory to path for graph_visualizer
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Change to twitterexplorer directory for proper imports
twitterexplorer_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'twitterexplorer')
sys.path.insert(0, twitterexplorer_dir)
os.chdir(twitterexplorer_dir)

from investigation_engine import InvestigationEngine, InvestigationConfig
sys.path.insert(0, '..')
from graph_visualizer import InvestigationGraphVisualizer
import json
from datetime import datetime

def run_real_investigation():
    """Run investigation on a real topic with actual data"""
    
    print("="*60)
    print("REAL INVESTIGATION: Elon Musk Twitter Activity")
    print("="*60)
    print("\nThis test uses a real topic that should return actual results.\n")
    
    # Load API key from secrets
    secrets_path = ".streamlit/secrets.toml"  # We're already in twitterexplorer dir
    api_key = None
    
    if os.path.exists(secrets_path):
        with open(secrets_path, 'r') as f:
            content = f.read()
            for line in content.split('\n'):
                if 'RAPIDAPI_KEY' in line:
                    api_key = line.split('=')[1].strip().strip('"')
                    break
    
    if not api_key:
        print("[ERROR] Could not load API key")
        return None
    
    print(f"[INFO] API Key loaded: {api_key[:10]}...")
    
    # Create engine with real API key
    engine = InvestigationEngine(api_key)
    
    # Configure for focused investigation
    config = InvestigationConfig(
        max_searches=10,
        pages_per_search=2,
        satisfaction_enabled=True,
        satisfaction_threshold=0.7,
        min_searches_before_satisfaction=3,
        enforce_endpoint_diversity=True,
        max_endpoint_repeats=3
    )
    
    print("\nConfiguration:")
    print(f"- Max searches: {config.max_searches}")
    print(f"- Satisfaction threshold: {config.satisfaction_threshold}")
    print(f"- Endpoint diversity: ENABLED")
    print("\nStarting investigation...")
    print("-"*60)
    
    # Run investigation on a real topic
    try:
        result = engine.conduct_investigation(
            "What is Elon Musk saying about Twitter recently?",
            config=config
        )
        
        print(f"\n[SUCCESS] Investigation completed!")
        print(f"Searches conducted: {result.search_count}")
        print(f"Total results found: {result.total_results_found}")
        
        # Show search history
        print("\n### SEARCH HISTORY ###")
        for i, search in enumerate(result.search_history[:10], 1):
            endpoint = search.endpoint if hasattr(search, 'endpoint') else 'unknown'
            
            # Get query or screenname
            if hasattr(search, 'query'):
                detail = search.query[:50]
            elif hasattr(search, 'params'):
                params = search.params if isinstance(search.params, dict) else {}
                detail = params.get('query', params.get('screenname', 'N/A'))[:50]
            else:
                detail = 'N/A'
            
            results = search.results_count if hasattr(search, 'results_count') else 0
            print(f"{i}. {endpoint}: {detail}... ({results} results)")
        
        # Analyze endpoint usage
        endpoint_counts = {}
        for search in result.search_history:
            endpoint = search.endpoint
            endpoint_counts[endpoint] = endpoint_counts.get(endpoint, 0) + 1
        
        print("\n### ENDPOINT DIVERSITY ###")
        print(f"Unique endpoints used: {len(endpoint_counts)}")
        for endpoint, count in sorted(endpoint_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"  {endpoint}: {count} times")
        
        # Show actual results found
        print("\n### SAMPLE RESULTS ###")
        if result.total_results_found > 0:
            print(f"Found {result.total_results_found} total results")
            
            # Show some key findings if available
            if hasattr(result, 'accumulated_findings') and result.accumulated_findings:
                print("\nKey Findings:")
                for i, finding in enumerate(result.accumulated_findings[:5], 1):
                    content = finding.content if hasattr(finding, 'content') else str(finding)
                    print(f"{i}. {content[:150]}...")
            
            # Check if we got Elon Musk tweets
            elon_tweets = 0
            twitter_mentions = 0
            for search in result.search_history:
                if hasattr(search, 'results_count'):
                    if search.endpoint == 'timeline.php' and 'elonmusk' in str(search.params).lower():
                        elon_tweets += search.results_count
                    if 'twitter' in str(search.query).lower() if hasattr(search, 'query') else False:
                        twitter_mentions += search.results_count
            
            if elon_tweets > 0:
                print(f"\n[SUCCESS] Found {elon_tweets} tweets from Elon Musk's timeline")
            if twitter_mentions > 0:
                print(f"[SUCCESS] Found {twitter_mentions} mentions of Twitter")
        else:
            print("No results found (unexpected for this topic)")
        
        # Graph analysis
        if hasattr(engine, 'llm_coordinator') and hasattr(engine.llm_coordinator, 'graph'):
            graph = engine.llm_coordinator.graph
            print(f"\n### KNOWLEDGE GRAPH ###")
            print(f"Nodes created: {len(graph.nodes)}")
            print(f"Edges created: {len(graph.edges)}")
            
            # Check if adaptive strategy was used
            if hasattr(engine.llm_coordinator, 'adaptive_strategy'):
                pivots = engine.llm_coordinator.adaptive_strategy.pivot_count
                if pivots > 0:
                    print(f"\n[ADAPTIVE] System made {pivots} strategic pivots")
        
        # Satisfaction analysis
        if hasattr(result, 'satisfaction_metrics'):
            satisfaction = result.satisfaction_metrics.overall_satisfaction()
            print(f"\n### SATISFACTION ###")
            print(f"Overall satisfaction: {satisfaction:.2f}")
            
            if satisfaction >= config.satisfaction_threshold:
                print(f"[SUCCESS] Satisfaction threshold met!")
                print("Investigation terminated early due to sufficient results")
        
        # Summary
        print("\n" + "="*60)
        print("INVESTIGATION SUMMARY")
        print("="*60)
        
        if result.total_results_found > 0:
            print(f"[OK] Successfully found {result.total_results_found} results")
            print(f"[OK] Used {len(endpoint_counts)} different endpoints")
            print(f"[OK] Completed in {result.search_count} searches")
            
            if result.search_count < config.max_searches:
                print(f"[OK] Efficient: Stopped early due to satisfaction")
        else:
            print("[ERROR] No results found (check API or topic)")
        
        # CREATE VISUALIZATION FROM REAL DATA
        print("\n" + "="*60)
        print("CREATING VISUALIZATION FROM REAL API DATA")
        print("="*60)
        
        viz = InvestigationGraphVisualizer()
        
        # Add root query
        query_id = viz.add_query_node("What is Elon Musk saying about Twitter recently?")
        
        # Add all searches
        for round_obj in result.rounds:
            for search in round_obj.searches:
                search_id = viz.add_search_node(
                    search.params,
                    search.endpoint,
                    search.search_id,
                    parent_id=query_id
                )
                
                # Add findings if they exist
                if search.results_count > 0:
                    # Create a sample datapoint
                    viz.add_datapoint_node(
                        f"Found {search.results_count} results from {search.endpoint}",
                        search.endpoint,
                        search_id,
                        relevance=search.effectiveness_score / 10.0
                    )
        
        # Save visualization
        html_file = "../real_twitter_investigation.html"
        viz.save_visualization(html_file)
        print(f"[OK] Visualization saved to: {html_file}")
        print(f"   Open this file in your browser to see the REAL investigation graph!")
        
        stats = viz.get_statistics()
        print(f"\nGraph contains:")
        print(f"  - {stats['node_counts']['search']} search nodes")
        print(f"  - {stats['node_counts']['datapoint']} finding nodes")
        print(f"  - {stats['total_edges']} connections")
        
        return result
        
    except Exception as e:
        print(f"\n[ERROR] Investigation failed: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    result = run_real_investigation()