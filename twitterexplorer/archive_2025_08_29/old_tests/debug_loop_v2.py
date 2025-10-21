"""Debug why system stops after one round - simpler approach"""
import sys
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
twitterexplorer_path = os.path.join(current_dir, 'twitterexplorer')
sys.path.insert(0, twitterexplorer_path)

from investigation_engine import InvestigationEngine, InvestigationConfig

def debug_loop():
    """Debug the core loop issue"""
    
    print("=== DEBUGGING LOOP TERMINATION ===\n")
    
    api_key = "d72bcd77e2msh76c7e6cf37f0b89p1c51bcjsnaad0f6b01e4f"
    engine = InvestigationEngine(api_key)
    
    # Patch conduct_investigation to add logging
    original_conduct = engine.conduct_investigation
    
    def debug_conduct(query, config=None):
        """Add debugging to conduct_investigation"""
        if config is None:
            from investigation_engine import InvestigationConfig
            config = InvestigationConfig()
        
        print(f"Config settings:")
        print(f"  max_searches: {config.max_searches}")
        print(f"  satisfaction_enabled: {config.satisfaction_enabled}")
        print(f"  min_searches_before_satisfaction: {config.min_searches_before_satisfaction}")
        
        # Create session directly
        from investigation_engine import InvestigationSession
        session = InvestigationSession(query, config)
        
        # Instrument the session
        original_should_continue = session.should_continue
        original_add_search = session.add_search_attempt
        
        call_count = [0]
        
        def debug_should_continue():
            call_count[0] += 1
            result, reason = original_should_continue()
            print(f"\n[should_continue #{call_count[0]}]")
            print(f"  search_count: {session.search_count}")
            print(f"  round_count: {session.round_count}")
            print(f"  config.max_searches: {session.config.max_searches}")
            print(f"  Result: {result} - {reason}")
            return result, reason
        
        def debug_add_search(attempt):
            print(f"\n[add_search_attempt]")
            print(f"  Before: search_count={session.search_count}")
            result = original_add_search(attempt)
            print(f"  After: search_count={session.search_count}")
            return result
        
        session.should_continue = debug_should_continue
        session.add_search_attempt = debug_add_search
        
        # Now call the original with our instrumented session
        # We need to inject our session somehow...
        # Let's just trace from outside
        
        # Actually, let's patch the whole loop
        import streamlit as st
        
        # Mock streamlit if needed
        if not hasattr(st, 'container'):
            st.container = lambda: None
            st.empty = lambda: None
            st.columns = lambda x: [None] * x
            st.info = lambda x: print(f"[INFO] {x}")
        
        # Initialize session containers
        progress_container = st.container()
        details_container = st.container()
        
        print("\n=== STARTING MAIN LOOP ===")
        
        round_num = 0
        while session.should_continue()[0]:
            round_num += 1
            print(f"\n>>> ROUND {round_num} STARTING")
            print(f"    Current search_count: {session.search_count}")
            
            # Generate strategy
            strategy = engine._generate_strategy(session)
            current_round = session.start_new_round(strategy['description'])
            
            searches_in_round = len(strategy.get('searches', []))
            print(f"    Searches planned: {searches_in_round}")
            print(f"    Will be search_count after: {session.search_count + searches_in_round}")
            
            # Execute searches
            round_results = []
            for i, search_plan in enumerate(strategy['searches']):
                print(f"\n    Executing search {i+1}/{searches_in_round}")
                search_id = session.search_count + 1
                
                # Execute search
                attempt = engine._execute_search(search_plan, search_id, round_num)
                session.add_search_attempt(attempt)
                round_results.append(attempt)
                
                # Check if we should stop mid-round
                should_cont, stop_reason = session.should_continue()
                if not should_cont:
                    print(f"\n    STOPPING MID-ROUND: {stop_reason}")
                    break
            
            # Analyze results
            engine._analyze_round_results_with_llm(session, current_round, round_results)
            
            print(f"\n>>> ROUND {round_num} COMPLETE")
            print(f"    Final search_count: {session.search_count}")
        
        print("\n=== LOOP TERMINATED ===")
        final_should, final_reason = session.should_continue()
        print(f"Final should_continue: {final_should}")
        print(f"Termination reason: {final_reason}")
        
        return session
    
    # Test with config that should allow multiple rounds
    config = InvestigationConfig(
        max_searches=10,
        pages_per_search=1,
        satisfaction_enabled=False  # Disable to isolate the issue
    )
    
    result = debug_conduct("test query", config)
    
    print(f"\n=== FINAL RESULT ===")
    print(f"Total searches: {result.search_count}")
    print(f"Total rounds: {result.round_count}")
    
    # Diagnose the issue
    print(f"\n=== DIAGNOSIS ===")
    if result.search_count <= 3 and config.max_searches > 3:
        print("PROBLEM: System stopped after first round")
        print(f"Expected up to {config.max_searches} searches")
        print(f"Got only {result.search_count} searches")
    else:
        print("System iterated correctly")

if __name__ == "__main__":
    debug_loop()