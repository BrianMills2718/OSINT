#!/usr/bin/env python3
"""
Timeout Behavior Test - Test what happens at different timeout boundaries
Tests GPT-5-mini response times with artificially complex prompts to understand timeout behavior
"""

import os
import time
import json
import statistics
import asyncio
from datetime import datetime
from dotenv import load_dotenv
import litellm
from typing import List, Dict, Any

# Load environment variables
load_dotenv()

MODEL = "gpt-5-mini-2025-08-07"

def get_text(resp):
    """Extract text from responses() API response"""
    texts = []
    for item in resp.output:
        if hasattr(item, "content"):
            for c in item.content:
                if hasattr(c, "text"):
                    texts.append(c.text)
    return "\n".join(texts)

def test_with_timeout(prompt: str, timeout_seconds: int, description: str) -> Dict[str, Any]:
    """Test a prompt with a specific timeout"""
    print(f"Testing: {description} (timeout: {timeout_seconds}s)")
    
    start_time = time.time()
    
    try:
        # Use asyncio to enforce timeout
        async def make_request():
            return litellm.responses(
                model=MODEL,
                input=prompt,
                text={"format": {"type": "text"}},
            )
        
        # Run with timeout
        response = asyncio.run(asyncio.wait_for(make_request(), timeout=timeout_seconds))
        
        end_time = time.time()
        duration = end_time - start_time
        content = get_text(response)
        
        result = {
            "description": description,
            "timeout_seconds": timeout_seconds,
            "actual_duration": duration,
            "success": True,
            "timed_out": False,
            "response_length": len(content),
            "response_preview": content[:200] + "..." if len(content) > 200 else content,
            "timestamp": datetime.now().isoformat()
        }
        
        print(f"✅ Completed in {duration:.2f}s (under {timeout_seconds}s timeout)")
        return result
        
    except asyncio.TimeoutError:
        end_time = time.time()
        duration = end_time - start_time
        
        result = {
            "description": description,
            "timeout_seconds": timeout_seconds,
            "actual_duration": duration,
            "success": False,
            "timed_out": True,
            "error": f"Timeout after {timeout_seconds}s",
            "timestamp": datetime.now().isoformat()
        }
        
        print(f"⏰ Timed out after {duration:.2f}s (timeout: {timeout_seconds}s)")
        return result
        
    except Exception as e:
        end_time = time.time()
        duration = end_time - start_time
        
        result = {
            "description": description,
            "timeout_seconds": timeout_seconds,
            "actual_duration": duration,
            "success": False,
            "timed_out": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }
        
        print(f"❌ Failed in {duration:.2f}s - Error: {e}")
        return result

