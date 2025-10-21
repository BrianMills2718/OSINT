from llm_client import LLMClient
from models import StrategyOutput, EndpointPlan

class IntelligentStrategyLiteLLM:
    """Strategy generator using LiteLLM structured output"""
    
    def __init__(self):
        self.llm_client = LLMClient()
    
    def generate_strategy(self, investigation_goal, current_understanding, 
                         information_gaps, search_history, max_endpoints_per_round=3):
        """Generate strategy with structured output"""
        
        # Build prompt (reuse existing prompt logic)
        prompt = f"""You are an expert Twitter investigation strategist.
        
Investigation Goal: {investigation_goal}
Current Understanding: {current_understanding}
Information Gaps: {', '.join(information_gaps)}
Search History: {search_history[-5:] if search_history else 'None'}

Generate a search strategy with:
1. Clear reasoning about next steps
2. 1-{max_endpoints_per_round} specific endpoint plans
3. Evaluation criteria for results
4. User-friendly progress update
5. Confidence score (0-1)

Focus on addressing the biggest information gaps.

For each endpoint plan, include:
- endpoint: One of [search.php, timeline.php, screenname.php, trends.php, following.php, followers.php, tweet.php, usermedia.php, retweets.php, tweet_thread.php, latest_replies.php, checkfollow.php, checkretweet.php, listtimeline.php, screennames.php, community_timeline.php, list_followers.php, list_members.php, spaces.php, affilates.php]
- query: For search.php - the search query
- screenname: For timeline.php/screenname.php - the username
- tweet_id: For tweet.php - the tweet ID
- filter_type: Optional filter (e.g., "recent", "popular")
- count: Number of results (default 50)
- expected_value: What you expect to find
- reason: Why this endpoint (optional)"""
        
        # Generate with structured output
        output = self.llm_client.generate(prompt, StrategyOutput)
        
        # Convert flattened endpoints back to params dict for compatibility
        result = output.model_dump()
        for endpoint in result['endpoints']:
            # Convert flattened fields to params dict
            endpoint['params'] = {}
            if endpoint.get('query'):
                endpoint['params']['query'] = endpoint.pop('query')
            if endpoint.get('screenname'):
                endpoint['params']['screenname'] = endpoint.pop('screenname')
            if endpoint.get('tweet_id'):
                endpoint['params']['tweet_id'] = endpoint.pop('tweet_id')
            if endpoint.get('filter_type'):
                endpoint['params']['filter'] = endpoint.pop('filter_type')
            if endpoint.get('count') and endpoint['count'] != 50:
                endpoint['params']['count'] = str(endpoint.pop('count'))
            else:
                endpoint.pop('count', None)
        
        return result