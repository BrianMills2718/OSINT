"""Fix for the zero results issue in investigation_engine.py

The problem: _execute_search only looks for results in data['timeline']
But the API returns data in various keys: timeline, followers, results, trends, users, etc.

This fix updates the result counting logic to handle all possible response formats.
"""

def extract_result_count_from_api_response(result: dict) -> int:
    """Extract result count from API response regardless of structure"""
    
    if 'error' in result:
        return 0
    
    data = result.get('data', {})
    
    if not data:
        return 0
    
    # List of all possible keys where results might be stored
    possible_keys = [
        'timeline', 'followers', 'following', 'users', 
        'trends', 'retweets', 'affilates', 'members', 
        'sharings', 'results', 'data'
    ]
    
    # Try to find results in any of these keys
    for key in possible_keys:
        if key in data and isinstance(data[key], list):
            return len(data[key])
    
    # Check if data itself is a list (direct list response)
    if isinstance(data, list):
        return len(data)
    
    # Check if it's a single item (wrapped as dict)
    if isinstance(data, dict) and data:
        # If it has any content, count as 1 result
        return 1
    
    return 0


def extract_results_for_evaluation(api_result: dict) -> list:
    """Extract results in a format suitable for LLM evaluation"""
    
    results = []
    
    try:
        data = api_result.get('data', {})
        
        if not data:
            return results
        
        # List of all possible keys where results might be stored
        possible_keys = [
            'timeline', 'followers', 'following', 'users', 
            'trends', 'retweets', 'affilates', 'members', 
            'sharings', 'results', 'data'
        ]
        
        # Try to extract from any key that contains a list
        for key in possible_keys:
            if key in data and isinstance(data[key], list):
                items = data[key]
                for item in items[:20]:  # Limit for evaluation
                    if isinstance(item, dict):
                        # Extract text content for evaluation
                        text_content = (
                            item.get('text') or 
                            item.get('content') or 
                            item.get('description') or
                            item.get('name') or
                            item.get('screen_name') or
                            str(item)
                        )
                        results.append({
                            'text': text_content,
                            'source': f'twitter_api_{key}',
                            'metadata': item
                        })
                break  # Use first list found
        
        # If no list found but data is dict with content
        if not results and isinstance(data, dict) and data:
            # Single result case
            text_content = (
                data.get('text') or 
                data.get('content') or 
                str(data)
            )
            results.append({
                'text': text_content,
                'source': 'twitter_api_single',
                'metadata': data
            })
            
    except Exception as e:
        # If extraction fails, return empty list
        pass
    
    return results


# Test the fix
if __name__ == "__main__":
    # Test various response formats
    test_cases = [
        # Timeline format
        {"data": {"timeline": [{"text": "tweet1"}, {"text": "tweet2"}]}},
        # Results format
        {"data": {"results": [{"content": "result1"}, {"content": "result2"}]}},
        # Followers format
        {"data": {"followers": [{"screen_name": "user1"}, {"screen_name": "user2"}]}},
        # Direct list
        {"data": [{"text": "item1"}, {"text": "item2"}]},
        # Single item
        {"data": {"text": "single tweet"}},
        # Empty
        {"data": {}},
        # Error
        {"error": "API error"},
    ]
    
    print("Testing result count extraction:")
    print("-" * 40)
    for i, test in enumerate(test_cases, 1):
        count = extract_result_count_from_api_response(test)
        print(f"Test {i}: {count} results")
        print(f"  Data: {str(test)[:80]}...")
    
    print("\nTesting result extraction for evaluation:")
    print("-" * 40)
    for i, test in enumerate(test_cases[:3], 1):
        results = extract_results_for_evaluation(test)
        print(f"Test {i}: {len(results)} items extracted")
        if results:
            print(f"  First item: {results[0]['text'][:50]}...")