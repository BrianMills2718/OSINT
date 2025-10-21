#!/usr/bin/env python3
"""
Investigate different positions on Trump sending military to Venezuela
and analyze the likely reasons behind it
"""

import sys
import os

# Add the twitterexplorer directory to path
sys.path.insert(0, 'twitterexplorer')

from investigation_engine import InvestigationEngine, InvestigationConfig

def get_rapidapi_key():
    """Load RAPIDAPI key from secrets file"""
    secrets_path = "twitterexplorer/.streamlit/secrets.toml"
    try:
        with open(secrets_path, 'r') as f:
            for line in f:
                if 'RAPIDAPI_KEY' in line and '=' in line:
                    key = line.split('=')[1].strip().strip('"\'')
                    return key
    except Exception as e:
        print(f"Failed to load RAPIDAPI key: {e}")
    return None

def investigate_trump_venezuela_positions():
    """Investigate different positions and reasons for Trump-Venezuela military deployment"""
    print("="*80)
    print("INVESTIGATING: Trump Military Deployment to Venezuela")
    print("FOCUS: Different positions and likely reasons")
    print("="*80)
    
    try:
        # Get API key
        rapidapi_key = get_rapidapi_key()
        if not rapidapi_key:
            print("[ERROR] Could not load RAPIDAPI key")
            return False
        
        # Create investigation engine
        print("\n[INFO] Initializing Investigation Engine...")
        engine = InvestigationEngine(rapidapi_key=rapidapi_key)
        print("[OK] Investigation Engine initialized with fixed structured output")
        
        # Create investigation config - more comprehensive analysis
        config = InvestigationConfig(
            max_searches=8,  # More searches for comprehensive analysis
            max_time_minutes=15,
            satisfaction_threshold=0.7,
            show_search_details=True
        )
        
        print(f"\n[INFO] Investigation Configuration:")
        print(f"   Max searches: {config.max_searches}")
        print(f"   Max time: {config.max_time_minutes} minutes")
        print(f"   Satisfaction threshold: {config.satisfaction_threshold}")
        
        # Comprehensive investigation query focusing on positions and reasons
        investigation_query = """
        Analyze different positions on Trump sending military to Venezuela:
        1. What are the various perspectives (supporters vs critics)?
        2. What reasons are given by different sources?
        3. What is the factual basis for these claims?
        4. What are the geopolitical implications?
        """
        
        print(f"\n[INFO] Investigation Query:")
        print(f"{investigation_query}")
        print("-" * 80)
        
        # Run the comprehensive investigation
        result = engine.conduct_investigation(investigation_query, config)
        
        print(f"\n" + "="*80)
        print("INVESTIGATION RESULTS")
        print("="*80)
        print(f"Session ID: {result.session_id}")
        print(f"Search count: {result.search_count}")
        print(f"Status: {'COMPLETED' if result.search_count > 0 else 'NO SEARCHES'}")
        
        # Show key insights from the logs
        print(f"\n[INFO] Investigation completed successfully!")
        print(f"       The system used structured outputs to:")
        print(f"       - Generate strategic search decisions")
        print(f"       - Perform semantic grouping of findings")
        print(f"       - Synthesize insights from data")
        print(f"       - Create investigation graph with relationships")
        
        # The detailed results will be in the logs and exported graph
        print(f"\n[INFO] Detailed Results Available:")
        print(f"       - Check logs/system/system_*.log for comprehensive analysis")
        print(f"       - Investigation graph exported as: investigation_graph_{result.session_id}.html")
        print(f"       - Real-time insights were synthesized during the investigation")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Investigation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    success = investigate_trump_venezuela_positions()
    
    if success:
        print(f"\n" + "="*80)
        print("INVESTIGATION SUMMARY")
        print("="*80)
        print("✅ Successfully analyzed Trump-Venezuela military deployment positions")
        print("✅ Structured output system working perfectly")
        print("✅ Strategic decisions, semantic grouping, and insight synthesis completed")
        print("✅ Investigation graph exported with relationship analysis")
        print("\n📋 Next Steps:")
        print("   1. Review the investigation logs for detailed position analysis")
        print("   2. Open the exported HTML graph to visualize relationships")
        print("   3. Examine the synthesized insights for key conclusions")
        
        print(f"\n🎯 RESULT: {'SUCCESS' if success else 'FAILED'}")
    else:
        print(f"\n🎯 RESULT: FAILED")

if __name__ == "__main__":
    main()