"""Quick test to verify the integrated system works"""

import sys
import os
sys.path.insert(0, 'twitterexplorer')

def test_basic_imports():
    """Test that all main components import"""
    print("Testing imports...")
    
    try:
        from investigation_engine import InvestigationEngine, InvestigationConfig
        print("  [OK] InvestigationEngine")
    except Exception as e:
        print(f"  [FAIL] InvestigationEngine: {e}")
        return False
        
    try:
        from graph_aware_llm_coordinator import GraphAwareLLMCoordinator
        print("  [OK] GraphAwareLLMCoordinator")
    except Exception as e:
        print(f"  [FAIL] GraphAwareLLMCoordinator: {e}")
        return False
        
    try:
        from llm_client import get_litellm_client
        print("  [OK] LLM Client")
    except Exception as e:
        print(f"  [FAIL] LLM Client: {e}")
        return False
        
    return True

def test_engine_initialization():
    """Test that engine initializes without errors"""
    print("\nTesting engine initialization...")
    
    try:
        from investigation_engine import InvestigationEngine
        engine = InvestigationEngine("test_api_key")
        print("  [OK] Engine created")
        
        # Check logger exists
        if hasattr(engine, 'logger'):
            print("  [OK] Logger attribute exists")
        else:
            print("  [FAIL] Logger attribute missing")
            return False
            
        # Check coordinator exists
        if hasattr(engine, 'llm_coordinator'):
            print("  [OK] LLM coordinator exists")
        else:
            print("  [FAIL] LLM coordinator missing")
            return False
            
        return True
        
    except Exception as e:
        print(f"  [FAIL] Engine initialization: {e}")
        return False

def test_v2_availability():
    """Check if v2 improvements are available"""
    print("\nChecking v2 improvements...")
    
    v2_files = ['models_v2.py', 'llm_client_v2.py']
    for file in v2_files:
        path = os.path.join('twitterexplorer', file)
        if os.path.exists(path):
            print(f"  [OK] {file} available")
        else:
            print(f"  [INFO] {file} not found")
    
    # Test if v2 can be imported
    try:
        sys.path.insert(0, 'twitterexplorer')
        from models_v2 import StrategyOutput, EndpointPlan
        print("  [OK] v2 models import successfully")
    except Exception as e:
        print(f"  [INFO] v2 models not importable: {e}")
    
    return True

def main():
    print("=" * 60)
    print("TWITTER EXPLORER SYSTEM TEST")
    print("=" * 60)
    
    all_pass = True
    
    # Run tests
    all_pass &= test_basic_imports()
    all_pass &= test_engine_initialization()
    test_v2_availability()  # Just informational
    
    print("\n" + "=" * 60)
    if all_pass:
        print("SUCCESS: Core system is working!")
        print("\nNext steps:")
        print("1. Run the app: streamlit run twitterexplorer/app.py")
        print("2. To use v2 structured output, update imports in graph_aware_llm_coordinator.py")
    else:
        print("ISSUES FOUND: Check the errors above")
    print("=" * 60)

if __name__ == "__main__":
    main()