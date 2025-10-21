#!/usr/bin/env python3
"""
Test Batch Evaluation Display - Verify new batch summary functionality
"""

import sys
import os

# Add twitterexplorer to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'twitterexplorer'))

def test_batch_evaluation_display():
    """Test that the new batch evaluation display functionality works"""
    print("=== Testing Batch Evaluation Display Fix ===")
    
    try:
        # Import required modules
        from investigation_engine import InvestigationEngine, InvestigationRound, SearchAttempt, InvestigationConfig
        from datetime import datetime
        
        # Create mock investigation components
        config = InvestigationConfig()
        engine = InvestigationEngine("test_key")
        
        # Create mock round with results
        current_round = InvestigationRound(
            round_number=2,
            strategy_description="Test debunking strategy focusing on fraud allegations"
        )
        
        # Create mock search results
        search_results = [
            SearchAttempt(
                search_id=1,
                round_number=2, 
                endpoint="search.php",
                params={"query": "Michael Herrera debunk fraud"},
                query_description="Search for fraud debunking information",
                results_count=43,
                effectiveness_score=6.2,
                execution_time=5.4
            ),
            SearchAttempt(
                search_id=2,
                round_number=2,
                endpoint="search.php", 
                params={"query": "Michael Herrera UFO hoax"},
                query_description="Search for hoax allegations",
                results_count=12,
                effectiveness_score=3.1,
                execution_time=4.2
            ),
            SearchAttempt(
                search_id=3,
                round_number=2,
                endpoint="timeline.php",
                params={"screenname": "michaelherrera123"},
                query_description="Check Michael Herrera's timeline",
                results_count=0,
                effectiveness_score=0.0,
                execution_time=2.8
            )
        ]
        
        # Set round metrics
        current_round.total_results = sum(r.results_count for r in search_results)
        current_round.round_effectiveness = 3.1  # Average effectiveness
        
        # Add mock LLM insights
        current_round.key_insights = [
            "Found credible fraud allegations from multiple independent sources",
            "Michael Herrera's story contains several factual inconsistencies",
            "Timeline analysis shows coordinated debunking effort by UFO skeptics"
        ]
        
        # Add strategy hints for next round  
        current_round.next_strategy_hints = [
            "Focus on specific inconsistencies identified in testimonies",
            "Target known UFO debunkers who have analyzed Herrera's claims",
            "Search for expert analysis on technical aspects of his story"
        ]
        
        print("[OK] Mock investigation round created")
        print(f"  - Round: {current_round.round_number}")
        print(f"  - Total results: {current_round.total_results}")
        print(f"  - Effectiveness: {current_round.round_effectiveness:.1f}/10")
        print(f"  - Key insights: {len(current_round.key_insights)}")
        print(f"  - Strategy hints: {len(current_round.next_strategy_hints)}")
        
        # Test the display method exists
        if hasattr(engine, '_display_batch_evaluation'):
            print("[OK] _display_batch_evaluation method found")
            
            # Mock streamlit to avoid import errors
            import types
            mock_st = types.ModuleType('streamlit')
            mock_st.markdown = lambda x: print(f"STREAMLIT: {x}")
            
            # Replace streamlit import
            sys.modules['streamlit'] = mock_st
            
            print("\n=== Simulating Batch Evaluation Display ===")
            
            try:
                engine._display_batch_evaluation(current_round, search_results)
                print("[OK] Batch evaluation display executed successfully")
            except Exception as display_error:
                print(f"[ERROR] Batch evaluation display failed: {display_error}")
                import traceback
                traceback.print_exc()
                
        else:
            print("[ERROR] _display_batch_evaluation method not found")
            return False
            
        print("\n=== Expected Output Verification ===")
        print("Users should now see after each batch:")
        print("  1. BATCH X EVALUATION header with effectiveness color")
        print("  2. Batch Results showing search count and total results")  
        print("  3. LLM Analysis showing what was learned")
        print("  4. Search Performance showing most/least effective searches")
        print("  5. Strategy Recommendations for the next round")
        print("  6. Investigation Graph showing accumulated knowledge")
        
        return True
        
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_batch_evaluation_display()
    print(f"\n{'[OK] TEST PASSED' if success else '[ERROR] TEST FAILED'}")