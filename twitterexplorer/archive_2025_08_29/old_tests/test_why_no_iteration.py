"""Debug why system doesn't iterate"""
import sys
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
twitterexplorer_path = os.path.join(current_dir, 'twitterexplorer')
sys.path.insert(0, twitterexplorer_path)

from investigation_engine import InvestigationEngine, InvestigationConfig

def test_iteration():
    print("=== WHY NO ITERATION? ===\n")
    
    api_key = "d72bcd77e2msh76c7e6cf37f0b89p1c51bcjsnaad0f6b01e4f"
    engine = InvestigationEngine(api_key)
    
    # Hook to see should_continue calls
    def track_session(session):
        original_should_continue = session.should_continue
        
        def should_continue_with_trace():
            result, reason = original_should_continue()
            print(f"\nshould_continue() called:")
            print(f"  search_count: {session.search_count}")
            print(f"  max_searches: {session.config.max_searches}")
            print(f"  Result: {result}")
            print(f"  Reason: {reason}")
            return result, reason
        
        session.should_continue = should_continue_with_trace
        return session
    
    # Replace conduct_investigation to hook session
    original_conduct = engine.conduct_investigation
    
    def conduct_with_tracking(query, config=None):
        # Hook into the session creation
        original_method = engine.conduct_investigation
        
        def wrapper(q, c):
            # Get the session by calling original up to session creation
            import streamlit as st
            if 'progress_container' not in st.session_state:
                st.session_state.progress_container = st.container()
            session = engine._create_session(q, c or InvestigationConfig())
            
            # Track it
            track_session(session)
            
            # Continue with original
            return original_method(q, c)
        
        return wrapper(query, config)
    
    # Run with config that SHOULD allow multiple rounds
    config = InvestigationConfig(
        max_searches=10,  # Should allow multiple rounds!
        pages_per_search=1
    )
    
    print(f"Config: max_searches={config.max_searches}")
    
    result = conduct_with_tracking(
        "test query",
        config
    )
    
    print(f"\n=== FINAL ===")
    print(f"Total searches executed: {result.search_count}")
    print(f"Total rounds: {len(result.rounds) if hasattr(result, 'rounds') else 'N/A'}")

if __name__ == "__main__":
    test_iteration()