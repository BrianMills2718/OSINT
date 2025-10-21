"""Test temporal timeline generation functionality"""
import sys
import os

# Add the twitterexplorer subdirectory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
twitterexplorer_path = os.path.join(current_dir, 'twitterexplorer')
sys.path.insert(0, twitterexplorer_path)

from investigation_engine import InvestigationEngine, InvestigationConfig

def test_temporal_timeline_generation():
    """EVIDENCE: Test chronological analysis of investigation results"""
    
    print("=== TEMPORAL TIMELINE GENERATION TEST ===")
    
    api_key = "d72bcd77e2msh76c7e6cf37f0b89p1c51bcjsnaad0f6b01e4f"
    engine = InvestigationEngine(api_key)
    
    # Run investigation that should generate temporal timeline
    config = InvestigationConfig(max_searches=2, pages_per_search=2)
    result = engine.conduct_investigation("Recent developments in Tesla AI and autopilot", config)
    
    print(f"\\nGenerated {len(result.accumulated_findings)} findings for timeline analysis")
    
    # Test temporal timeline analysis
    if hasattr(result, 'temporal_timeline'):
        timeline = result.temporal_timeline
        if timeline is None:
            print("FAIL: temporal_timeline attribute is None")
            print(f"Debug: findings count = {len(result.accumulated_findings)}")
            return False
        else:
            print(f"Timeline events found: {len(timeline.events)}")
            print(f"Timeline spans: {timeline.start_date} to {timeline.end_date}")
            print(f"Temporal consistency: {timeline.consistency_score:.2f}")
            
            # Show timeline events
            if timeline.events:
                print("\\nTimeline events (chronological order):")
                for i, event in enumerate(timeline.events[:5]):  # Show first 5 events
                    # Handle Unicode characters safely
                    try:
                        description = event.description[:100].encode('ascii', 'ignore').decode('ascii')
                        print(f"  {i+1}. {event.timestamp}: {description}...")
                        print(f"     Significance: {event.significance_score:.2f}")
                    except:
                        print(f"  {i+1}. {event.timestamp}: [content with special characters]")
                        print(f"     Significance: {event.significance_score:.2f}")
            
            # Evidence requirements:
            assert len(timeline.events) > 0, "Should have at least one timeline event"
            assert hasattr(timeline, 'consistency_score'), "Should have temporal consistency scoring"
            assert hasattr(timeline, 'start_date'), "Should have timeline start date"
            assert hasattr(timeline, 'end_date'), "Should have timeline end date"
            
            return True
    else:
        print("FAIL: No temporal_timeline attribute found")
        return False

if __name__ == "__main__":
    success = test_temporal_timeline_generation()
    print(f"\\nTEMPORAL TIMELINE ANALYSIS: {'PASS' if success else 'FAIL'}")