def get_timeout_test_prompts() -> List[tuple]:
    """Get prompts of varying complexity to test timeout behavior"""
    
    return [
        # Quick prompt - should complete fast
        ("Write 'Hello World' in Python.", 10, "Quick task"),
        
        # Medium prompt - moderate complexity
        ("Write a Python class for a todo list with add, remove, and list methods.", 30, "Medium complexity"),
        
        # Complex prompt - high complexity
        ("""Create a complete Python web application using FastAPI that includes:
1. User authentication with JWT tokens
2. CRUD operations for a blog system
3. Database integration with SQLAlchemy
4. Input validation with Pydantic
5. API documentation with OpenAPI
6. Error handling and logging
7. Unit tests for all endpoints
8. Docker configuration
9. Environment configuration
10. Rate limiting and security middleware

Include complete working code for all components.""", 60, "High complexity - 60s timeout"),
        
        # Very complex prompt - extreme complexity
        ("""Design and implement a complete microservices architecture for an e-commerce platform including:

1. **User Service**: Authentication, authorization, user profiles, JWT tokens
2. **Product Service**: Product catalog, inventory, categories, search
3. **Order Service**: Order processing, workflow, status tracking
4. **Payment Service**: Payment processing, multiple providers, refunds
5. **Notification Service**: Email, SMS, push notifications
6. **Analytics Service**: User behavior, sales metrics, reporting

For each service, provide:
- Complete FastAPI application code
- Database models with SQLAlchemy
- Pydantic schemas for validation
- Docker configuration
- API documentation
- Unit and integration tests
- Error handling and logging
- Service-to-service communication
- Event-driven architecture with message queues
- Monitoring and health checks
- Configuration management
- Security implementation
- Performance optimization
- Deployment scripts

Include inter-service communication patterns, API gateway configuration, database design, message queue setup, monitoring dashboards, and complete deployment documentation.

Provide production-ready code for all components.""", 90, "Extreme complexity - 90s timeout"),
        
        # Impossible prompt - designed to timeout
        ("""Create a complete enterprise software suite including:
1. Full ERP system with 50+ modules
2. Complete CRM with AI recommendations  
3. Advanced analytics platform with ML
4. Real-time collaboration tools
5. Mobile applications for iOS/Android
6. Desktop applications for Windows/Mac/Linux
7. Blockchain integration
8. IoT device management
9. AI/ML pipeline with training
10. Complete DevOps infrastructure
11. Security framework with compliance
12. Internationalization for 20+ languages
13. Accessibility features
14. Performance optimization
15. Complete test suites

Provide complete working code, documentation, deployment guides, and user manuals for everything.""", 120, "Impossible task - 120s timeout"),
    ]

def run_timeout_tests() -> List[Dict[str, Any]]:
    """Run timeout behavior tests"""
    
    test_cases = get_timeout_test_prompts()
    
    print("=" * 80)
    print("⏰ TIMEOUT BEHAVIOR TESTS - GPT-5-MINI")
    print("=" * 80)
    print(f"Model: {MODEL}")
    print(f"Test cases: {len(test_cases)}")
    print()
    
    results = []
    
    for i, (prompt, timeout, description) in enumerate(test_cases, 1):
        print(f"\n[{i}/{len(test_cases)}] ", end="")
        result = test_with_timeout(prompt, timeout, description)
        results.append(result)
        
        # Delay between tests
        time.sleep(3)
    
    return results

