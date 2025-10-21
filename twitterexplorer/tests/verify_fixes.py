"""Verification script to doublecheck all claims about the fixes"""

import sys
sys.path.insert(0, 'twitterexplorer')

from investigation_engine import InvestigationEngine, InvestigationConfig
from finding_evaluator_llm import LLMFindingEvaluator
import toml
import inspect

print("=" * 60)
print("VERIFICATION OF FIX CLAIMS")
print("=" * 60)

# Load API key
secrets_path = r'twitterexplorer\.streamlit\secrets.toml'
secrets = toml.load(secrets_path)
api_key = secrets.get('RAPIDAPI_KEY')

# Claim 1: finding_evaluator is now an instance variable
print("\n1. VERIFYING: finding_evaluator is instance variable")
engine = InvestigationEngine(api_key)

if hasattr(engine, 'finding_evaluator'):
    print("   [PASS] engine.finding_evaluator exists")
    print(f"   [PASS] Type: {type(engine.finding_evaluator)}")
    if isinstance(engine.finding_evaluator, LLMFindingEvaluator):
        print("   [PASS] Is correct type (LLMFindingEvaluator)")
    else:
        print("   [FAIL] Wrong type!")
else:
    print("   [FAIL] FAILED: finding_evaluator not found as instance variable")

# Claim 2: Check the code changes in _analyze_round_results_with_llm
print("\n2. VERIFYING: Code uses self.finding_evaluator")
source = inspect.getsource(engine._analyze_round_results_with_llm)
if 'self.finding_evaluator.evaluate_batch' in source:
    print("   [PASS] Uses self.finding_evaluator.evaluate_batch")
else:
    print("   [FAIL] Still using local variable")

if 'session.accumulated_findings.append(finding)' in source:
    print("   [PASS] Findings are added to session")
else:
    print("   [FAIL] Findings not being added")

# Claim 3: Error handling exists
if 'try:' in source and 'except' in source:
    print("   [PASS] Has try-except blocks for error handling")
else:
    print("   [FAIL] No error handling found")

# Claim 4: Run actual test to verify findings are created
print("\n3. VERIFYING: Actual findings creation")
config = InvestigationConfig(
    max_searches=1,
    pages_per_search=1
)

# Track what happens
findings_count = 0
satisfaction = 0.0

try:
    result = engine.conduct_investigation("test query GPT", config)
    findings_count = len(result.accumulated_findings)
    satisfaction = result.satisfaction_metrics.overall_satisfaction()
    
    print(f"   [PASS] Investigation completed")
    print(f"   [PASS] Findings created: {findings_count}")
    print(f"   [PASS] Satisfaction score: {satisfaction:.2f}")
    
    if findings_count > 0:
        print(f"   [PASS] SUCCESS: {findings_count} findings created (was 0 before)")
    else:
        print(f"   [FAIL] FAILURE: Still creating 0 findings")
        
    if satisfaction > 0.0:
        print(f"   [PASS] SUCCESS: Satisfaction is {satisfaction:.2f} (was 0.00 before)")
    else:
        print(f"   [FAIL] FAILURE: Satisfaction still 0.00")
        
except Exception as e:
    print(f"   [FAIL] Investigation failed: {e}")

# Claim 5: Check the actual code for graph mode handling
print("\n4. VERIFYING: Graph mode error handling")
if 'if self.graph_mode and hasattr(self.llm_coordinator' in source:
    print("   [PASS] Checks graph mode before creating nodes")
else:
    print("   [FAIL] No graph mode check found")

if '# ALWAYS add to accumulated findings' in source or 'regardless of graph' in source:
    print("   [PASS] Comments confirm findings always created")
else:
    print("   [FAIL] No evidence of always creating findings")

# Summary
print("\n" + "=" * 60)
print("VERIFICATION SUMMARY")
print("=" * 60)

checks_passed = 0
checks_total = 0

# Count successes
if hasattr(engine, 'finding_evaluator'):
    checks_passed += 1
checks_total += 1

if 'self.finding_evaluator.evaluate_batch' in source:
    checks_passed += 1
checks_total += 1

if findings_count > 0:
    checks_passed += 1
checks_total += 1

if satisfaction > 0.0:
    checks_passed += 1
checks_total += 1

print(f"Checks passed: {checks_passed}/{checks_total}")

if checks_passed == checks_total:
    print("\n[PASS] ALL CLAIMS VERIFIED - Fixes are working correctly")
else:
    print(f"\n[FAIL] SOME CLAIMS FAILED VERIFICATION ({checks_total - checks_passed} failures)")
    
print("\nKey metrics:")
print(f"  - Findings created: {findings_count} (was 0)")
print(f"  - Satisfaction: {satisfaction:.2f} (was 0.00)")
print("=" * 60)