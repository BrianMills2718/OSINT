#!/usr/bin/env python3

"""
Test script to trace the complete pipeline from API results to DataPoints
to identify where the 121 results are being lost
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'twitterexplorer'))

from investigation_engine import InvestigationEngine, InvestigationConfig
from unittest.mock import Mock, patch

def test_complete_pipeline():
    """Test the complete pipeline step by step"""
    
    print("TRACING COMPLETE PIPELINE: 121 Results -> 0 DataPoints")
    print("=" * 60)
    
    # Create investigation engine
    try:
        engine = InvestigationEngine("test_key")
        print("1. Investigation engine created successfully")
        print(f"   - Graph mode: {getattr(engine, 'graph_mode', 'Unknown')}")
        print(f"   - Finding evaluator: {'Present' if hasattr(engine, 'finding_evaluator') else 'Missing'}")
        print()
    except Exception as e:
        print(f"FAILED to create investigation engine: {e}")
        return
    
    # Mock API results similar to the 121 from the real investigation
    mock_search_results = []
    
    # Create 121 mock results like climate change investigation
    for i in range(121):
        if i < 60:
            source_type = "climate_debate"
        elif i < 120:
            source_type = "ipcc_timeline"  
        else:
            source_type = "industry_response"
            
        mock_search_results.append({
            "text": f"Climate change policy {source_type} discussion {i}: Various perspectives on environmental regulations and economic impacts",
            "username": f"user{i}",
            "source": "twitter_api",
            "id": f"tweet_{i}"
        })
    
    print(f"2. Created {len(mock_search_results)} mock results (matching real 121)")
    
    # Mock the API client to return our results
    with patch.object(engine, '_execute_search') as mock_execute:
        
        # Configure mock to return our results with _raw_results properly set
        def mock_search_execution(search_plan, search_id, round_number):
            from investigation_engine import SearchAttempt
            attempt = SearchAttempt(
                search_id=search_id,
                round_number=round_number,
                endpoint=search_plan['endpoint'],
                params=search_plan['params'],
                query_description="Mock search",
                results_count=len(mock_search_results),
                effectiveness_score=7.0,
                execution_time=1.0
            )
            
            # CRITICAL: Set _raw_results like the real code does
            attempt._raw_results = mock_search_results
            
            print(f"3. Mock search executed - {attempt.results_count} results")
            print(f"   - _raw_results set: {'Yes' if hasattr(attempt, '_raw_results') else 'No'}")
            print(f"   - _raw_results length: {len(attempt._raw_results) if hasattr(attempt, '_raw_results') else 0}")
            
            return attempt
        
        mock_execute.side_effect = mock_search_execution
        
        # Run investigation with minimal config
        try:
            print("4. Starting investigation...")
            result = engine.conduct_investigation(
                "What are different perspectives on climate change policies",
                InvestigationConfig(max_searches=1)  # Just one search to trace
            )
            
            print("5. Investigation completed - analyzing results...")
            print(f"   - Search count: {result.search_count}")
            print(f"   - Total results found: {result.total_results_found}")
            print(f"   - Accumulated findings: {len(result.accumulated_findings)}")
            
            # Check graph state if graph mode
            if hasattr(engine, 'graph_mode') and engine.graph_mode:
                if hasattr(engine, 'llm_coordinator') and hasattr(engine.llm_coordinator, 'graph'):
                    graph = engine.llm_coordinator.graph
                    datapoints = graph.get_nodes_by_type("DataPoint") if hasattr(graph, 'get_nodes_by_type') else []
                    insights = graph.get_nodes_by_type("Insight") if hasattr(graph, 'get_nodes_by_type') else []
                    
                    print(f"   - DataPoint nodes: {len(datapoints)}")
                    print(f"   - Insight nodes: {len(insights)}")
                    
                    if len(datapoints) == 0:
                        print()
                        print("CRITICAL FAILURE IDENTIFIED:")
                        print("- 121 API results processed")
                        print("- 0 DataPoint nodes created")  
                        print("- This confirms the pipeline breakdown")
                        
                        # Try to trace where the failure occurs
                        print()
                        print("TRACING FAILURE POINT:")
                        
                        # Check if finding evaluator is working
                        try:
                            test_results = mock_search_results[:3]
                            assessments = engine.finding_evaluator.evaluate_batch(
                                test_results, 
                                "What are different perspectives on climate change policies"
                            )
                            print(f"- Finding evaluator works: {len(assessments)} assessments generated")
                            
                            significant_count = sum(1 for a in assessments if a.is_significant)
                            print(f"- Significant findings: {significant_count}/{len(assessments)}")
                            
                            if significant_count == 0:
                                print("FOUND ISSUE: All findings marked as NOT significant!")
                                for i, assessment in enumerate(assessments):
                                    print(f"  Result {i}: significant={assessment.is_significant}, score={assessment.relevance_score:.2f}")
                                    print(f"             reasoning: {assessment.reasoning}")
                            
                        except Exception as e:
                            print(f"- Finding evaluator FAILED: {e}")
                            print("THIS IS THE ROOT CAUSE")
                
            else:
                print("   - Not in graph mode - no DataPoint analysis available")
                
        except Exception as e:
            print(f"FAILED during investigation: {e}")
            import traceback
            traceback.print_exc()
        
    print()
    print("PIPELINE ANALYSIS COMPLETE")

if __name__ == "__main__":
    test_complete_pipeline()