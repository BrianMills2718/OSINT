from llm_client import LLMClient
from models import EvaluationOutput, Finding, RejectionFeedback
import json

class ResultEvaluatorLiteLLM:
    """Result evaluator using LiteLLM structured output"""
    
    def __init__(self):
        self.llm_client = LLMClient()
    
    def evaluate_results(self, investigation_goal, search_results, endpoint, 
                        query, current_understanding, evaluation_criteria=None):
        """Evaluate search results with structured output"""
        
        # Format results for evaluation
        results_text = json.dumps(search_results[:10], indent=2) if search_results else "No results"
        
        prompt = f"""You are an expert Twitter investigation analyst evaluating search results.

Investigation Goal: {investigation_goal}
Current Understanding: {current_understanding}
Search Endpoint: {endpoint}
Search Query: {query}
Number of Results: {len(search_results) if search_results else 0}

Results to Evaluate (first 10):
{results_text}

Evaluation Criteria: {evaluation_criteria if evaluation_criteria else 'General relevance to investigation goal'}

Analyze these results and provide:
1. findings: List of key findings (each with content, relevance_score 0-10, reasoning, source_endpoint)
2. relevance_score: Overall relevance score (0-10)
3. remaining_gaps: List of information gaps still to be addressed
4. rejection_feedback: Analysis of rejected/irrelevant results

For each finding:
- content: Clear, concise summary of the finding (max 500 chars)
- relevance_score: How relevant to the investigation (0-10)
- reasoning: Why this is relevant or important
- source_endpoint: The endpoint that provided this finding

Be honest about relevance. If results are completely off-topic (e.g., "find different ways to save money" for a Trump/Epstein investigation), score them 0-1, not 4-5."""
        
        # Generate with structured output
        output = self.llm_client.generate(prompt, EvaluationOutput)
        
        # Return as dict for compatibility
        result = output.model_dump()
        
        # Ensure rejection_feedback exists
        if not result.get('rejection_feedback'):
            result['rejection_feedback'] = {
                'rejection_rate': 0.0,
                'rejection_themes': [],
                'rejected_keywords': []
            }
        
        return result