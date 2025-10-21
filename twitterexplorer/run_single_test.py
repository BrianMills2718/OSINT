#!/usr/bin/env python3

import sys
import os

# Add the twitterexplorer module to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'twitterexplorer'))

from utils.llm_call_tracer import get_tracer

def test_bridge_integration():
    """Test the bridge integration frequency measurement"""
    tracer = get_tracer()
    tracer.reset()
    
    # Simulate 8 insights being created (typical search scenario)
    for i in range(8):
        # Each insight creation should trigger bridge notification
        tracer.log_trigger("insight_created", "investigation_bridge", "notify_insight_created")
        
        # Each bridge notification triggers emergent question detection on ALL insights
        # This creates quadratic growth: 1, 2, 3, 4, 5, 6, 7, 8 = 36 total LLM calls
        for j in range(i + 1):  # Process all insights so far
            tracer.log_trigger("insights_processed", "graph_aware_llm_coordinator", "detect_emergent_questions")
    
    analysis = tracer.analyze_patterns()
    print("Analysis keys:", list(analysis.keys()))
    
    if 'trigger_patterns' in analysis:
        bridge_triggers = analysis['trigger_patterns'].get('insight_created', [])
        emergent_calls = analysis['trigger_patterns'].get('insights_processed', [])
        
        print(f"Bridge triggers: {len(bridge_triggers)}")
        print(f"Emergent calls: {len(emergent_calls)}")
        print(f"Expected quadratic: {sum(range(1, 9))}")
        
        return {
            'bridge_triggers': len(bridge_triggers),
            'emergent_question_calls': len(emergent_calls),
            'expected_quadratic_calls': sum(range(1, 9)),  # 36 calls
            'quadratic_growth_confirmed': len(emergent_calls) == sum(range(1, 9))
        }
    else:
        print("No trigger_patterns in analysis")
        return None

if __name__ == "__main__":
    result = test_bridge_integration()
    print("Result:", result)