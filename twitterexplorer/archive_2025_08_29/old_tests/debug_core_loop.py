"""Deep investigation of why the system stops after one round"""
import sys
import os
import json

current_dir = os.path.dirname(os.path.abspath(__file__))
twitterexplorer_path = os.path.join(current_dir, 'twitterexplorer')
sys.path.insert(0, twitterexplorer_path)

from investigation_engine import InvestigationEngine, InvestigationConfig
from datetime import datetime

def investigate_core_loop():
    """Instrument the core loop to understand exactly what's happening"""
    
    print("=== INVESTIGATING CORE LOOP BEHAVIOR ===\n")
    
    api_key = "d72bcd77e2msh76c7e6cf37f0b89p1c51bcjsnaad0f6b01e4f"
    engine = InvestigationEngine(api_key)
    
    # Create detailed trace
    trace = {
        'should_continue_calls': [],
        'rounds': [],
        'searches': [],
        'termination': None
    }
    
    # Hook the conduct_investigation method to trace the while loop
    original_conduct = engine.conduct_investigation
    
    def traced_conduct(query, config=None):
        """Trace the investigation execution"""
        print(f"Starting investigation with config:")
        print(f"  max_searches: {config.max_searches if config else 'default'}")
        print(f"  satisfaction_enabled: {config.satisfaction_enabled if config else 'default'}")
        print(f"  satisfaction_threshold: {config.satisfaction_threshold if config else 'default'}")
        print(f"  min_searches_before_satisfaction: {config.min_searches_before_satisfaction if config else 'default'}")
        
        # Call original and return
        return original_conduct(query, config)
    
    # Hook into session to trace should_continue
    original_create = engine._create_session
    
    def create_with_tracing(query, config):
        """Create session with tracing"""
        session = original_create(query, config)
        
        # Wrap should_continue
        original_should = session.should_continue
        call_count = [0]
        
        def traced_should_continue():
            call_count[0] += 1
            result, reason = original_should()
            
            trace_entry = {
                'call': call_count[0],
                'search_count': session.search_count,
                'round_count': session.round_count,
                'max_searches': session.config.max_searches,
                'elapsed_minutes': (datetime.now() - session.start_time).seconds / 60,
                'satisfaction': session.satisfaction_metrics.overall_satisfaction() if hasattr(session, 'satisfaction_metrics') else 0,
                'result': result,
                'reason': reason
            }
            
            trace['should_continue_calls'].append(trace_entry)
            
            print(f"\n[Call {call_count[0]}] should_continue():")
            print(f"  Searches so far: {session.search_count}/{session.config.max_searches}")
            print(f"  Rounds so far: {session.round_count}")
            print(f"  Decision: {'CONTINUE' if result else 'STOP'}")
            print(f"  Reason: {reason}")
            
            if not result:
                trace['termination'] = {
                    'after_searches': session.search_count,
                    'after_rounds': session.round_count,
                    'reason': reason
                }
            
            return result, reason
        
        session.should_continue = traced_should_continue
        return session
    
    engine._create_session = create_with_tracing
    engine.conduct_investigation = traced_conduct
    
    # Also trace strategy generation
    original_generate = engine._generate_strategy
    
    def traced_generate(session):
        """Trace strategy generation"""
        result = original_generate(session)
        searches_planned = len(result.get('searches', []))
        
        print(f"\n[Round {session.round_count + 1}] Strategy generated:")
        print(f"  Searches planned: {searches_planned}")
        print(f"  Current search count: {session.search_count}")
        print(f"  After this round: {session.search_count + searches_planned}")
        
        trace['rounds'].append({
            'round': session.round_count + 1,
            'searches_planned': searches_planned,
            'search_count_before': session.search_count,
            'search_count_after': session.search_count + searches_planned
        })
        
        return result
    
    engine._generate_strategy = traced_generate
    
    # Run investigation with config that SHOULD allow multiple rounds
    config = InvestigationConfig(
        max_searches=12,  # Should allow 4 rounds of 3 searches
        pages_per_search=1,
        satisfaction_enabled=False,  # Disable satisfaction to isolate the issue
        max_time_minutes=10
    )
    
    print(f"Configuration: max_searches={config.max_searches}, satisfaction_enabled={config.satisfaction_enabled}\n")
    print("="*60 + "\n")
    
    result = engine.conduct_investigation(
        "simple test query",
        config
    )
    
    # Analyze the trace
    print("\n" + "="*60)
    print("TRACE ANALYSIS")
    print("="*60)
    
    print(f"\nTotal should_continue() calls: {len(trace['should_continue_calls'])}")
    print(f"Total rounds executed: {len(trace['rounds'])}")
    print(f"Total searches executed: {result.search_count}")
    
    if trace['termination']:
        print(f"\nTermination:")
        print(f"  After {trace['termination']['after_searches']} searches")
        print(f"  After {trace['termination']['after_rounds']} rounds")
        print(f"  Reason: {trace['termination']['reason']}")
    
    # Identify the problem
    print("\n" + "="*60)
    print("PROBLEM IDENTIFICATION")
    print("="*60)
    
    if len(trace['rounds']) == 1 and config.max_searches > 3:
        print("\n❌ PROBLEM CONFIRMED: System stops after first round")
        print(f"   Config allowed {config.max_searches} searches")
        print(f"   But only {result.search_count} were executed")
        
        # Check if it's a counting issue
        if trace['rounds']:
            first_round = trace['rounds'][0]
            if first_round['search_count_after'] >= config.max_searches:
                print("\n   ROOT CAUSE: Search count incremented BEFORE execution")
                print(f"   After planning: {first_round['search_count_after']}")
                print(f"   This triggers early termination")
        
        # Check the should_continue calls
        stop_calls = [c for c in trace['should_continue_calls'] if not c['result']]
        if stop_calls:
            first_stop = stop_calls[0]
            print(f"\n   First STOP at call {first_stop['call']}:")
            print(f"   Search count: {first_stop['search_count']}")
            print(f"   Max searches: {first_stop['max_searches']}")
            print(f"   Reason: {first_stop['reason']}")
    else:
        print("\n✓ System appears to be iterating correctly")
    
    return trace

if __name__ == "__main__":
    try:
        trace = investigate_core_loop()
        
        # Save trace for analysis
        with open('investigation_trace.json', 'w') as f:
            json.dump(trace, f, indent=2, default=str)
        print("\nTrace saved to investigation_trace.json")
        
    except Exception as e:
        print(f"\n❌ Investigation failed: {e}")
        import traceback
        traceback.print_exc()