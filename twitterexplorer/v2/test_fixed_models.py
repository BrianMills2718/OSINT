"""Test that fixed models work with Gemini structured output"""

import os
import json
from litellm import completion
import toml

# Load API key
secrets_path = r'C:\Users\Brian\projects\twitterexplorer\twitterexplorer\.streamlit\secrets.toml'
try:
    secrets = toml.load(secrets_path)
    os.environ['GEMINI_API_KEY'] = secrets.get('GEMINI_API_KEY', '')
except:
    pass

def test_fixed_endpoint_plan():
    """Test the flattened EndpointPlan"""
    from models_fixed import EndpointPlan
    
    try:
        response = completion(
            model="gemini/gemini-2.0-flash-exp",
            messages=[{"role": "user", "content": "Generate an endpoint plan for searching 'AI news' on search.php"}],
            response_format=EndpointPlan
        )
        
        content = response.choices[0].message.content
        if isinstance(content, str):
            data = json.loads(content)
            plan = EndpointPlan(**data)
        else:
            plan = EndpointPlan(**content) if isinstance(content, dict) else content
            
        print(f"[PASS] EndpointPlan works!")
        print(f"  Endpoint: {plan.endpoint}")
        print(f"  Query: {plan.query}")
        print(f"  Params dict: {plan.to_params_dict()}")
        return True
    except Exception as e:
        print(f"[FAIL] EndpointPlan failed: {e}")
        return False

def test_fixed_strategy_output():
    """Test the complete StrategyOutput with flattened structure"""
    from models_fixed import StrategyOutput, EndpointPlan, EvaluationCriteria
    
    prompt = """Generate a strategy for investigating 'Trump Epstein drama'.
    Return a StrategyOutput with:
    - reasoning: Your analysis
    - endpoints: List of EndpointPlan objects
    - evaluation_criteria: What to look for
    - user_update: Message for user
    - confidence: 0-1 score
    
    For endpoints, use fields:
    - endpoint: API endpoint name
    - query: Search query (for search.php)
    - screenname: Username (for timeline.php)
    - expected_value: What you hope to find
    """
    
    try:
        response = completion(
            model="gemini/gemini-2.0-flash-exp",
            messages=[{"role": "user", "content": prompt}],
            response_format=StrategyOutput
        )
        
        content = response.choices[0].message.content
        if isinstance(content, str):
            data = json.loads(content)
            strategy = StrategyOutput(**data)
        else:
            strategy = StrategyOutput(**content) if isinstance(content, dict) else content
            
        print(f"[PASS] StrategyOutput works with structured output!")
        print(f"  Reasoning: {strategy.reasoning[:100]}...")
        print(f"  Endpoints: {len(strategy.endpoints)}")
        for ep in strategy.endpoints:
            print(f"    - {ep.endpoint}: {ep.to_params_dict()}")
        print(f"  Confidence: {strategy.confidence}")
        return True
    except Exception as e:
        print(f"[FAIL] StrategyOutput failed: {e}")
        return False

def test_evaluation_output():
    """Test EvaluationOutput"""
    from models_fixed import EvaluationOutput, Finding
    
    try:
        response = completion(
            model="gemini/gemini-2.0-flash-exp",
            messages=[{"role": "user", "content": "Generate an evaluation with one finding about 'AI progress'"}],
            response_format=EvaluationOutput
        )
        
        content = response.choices[0].message.content
        if isinstance(content, str):
            data = json.loads(content)
            evaluation = EvaluationOutput(**data)
        else:
            evaluation = EvaluationOutput(**content) if isinstance(content, dict) else content
            
        print(f"[PASS] EvaluationOutput works!")
        print(f"  Findings: {len(evaluation.findings)}")
        print(f"  Relevance score: {evaluation.relevance_score}")
        return True
    except Exception as e:
        print(f"[FAIL] EvaluationOutput failed: {e}")
        return False

def run_all_tests():
    """Run all fixed model tests"""
    print("=" * 60)
    print("TESTING FIXED MODELS WITH STRUCTURED OUTPUT")
    print("=" * 60)
    
    results = {
        "EndpointPlan": test_fixed_endpoint_plan(),
        "StrategyOutput": test_fixed_strategy_output(),
        "EvaluationOutput": test_evaluation_output()
    }
    
    print("\n" + "=" * 60)
    print("RESULTS:")
    for name, passed in results.items():
        status = "[PASS]" if passed else "[FAIL]"
        print(f"{name:20} {status}")
    
    if all(results.values()):
        print("\n[SUCCESS] All models work with structured output!")
    else:
        print("\n[WARNING] Some models still have issues")
    print("=" * 60)
    
    return all(results.values())

if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)