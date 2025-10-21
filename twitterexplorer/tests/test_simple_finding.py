"""Simple test to verify finding creation works"""

import sys
sys.path.insert(0, 'twitterexplorer')

from investigation_engine import InvestigationEngine, InvestigationConfig
from finding_evaluator_llm import LLMFindingEvaluator
from llm_client import get_litellm_client
import toml

# Load API key
secrets_path = r'twitterexplorer\.streamlit\secrets.toml'
secrets = toml.load(secrets_path)
api_key = secrets.get('RAPIDAPI_KEY')

print("=" * 60)
print("TESTING SIMPLE FINDING CREATION")
print("=" * 60)

# Test 1: Can we create a finding evaluator?
print("\n1. Testing Finding Evaluator...")
try:
    llm_client = get_litellm_client()
    evaluator = LLMFindingEvaluator(llm_client)
    print("   [OK] Finding evaluator created")
except Exception as e:
    print(f"   [FAIL] {e}")
    exit(1)

# Test 2: Can we evaluate a sample result?
print("\n2. Testing sample evaluation...")
sample_result = {
    'text': 'OpenAI announces GPT-5 with breakthrough reasoning capabilities',
    'source': 'test'
}
try:
    assessment = evaluator.evaluate_finding(sample_result, "OpenAI GPT news")
    print(f"   [OK] Evaluation completed")
    print(f"   Is significant: {assessment.is_significant}")
    print(f"   Relevance: {assessment.relevance_score}")
except Exception as e:
    print(f"   [FAIL] {e}")

# Test 3: Run minimal investigation
print("\n3. Testing minimal investigation...")
config = InvestigationConfig(
    max_searches=1,
    pages_per_search=1
)

engine = InvestigationEngine(api_key)

# Monkey patch to see what's happening with findings
original_analyze = engine._analyze_round_results_with_llm
findings_created = []

def track_findings(session, current_round, results):
    before_count = len(session.accumulated_findings)
    print(f"   Findings before: {before_count}")
    
    try:
        result = original_analyze(session, current_round, results)
    except Exception as e:
        print(f"   [ERROR in analyze]: {e}")
        result = None
    
    after_count = len(session.accumulated_findings)
    print(f"   Findings after: {after_count}")
    print(f"   New findings created: {after_count - before_count}")
    
    if after_count > before_count:
        for f in session.accumulated_findings[before_count:]:
            findings_created.append(f)
            print(f"   New finding: {f.content[:60]}...")
    
    return result

engine._analyze_round_results_with_llm = track_findings

# Run investigation
result = engine.conduct_investigation("OpenAI GPT", config)

print("\n" + "=" * 60)
print("FINAL RESULTS")
print("=" * 60)
print(f"Total searches: {len(result.search_history)}")
print(f"Total results retrieved: {sum(s.results_count for s in result.search_history)}")
print(f"Findings in result: {len(result.accumulated_findings)}")
print(f"Findings tracked: {len(findings_created)}")
print(f"Satisfaction: {result.satisfaction_metrics.overall_satisfaction():.2f}")

if len(result.accumulated_findings) > 0:
    print("\n[SUCCESS] Findings are being created!")
    for i, f in enumerate(result.accumulated_findings[:3], 1):
        print(f"  {i}. {f.content[:60]}...")
else:
    print("\n[FAILURE] No findings created")
    print("\nDebug info:")
    print(f"  Graph mode: {engine.graph_mode}")
    print(f"  Has finding evaluator: {hasattr(engine, 'finding_evaluator')}")
    print(f"  Has LLM coordinator: {hasattr(engine, 'llm_coordinator')}")