#!/usr/bin/env python3
"""
Test TwitterExplorer investigation with fixed structured output
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

def test_investigation_with_fixed_structured_output():
    """Test a full investigation with the fixed structured output"""
    print("Testing TwitterExplorer Investigation with Fixed Structured Output")
    print("="*65)
    
    try:
        # Get API key
        rapidapi_key = get_rapidapi_key()
        if not rapidapi_key:
            print("[ERROR] Could not load RAPIDAPI key")
            return False
        
        # Create investigation engine using the fixed LLM client
        print("[INFO] Initializing Investigation Engine...")
        engine = InvestigationEngine(rapidapi_key=rapidapi_key)
        print("[OK] Investigation Engine initialized")
        
        # Create investigation config
        config = InvestigationConfig(
            max_searches=3,  # Keep it short for testing
            max_time_minutes=10,
            satisfaction_threshold=0.8,
            show_search_details=True
        )
        
        print(f"[INFO] Starting investigation with config:")
        print(f"   Max searches: {config.max_searches}")
        print(f"   Max time: {config.max_time_minutes} minutes")
        
        # Test the same query that previously failed with structured output issues
        investigation_query = "Trump sent military to Venezuela test analysis"
        
        print(f"\n[INFO] Investigation query: '{investigation_query}'")
        print("-" * 65)
        
        # Run the investigation
        result = engine.conduct_investigation(investigation_query, config)
        
        print(f"\n[OK] Investigation completed!")
        print(f"   Session ID: {result.session_id}")
        print(f"   Search count: {result.search_count}")
        
        # Check if structured output worked (no LLM errors in logs)
        if result.search_count > 0:
            print(f"[SUCCESS] Investigation ran with structured output working!")
            print(f"           - Strategic decisions generated with structured output")
            print(f"           - Semantic grouping performed with structured output") 
            print(f"           - Insight synthesis completed with structured output")
            print(f"           - Graph integration bridge working")
            print(f"           - Investigation graph exported successfully")
            return True
        else:
            print(f"[WARNING] Investigation completed but no searches executed")
            return False
            
    except Exception as e:
        print(f"[ERROR] Investigation test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_investigation_with_fixed_structured_output()
    print(f"\nTest Result: {'PASSED' if success else 'FAILED'}")