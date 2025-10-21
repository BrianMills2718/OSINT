"""Debug the complete finding creation flow with detailed output"""

import sys
sys.path.insert(0, 'twitterexplorer')

from investigation_engine import InvestigationEngine, InvestigationConfig
import toml

# Load API key
secrets_path = r'twitterexplorer\.streamlit\secrets.toml'
secrets = toml.load(secrets_path)
api_key = secrets.get('RAPIDAPI_KEY')

print("=" * 60)
print("DEBUGGING COMPLETE FINDING FLOW")
print("=" * 60)

# Create simple config - just 1 search
config = InvestigationConfig(
    max_searches=1,
    pages_per_search=1
)

# Create engine
engine = InvestigationEngine(api_key)

# Check components
print(f"\n1. Graph mode: {engine.graph_mode}")
print(f"2. Has finding_evaluator: {hasattr(engine, 'finding_evaluator')}")
print(f"3. Has llm_coordinator: {hasattr(engine, 'llm_coordinator')}")
if hasattr(engine.llm_coordinator, 'graph'):
    print(f"4. LLM coordinator has graph: True")
else:
    print(f"4. LLM coordinator has graph: False")

# Patch to debug the finding creation section
original_analyze = engine._analyze_round_results_with_llm
def debug_analyze(session, current_round, results):
    print(f"\n[DEBUG] _analyze_round_results_with_llm called with {len(results)} results")
    
    for i, attempt in enumerate(results):
        print(f"\n[DEBUG] Processing attempt {i+1}:")
        print(f"  Endpoint: {attempt.endpoint}")
        print(f"  Results count: {attempt.results_count}")
        print(f"  Has _raw_results: {hasattr(attempt, '_raw_results')}")
        
        if hasattr(attempt, '_raw_results') and attempt._raw_results:
            print(f"  Raw results count: {len(attempt._raw_results)}")
            
            # Check what happens in the evaluation
            if engine.finding_evaluator:
                print(f"  Calling finding_evaluator.evaluate_batch...")
                assessments = engine.finding_evaluator.evaluate_batch(
                    attempt._raw_results[:5],  # Just test with 5
                    session.original_query
                )
                print(f"  Got {len(assessments)} assessments")
                significant = sum(1 for a in assessments if a.is_significant)
                print(f"  Significant: {significant}/{len(assessments)}")
                
                # Check if findings would be created
                if significant > 0:
                    print(f"  [SHOULD CREATE {significant} FINDINGS]")
                    
                    # Check graph mode issues
                    print(f"  Graph mode: {engine.graph_mode}")
                    print(f"  Has graph: {hasattr(engine.llm_coordinator, 'graph')}")
                    
                    # Try to create a finding manually
                    for j, (result, assessment) in enumerate(zip(attempt._raw_results[:5], assessments)):
                        if assessment.is_significant:
                            print(f"\n  Creating finding {j+1}:")
                            print(f"    Text: {result.get('text', '')[:50]}...")
                            print(f"    Relevance: {assessment.relevance_score}")
                            
                            # Check if graph creation would fail
                            if engine.graph_mode and hasattr(engine.llm_coordinator, 'graph'):
                                try:
                                    print("    Attempting graph node creation...")
                                    # This is where it might fail
                                    dp = engine.llm_coordinator.graph.create_datapoint_node(
                                        content=result.get('text', ''),
                                        source=attempt.endpoint,
                                        timestamp="test",
                                        entities=assessment.entities,
                                        follow_up_needed=assessment.suggested_followup
                                    )
                                    print("    [SUCCESS] Graph node created")
                                except Exception as e:
                                    print(f"    [ERROR] Graph node creation failed: {e}")
    
    # Call original
    return original_analyze(session, current_round, results)

engine._analyze_round_results_with_llm = debug_analyze

# Run investigation
print("\n" + "=" * 60)
print("RUNNING TEST INVESTIGATION")
print("=" * 60)

result = engine.conduct_investigation("AI technology news", config)

print("\n" + "=" * 60)
print("FINAL RESULTS")
print("=" * 60)
print(f"Findings created: {len(result.accumulated_findings)}")

if len(result.accumulated_findings) > 0:
    print("\nSUCCESS! Findings were created:")
    for i, finding in enumerate(result.accumulated_findings[:3], 1):
        print(f"  {i}. {finding.content[:80]}...")
else:
    print("\nFAILURE! No findings created despite significant results")