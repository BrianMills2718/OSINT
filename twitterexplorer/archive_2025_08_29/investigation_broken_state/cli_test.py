"""CLI test for Twitter investigation system"""

import sys
import os
sys.path.insert(0, 'twitterexplorer')

from investigation_engine import InvestigationEngine, InvestigationConfig

def run_cli_investigation(query, max_searches=3):
    """Run a simple investigation from CLI"""
    
    print("=" * 60)
    print(f"TWITTER INVESTIGATION: {query}")
    print("=" * 60)
    
    # Load API key
    api_key = None
    
    # Try to get from secrets.toml
    try:
        import toml
        secrets_path = r'twitterexplorer\.streamlit\secrets.toml'
        if os.path.exists(secrets_path):
            secrets = toml.load(secrets_path)
            api_key = secrets.get('RAPIDAPI_KEY')
            print(f"[OK] Loaded API key from secrets.toml")
    except Exception as e:
        print(f"[WARNING] Could not load secrets: {e}")
    
    # Fallback to environment variable
    if not api_key:
        api_key = os.getenv('RAPIDAPI_KEY', 'test_key')
        if api_key == 'test_key':
            print("[WARNING] Using test API key - real searches won't work")
    
    # Create config
    config = InvestigationConfig(
        max_searches=max_searches,
        show_search_details=True,
        show_strategy_reasoning=True,
        show_effectiveness_scores=True,
        pages_per_search=1  # Quick test
    )
    
    print(f"\nConfiguration:")
    print(f"  Max searches: {config.max_searches}")
    print(f"  Show details: {config.show_search_details}")
    
    # Create engine
    try:
        print("\nInitializing investigation engine...")
        engine = InvestigationEngine(api_key)
        print("[OK] Engine initialized")
        
        # Check components
        if hasattr(engine, 'logger'):
            print("[OK] Logger ready")
        if hasattr(engine, 'llm_coordinator'):
            print("[OK] LLM coordinator ready")
            
    except Exception as e:
        print(f"[ERROR] Failed to initialize engine: {e}")
        return
    
    # Run investigation
    print(f"\n" + "=" * 60)
    print("STARTING INVESTIGATION")
    print("=" * 60)
    
    try:
        result = engine.conduct_investigation(query, config)
        
        print(f"\n" + "=" * 60)
        print("INVESTIGATION COMPLETE")
        print("=" * 60)
        
        print(f"\nResults:")
        print(f"  Total searches: {len(result.search_history)}")
        print(f"  Total results: {sum(s.results_count for s in result.search_history)}")
        print(f"  Findings: {len(result.accumulated_findings)}")
        print(f"  Satisfaction: {result.satisfaction_metrics.overall_satisfaction():.2f}")
        print(f"  Status: {'Success' if result.completion_reason else 'In Progress'}")
        
        if hasattr(result, 'error') and result.error:
            print(f"  Error: {result.error}")
        
        # Show some findings
        if result.accumulated_findings:
            print(f"\nTop Findings:")
            for i, finding in enumerate(result.accumulated_findings[:3], 1):
                print(f"  {i}. {finding.content[:100]}...")
                print(f"     Credibility: {finding.credibility_score:.1f}")
        
        # Show search history
        if result.search_history:
            print(f"\nSearch History:")
            for search in result.search_history[:5]:
                query_text = getattr(search, 'query', 'N/A')
                if query_text and len(query_text) > 50:
                    query_text = query_text[:50] + "..."
                print(f"  - {search.endpoint}: {query_text}")
                print(f"    Results: {search.results_count}, Score: {search.effectiveness_score:.1f}")
        
        return result
        
    except Exception as e:
        print(f"\n[ERROR] Investigation failed: {e}")
        import traceback
        traceback.print_exc()
        return None

def main():
    """Main CLI entry point"""
    
    # Default query or from command line
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
    else:
        # Default test query
        query = "latest AI developments 2024"
    
    print("Twitter Explorer CLI Test")
    print("-" * 60)
    
    # Run investigation
    result = run_cli_investigation(query, max_searches=3)
    
    if result:
        print("\n[STATUS] Investigation completed!")
    else:
        print("\n[ERROR] Investigation failed or incomplete")

if __name__ == "__main__":
    main()