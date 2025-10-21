"""Debug LLM responses to understand JSON structure issues"""
import sys
import os
import json

# Setup paths
sys.path.insert(0, 'twitterexplorer')
os.chdir('twitterexplorer')

import litellm
from investigation_prompts import format_coordinator_prompt

# Configure API key
os.environ["GEMINI_API_KEY"] = "AIzaSyAhwSgnnZrVbTECNCXDp1nODEVh3rtoTq8"

def debug_llm_response():
    """Debug actual LLM response structure"""
    
    print("=== DEBUGGING LLM RESPONSES ===")
    
    # Test the coordinator decision prompt
    available_endpoints = {
        'search.php': {
            'description': 'General keyword searches for broad topic exploration',
            'params': ['query', 'result_type'],
            'best_for': 'General topics, keyword exploration, trending content'
        },
        'timeline.php': {
            'description': 'Specific user timeline posts and statements',
            'params': ['screenname', 'count'],
            'best_for': 'Direct statements from specific users/figures'
        }
    }
    
    prompt = format_coordinator_prompt(
        investigation_goal="analyze Trump's recent statements about Epstein",
        current_understanding="Need direct source access",
        information_gaps=["Trump's actual tweets about Epstein"],
        recent_searches=[],
        available_endpoints=available_endpoints,
        failed_strategies=[]
    )
    
    print("PROMPT BEING SENT:")
    print("=" * 60)
    print(prompt)
    print("=" * 60)
    
    try:
        print("\nCalling LLM...")
        response = litellm.completion(
            model="gemini/gemini-2.5-flash",
            messages=[
                {"role": "system", "content": "You are an expert Twitter investigation coordinator. Always return valid JSON."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )
        
        print("\nRAW LLM RESPONSE:")
        print("=" * 60)
        raw_content = response.choices[0].message.content
        print(raw_content)
        print("=" * 60)
        
        print("\nTrying to parse as JSON:")
        try:
            parsed = json.loads(raw_content)
            print("JSON PARSING SUCCESSFUL!")
            print(json.dumps(parsed, indent=2))
            
            # Check for expected fields
            print("\nCHECKING EXPECTED FIELDS:")
            expected_fields = ['endpoint', 'parameters', 'reasoning', 'evaluation_criteria', 'user_update']
            for field in expected_fields:
                if field in parsed:
                    print(f"✅ {field}: {parsed[field]}")
                else:
                    print(f"❌ {field}: MISSING")
            
            # Check for batch format
            if 'searches' in parsed:
                print(f"\n✅ BATCH FORMAT with {len(parsed['searches'])} searches")
                for i, search in enumerate(parsed['searches']):
                    print(f"  Search {i+1}: {search.get('endpoint', 'NO ENDPOINT')} - {search.get('parameters', 'NO PARAMS')}")
            
        except json.JSONDecodeError as e:
            print(f"JSON PARSING FAILED: {e}")
            print("Raw content needs cleaning or format adjustment")
            
            # Try cleaning up the response
            cleaned = raw_content.strip()
            if cleaned.startswith('```json'):
                cleaned = cleaned[7:]
            if cleaned.endswith('```'):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()
            
            print(f"\nTrying with cleaned content:")
            try:
                parsed_cleaned = json.loads(cleaned)
                print("CLEANED JSON PARSING SUCCESSFUL!")
                print(json.dumps(parsed_cleaned, indent=2))
            except json.JSONDecodeError as e2:
                print(f"CLEANED JSON PARSING ALSO FAILED: {e2}")
                
    except Exception as e:
        print(f"LLM CALL FAILED: {e}")

if __name__ == "__main__":
    debug_llm_response()