"""Test if tweet content actually flows through the system"""
import os
import sys
import json

# Setup paths
twitterexplorer_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'twitterexplorer')
sys.path.insert(0, twitterexplorer_dir)
os.chdir(twitterexplorer_dir)

from investigation_engine import InvestigationEngine, InvestigationConfig

# Load API key
secrets_path = ".streamlit/secrets.toml"
with open(secrets_path, 'r') as f:
    content = f.read()
    for line in content.split('\n'):
        if 'RAPIDAPI_KEY' in line:
            api_key = line.split('=')[1].strip().strip('"')
            break

print("="*60)
print("TESTING FULL FLOW: API -> TWEETS -> LLM -> SUMMARY")
print("="*60)

# Create engine
engine = InvestigationEngine(api_key)

# Small config for testing
config = InvestigationConfig(
    max_searches=2,  # Just 2 searches
    pages_per_search=1
)

# Run investigation
query = "What is Elon Musk's latest announcement about X platform?"
print(f"\nQuery: {query}\n")

try:
    result = engine.conduct_investigation(query, config)
    
    print("\n" + "="*60)
    print("INVESTIGATION RESULTS")
    print("="*60)
    
    # Check basic stats
    print(f"Searches conducted: {result.search_count}")
    print(f"Total results found: {result.total_results_found}")
    
    # Check if we have accumulated findings
    print(f"\n[FINDINGS CHECK]")
    if hasattr(result, 'accumulated_findings'):
        print(f"Accumulated findings: {len(result.accumulated_findings)}")
        if result.accumulated_findings:
            print("\nSample findings:")
            for i, finding in enumerate(result.accumulated_findings[:3], 1):
                if hasattr(finding, 'content'):
                    print(f"{i}. {finding.content[:100]}...")
                else:
                    print(f"{i}. {str(finding)[:100]}...")
    else:
        print("No accumulated_findings attribute")
    
    # Check rounds for insights
    print(f"\n[ROUNDS CHECK]")
    for round_idx, round_obj in enumerate(result.rounds):
        print(f"\nRound {round_idx + 1}:")
        print(f"  Strategy: {round_obj.strategy_description[:50]}...")
        print(f"  Total results: {round_obj.total_results}")
        print(f"  Effectiveness: {round_obj.round_effectiveness}")
        
        if hasattr(round_obj, 'key_insights') and round_obj.key_insights:
            print(f"  Key insights: {round_obj.key_insights}")
        else:
            print(f"  No key insights captured")
    
    # Check if LLM saw actual tweets
    print(f"\n[LLM ANALYSIS CHECK]")
    
    # Try to access a search attempt's raw results
    if result.search_history:
        first_search = result.search_history[0]
        if hasattr(first_search, '_raw_results'):
            print(f"First search has {len(first_search._raw_results)} raw results")
            if first_search._raw_results:
                first_tweet = first_search._raw_results[0]
                print(f"Sample tweet text: {first_tweet.get('text', 'NO TEXT')[:100]}...")
        else:
            print("No _raw_results attribute on search attempts")
    
    # Check graph nodes if in graph mode
    if hasattr(engine, 'graph_mode') and engine.graph_mode:
        if hasattr(engine.llm_coordinator, 'graph'):
            graph = engine.llm_coordinator.graph
            print(f"\n[GRAPH CHECK]")
            print(f"Total nodes: {len(graph.nodes)}")
            print(f"Total edges: {len(graph.edges)}")
            
            # Count node types
            datapoints = [n for n in graph.nodes.values() if 'DataPoint' in str(type(n))]
            insights = [n for n in graph.nodes.values() if 'Insight' in str(type(n))]
            
            print(f"DataPoint nodes: {len(datapoints)}")
            print(f"Insight nodes: {len(insights)}")
            
            if datapoints:
                print("\nSample DataPoint content:")
                for i, dp in enumerate(datapoints[:2], 1):
                    content = dp.properties.get('content', 'NO CONTENT')
                    print(f"{i}. {content[:100]}...")
    
    # Final summary check
    print(f"\n[SUMMARY CHECK]")
    if hasattr(result, 'final_summary'):
        print(f"Has final summary: {result.final_summary[:200]}...")
    else:
        print("No final summary attribute")
    
    # Check satisfaction
    if hasattr(result, 'satisfaction_metrics'):
        satisfaction = result.satisfaction_metrics.overall_satisfaction()
        print(f"\nOverall satisfaction: {satisfaction:.2%}")
    
    print("\n" + "="*60)
    print("DIAGNOSIS")
    print("="*60)
    
    if result.total_results_found > 0:
        print("[OK] API calls returned results")
    else:
        print("[FAIL] No results from API")
    
    if hasattr(result.search_history[0], '_raw_results'):
        print("[OK] Raw tweet data is captured")
    else:
        print("[FAIL] Raw tweet data not captured")
    
    if hasattr(result, 'accumulated_findings') and result.accumulated_findings:
        print("[OK] Findings are accumulated")
    else:
        print("[FAIL] No findings accumulated")
    
    if hasattr(engine.llm_coordinator, 'graph') and len(graph.nodes) > 5:
        print("[OK] Knowledge graph is populated")
    else:
        print("[FAIL] Knowledge graph not populated")
        
except Exception as e:
    print(f"\n[ERROR] Investigation failed: {e}")
    import traceback
    traceback.print_exc()