def analyze_timeout_results(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze timeout test results"""
    
    successful_results = [r for r in results if r["success"]]
    timed_out_results = [r for r in results if r.get("timed_out", False)]
    failed_results = [r for r in results if not r["success"] and not r.get("timed_out", False)]
    
    analysis = {
        "total_tests": len(results),
        "successful_tests": len(successful_results),
        "timed_out_tests": len(timed_out_results),
        "failed_tests": len(failed_results),
        "success_rate": len(successful_results) / len(results),
        "timeout_rate": len(timed_out_results) / len(results),
        
        "timeout_analysis": {},
        "test_timestamp": datetime.now().isoformat(),
        "model": MODEL
    }
    
    # Analyze by timeout value
    timeout_groups = {}
    for result in results:
        timeout = result["timeout_seconds"]
        if timeout not in timeout_groups:
            timeout_groups[timeout] = []
        timeout_groups[timeout].append(result)
    
    for timeout, group_results in timeout_groups.items():
        successful = [r for r in group_results if r["success"]]
        timed_out = [r for r in group_results if r.get("timed_out", False)]
        
        group_analysis = {
            "total": len(group_results),
            "successful": len(successful),
            "timed_out": len(timed_out),
            "success_rate": len(successful) / len(group_results) if group_results else 0,
        }
        
        if successful:
            durations = [r["actual_duration"] for r in successful]
            group_analysis.update({
                "avg_duration": statistics.mean(durations),
                "max_duration": max(durations),
                "min_duration": min(durations),
            })
        
        analysis["timeout_analysis"][f"{timeout}s"] = group_analysis
    
    # Overall timing for successful requests
    if successful_results:
        durations = [r["actual_duration"] for r in successful_results]
        analysis["successful_timing"] = {
            "min_duration": min(durations),
            "max_duration": max(durations),
            "average_duration": statistics.mean(durations),
            "median_duration": statistics.median(durations),
        }
    
    return analysis

def print_timeout_analysis(analysis: Dict[str, Any]):
    """Print timeout analysis results"""
    
    print("\n" + "=" * 80)
    print("📊 TIMEOUT BEHAVIOR ANALYSIS")
    print("=" * 80)
    
    print(f"Total Tests: {analysis['total_tests']}")
    print(f"Successful: {analysis['successful_tests']}")
    print(f"Timed Out: {analysis['timed_out_tests']}")
    print(f"Failed: {analysis['failed_tests']}")
    print(f"Success Rate: {analysis['success_rate']:.1%}")
    print(f"Timeout Rate: {analysis['timeout_rate']:.1%}")
    
    if "timeout_analysis" in analysis:
        print(f"\n⏰ TIMEOUT ANALYSIS BY DURATION:")
        for timeout_str, data in analysis["timeout_analysis"].items():
            print(f"  {timeout_str:8}: {data['successful']:2}/{data['total']} succeeded, {data['timed_out']:2} timed out")
            if data["successful"] > 0 and "avg_duration" in data:
                print(f"           avg: {data['avg_duration']:5.1f}s, max: {data['max_duration']:5.1f}s")
    
    if "successful_timing" in analysis:
        timing = analysis["successful_timing"]
        print(f"\n⏱️  SUCCESSFUL REQUEST TIMING:")
        print(f"  Min:     {timing['min_duration']:.2f}s")
        print(f"  Max:     {timing['max_duration']:.2f}s")
        print(f"  Average: {timing['average_duration']:.2f}s")
        print(f"  Median:  {timing['median_duration']:.2f}s")
    
    print(f"\n🎯 TIMEOUT RECOMMENDATIONS:")
    
    # Analyze timeout effectiveness
    timeout_effectiveness = []
    for timeout_str, data in analysis.get("timeout_analysis", {}).items():
        timeout_val = int(timeout_str.replace('s', ''))
        if data["total"] > 0:
            success_rate = data["success_rate"]
            timeout_effectiveness.append((timeout_val, success_rate, data))
    
    if timeout_effectiveness:
        print("  Timeout vs Success Rate:")
        for timeout_val, success_rate, data in sorted(timeout_effectiveness):
            status = "✅" if success_rate > 0.8 else "⚠️" if success_rate > 0.5 else "❌"
            print(f"    {timeout_val:3}s: {success_rate:5.1%} success rate {status}")
        
        # Find optimal timeout
        high_success = [t for t, sr, _ in timeout_effectiveness if sr >= 0.8]
        if high_success:
            optimal = min(high_success)
            print(f"\n  💡 Recommended minimum timeout: {optimal}s (for 80%+ success rate)")
        else:
            print(f"\n  ⚠️  No timeout achieved 80%+ success rate - tasks may be too complex")

def save_timeout_results(results: List[Dict[str, Any]], analysis: Dict[str, Any], filename: str):
    """Save timeout results to JSON file"""
    
    output = {
        "test_metadata": {
            "test_type": "timeout_behavior",
            "model": MODEL,
            "timestamp": datetime.now().isoformat(),
            "total_tests": len(results)
        },
        "analysis": analysis,
        "raw_results": results
    }
    
    filepath = f"/home/brian/projects/autocoder4_cc/gpt_5_mini_examples/litellm/timing_tests/results/{filename}"
    
    with open(filepath, 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"\n💾 Results saved to: {filepath}")

def main():
    """Run timeout behavior tests"""
    
    print("Starting timeout behavior tests...")
    
    # Run tests
    results = run_timeout_tests()
    
    # Analyze results
    analysis = analyze_timeout_results(results)
    
    # Print analysis
    print_timeout_analysis(analysis)
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"timeout_behavior_results_{timestamp}.json"
    save_timeout_results(results, analysis, filename)
    
    print("\n✅ Timeout behavior tests completed!")
    
    return results, analysis

if __name__ == "__main__":
    main()