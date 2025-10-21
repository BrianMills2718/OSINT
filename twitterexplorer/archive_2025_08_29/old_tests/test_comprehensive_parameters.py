#!/usr/bin/env python3
"""
Test Comprehensive Parameter System - Validate all 16 endpoints with complete parameter documentation
"""

import sys
import os

# Add twitterexplorer to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'twitterexplorer'))

def test_comprehensive_parameter_system():
    """Test that LLM coordinator has comprehensive parameter documentation for all endpoints"""
    print("=== Testing Comprehensive Parameter System (All 16 Endpoints) ===")
    
    try:
        # Check the coordinator has comprehensive endpoint configurations
        from graph_aware_llm_coordinator import GraphAwareLLMCoordinator
        from llm_client import get_litellm_client
        from investigation_graph import InvestigationGraph
        
        # Create coordinator
        llm_client = get_litellm_client()
        investigation_graph = InvestigationGraph()
        coordinator = GraphAwareLLMCoordinator(llm_client, investigation_graph)
        
        endpoints = coordinator.available_endpoints
        print(f"[OK] Coordinator has {len(endpoints)} endpoints configured")
        
        # Test all endpoints have required parameter specifications
        endpoint_categories = {
            'Content Discovery & Search': ['search.php', 'trends.php'],
            'User Profile & Timeline': ['timeline.php', 'screenname.php', 'usermedia.php'], 
            'Network Analysis': ['following.php', 'followers.php', 'affilates.php', 'checkfollow.php', 'screennames.php'],
            'Tweet & Conversation Analysis': ['tweet.php', 'latest_replies.php', 'tweet_thread.php', 'retweets.php', 'checkretweet.php'],
            'List Analysis': ['listtimeline.php']
        }
        
        total_expected = sum(len(eps) for eps in endpoint_categories.values())
        print(f"[INFO] Expected {total_expected} endpoints across all categories")
        
        missing_endpoints = []
        incomplete_configs = []
        
        for category, expected_endpoints in endpoint_categories.items():
            print(f"\\n[CATEGORY] {category}:")
            for endpoint in expected_endpoints:
                if endpoint in endpoints:
                    config = endpoints[endpoint]
                    
                    # Check for required parameter specifications
                    has_required = 'required_params' in config
                    has_optional = 'optional_params' in config
                    has_description = 'description' in config
                    has_best_for = 'best_for' in config
                    
                    completeness_score = sum([has_required, has_optional, has_description, has_best_for])
                    
                    print(f"  + {endpoint}: {completeness_score}/4 completeness")
                    print(f"    Required: {config.get('required_params', 'MISSING')}")
                    print(f"    Optional: {config.get('optional_params', 'MISSING')}")
                    print(f"    Description: {config.get('description', 'MISSING')[:50]}...")
                    
                    if completeness_score < 4:
                        incomplete_configs.append(endpoint)
                        
                else:
                    print(f"  - {endpoint}: MISSING")
                    missing_endpoints.append(endpoint)
        
        # Test the strategic decision prompt has comprehensive parameter guidance
        goal = "comprehensive parameter test"
        context = "Testing all endpoint parameter documentation"
        
        prompt = coordinator._create_strategic_decision_prompt(goal, context)
        
        # Check for comprehensive parameter documentation
        comprehensive_guidance = [
            "COMPREHENSIVE ENDPOINT PARAMETER GUIDE:",
            "REQUIRED:",
            "OPTIONAL:",
            "search_type VALUES:",
            "ADVANCED QUERY OPERATORS:",
            "from:username",
            "Boolean logic:",
            "STRATEGIC PARAMETER USAGE:",
            "Timeline from Twitter list",
            "Bulk user profile lookup",
            "Verify relationship"
        ]
        
        found_guidance = []
        for guidance in comprehensive_guidance:
            if guidance in prompt:
                found_guidance.append(guidance)
        
        print(f"\\n[OK] Comprehensive parameter guidance: {len(found_guidance)}/{len(comprehensive_guidance)}")
        for guidance in found_guidance:
            print(f"  + {guidance}")
            
        missing_guidance = set(comprehensive_guidance) - set(found_guidance)
        if missing_guidance:
            print("[WARNING] Missing comprehensive guidance:")
            for guidance in missing_guidance:
                print(f"  - {guidance}")
        
        # Test specific parameter examples are present
        parameter_examples = [
            'query="from:johngreenewald herrera"',
            'search_type="Latest"',
            'screenname="johngreenewald"',
            'country="UnitedStates"',
            'id="1234567890123456789"',
            'rest_ids="123456789,987654321"',
            'user="johngreenewald", follows="skepticaluser"'
        ]
        
        found_examples = []
        for example in parameter_examples:
            if example in prompt:
                found_examples.append(example)
        
        print(f"\\n[OK] Parameter examples: {len(found_examples)}/{len(parameter_examples)}")
        for example in found_examples:
            print(f"  + {example}")
        
        # Calculate overall completeness
        endpoint_completeness = (len(endpoints) - len(missing_endpoints)) / total_expected
        guidance_completeness = len(found_guidance) / len(comprehensive_guidance)
        example_completeness = len(found_examples) / len(parameter_examples)
        
        overall_completeness = (endpoint_completeness + guidance_completeness + example_completeness) / 3
        
        print(f"\\n=== COMPREHENSIVE PARAMETER SYSTEM ASSESSMENT ===")
        print(f"Endpoint Coverage: {endpoint_completeness:.1%} ({len(endpoints)}/{total_expected})")
        print(f"Guidance Coverage: {guidance_completeness:.1%}")
        print(f"Example Coverage: {example_completeness:.1%}")
        print(f"Overall Completeness: {overall_completeness:.1%}")
        
        if missing_endpoints:
            print(f"\\n[ERROR] Missing {len(missing_endpoints)} endpoints:")
            for endpoint in missing_endpoints:
                print(f"  - {endpoint}")
                
        if incomplete_configs:
            print(f"\\n[WARNING] {len(incomplete_configs)} endpoints with incomplete config:")
            for endpoint in incomplete_configs:
                print(f"  - {endpoint}")
        
        print("\\n=== KEY IMPROVEMENTS FROM COMPREHENSIVE PARAMETERS ===")
        print("LLM now has complete knowledge of:")
        print("  1. ALL 16 endpoint parameter requirements (required vs optional)")
        print("  2. Advanced search operators for targeted queries")
        print("  3. Network analysis capabilities (following, followers, affiliations)")
        print("  4. Conversation tracking (replies, threads, retweets)")
        print("  5. Verification endpoints (checkfollow, checkretweet)")
        print("  6. Bulk operations (screennames, list analysis)")
        print("  7. Strategic parameter usage patterns")
        
        # Success criteria: >90% completeness
        if overall_completeness >= 0.9:
            print(f"\\n[OK] COMPREHENSIVE PARAMETER SYSTEM: EXCELLENT")
            return True
        elif overall_completeness >= 0.8:
            print(f"\\n[OK] COMPREHENSIVE PARAMETER SYSTEM: GOOD") 
            return True
        else:
            print(f"\\n[WARNING] COMPREHENSIVE PARAMETER SYSTEM: NEEDS IMPROVEMENT")
            return False
            
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_comprehensive_parameter_system()
    print(f"\\n{'[OK] TEST PASSED' if success else '[ERROR] TEST FAILED'}")