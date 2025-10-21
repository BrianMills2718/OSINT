import pytest
from pydantic import ValidationError
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_pydantic_models():
    """Test that Pydantic models validate correctly"""
    from v2.models import Finding, StrategyOutput, EndpointPlan
    
    # Test valid Finding
    finding = Finding(
        content="Trump mentioned Epstein",
        relevance_score=8.5,
        reasoning="Direct mention of investigation target"
    )
    assert finding.relevance_score == 8.5
    
    # Test invalid score (>10)
    with pytest.raises(ValidationError):
        Finding(content="test", relevance_score=11.0, reasoning="test")
    
    # Test valid strategy
    strategy = StrategyOutput(
        reasoning="Search for recent mentions",
        endpoints=[
            EndpointPlan(
                endpoint="search.php",
                params={"query": "Trump Epstein"},
                expected_value="Recent tweets"
            )
        ],
        user_update="Searching for Trump-Epstein mentions"
    )
    assert len(strategy.endpoints) == 1
    assert strategy.confidence == 0.7  # Default value

def test_litellm_structured_generation():
    """Test actual LLM generation with structured output"""
    from v2.llm_client import LLMClient
    from v2.models import StrategyOutput
    
    client = LLMClient(model="gemini/gemini-2.0-flash-exp")
    
    # Test with real prompt
    prompt = """Generate a Twitter search strategy for investigating recent AI developments.
    Return a JSON with: reasoning (string), endpoints (array of endpoint plans), 
    user_update (string), confidence (float 0-1)."""
    
    output = client.generate(prompt, StrategyOutput)
    
    # Validate structure
    assert isinstance(output, StrategyOutput)
    assert len(output.endpoints) >= 1
    assert output.user_update
    assert 0 <= output.confidence <= 1

def test_backward_compatibility():
    """Ensure new models work with existing dict-based code"""
    from v2.models import StrategyOutput, EndpointPlan
    
    # Existing code expects dicts
    strategy = StrategyOutput(
        reasoning="test",
        endpoints=[EndpointPlan(
            endpoint="search.php", 
            params={"q": "test"}, 
            expected_value="test"
        )],
        user_update="testing"
    )
    
    # Should convert to dict seamlessly
    strategy_dict = strategy.model_dump()
    assert strategy_dict["reasoning"] == "test"
    assert isinstance(strategy_dict["endpoints"], list)